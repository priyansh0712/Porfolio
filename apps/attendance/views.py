"""
Attendance Views — Kiosk Scanner & Scan API (3-Layer Security).

Layer 1: TenantMiddleware (request.tenant)
Layer 2: SchoolAdminRequiredMixin (role-based access)
Layer 3: Queryset scoping (school=request.tenant)

Contains:
  - AttendanceKioskView: Fullscreen kiosk template for face scanning.
  - AttendanceScanAPIView: POST-only AJAX endpoint processing face vectors.
"""
import json
import logging

from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.permissions import SchoolAdminRequiredMixin
from apps.attendance.services import FaceVectorMatcher, AttendanceStateMachine

from django.utils.decorators import method_decorator
from apps.core.ratelimit import rate_limit

logger = logging.getLogger(__name__)


class AttendanceKioskView(SchoolAdminRequiredMixin, TemplateView):
    """
    Renders the fullscreen attendance scanning kiosk interface.

    Features:
      - Live webcam video stream via getUserMedia API.
      - Real-time clock widget with school tenant badge.
      - Visual status badge overlays (Scanning, Verified, Unrecognized, Cooldown).
      - Web Audio API chime synthesis for audio feedback.
      - Screen Wake Lock API to prevent display sleep.

    Requires School Admin authentication on a valid tenant subdomain.
    """
    template_name = 'attendance/kiosk.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.request.tenant
        return context


class AttendanceScanAPIView(SchoolAdminRequiredMixin, View):
    """
    POST-only AJAX endpoint for processing a face scan vector.

    Expects JSON body: { "vector": [512 floats], "device_info": "optional string" }

    Pipeline:
      1. Validates Content-Type and parses JSON payload.
      2. Passes 512-d vector to FaceVectorMatcher for identification.
      3. Delegates matched faculty to AttendanceStateMachine for state transition.
      4. Returns JSON response with action, faculty info, and status badge data.
    """

    def post(self, request):
        school = request.tenant

        # ── Content-Type validation ──
        content_type = request.content_type or ''
        if 'application/json' not in content_type:
            return JsonResponse(
                {'success': False, 'error': 'Content-Type must be application/json.'},
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

        scan_vector = data.get('vector')
        device_info = data.get('device_info', '')

        if not isinstance(scan_vector, list):
            return JsonResponse(
                {'success': False, 'error': 'Missing or invalid "vector" field.'},
                status=400,
            )

        # ── Step 1: Face Vector Identification ──
        try:
            match_result = FaceVectorMatcher.identify(school, scan_vector)
        except ValueError as e:
            return JsonResponse(
                {'success': False, 'error': str(e)},
                status=400,
            )
        except Exception as e:
            logger.exception("Unexpected error during face identification")
            return JsonResponse(
                {'success': False, 'error': 'Face identification error. Please try again.'},
                status=500,
            )

        if match_result is None:
            return JsonResponse({
                'success': True,
                'recognized': False,
                'action': 'unrecognized',
                'message': 'Face not recognized. Please ensure you are enrolled.',
            })

        faculty, confidence = match_result

        # ── Step 2: Attendance State Machine ──
        try:
            result = AttendanceStateMachine.process_scan(
                school=school,
                faculty=faculty,
                confidence=confidence,
                device_info=device_info[:255] if device_info else '',
            )
        except Exception as e:
            logger.exception("Unexpected error during attendance state processing")
            return JsonResponse(
                {'success': False, 'error': 'Attendance processing error. Please try again.'},
                status=500,
            )

        # ── Build response payload ──
        attendance = result.get('attendance')
        response_data = {
            'success': True,
            'recognized': True,
            'action': result['action'],
            'message': result['message'],
            'faculty': {
                'id': faculty.pk,
                'name': faculty.full_name,
                'employee_code': faculty.employee_code,
                'department': faculty.department,
                'designation': faculty.designation,
            },
            'confidence': round(confidence, 4),
        }

        if result['action'] == 'cooldown':
            response_data['remaining_seconds'] = result.get('remaining_seconds', 0)
            return JsonResponse(response_data, status=429)

        if attendance:
            response_data['attendance'] = {
                'date': str(attendance.date),
                'check_in': attendance.check_in_time.strftime('%H:%M:%S') if attendance.check_in_time else None,
                'check_out': attendance.check_out_time.strftime('%H:%M:%S') if attendance.check_out_time else None,
                'status': attendance.get_status_display(),
            }

        return JsonResponse(response_data)
