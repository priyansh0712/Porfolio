"""
Reports & Dashboard Service Layer — KPI Metrics, Filterable Reports, CSV Exporter, and Correction Pipeline.

Architecture:
  - DashboardService: Aggregates real-time daily attendance metrics (total, present, late, half-day, absent).
  - ReportService: Builds filtered AttendanceLog querysets, generates CSV exports, and executes atomic corrections.
"""
import csv
import io
import logging
from datetime import datetime

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.attendance.models import AttendanceLog
from apps.faculty.models import Faculty
from apps.reports.models import AttendanceCorrection

logger = logging.getLogger(__name__)


class DashboardService:
    """Aggregates real-time KPI metrics for the School Admin Dashboard."""

    @classmethod
    def get_metrics(cls, school):
        """
        Computes today's attendance summary numbers for a school tenant.

        Returns:
            dict: {
                'today': date,
                'total_faculty': int,
                'present_count': int,
                'late_count': int,
                'half_day_count': int,
                'absent_count': int,
                'total_scans': int,
                'live_feed': QuerySet of AttendanceLog,
            }
        """
        today = timezone.localdate()

        # ── 1. Total Active Faculty ──
        total_faculty = Faculty.objects.filter(school=school, is_active=True).count()

        # ── 2. Today's Attendance Logs ──
        today_logs = AttendanceLog.objects.filter(school=school, date=today)

        present_count = today_logs.filter(status=AttendanceLog.Status.PRESENT).count()
        late_count = today_logs.filter(status=AttendanceLog.Status.LATE).count()
        half_day_count = today_logs.filter(status=AttendanceLog.Status.HALF_DAY).count()

        scanned_faculty_ids = set(today_logs.values_list('faculty_id', flat=True))
        absent_count = max(0, total_faculty - len(scanned_faculty_ids))
        total_scans = today_logs.count()

        # ── 3. Live Feed (Most recent scans) ──
        live_feed = today_logs.select_related('faculty').order_by('-last_scan_at')[:25]

        return {
            'today': today,
            'total_faculty': total_faculty,
            'present_count': present_count,
            'late_count': late_count,
            'half_day_count': half_day_count,
            'absent_count': absent_count,
            'total_scans': total_scans,
            'live_feed': live_feed,
        }


class ReportService:
    """Filterable attendance report query engine, CSV generator, and manual correction service."""

    @classmethod
    def get_report_queryset(cls, school, start_date=None, end_date=None, department='', status='', search=''):
        """
        Builds a filtered QuerySet of AttendanceLog records for a school tenant.

        Args:
            school: The School tenant instance.
            start_date: Optional DateField/date (start boundary).
            end_date: Optional DateField/date (end boundary).
            department: Optional str (department filter).
            status: Optional str (status choice filter).
            search: Optional str (name/code search query).

        Returns:
            QuerySet: Filtered AttendanceLog records with select_related('faculty').
        """
        qs = AttendanceLog.objects.filter(school=school).select_related('faculty')

        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        if department:
            qs = qs.filter(faculty__department__iexact=department)
        if status:
            qs = qs.filter(status=status)
        if search:
            qs = qs.filter(
                Q(faculty__first_name__icontains=search) |
                Q(faculty__last_name__icontains=search) |
                Q(faculty__employee_code__icontains=search)
            )

        return qs.order_by('-date', '-check_in_time')

    @classmethod
    def generate_csv(cls, school, queryset):
        """
        Generates CSV file content string for a queryset of AttendanceLog records.

        Returns:
            str: Full CSV output string.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Write Header
        writer.writerow([
            'Date', 'Employee Code', 'Faculty Name', 'Department',
            'Designation', 'Check In', 'Check Out', 'Duration (Hours)',
            'Status', 'Early Departure', 'Corrections Count',
        ])

        for log in queryset:
            duration_str = ''
            if log.duration:
                hours = log.duration.total_seconds() / 3600.0
                duration_str = f"{hours:.2f}"

            check_in_str = log.check_in_time.strftime('%H:%M:%S') if log.check_in_time else ''
            check_out_str = log.check_out_time.strftime('%H:%M:%S') if log.check_out_time else ''

            writer.writerow([
                str(log.date),
                log.faculty.employee_code,
                log.faculty.full_name,
                log.faculty.department,
                log.faculty.designation,
                check_in_str,
                check_out_str,
                duration_str,
                log.get_status_display(),
                'Yes' if getattr(log, 'early_departure', False) else 'No',
                log.corrections.count(),
            ])

        return output.getvalue()

    @classmethod
    @transaction.atomic
    def correct_attendance(cls, school, admin_user, attendance, new_status, new_check_in=None, new_check_out=None, reason=''):
        """
        Executes a manual attendance record correction with immutable audit trail.

        Args:
            school: The School tenant instance.
            admin_user: The User (School Admin) performing the correction.
            attendance: The AttendanceLog instance to correct.
            new_status: String choice (PRESENT, LATE, HALF_DAY, etc.).
            new_check_in: Optional new check-in DateTime.
            new_check_out: Optional new check-out DateTime.
            reason: Mandatory non-empty explanation string.

        Returns:
            AttendanceCorrection instance created.

        Raises:
            ValueError: If reason is empty or invalid.
        """
        if not reason or not reason.strip():
            raise ValueError("A mandatory explanation reason must be provided for manual corrections.")

        reason = reason.strip()

        # Capture old state before modification
        old_status = attendance.status
        old_check_in = attendance.check_in_time
        old_check_out = attendance.check_out_time

        # Create immutable audit log entry
        correction = AttendanceCorrection.objects.create(
            school=school,
            attendance=attendance,
            performed_by=admin_user,
            old_status=old_status,
            new_status=new_status,
            old_check_in_time=old_check_in,
            new_check_in_time=new_check_in or old_check_in,
            old_check_out_time=old_check_out,
            new_check_out_time=new_check_out or old_check_out,
            reason=reason,
        )

        # Apply changes to AttendanceLog
        attendance.status = new_status
        if new_check_in:
            attendance.check_in_time = new_check_in
        if new_check_out:
            attendance.check_out_time = new_check_out
        attendance.save()

        logger.info(
            "Manual Attendance Correction applied to %s (Date %s) by %s: %s → %s (Reason: %s)",
            attendance.faculty.full_name, attendance.date, admin_user.email,
            old_status, new_status, reason,
        )

        return correction
