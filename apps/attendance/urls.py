"""
Attendance URL Configuration.

Routes:
  - /attendance/kiosk/       → Fullscreen kiosk scanning view
  - /attendance/api/scan/    → POST-only face scan API endpoint
"""
from django.urls import path

from apps.attendance.views import AttendanceKioskView, AttendanceScanAPIView

app_name = 'attendance'

urlpatterns = [
    path('kiosk/', AttendanceKioskView.as_view(), name='kiosk'),
    path('api/scan/', AttendanceScanAPIView.as_view(), name='api-scan'),
]
