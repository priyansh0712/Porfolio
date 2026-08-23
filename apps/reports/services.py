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
    """
    Modular, feature-aware KPI metrics and activity aggregation for School Overview Dashboard.
    Ensures ZERO unnecessary DB queries for disabled modules.
    """

    @classmethod
    def get_metrics(cls, school):
        """
        Master aggregator method for Principal Dashboard.
        Inspects enabled features and conditionally calls modular service methods.
        """
        from apps.tenants.features import FeatureService
        features = FeatureService.get_school_features(school)
        today = timezone.localdate()

        context = {
            'today': today,
            'features': features,
        }

        # ── 1. Top-Level Neutral Metrics (Always queried) ──
        top_metrics = cls.get_top_level_metrics(school)
        context.update(top_metrics)

        # ── 2. Today's Faculty Attendance Snapshot (ONLY if faculty_attendance is enabled) ──
        if features.get('faculty_attendance', False):
            context.update(cls.get_faculty_attendance_metrics(school, today, top_metrics.get('total_faculty', 0)))
        else:
            context.update({
                'present_count': 0,
                'late_count': 0,
                'half_day_count': 0,
                'leave_count': 0,
                'absent_count': 0,
                'total_scans': 0,
                'live_feed': [],
                'punctuality_rate': 0,
                'donut_present_dash': 0,
                'donut_late_dash': 0,
                'donut_late_offset': 0,
            })

        # ── 3. Today's Leaves Snapshot (ONLY if faculty_leave is enabled) ──
        if features.get('faculty_leave', False):
            context.update(cls.get_leaves_metrics(school, today))
        else:
            context.update({
                'pending_leaves_count': 0,
                'approved_leaves_today': 0,
            })

        # ── 4. Academic Snapshot Metrics (ONLY if academics is enabled) ──
        if features.get('academics', True):
            context.update(cls.get_academic_metrics(school, top_metrics.get('current_academic_year')))
        else:
            context.update({
                'standards_count': 0,
                'divisions_count': 0,
                'subjects_count': 0,
                'allocated_teachers_count': 0,
            })

        # ── 5. Needs Your Attention Actionable Items (Evaluates enabled features only) ──
        context['attention_items'] = cls.get_attention_items(school, features, top_metrics.get('current_academic_year'))

        # ── 6. Recent Activity Feed (Multi-source, only from enabled modules) ──
        context['recent_activities'] = cls.get_recent_activity(school, features)

        return context

    @classmethod
    def get_top_level_metrics(cls, school):
        """Universal school-level KPI metrics that do NOT depend on attendance."""
        from apps.students.models import Student
        from apps.faculty.models import Faculty
        from apps.academics.models import Division
        from apps.academics.services import AcademicService

        total_students = Student.objects.filter(school=school, is_active=True).count()
        total_faculty = Faculty.objects.filter(school=school, is_active=True).count()
        total_classes = Division.objects.filter(school=school, is_active=True).count()
        current_academic_year = AcademicService.get_current_academic_year(school)

        return {
            'total_students': total_students,
            'total_faculty': total_faculty,
            'total_classes': total_classes,
            'current_academic_year': current_academic_year,
            'academic_year_name': current_academic_year.name if current_academic_year else 'Not Configured',
        }

    @classmethod
    def get_faculty_attendance_metrics(cls, school, today, total_faculty):
        """Attendance stats and live feed — executed ONLY when faculty_attendance is enabled."""
        today_logs = AttendanceLog.objects.filter(school=school, date=today)

        present_count = today_logs.filter(status=AttendanceLog.Status.PRESENT).count()
        late_count = today_logs.filter(status=AttendanceLog.Status.LATE).count()
        half_day_count = today_logs.filter(status=AttendanceLog.Status.HALF_DAY).count()
        leave_count = today_logs.filter(status=AttendanceLog.Status.LEAVE).count()

        scanned_faculty_ids = set(today_logs.values_list('faculty_id', flat=True))
        absent_count = max(0, total_faculty - len(scanned_faculty_ids))
        total_scans = today_logs.exclude(status=AttendanceLog.Status.LEAVE).count()

        live_feed = today_logs.select_related('faculty').order_by('-last_scan_at')[:15]

        total_checked_in = present_count + late_count + half_day_count
        if total_checked_in > 0:
            punctuality_rate = round((present_count / total_checked_in) * 100)
        elif present_count > 0:
            punctuality_rate = 100
        else:
            punctuality_rate = 0 if total_faculty > 0 else 100

        if total_faculty > 0:
            donut_present_dash = round((present_count / total_faculty) * 100)
            donut_late_dash = round((late_count / total_faculty) * 100)
        else:
            donut_present_dash = 0
            donut_late_dash = 0

        donut_late_offset = -donut_present_dash

        return {
            'present_count': present_count,
            'late_count': late_count,
            'half_day_count': half_day_count,
            'leave_count': leave_count,
            'absent_count': absent_count,
            'total_scans': total_scans,
            'live_feed': live_feed,
            'punctuality_rate': punctuality_rate,
            'donut_present_dash': donut_present_dash,
            'donut_late_dash': donut_late_dash,
            'donut_late_offset': donut_late_offset,
        }

    @classmethod
    def get_leaves_metrics(cls, school, today):
        """Staff leave metrics — executed ONLY when faculty_leave is enabled."""
        from apps.leaves.models import LeaveRequest

        pending_leaves_count = LeaveRequest.objects.filter(
            school=school, status=LeaveRequest.Status.PENDING
        ).count()
        approved_leaves_today = LeaveRequest.objects.filter(
            school=school,
            status=LeaveRequest.Status.APPROVED,
            from_date__lte=today,
            to_date__gte=today,
        ).count()

        return {
            'pending_leaves_count': pending_leaves_count,
            'approved_leaves_today': approved_leaves_today,
        }

    @classmethod
    def get_academic_metrics(cls, school, current_year=None):
        """Academic structure stats — executed ONLY when academics is enabled."""
        from apps.academics.models import Standard, Division, Subject, ClassTeacherAllocation

        standards_count = Standard.objects.filter(school=school, is_active=True).count()
        divisions_count = Division.objects.filter(school=school, is_active=True).count()
        subjects_count = Subject.objects.filter(school=school, is_active=True).count()

        allocated_teachers_count = 0
        if current_year:
            allocated_teachers_count = ClassTeacherAllocation.objects.filter(
                school=school, academic_year=current_year
            ).count()

        return {
            'standards_count': standards_count,
            'divisions_count': divisions_count,
            'subjects_count': subjects_count,
            'allocated_teachers_count': allocated_teachers_count,
        }

    @classmethod
    def get_attention_items(cls, school, features, current_year=None):
        """
        Builds a prioritized list of actionable items for enabled modules.
        Returns a list of dicts.
        """
        from django.urls import reverse
        items = []

        # 1. Pending Leave Requests
        if features.get('faculty_leave', False):
            from apps.leaves.models import LeaveRequest
            pending_leaves = LeaveRequest.objects.filter(
                school=school, status=LeaveRequest.Status.PENDING
            ).count()
            if pending_leaves > 0:
                items.append({
                    'id': 'leaves',
                    'title': 'Leave Requests',
                    'count': pending_leaves,
                    'description': f"{pending_leaves} staff leave request{'s' if pending_leaves > 1 else ''} awaiting your review",
                    'url': reverse('leaves:admin_requests'),
                    'urgency': 'high',
                    'badge_color': 'amber',
                })

        # 2. Pending Student Transfer Requests
        if features.get('students', False):
            from apps.students.models import StudentTransferRequest
            pending_transfers = StudentTransferRequest.objects.filter(
                school=school, status=StudentTransferRequest.Status.PENDING
            ).count()
            if pending_transfers > 0:
                items.append({
                    'id': 'transfers',
                    'title': 'Student Transfer Requests',
                    'count': pending_transfers,
                    'description': f"{pending_transfers} division transfer request{'s' if pending_transfers > 1 else ''} awaiting approval",
                    'url': f"{reverse('students:hub')}?tab=transfers",
                    'urgency': 'medium',
                    'badge_color': 'blue',
                })

        # 3. Academics: Unassigned Class Teachers or Missing Year
        if features.get('academics', False):
            from apps.academics.models import Division, ClassTeacherAllocation
            if current_year:
                total_divs = Division.objects.filter(school=school, is_active=True).count()
                assigned_divs = ClassTeacherAllocation.objects.filter(
                    school=school, academic_year=current_year
                ).values('division').distinct().count()
                unassigned = max(0, total_divs - assigned_divs)
                if unassigned > 0:
                    items.append({
                        'id': 'class_teachers',
                        'title': 'Class Teacher Allocation',
                        'count': unassigned,
                        'description': f"{unassigned} class section{'s' if unassigned > 1 else ''} need a class teacher assigned",
                        'url': f"{reverse('academics:hub')}?tab=classes",
                        'urgency': 'medium',
                        'badge_color': 'purple',
                    })
            else:
                items.append({
                    'id': 'missing_year',
                    'title': 'Academic Setup',
                    'count': 1,
                    'description': 'No active academic year configured for this school',
                    'url': f"{reverse('academics:hub')}?tab=years",
                    'urgency': 'high',
                    'badge_color': 'rose',
                })

        # 4. Biometric Face Enrollment (Only if faculty_attendance is enabled)
        if features.get('faculty_attendance', False):
            from apps.faculty.models import Faculty
            unenrolled = Faculty.objects.filter(
                school=school, is_active=True, is_face_enrolled=False
            ).count()
            if unenrolled > 0:
                items.append({
                    'id': 'biometrics',
                    'title': 'Faculty Biometrics',
                    'count': unenrolled,
                    'description': f"{unenrolled} active faculty member{'s' if unenrolled > 1 else ''} pending Face ID registration",
                    'url': reverse('faculty:list'),
                    'urgency': 'low',
                    'badge_color': 'gray',
                })

        return items

    @classmethod
    def get_recent_activity(cls, school, features):
        """
        Aggregates recent actual activity logs from enabled modules.
        Returns up to 8 recent items sorted by timestamp desc.
        """
        from django.urls import reverse
        activities = []

        # 1. Recent Leaves
        if features.get('faculty_leave', False):
            from apps.leaves.models import LeaveRequest
            recent_leaves = LeaveRequest.objects.filter(school=school).select_related('faculty').order_by('-created_at')[:4]
            for lr in recent_leaves:
                activities.append({
                    'title': f"{lr.faculty.full_name} submitted a leave request",
                    'detail': f"{lr.get_leave_type_display()} ({lr.from_date.strftime('%b %d')} - {lr.to_date.strftime('%b %d')})",
                    'status': lr.get_status_display(),
                    'timestamp': lr.created_at,
                    'url': reverse('leaves:admin_requests'),
                    'module': 'Leaves',
                    'icon': 'leaves',
                })

        # 2. Recent Student Transfers
        if features.get('students', False):
            from apps.students.models import StudentTransferRequest
            recent_transfers = StudentTransferRequest.objects.filter(school=school).select_related('student', 'to_standard', 'to_division').order_by('-created_at')[:4]
            for tr in recent_transfers:
                activities.append({
                    'title': f"Transfer requested for {tr.student.full_name}",
                    'detail': f"To {tr.to_standard.name} - {tr.to_division.name}",
                    'status': tr.get_status_display(),
                    'timestamp': tr.created_at,
                    'url': f"{reverse('students:hub')}?tab=transfers",
                    'module': 'Students',
                    'icon': 'students',
                })

        # 3. Recent Attendance Check-ins (ONLY if faculty_attendance is enabled)
        if features.get('faculty_attendance', False):
            recent_scans = AttendanceLog.objects.filter(school=school).select_related('faculty').order_by('-created_at')[:4]
            for log in recent_scans:
                time_str = log.check_in_time.strftime('%I:%M %p') if log.check_in_time else ''
                activities.append({
                    'title': f"{log.faculty.full_name} recorded attendance",
                    'detail': f"{log.get_status_display()} at {time_str}" if time_str else log.get_status_display(),
                    'status': log.get_status_display(),
                    'timestamp': log.created_at,
                    'url': reverse('reports:report-list'),
                    'module': 'Attendance',
                    'icon': 'attendance',
                })

        # 4. Recent Student Enrollments
        if features.get('students', False):
            from apps.students.models import Student
            recent_students = Student.objects.filter(school=school, is_active=True).select_related('standard', 'division').order_by('-created_at')[:3]
            for st in recent_students:
                activities.append({
                    'title': f"New student enrolled: {st.full_name}",
                    'detail': f"GR #{st.gr_number} • {st.standard.name} {st.division.name}",
                    'status': 'Active',
                    'timestamp': st.created_at,
                    'url': reverse('students:hub'),
                    'module': 'Students',
                    'icon': 'students',
                })

        # Sort all aggregated activities by timestamp descending
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return activities[:8]


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
        qs = AttendanceLog.objects.filter(school=school).select_related('faculty').prefetch_related('corrections')

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

            from django.utils import timezone
            local_in = timezone.localtime(log.check_in_time) if log.check_in_time else None
            local_out = timezone.localtime(log.check_out_time) if log.check_out_time else None

            check_in_str = local_in.strftime('%H:%M:%S') if local_in else ''
            check_out_str = local_out.strftime('%H:%M:%S') if local_out else ''

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
