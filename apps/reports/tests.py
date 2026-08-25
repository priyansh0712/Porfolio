"""
Reports Unit Tests — Dashboard Metrics, Filtered Queries, CSV Exporter, and Correction Audit Logging.

Test Coverage:
  - DashboardService: Accurate daily KPI metrics (present, late, half-day, absent).
  - ReportService:
      - Queryset filtering (date range, department, status, search).
      - CSV export format.
      - Atomic manual correction (creates AttendanceCorrection record, updates AttendanceLog).
      - Empty reason rejection (raises ValueError).
  - AdminDashboardView & AttendanceReportView: Access control and context.
  - AttendanceExportCSVView: CSV download headers.
  - AttendanceCorrectView: POST manual correction execution.
"""
from datetime import date, datetime, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.attendance.models import AttendanceLog
from apps.faculty.models import Faculty
from apps.reports.models import AttendanceCorrection
from apps.reports.services import DashboardService, ReportService
from apps.tenants.models import School


class ReportsTestBase(TestCase):
    """Base setup for reports unit tests."""

    def setUp(self):
        self.school = School.objects.create(
            name='Horizon High',
            subdomain='horizon',
            contact_email='admin@horizon.edu',
        )
        self.admin_user = User.objects.create_user(
            username='horizon_admin',
            email='admin@horizon.edu',
            password='TestPassword123!',
            first_name='Horizon',
            last_name='Admin',
            role=User.Role.SCHOOL_ADMIN,
            school=self.school,
        )

        # Create two faculty members
        self.faculty_1 = Faculty.objects.create(
            school=self.school,
            first_name='Alice',
            last_name='Smith',
            email='alice@horizon.edu',
            employee_code='HORIZON-FAC-001',
            department='Mathematics',
            is_active=True,
        )
        self.faculty_2 = Faculty.objects.create(
            school=self.school,
            first_name='Bob',
            last_name='Jones',
            email='bob@horizon.edu',
            employee_code='HORIZON-FAC-002',
            department='Science',
            is_active=True,
        )


class DashboardServiceTest(ReportsTestBase):
    """Tests for DashboardService KPI metrics aggregation."""

    def test_metrics_calculation(self):
        """DashboardService should accurately aggregate daily attendance metrics."""
        today = timezone.localdate()
        now = timezone.now()

        # Alice checked in on time today
        AttendanceLog.objects.create(
            school=self.school,
            faculty=self.faculty_1,
            date=today,
            check_in_time=now - timedelta(hours=2),
            last_scan_at=now - timedelta(hours=2),
            status=AttendanceLog.Status.PRESENT,
        )

        # Bob has no scan today (Absent)

        metrics = DashboardService.get_metrics(self.school)

        self.assertEqual(metrics['total_faculty'], 2)
        self.assertEqual(metrics['present_count'], 1)
        self.assertEqual(metrics['late_count'], 0)
        self.assertEqual(metrics['absent_count'], 1)
        self.assertEqual(metrics['total_scans'], 1)


class ReportServiceTest(ReportsTestBase):
    """Tests for ReportService filtering, CSV export, and manual correction audit log."""

    def setUp(self):
        super().setUp()
        self.today = timezone.localdate()
        self.now = timezone.now()

        self.log_1 = AttendanceLog.objects.create(
            school=self.school,
            faculty=self.faculty_1,
            date=self.today,
            check_in_time=self.now - timedelta(hours=4),
            check_out_time=self.now,
            last_scan_at=self.now,
            status=AttendanceLog.Status.PRESENT,
        )

    def test_report_queryset_filtering(self):
        """get_report_queryset should filter by department, status, and search query."""
        qs = ReportService.get_report_queryset(
            school=self.school,
            department='Mathematics',
            status='PRESENT',
            search='Alice',
        )
        self.assertEqual(qs.count(), 1)

        # Filter by different department should return empty
        qs_empty = ReportService.get_report_queryset(
            school=self.school,
            department='English',
        )
        self.assertEqual(qs_empty.count(), 0)

    def test_generate_csv_output(self):
        """generate_csv should output valid CSV string with headers."""
        qs = AttendanceLog.objects.filter(school=self.school)
        csv_str = ReportService.generate_csv(self.school, qs)

        self.assertIn('Date,Employee Code,Faculty Name', csv_str)
        self.assertIn('Alice Smith', csv_str)
        self.assertIn('HORIZON-FAC-001', csv_str)

    def test_correct_attendance_creates_audit_log(self):
        """correct_attendance should update AttendanceLog and create AttendanceCorrection audit log."""
        correction = ReportService.correct_attendance(
            school=self.school,
            admin_user=self.admin_user,
            attendance=self.log_1,
            new_status=AttendanceLog.Status.LATE,
            reason='Faculty arrived late due to weather',
        )

        self.assertIsNotNone(correction)
        self.assertEqual(correction.old_status, AttendanceLog.Status.PRESENT)
        self.assertEqual(correction.new_status, AttendanceLog.Status.LATE)
        self.assertEqual(correction.performed_by, self.admin_user)
        self.assertEqual(correction.reason, 'Faculty arrived late due to weather')

        # AttendanceLog status should be updated
        self.log_1.refresh_from_db()
        self.assertEqual(self.log_1.status, AttendanceLog.Status.LATE)

    def test_correct_attendance_empty_reason_raises(self):
        """Passing an empty reason string should raise ValueError."""
        with self.assertRaises(ValueError):
            ReportService.correct_attendance(
                school=self.school,
                admin_user=self.admin_user,
                attendance=self.log_1,
                new_status=AttendanceLog.Status.LATE,
                reason='',
            )


class ReportsViewsTest(ReportsTestBase):
    """Tests for reports CBVs."""

    def test_dashboard_view_access(self):
        """AdminDashboardView should require authentication and render 200 for School Admin."""
        # Unauthenticated
        response = self.client.get(reverse('reports:dashboard'))
        self.assertEqual(response.status_code, 302)

        # Authenticated School Admin
        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse('reports:dashboard'),
            HTTP_HOST='horizon.localhost:8000',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/dashboard.html')

    def test_attendance_report_view_access(self):
        """AttendanceReportView should render reports table for School Admin."""
        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse('reports:report-list'),
            HTTP_HOST='horizon.localhost:8000',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/attendance_report.html')

    def test_export_csv_view(self):
        """AttendanceExportCSVView should return downloadable text/csv response."""
        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse('reports:export-csv'),
            HTTP_HOST='horizon.localhost:8000',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment;', response['Content-Disposition'])

    def test_correct_attendance_view_post(self):
        """AttendanceCorrectView POST should apply correction and redirect."""
        log = AttendanceLog.objects.create(
            school=self.school,
            faculty=self.faculty_1,
            date=timezone.localdate(),
            check_in_time=timezone.now(),
            last_scan_at=timezone.now(),
            status=AttendanceLog.Status.PRESENT,
        )

        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse('reports:correct', kwargs={'pk': log.pk}),
            {
                'new_status': 'LATE',
                'reason': 'Adjusted for late check-in',
            },
            HTTP_HOST='horizon.localhost:8000',
        )
        self.assertRedirects(response, reverse('reports:report-list'))

        log.refresh_from_db()
        self.assertEqual(log.status, 'LATE')
        self.assertTrue(AttendanceCorrection.objects.filter(attendance=log).exists())


class PrincipalDashboardModuleAwarenessTest(ReportsTestBase):
    """
    Validates that the Principal Dashboard dynamically adapts based on enabled features,
    executes zero unnecessary DB queries, and reflows seamlessly across scenarios.
    """

    def setUp(self):
        super().setUp()
        from apps.tenants.features import FeatureService
        from apps.academics.models import AcademicYear, Standard, Division, Subject
        from apps.students.models import Student
        from apps.leaves.models import LeaveRequest

        # Set up active academic year, standards, divisions, subjects
        self.academic_year = AcademicYear.objects.create(
            school=self.school,
            name='2026-2027',
            start_date=date(2026, 6, 1),
            end_date=date(2027, 4, 30),
            is_current=True,
        )
        self.standard_10 = Standard.objects.create(
            school=self.school,
            name='Grade 10',
            order_index=10,
        )
        self.division_a = Division.objects.create(
            school=self.school,
            standard=self.standard_10,
            name='A',
        )
        self.subject_math = Subject.objects.create(
            school=self.school,
            name='Mathematics',
            code='MATH10',
        )

        # Create active student
        self.student_1 = Student.objects.create(
            school=self.school,
            full_name='Rahul Sharma',
            gr_number='GR-1001',
            academic_year=self.academic_year,
            standard=self.standard_10,
            division=self.division_a,
            is_active=True,
        )

    def test_dashboard_identity_and_universal_metrics(self):
        """Dashboard renders neutral identity and universal metrics."""
        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse('reports:dashboard'),
            HTTP_HOST='horizon.localhost:8000',
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'School Overview')
        self.assertContains(response, 'Real-time school performance and operational snapshot.')
        self.assertContains(response, 'Total Students')
        self.assertContains(response, 'Total Faculty')
        self.assertContains(response, 'Active Divisions')
        self.assertContains(response, '2026-2027')

    def test_scenario_a_attendance_disabled(self):
        """Scenario A: Faculty Attendance disabled -> Zero attendance cards, zero Kiosk CTA."""
        from apps.tenants.features import FeatureService
        FeatureService.set_feature_status(self.school, 'faculty_attendance', False)

        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse('reports:dashboard'),
            HTTP_HOST='horizon.localhost:8000',
        )
        self.assertEqual(response.status_code, 200)
        # Should NOT contain attendance-specific UI or Kiosk button
        self.assertNotContains(response, 'Launch Kiosk')
        self.assertNotContains(response, 'Live Attendance Feed')
        self.assertNotContains(response, 'Attendance Export')

        # Should still contain neutral overview, leaves, academics
        self.assertContains(response, 'Total Students')
        self.assertContains(response, 'Total Faculty')
        self.assertContains(response, 'Academic Overview')

    def test_scenario_b_faculty_attendance_enabled(self):
        """Scenario B: Faculty Attendance enabled -> Shows Live Attendance snapshot & Kiosk."""
        from apps.tenants.features import FeatureService
        FeatureService.set_feature_status(self.school, 'faculty_attendance', True)

        # Create attendance log for today
        AttendanceLog.objects.create(
            school=self.school,
            faculty=self.faculty_1,
            date=timezone.localdate(),
            check_in_time=timezone.now(),
            last_scan_at=timezone.now(),
            status=AttendanceLog.Status.PRESENT,
        )

        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse('reports:dashboard'),
            HTTP_HOST='horizon.localhost:8000',
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Launch Kiosk')
        self.assertContains(response, 'Faculty Attendance')
        self.assertContains(response, 'Live Attendance Feed')
        self.assertContains(response, 'Alice Smith')

    def test_scenario_c_academics_disabled(self):
        """Scenario C: Academics disabled -> Academic snapshot & Hub links omitted."""
        from apps.tenants.features import FeatureService
        FeatureService.set_feature_status(self.school, 'academics', False)

        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse('reports:dashboard'),
            HTTP_HOST='horizon.localhost:8000',
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Academic Overview')
        self.assertNotContains(response, 'Academics Hub')

    def test_scenario_d_basic_students_and_faculty_only(self):
        """Scenario D: Only Students & Faculty enabled -> Clean minimal layout."""
        from apps.tenants.features import FeatureService
        FeatureService.set_feature_status(self.school, 'faculty_attendance', False)
        FeatureService.set_feature_status(self.school, 'faculty_leave', False)
        FeatureService.set_feature_status(self.school, 'academics', False)

        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse('reports:dashboard'),
            HTTP_HOST='horizon.localhost:8000',
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'School Overview')
        self.assertContains(response, 'Total Students')
        self.assertContains(response, 'Total Faculty')
        self.assertNotContains(response, 'Launch Kiosk')
        self.assertNotContains(response, 'Staff Leaves')
        self.assertNotContains(response, 'Academic Overview')

    def test_zero_attendance_queries_when_attendance_disabled(self):
        """Ensures AttendanceLog is NEVER queried when faculty_attendance is disabled."""
        from apps.tenants.features import FeatureService
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        FeatureService.set_feature_status(self.school, 'faculty_attendance', False)

        with CaptureQueriesContext(connection) as queries:
            metrics = DashboardService.get_metrics(self.school)

        # Assert no query touched attendance_attendancelog
        for query in queries.captured_queries:
            self.assertNotIn(
                'attendance_attendancelog',
                query['sql'].lower(),
                f"Unexpected attendance query was executed: {query['sql']}"
            )

        self.assertEqual(metrics['present_count'], 0)
        self.assertEqual(metrics['total_scans'], 0)
        self.assertEqual(metrics['live_feed'], [])

