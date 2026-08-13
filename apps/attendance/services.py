"""
Attendance Service Layer — Face Vector Matching & State Machine Engine.

Contains:
  - FaceVectorMatcher: Cosine distance comparison of incoming 512-d scan vector
    against all enrolled tenant faculty biometric vectors.
  - AttendanceStateMachine: Check-In / Check-Out state transition engine with
    30-second server-side cooldown lock and select_for_update concurrency guard.

Architecture:
  Scan Vector (512 floats)
    → NumPy dot product matrix multiplication (V_scan · V_tenant^T)
    → Cosine Distance thresholding (≤ 0.40 = match)
    → State Machine evaluation (Check-In / Check-Out / Update)
    → AttendanceLog DB write with atomic locking

Security:
  - Tenant isolation: Only queries FacultyBiometric within request.tenant.
  - 30-second cooldown: Rejects rapid duplicate scans per faculty member.
  - select_for_update: Prevents race conditions during concurrent frame scans.
"""
import logging
from datetime import timedelta

import numpy as np
from django.db import transaction
from django.utils import timezone

from apps.attendance.models import AttendanceLog
from apps.biometrics.models import FacultyBiometric

logger = logging.getLogger(__name__)

# ── Matching Thresholds ──
# ArcFace 512-d Cosine Distance threshold for positive identification.
# Distance ≤ 0.40 corresponds to Cosine Similarity ≥ 0.60.
COSINE_DISTANCE_THRESHOLD = 0.40

# ── Scan Cooldown ──
# Minimum seconds between consecutive scans for the same faculty member.
SCAN_COOLDOWN_SECONDS = 30


class FaceVectorMatcher:
    """
    Identifies a faculty member by comparing an incoming 512-d face vector
    against all enrolled biometric vectors within the given tenant school.

    Uses NumPy dot product for efficient batch cosine similarity calculation.
    All enrolled vectors are pre-normalized to ||V|| = 1.0 during Phase 6
    enrollment, so dot product equals cosine similarity directly.
    """

    @staticmethod
    def identify(school, scan_vector):
        """
        Match a scan vector against all enrolled tenant faculty vectors.

        Args:
            school: The School tenant instance (for tenant isolation).
            scan_vector: List of 512 float values from webcam face detection.

        Returns:
            tuple: (Faculty instance, cosine_similarity_score) if match found.
            None: If no match exceeds the threshold.

        Raises:
            ValueError: If scan_vector is not a valid 512-element float list.
        """
        # ── Validate incoming vector ──
        if not isinstance(scan_vector, (list, tuple)) or len(scan_vector) != 512:
            raise ValueError(
                f"Scan vector must be a list of 512 floats, "
                f"got {type(scan_vector).__name__} with length {len(scan_vector) if hasattr(scan_vector, '__len__') else 'N/A'}."
            )

        try:
            scan_np = np.array(scan_vector, dtype=np.float64)
        except (TypeError, ValueError):
            raise ValueError("Scan vector contains non-numeric values.")

        # ── L2-normalize the incoming scan vector ──
        norm = np.linalg.norm(scan_np)
        if norm == 0:
            raise ValueError("Scan vector has zero magnitude — invalid face embedding.")
        scan_np = scan_np / norm

        # ── Load all enrolled biometrics for this tenant ──
        biometrics = list(
            FacultyBiometric.objects.filter(
                school=school,
            ).select_related('faculty').only(
                'embedding', 'faculty__id', 'faculty__first_name',
                'faculty__last_name', 'faculty__employee_code',
                'faculty__is_active',
            )
        )

        if not biometrics:
            logger.info("No enrolled biometrics found for school %s", school.subdomain)
            return None

        # ── Build vector matrix and compute dot product similarities ──
        # Each enrolled vector is already L2-normalized from enrollment.
        enrolled_vectors = np.array(
            [b.embedding for b in biometrics], dtype=np.float64
        )

        # Matrix dot product: (N, 512) · (512,) → (N,) similarities
        similarities = enrolled_vectors @ scan_np

        # ── Find best match ──
        best_idx = int(np.argmax(similarities))
        best_similarity = float(similarities[best_idx])
        best_distance = 1.0 - best_similarity

        if best_distance > COSINE_DISTANCE_THRESHOLD:
            logger.info(
                "No match: best distance %.4f exceeds threshold %.4f (school: %s)",
                best_distance, COSINE_DISTANCE_THRESHOLD, school.subdomain,
            )
            return None

        matched_biometric = biometrics[best_idx]
        faculty = matched_biometric.faculty

        # ── Reject inactive faculty ──
        if not faculty.is_active:
            logger.warning(
                "Matched inactive faculty %s (ID: %s, score: %.4f). Rejecting scan.",
                faculty.full_name, faculty.pk, best_similarity,
            )
            return None

        logger.info(
            "Matched faculty %s (ID: %s) with similarity %.4f (distance: %.4f)",
            faculty.full_name, faculty.pk, best_similarity, best_distance,
        )

        return (faculty, best_similarity)


class AttendanceStateMachine:
    """
    Processes a verified face match into an attendance state transition.

    State Rules (per calendar date):
      1. No record today → Create AttendanceLog with check_in_time.
      2. Record exists, no check_out → Set check_out_time.
      3. Record exists, has check_out → Update check_out_time to latest.

    Cooldown: Rejects scans within 30 seconds of the previous scan
    for the same faculty member (HTTP 429 equivalent).

    Concurrency: Uses select_for_update() to prevent race conditions
    when multiple camera frames hit the API simultaneously.
    """

    @staticmethod
    @transaction.atomic
    def process_scan(school, faculty, confidence, device_info=''):
        """
        Process a verified face scan into an attendance state transition.

        Args:
            school: The School tenant instance.
            faculty: The matched Faculty instance.
            confidence: Cosine similarity score (float).
            device_info: Browser User-Agent string for audit.

        Returns:
            dict: {
                'action': 'check_in' | 'check_out' | 'updated' | 'cooldown',
                'attendance': AttendanceLog instance (or None for cooldown),
                'message': Human-readable status message,
            }
        """
        now = timezone.now()
        today = timezone.localdate()

        # ── Attempt to lock existing record for this faculty + today ──
        try:
            existing = (
                AttendanceLog.objects
                .select_for_update()
                .get(school=school, faculty=faculty, date=today)
            )
        except AttendanceLog.DoesNotExist:
            existing = None

        # ── Cooldown check ──
        if existing and existing.last_scan_at:
            elapsed = (now - existing.last_scan_at).total_seconds()
            if elapsed < SCAN_COOLDOWN_SECONDS:
                remaining = int(SCAN_COOLDOWN_SECONDS - elapsed)
                logger.info(
                    "Cooldown lock: %s scanned %.1fs ago (remaining: %ds)",
                    faculty.full_name, elapsed, remaining,
                )
                return {
                    'action': 'cooldown',
                    'attendance': existing,
                    'message': (
                        f"Please wait {remaining} seconds before scanning again."
                    ),
                    'remaining_seconds': remaining,
                }

        from apps.schedules.calculator import PunctualityCalculator

        if existing is None:
            # ── State 1: First scan of day → Check-In ──
            calc = PunctualityCalculator.calculate_status(
                school=school, date=today, check_in_time=now,
            )
            attendance = AttendanceLog.objects.create(
                school=school,
                faculty=faculty,
                date=today,
                check_in_time=now,
                last_scan_at=now,
                status=calc['status'],
                early_departure=calc['early_departure'],
                match_confidence=confidence,
                device_info=device_info,
            )
            logger.info("CHECK-IN: %s at %s (%s)", faculty.full_name, now.strftime('%H:%M:%S'), calc['status'])
            return {
                'action': 'check_in',
                'attendance': attendance,
                'message': f"Good morning, {faculty.first_name}! Check-in recorded ({attendance.get_status_display()}).",
            }

        elif not existing.has_checked_out:
            # ── State 2: Second scan → Check-Out ──
            existing.check_out_time = now
            existing.last_scan_at = now
            existing.match_confidence = max(existing.match_confidence, confidence)

            calc = PunctualityCalculator.calculate_status(
                school=school, date=today,
                check_in_time=existing.check_in_time,
                check_out_time=now,
            )
            existing.status = calc['status']
            existing.early_departure = calc['early_departure']

            existing.save(update_fields=[
                'check_out_time', 'last_scan_at', 'status',
                'early_departure', 'match_confidence', 'updated_at',
            ])
            logger.info("CHECK-OUT: %s at %s", faculty.full_name, now.strftime('%H:%M:%S'))
            return {
                'action': 'check_out',
                'attendance': existing,
                'message': f"Goodbye, {faculty.first_name}! Check-out recorded.",
            }

        else:
            # ── State 3: Subsequent scan → Update Check-Out ──
            existing.check_out_time = now
            existing.last_scan_at = now
            existing.match_confidence = max(existing.match_confidence, confidence)

            calc = PunctualityCalculator.calculate_status(
                school=school, date=today,
                check_in_time=existing.check_in_time,
                check_out_time=now,
            )
            existing.status = calc['status']
            existing.early_departure = calc['early_departure']

            existing.save(update_fields=[
                'check_out_time', 'last_scan_at', 'status',
                'early_departure', 'match_confidence', 'updated_at',
            ])
            logger.info(
                "CHECK-OUT UPDATED: %s at %s", faculty.full_name, now.strftime('%H:%M:%S')
            )
            return {
                'action': 'updated',
                'attendance': existing,
                'message': f"Check-out time updated for {faculty.first_name}.",
            }
