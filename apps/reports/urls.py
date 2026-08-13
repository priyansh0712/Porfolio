"""
Reports & Dashboard URL Configuration.

Routes:
  - /dashboard/          → AdminDashboardView (Main Admin Dashboard)
  - /reports/            → AttendanceReportView (Filterable Reports Table)
  - /reports/export/csv/ → AttendanceExportCSVView (Downloadable CSV)
  - /reports/correct/<pk>/ → AttendanceCorrectView (Manual Attendance Correction)
"""
from django.urls import path

from apps.reports.views import (
    AdminDashboardView, AttendanceReportView,
    AttendanceExportCSVView, AttendanceCorrectView,
)

app_name = 'reports'

urlpatterns = [
    path('dashboard/', AdminDashboardView.as_view(), name='dashboard'),
    path('reports/', AttendanceReportView.as_view(), name='report-list'),
    path('reports/export/csv/', AttendanceExportCSVView.as_view(), name='export-csv'),
    path('reports/correct/<int:pk>/', AttendanceCorrectView.as_view(), name='correct'),
]
