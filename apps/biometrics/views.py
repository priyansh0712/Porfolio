"""
Biometrics Views — Tenant-Scoped Face Enrollment & Reset (3-Layer Security).

Layer 1: TenantMiddleware (request.tenant)
Layer 2: SchoolAdminRequiredMixin (role-based access)
Layer 3: Queryset scoping (school=request.tenant, pk=pk)

Both endpoints are POST-only AJAX views expecting Content-Type: application/json.
"""
import json
import logging

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from apps.accounts.permissions import SchoolAdminRequiredMixin, FeatureRequiredMixin
from apps.biometrics.services import BiometricService, MAX_PAYLOAD_SIZE_BYTES
from apps.core.ratelimit import rate_limit
from apps.faculty.models import Faculty
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)


@method_decorator(rate_limit(key_prefix='enroll', limit=10, period_seconds=60), name='dispatch')
class FacultyFaceEnrollView(FeatureRequiredMixin, SchoolAdminRequiredMixin, View):
    """
    POST-only AJAX endpoint for face enrollment.
    """
    feature_key = 'faculty_attendance'

    def post(self, request, pk):
        # ── Layer 3: Tenant-scoped faculty lookup ──
        faculty = get_object_or_404(
            Faculty, pk=pk, school=request.tenant
        )

        # ── Content-Type validation ──
        content_type = request.content_type or ''
        if 'application/json' not in content_type:
            return JsonResponse(
                {'success': False, 'error': 'Content-Type must be application/json.'},
                status=400,
            )

        # ── Payload size check ──
        if request.body and len(request.body) > MAX_PAYLOAD_SIZE_BYTES:
            return JsonResponse(
                {'success': False, 'error': 'Request payload too large.'},
                status=400,
            )

        # ── Parse JSON body ──
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse(
                {'success': False, 'error': 'Invalid JSON payload.'},
                status=400,
            )

        frames = data.get('frames')
        if not isinstance(frames, list):
            return JsonResponse(
                {'success': False, 'error': 'Missing or invalid "frames" field.'},
                status=400,
            )

        # ── Delegate to BiometricService ──
        try:
            BiometricService.enroll_faculty_face(
                school=request.tenant,
                faculty=faculty,
                base64_frames=frames,
                user=request.user,
            )
            return JsonResponse({
                'success': True,
                'message': f'Face enrolled successfully for {faculty.full_name}.',
                'is_face_enrolled': True,
            })
        except ValueError as e:
            return JsonResponse(
                {'success': False, 'error': str(e)},
                status=400,
            )
        except Exception as e:
            logger.exception("Unexpected error during face enrollment for faculty %s", pk)
            return JsonResponse(
                {'success': False, 'error': 'An unexpected error occurred. Please try again.'},
                status=500,
            )


class FacultyFaceResetView(FeatureRequiredMixin, SchoolAdminRequiredMixin, View):
    """
    POST-only AJAX endpoint for resetting face biometrics.
    """
    feature_key = 'faculty_attendance'

    def post(self, request, pk):
        # ── Layer 3: Tenant-scoped faculty lookup ──
        faculty = get_object_or_404(
            Faculty, pk=pk, school=request.tenant
        )

        try:
            was_deleted = BiometricService.reset_faculty_face(
                school=request.tenant,
                faculty=faculty,
            )
            message = (
                f'Face biometric removed for {faculty.full_name}.'
                if was_deleted
                else f'No face biometric found for {faculty.full_name}.'
            )
            return JsonResponse({
                'success': True,
                'message': message,
                'is_face_enrolled': False,
            })
        except Exception as e:
            logger.exception("Unexpected error during face reset for faculty %s", pk)
            return JsonResponse(
                {'success': False, 'error': 'An unexpected error occurred.'},
                status=500,
            )
