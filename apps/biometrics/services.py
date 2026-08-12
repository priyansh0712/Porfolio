"""
Biometrics Service Layer — Zero-Raw-Photo Face Vector Pipeline.

Architecture:
  Browser Webcam (3 JPEG base64 frames)
    → In-Memory Decode (cv2.imdecode, RAM only)
    → InsightFace ArcFace 512-d Extraction
    → Instant Raw Byte Destruction (del + gc.collect)
    → Element-wise Mean Averaging + L2 Normalization
    → PostgreSQL JSONB Storage (FacultyBiometric)

Security:
  - Strict 3-frame payload validation (no more, no less).
  - Single-face constraint per frame (reject 0 or >1 faces).
  - Minimum face bounding box size check (>= 120x120 px).
  - Max payload size limit (5MB total).
  - Atomic transaction for DB writes.
"""
import base64
import gc
import logging

import cv2
import numpy as np
from django.db import transaction

logger = logging.getLogger(__name__)

# Maximum total payload size for biometric enrollment (5MB)
MAX_PAYLOAD_SIZE_BYTES = 5 * 1024 * 1024

# Required number of frames for multi-frame sampling
REQUIRED_FRAME_COUNT = 3

# Minimum face bounding box dimension (pixels)
MIN_FACE_SIZE = 120


class BiometricService:
    """
    Service class for face enrollment and reset operations.

    Uses a process-level lazy singleton for InsightFace model initialization.
    Acceptable for local dev and single-worker execution.

    Note: Multi-worker Gunicorn deployments will load model weights per worker
    process (~300MB RAM each). Standalone microservice / shared worker memory
    architecture is deferred to production deployment phase.
    """
    _app = None

    @classmethod
    def get_face_analyzer(cls):
        """
        Lazy singleton initialization of InsightFace ArcFace model.

        Uses CPU-only ONNX runtime. Model weights loaded once per process.
        """
        if cls._app is None:
            from insightface.app import FaceAnalysis
            cls._app = FaceAnalysis(
                name='buffalo_l',
                providers=['CPUExecutionProvider'],
            )
            cls._app.prepare(ctx_id=0, det_size=(640, 640))
            logger.info("InsightFace ArcFace model initialized (buffalo_l, CPU).")
        return cls._app

    @classmethod
    def decode_base64_frame(cls, base64_str):
        """
        Decodes a base64 image string into a NumPy BGR image in RAM.

        Strips data URI prefix if present. Validates base64 format.
        Returns decoded OpenCV image array. Clears raw byte buffer immediately.

        Raises:
            ValueError: If base64 string is invalid or image cannot be decoded.
        """
        try:
            if ',' in base64_str:
                base64_str = base64_str.split(',', 1)[1]
            img_bytes = base64.b64decode(base64_str)
        except Exception:
            raise ValueError("Invalid base64 image data.")

        if len(img_bytes) > MAX_PAYLOAD_SIZE_BYTES:
            del img_bytes
            raise ValueError("Individual frame exceeds maximum allowed size.")

        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Destroy raw byte buffers from RAM immediately
        del img_bytes, nparr

        if img is None:
            raise ValueError("Could not decode image. Unsupported or corrupted image format.")

        return img

    @classmethod
    @transaction.atomic
    def enroll_faculty_face(cls, school, faculty, base64_frames, user=None):
        """
        Processes 3 frames in RAM, extracts & averages 512-d ArcFace vectors,
        saves FacultyBiometric JSONB, and sets faculty.is_face_enrolled = True.

        Args:
            school: The School tenant instance.
            faculty: The Faculty instance to enroll.
            base64_frames: List of exactly 3 base64-encoded JPEG strings.
            user: Optional User who performed enrollment (for audit trail).

        Returns:
            FacultyBiometric instance (created or updated).

        Raises:
            ValueError: On frame count mismatch, no face, multiple faces,
                        face too small, or invalid image data.
        """
        # ── Strict frame count validation ──
        if not isinstance(base64_frames, list):
            raise ValueError("Frames must be provided as a list.")
        if len(base64_frames) != REQUIRED_FRAME_COUNT:
            raise ValueError(
                f"Exactly {REQUIRED_FRAME_COUNT} frames required, "
                f"but {len(base64_frames)} received."
            )

        # ── Total payload size check ──
        total_size = sum(len(f.encode('utf-8')) if isinstance(f, str) else len(f) for f in base64_frames)
        if total_size > MAX_PAYLOAD_SIZE_BYTES:
            raise ValueError(
                f"Total payload size ({total_size} bytes) exceeds "
                f"maximum allowed ({MAX_PAYLOAD_SIZE_BYTES} bytes)."
            )

        analyzer = cls.get_face_analyzer()
        embeddings = []

        for idx, b64_frame in enumerate(base64_frames, start=1):
            if not isinstance(b64_frame, str) or not b64_frame.strip():
                raise ValueError(f"Frame {idx}: Empty or invalid frame data.")

            img = cls.decode_base64_frame(b64_frame)
            try:
                faces = analyzer.get(img)

                if len(faces) == 0:
                    raise ValueError(
                        f"Frame {idx}: No face detected. "
                        "Please face the camera clearly."
                    )
                if len(faces) > 1:
                    raise ValueError(
                        f"Frame {idx}: Multiple faces detected ({len(faces)}). "
                        "Please ensure only one person is in frame."
                    )

                face = faces[0]
                bbox = face.bbox.astype(int)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
                    raise ValueError(
                        f"Frame {idx}: Face is too small ({w}x{h}px). "
                        f"Minimum size is {MIN_FACE_SIZE}x{MIN_FACE_SIZE}px. "
                        "Please move closer to the camera."
                    )

                embeddings.append(face.embedding)
            finally:
                # Destroy frame image from RAM immediately
                del img
                gc.collect()

        # ── Multi-frame averaging & L2 normalization ──
        avg_emb = np.mean(embeddings, axis=0)
        norm = np.linalg.norm(avg_emb)
        if norm == 0:
            raise ValueError("Failed to compute valid face vector. Please try again.")
        normalized_vector = (avg_emb / norm).tolist()

        # ── Save to DB (create or update) ──
        from apps.biometrics.models import FacultyBiometric
        biometric, _created = FacultyBiometric.objects.update_or_create(
            school=school,
            faculty=faculty,
            defaults={
                'embedding': normalized_vector,
                'enrolled_by': user,
            },
        )

        # ── Sync Faculty enrollment status ──
        faculty.is_face_enrolled = True
        faculty.save(update_fields=['is_face_enrolled'])

        logger.info(
            "Face enrolled for %s (ID: %s) by %s",
            faculty.full_name, faculty.pk,
            user.email if user else 'system',
        )

        return biometric

    @classmethod
    @transaction.atomic
    def reset_faculty_face(cls, school, faculty):
        """
        Removes face biometric data and resets enrollment status.

        Args:
            school: The School tenant instance.
            faculty: The Faculty instance to reset.

        Returns:
            True if biometric was deleted, False if none existed.
        """
        from apps.biometrics.models import FacultyBiometric

        deleted_count, _ = FacultyBiometric.objects.filter(
            school=school,
            faculty=faculty,
        ).delete()

        faculty.is_face_enrolled = False
        faculty.save(update_fields=['is_face_enrolled'])

        logger.info(
            "Face biometric reset for %s (ID: %s). Records deleted: %d",
            faculty.full_name, faculty.pk, deleted_count,
        )

        return deleted_count > 0
