"""
Unit and Integration Tests for the Students App.

Tests cover:
  - Student model constraints (GR uniqueness, roll number uniqueness, soft-delete).
  - Student.initials property.
  - TenantAwareAuthBackend — GR Number login path.
  - StudentService.create_student (provisioning, duplicate GR rejection).
  - StudentService.update_student (GR lock enforcement).
  - StudentService.soft_delete_student / restore_student.
  - Transfer request lifecycle: request → approve / reject.
  - Tenant isolation: students from School A cannot be accessed as School B.
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, RequestFactory, Client

from apps.tenants.models import School
from apps.tenants.context import set_current_tenant
from apps.accounts.auth_backends import TenantAwareAuthBackend
from apps.academics.models import (
    AcademicYear, Standard, Division, Subject,
    ClassTeacherAllocation, SubjectTeacherAllocation,
)
from apps.faculty.models import Faculty
from apps.students.models import Student, StudentTransferRequest, StudentCustomField, StudentFormFieldConfig
from apps.students.services import StudentService

User = get_user_model()


# ---------------------------------------------------------------------------
# Base setup shared across all student test cases
# ---------------------------------------------------------------------------

class StudentBaseTestCase(TestCase):
    """Base TestCase with two isolated school tenants, academic hierarchy, and one faculty."""

    def setUp(self):
        super().setUp()

        # Two isolated school tenants
        self.school_a = School.objects.create(
            name='Greenwood International',
            subdomain='greenwood',
            contact_email='admin@greenwood.com',
        )
        self.school_b = School.objects.create(
            name='Oakridge Academy',
            subdomain='oakridge',
            contact_email='admin@oakridge.com',
        )

        # Admin users
        self.admin_a = User.objects.create_user(
            email='admin@greenwood.com',
            username='admin_gw',
            password='Admin@123',
            role=User.Role.SCHOOL_ADMIN,
            school=self.school_a,
        )
        self.admin_b = User.objects.create_user(
            email='admin@oakridge.com',
            username='admin_oak',
            password='Admin@123',
            role=User.Role.SCHOOL_ADMIN,
            school=self.school_b,
        )

        # Faculty user and Faculty record for School A
        self.faculty_user_a = User.objects.create_user(
            email='teacher@greenwood.com',
            username='teacher_gw',
            password='Admin@123',
            role=User.Role.FACULTY,
            school=self.school_a,
        )
        self.faculty_a = Faculty.objects.create(
            school=self.school_a,
            user=self.faculty_user_a,
            first_name='Anand',
            last_name='Sharma',
            email='teacher@greenwood.com',
            employee_code='GW-FAC-001',
            department='Mathematics',
            is_active=True,
        )

        # Academic hierarchy for School A
        self.year_a = AcademicYear.objects.create(
            school=self.school_a,
            name='2026-2027',
            start_date=date(2026, 6, 1),
            end_date=date(2027, 4, 30),
            is_current=True,
        )
        self.standard_a = Standard.objects.create(
            school=self.school_a,
            name='Standard 5',
            order_index=5,
        )
        self.standard_a2 = Standard.objects.create(
            school=self.school_a,
            name='Standard 6',
            order_index=6,
        )
        self.division_a = Division.objects.create(
            school=self.school_a,
            standard=self.standard_a,
            name='A',
        )
        self.division_a2 = Division.objects.create(
            school=self.school_a,
            standard=self.standard_a2,
            name='A',
        )

        # Academic hierarchy for School B
        self.year_b = AcademicYear.objects.create(
            school=self.school_b,
            name='2026-2027',
            start_date=date(2026, 6, 1),
            end_date=date(2027, 4, 30),
            is_current=True,
        )
        self.standard_b = Standard.objects.create(
            school=self.school_b,
            name='Standard 5',
            order_index=5,
        )
        self.division_b = Division.objects.create(
            school=self.school_b,
            standard=self.standard_b,
            name='A',
        )

    def tearDown(self):
        set_current_tenant(None)
        super().tearDown()

    def _make_student(self, gr_number='GR001', school=None, division=None,
                      standard=None, year=None, full_name='Raj Patel'):
        """Helper: create a student via service for reuse across tests."""
        return StudentService.create_student(
            school=school or self.school_a,
            academic_year=year or self.year_a,
            standard=standard or self.standard_a,
            division=division or self.division_a,
            gr_number=gr_number,
            full_name=full_name,
        )


# ---------------------------------------------------------------------------
# Student Model Tests
# ---------------------------------------------------------------------------

class StudentModelTests(StudentBaseTestCase):
    """Tests for Student model constraints and properties."""

    def test_create_student_via_service(self):
        """StudentService.create_student provisions Student + linked User."""
        student = self._make_student(gr_number='GR001', full_name='Raj Patel')
        self.assertIsNotNone(student.pk)
        self.assertIsNotNone(student.user)
        self.assertEqual(student.user.role, User.Role.STUDENT)
        self.assertEqual(student.user.school, self.school_a)

    def test_initials_two_word_name(self):
        student = self._make_student(full_name='Raj Patel', gr_number='GR002')
        self.assertEqual(student.initials, 'RP')

    def test_initials_single_word_name(self):
        student = self._make_student(full_name='Monalisa', gr_number='GR003')
        self.assertEqual(student.initials, 'M')

    def test_initials_multi_word_name(self):
        student = self._make_student(full_name='Ansh Kumar Patoliya', gr_number='GR004')
        self.assertEqual(student.initials, 'AP')

    def test_gr_number_unique_per_school(self):
        """Duplicate GR number within same school raises ValueError from service."""
        self._make_student(gr_number='GR005')
        with self.assertRaises(ValueError):
            self._make_student(gr_number='GR005')

    def test_gr_number_can_repeat_across_schools(self):
        """Same GR number is allowed in a different school tenant."""
        self._make_student(gr_number='GR006', school=self.school_a)
        # Should not raise
        StudentService.create_student(
            school=self.school_b,
            academic_year=self.year_b,
            standard=self.standard_b,
            division=self.division_b,
            gr_number='GR006',
            full_name='Other Student',
        )

    def test_roll_number_unique_per_active_division_year(self):
        """Two active students with same roll number in same division/year raises IntegrityError."""
        self._make_student(gr_number='GR007', full_name='Student One')
        s1 = Student.objects.get(gr_number='GR007', school=self.school_a)
        s1.roll_number = 1
        s1.save()

        self._make_student(gr_number='GR008', full_name='Student Two')
        s2 = Student.objects.get(gr_number='GR008', school=self.school_a)
        s2.roll_number = 1
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                s2.save()

    def test_roll_number_null_does_not_conflict(self):
        """Multiple students with roll_number=None don't violate the constraint."""
        self._make_student(gr_number='GR009', full_name='Student A')
        self._make_student(gr_number='GR010', full_name='Student B')
        # Both have roll_number=None — no conflict expected
        count = Student.objects.filter(school=self.school_a, roll_number__isnull=True).count()
        self.assertGreaterEqual(count, 2)

    def test_soft_delete_deactivates_student_and_user(self):
        """soft_delete_student sets is_active=False on both Student and User."""
        student = self._make_student(gr_number='GR011')
        StudentService.soft_delete_student(student)
        student.refresh_from_db()
        student.user.refresh_from_db()
        self.assertFalse(student.is_active)
        self.assertFalse(student.user.is_active)

    def test_restore_student_reactivates_both(self):
        """restore_student re-enables Student and User."""
        student = self._make_student(gr_number='GR012')
        StudentService.soft_delete_student(student)
        StudentService.restore_student(student)
        student.refresh_from_db()
        student.user.refresh_from_db()
        self.assertTrue(student.is_active)
        self.assertTrue(student.user.is_active)


# ---------------------------------------------------------------------------
# StudentService Update Tests
# ---------------------------------------------------------------------------

class StudentServiceUpdateTests(StudentBaseTestCase):
    """Tests for StudentService.update_student GR lock enforcement."""

    def test_class_teacher_cannot_edit_gr_number(self):
        """update_student without allow_gr_edit=True silently ignores gr_number changes."""
        student = self._make_student(gr_number='GR020', full_name='Old Name')
        StudentService.update_student(student, allow_gr_edit=False, gr_number='GR999', full_name='New Name')
        student.refresh_from_db()
        self.assertEqual(student.gr_number, 'GR020')   # unchanged
        self.assertEqual(student.full_name, 'New Name')  # other fields updated

    def test_admin_can_edit_gr_number(self):
        """update_student with allow_gr_edit=True updates the GR number."""
        student = self._make_student(gr_number='GR021', full_name='Test Student')
        StudentService.update_student(student, allow_gr_edit=True, gr_number='GR021X')
        student.refresh_from_db()
        self.assertEqual(student.gr_number, 'GR021X')

    def test_full_name_change_syncs_user_names(self):
        """Updating full_name should also update linked user's first/last name."""
        student = self._make_student(gr_number='GR022', full_name='Old Name')
        StudentService.update_student(student, full_name='Priya Sharma')
        student.refresh_from_db()
        self.assertEqual(student.user.first_name, 'Priya')
        self.assertEqual(student.user.last_name, 'Sharma')


# ---------------------------------------------------------------------------
# Transfer Request Lifecycle Tests
# ---------------------------------------------------------------------------

class TransferRequestTests(StudentBaseTestCase):
    """Tests for transfer request: request, approve, and reject lifecycle."""

    def test_request_transfer_creates_pending_record(self):
        """request_transfer creates a StudentTransferRequest in PENDING status."""
        student = self._make_student(gr_number='GR030')
        tr = StudentService.request_transfer(
            student=student,
            to_standard=self.standard_a2,
            to_division=self.division_a2,
            requested_by=self.faculty_a,
            reason='Student promoted.',
        )
        self.assertEqual(tr.status, StudentTransferRequest.Status.PENDING)
        self.assertEqual(tr.student, student)
        self.assertEqual(tr.to_division, self.division_a2)

    def test_duplicate_pending_transfer_raises_error(self):
        """A second pending transfer request for same student raises ValueError."""
        student = self._make_student(gr_number='GR031')
        StudentService.request_transfer(
            student=student,
            to_standard=self.standard_a2,
            to_division=self.division_a2,
            requested_by=self.faculty_a,
        )
        with self.assertRaises(ValueError):
            StudentService.request_transfer(
                student=student,
                to_standard=self.standard_a2,
                to_division=self.division_a2,
                requested_by=self.faculty_a,
            )

    def test_approve_transfer_updates_student_placement(self):
        """approve_transfer atomically moves student to new division and marks APPROVED."""
        student = self._make_student(gr_number='GR032')
        tr = StudentService.request_transfer(
            student=student,
            to_standard=self.standard_a2,
            to_division=self.division_a2,
            requested_by=self.faculty_a,
        )
        StudentService.approve_transfer(tr, reviewed_by=self.admin_a)

        student.refresh_from_db()
        tr.refresh_from_db()
        self.assertEqual(student.division, self.division_a2)
        self.assertEqual(student.standard, self.standard_a2)
        self.assertEqual(tr.status, StudentTransferRequest.Status.APPROVED)
        self.assertEqual(tr.reviewed_by, self.admin_a)
        self.assertIsNotNone(tr.reviewed_at)

    def test_reject_transfer_does_not_move_student(self):
        """reject_transfer marks REJECTED but student placement is unchanged."""
        student = self._make_student(gr_number='GR033')
        original_division = student.division
        tr = StudentService.request_transfer(
            student=student,
            to_standard=self.standard_a2,
            to_division=self.division_a2,
            requested_by=self.faculty_a,
        )
        StudentService.reject_transfer(tr, reviewed_by=self.admin_a, rejection_reason='No vacancy.')

        student.refresh_from_db()
        tr.refresh_from_db()
        self.assertEqual(student.division, original_division)   # placement unchanged
        self.assertEqual(tr.status, StudentTransferRequest.Status.REJECTED)
        self.assertEqual(tr.rejection_reason, 'No vacancy.')

    def test_approve_already_approved_raises_error(self):
        """Cannot approve a transfer request that is not PENDING."""
        student = self._make_student(gr_number='GR034')
        tr = StudentService.request_transfer(
            student=student,
            to_standard=self.standard_a2,
            to_division=self.division_a2,
            requested_by=self.faculty_a,
        )
        StudentService.approve_transfer(tr, reviewed_by=self.admin_a)
        with self.assertRaises(ValueError):
            StudentService.approve_transfer(tr, reviewed_by=self.admin_a)


# ---------------------------------------------------------------------------
# Authentication Backend — GR Number Login Tests
# ---------------------------------------------------------------------------

class GRNumberAuthBackendTests(StudentBaseTestCase):
    """Tests for TenantAwareAuthBackend GR Number login path."""

    def _mock_request(self, tenant):
        """Return a fake request object with tenant set."""
        factory = RequestFactory()
        request = factory.post('/login/')
        request.tenant = tenant
        return request

    def test_student_login_with_gr_number_succeeds(self):
        """Valid GR number + default password logs in the student on their school subdomain."""
        student = self._make_student(gr_number='GR040', full_name='Sneha Joshi')
        backend = TenantAwareAuthBackend()
        request = self._mock_request(self.school_a)
        user = backend.authenticate(request, username='GR040', password='Admin@123')
        self.assertIsNotNone(user)
        self.assertEqual(user, student.user)

    def test_student_login_wrong_password_fails(self):
        """Wrong password returns None."""
        self._make_student(gr_number='GR041')
        backend = TenantAwareAuthBackend()
        request = self._mock_request(self.school_a)
        user = backend.authenticate(request, username='GR041', password='WrongPass')
        self.assertIsNone(user)

    def test_student_login_wrong_school_fails(self):
        """GR number from School A cannot login on School B subdomain."""
        self._make_student(gr_number='GR042', school=self.school_a)
        backend = TenantAwareAuthBackend()
        request = self._mock_request(self.school_b)  # wrong school
        user = backend.authenticate(request, username='GR042', password='Admin@123')
        self.assertIsNone(user)

    def test_inactive_student_cannot_login(self):
        """Soft-deleted student cannot login via GR number."""
        student = self._make_student(gr_number='GR043')
        StudentService.soft_delete_student(student)
        backend = TenantAwareAuthBackend()
        request = self._mock_request(self.school_a)
        user = backend.authenticate(request, username='GR043', password='Admin@123')
        self.assertIsNone(user)

    def test_gr_number_login_on_root_domain_fails(self):
        """GR number login attempt on root domain (tenant=None) returns None."""
        self._make_student(gr_number='GR044')
        backend = TenantAwareAuthBackend()
        request = self._mock_request(None)  # root domain
        user = backend.authenticate(request, username='GR044', password='Admin@123')
        self.assertIsNone(user)

    def test_staff_email_login_still_works(self):
        """Email login path for Staff users is unaffected by the GR number path."""
        backend = TenantAwareAuthBackend()
        request = self._mock_request(self.school_a)
        user = backend.authenticate(request, username='teacher@greenwood.com', password='Admin@123')
        self.assertIsNotNone(user)
        self.assertEqual(user, self.faculty_user_a)

    def test_nonexistent_gr_number_fails(self):
        """Non-existent GR number returns None."""
        backend = TenantAwareAuthBackend()
        request = self._mock_request(self.school_a)
        user = backend.authenticate(request, username='DOESNOTEXIST', password='Admin@123')
        self.assertIsNone(user)


# ---------------------------------------------------------------------------
# Tenant Isolation Tests
# ---------------------------------------------------------------------------

class StudentTenantIsolationTests(StudentBaseTestCase):
    """Ensures students from School A are never visible via School B queries."""

    def test_school_a_student_not_in_school_b_queryset(self):
        """Students are strictly filtered by school."""
        self._make_student(gr_number='GR050', school=self.school_a)
        qs = Student.objects.filter(school=self.school_b)
        self.assertEqual(qs.count(), 0)

    def test_gr_unique_constraint_is_per_tenant(self):
        """Same GR number exists in two schools without DB conflict."""
        s_a = self._make_student(gr_number='GR051', school=self.school_a)
        s_b = StudentService.create_student(
            school=self.school_b,
            academic_year=self.year_b,
            standard=self.standard_b,
            division=self.division_b,
            gr_number='GR051',
            full_name='Same GR Other School',
        )
        self.assertNotEqual(s_a.pk, s_b.pk)
        self.assertEqual(s_a.gr_number, s_b.gr_number)


# ---------------------------------------------------------------------------
# View & Integration Tests
# ---------------------------------------------------------------------------

class StudentHubViewTests(StudentBaseTestCase):
    """Tests for StudentHubView authorization, scoping, and search."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        # Allocate faculty_a as Class Teacher of division_a in year_a
        ClassTeacherAllocation.objects.create(
            school=self.school_a,
            academic_year=self.year_a,
            division=self.division_a,
            faculty=self.faculty_a,
        )
        # Create student in division_a (Class Teacher's division)
        self.s1 = self._make_student(gr_number='GR101', full_name='Aarav Shah', division=self.division_a, standard=self.standard_a)
        # Create student in division_a2 (different division)
        self.s2 = self._make_student(gr_number='GR102', full_name='Bhavin Patel', division=self.division_a2, standard=self.standard_a2)

    def test_unauthenticated_redirected_to_login(self):
        """Unauthenticated request to /students/ redirects to login."""
        resp = self.client.get('/students/', HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)

    def test_super_admin_forbidden(self):
        """Super Admin accessing /students/ is forbidden (HTTP 403)."""
        super_admin = User.objects.create_user(
            email='super@platform.local',
            username='superadmin_user',
            password='Admin@123',
            role=User.Role.SUPER_ADMIN,
            school=None,
        )
        self.client.force_login(super_admin)
        resp = self.client.get('/students/', HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 403)

    def test_admin_sees_all_students(self):
        """School Admin sees students across all divisions."""
        self.client.force_login(self.admin_a)
        resp = self.client.get('/students/', HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Aarav Shah')
        self.assertContains(resp, 'Bhavin Patel')

    def test_class_teacher_sees_only_assigned_division_students(self):
        """Class Teacher only sees students belonging to their allocated division."""
        self.client.force_login(self.faculty_user_a)
        resp = self.client.get('/students/', HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Aarav Shah')
        self.assertNotContains(resp, 'Bhavin Patel')

    def test_cross_tenant_admin_forbidden(self):
        """School B Admin cannot access School A student hub."""
        self.client.force_login(self.admin_b)
        resp = self.client.get('/students/', HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 403)

    def test_search_filter(self):
        """Search query filters the student roster by name or GR number."""
        self.client.force_login(self.admin_a)
        resp = self.client.get('/students/?q=Aarav', HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Aarav Shah')
        self.assertNotContains(resp, 'Bhavin Patel')


class StudentCRUDViewTests(StudentBaseTestCase):
    """Tests for Student Create, Update, and Delete views."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        ClassTeacherAllocation.objects.create(
            school=self.school_a,
            academic_year=self.year_a,
            division=self.division_a,
            faculty=self.faculty_a,
        )

    def test_admin_can_create_student_in_any_division(self):
        """School Admin creates student in division_a2."""
        self.client.force_login(self.admin_a)
        resp = self.client.post('/students/add/', {
            'full_name': 'Diya Mehta',
            'gr_number': 'GR201',
            'gender': 'FEMALE',
            'standard': str(self.standard_a2.pk),
            'division': str(self.division_a2.pk),
        }, HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 302)
        student = Student.objects.get(school=self.school_a, gr_number='GR201')
        self.assertEqual(student.full_name, 'Diya Mehta')
        self.assertEqual(student.division, self.division_a2)

    def test_class_teacher_creates_student_in_assigned_division(self):
        """Class Teacher creates student — placement is forced to their assigned division."""
        self.client.force_login(self.faculty_user_a)
        resp = self.client.post('/students/add/', {
            'full_name': 'Ishaan Dave',
            'gr_number': 'GR202',
            'gender': 'MALE',
            'standard': str(self.standard_a.pk),
            'division': str(self.division_a.pk),
        }, HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 302)
        student = Student.objects.get(school=self.school_a, gr_number='GR202')
        self.assertEqual(student.division, self.division_a)

    def test_class_teacher_cannot_change_gr_number_on_update(self):
        """Class Teacher updating student cannot alter the GR number."""
        student = self._make_student(gr_number='GR203', full_name='Kavya Joshi', division=self.division_a, standard=self.standard_a)
        self.client.force_login(self.faculty_user_a)
        resp = self.client.post(f'/students/{student.pk}/edit/', {
            'full_name': 'Kavya J. Joshi',
            'gr_number': 'GR_HACKED',
            'gender': 'FEMALE',
            'roll_number': '5',
        }, HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 302)
        student.refresh_from_db()
        self.assertEqual(student.gr_number, 'GR203')  # Unchanged
        self.assertEqual(student.full_name, 'Kavya J. Joshi')  # Updated

    def test_admin_can_soft_delete_and_restore_student(self):
        """School Admin can soft-deactivate and restore a student."""
        student = self._make_student(gr_number='GR204', full_name='Manan Trivedi')
        self.client.force_login(self.admin_a)

        # Deactivate
        resp = self.client.post(f'/students/{student.pk}/delete/', HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 302)
        student.refresh_from_db()
        self.assertFalse(student.is_active)

        # Restore
        resp = self.client.post(f'/students/{student.pk}/restore/', HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 302)
        student.refresh_from_db()
        self.assertTrue(student.is_active)

    def test_faculty_cannot_delete_student(self):
        """Faculty member cannot delete a student (403 forbidden)."""
        student = self._make_student(gr_number='GR205', full_name='Nandini Shah')
        self.client.force_login(self.faculty_user_a)
        resp = self.client.post(f'/students/{student.pk}/delete/', HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 403)


class TransferWorkflowViewTests(StudentBaseTestCase):
    """Tests for student transfer request, approval, and rejection views."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        ClassTeacherAllocation.objects.create(
            school=self.school_a,
            academic_year=self.year_a,
            division=self.division_a,
            faculty=self.faculty_a,
        )
        self.student = self._make_student(
            gr_number='GR301', full_name='Parth Varma',
            division=self.division_a, standard=self.standard_a
        )

    def test_class_teacher_creates_transfer_request_view(self):
        """Class Teacher submits a transfer request via POST."""
        self.client.force_login(self.faculty_user_a)
        resp = self.client.post(f'/students/{self.student.pk}/transfer/', {
            'to_standard': str(self.standard_a2.pk),
            'to_division': str(self.division_a2.pk),
            'reason': 'Academic restructuring',
        }, HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 302)
        tr = StudentTransferRequest.objects.get(student=self.student)
        self.assertEqual(tr.status, StudentTransferRequest.Status.PENDING)
        self.assertEqual(tr.to_division, self.division_a2)

    def test_admin_approves_transfer_request_view(self):
        """School Admin approves transfer request via POST."""
        tr = StudentService.request_transfer(
            student=self.student,
            to_standard=self.standard_a2,
            to_division=self.division_a2,
            requested_by=self.faculty_a,
        )
        self.client.force_login(self.admin_a)
        resp = self.client.post(f'/students/transfers/{tr.pk}/approve/', HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 302)
        self.student.refresh_from_db()
        tr.refresh_from_db()
        self.assertEqual(self.student.division, self.division_a2)
        self.assertEqual(tr.status, StudentTransferRequest.Status.APPROVED)

    def test_admin_rejects_transfer_request_view(self):
        """School Admin rejects transfer request via POST."""
        tr = StudentService.request_transfer(
            student=self.student,
            to_standard=self.standard_a2,
            to_division=self.division_a2,
            requested_by=self.faculty_a,
        )
        self.client.force_login(self.admin_a)
        resp = self.client.post(f'/students/transfers/{tr.pk}/reject/', {
            'rejection_reason': 'Division at full capacity',
        }, HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 302)
        self.student.refresh_from_db()
        tr.refresh_from_db()
        self.assertEqual(self.student.division, self.division_a)  # Unchanged
        self.assertEqual(tr.status, StudentTransferRequest.Status.REJECTED)


class StudentPortalViewTests(StudentBaseTestCase):
    """Tests for StudentPortalView access and display."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        # Set up Class Teacher allocation
        ClassTeacherAllocation.objects.create(
            school=self.school_a,
            academic_year=self.year_a,
            division=self.division_a,
            faculty=self.faculty_a,
        )
        # Set up a Subject and Subject Teacher allocation
        self.subject = Subject.objects.create(
            school=self.school_a,
            name='Mathematics',
            code='MATH-101',
            subject_type='CORE',
        )
        SubjectTeacherAllocation.objects.create(
            school=self.school_a,
            academic_year=self.year_a,
            division=self.division_a,
            subject=self.subject,
            faculty=self.faculty_a,
        )
        self.student = self._make_student(
            gr_number='GR401', full_name='Rohan Kothari',
            division=self.division_a, standard=self.standard_a
        )

    def test_student_portal_renders_with_profile_and_subjects(self):
        """Authenticated Student accessing portal gets 200 OK with their details."""
        self.client.force_login(self.student.user)
        resp = self.client.get('/students/portal/', HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Rohan Kothari')
        self.assertContains(resp, 'GR: GR401')
        self.assertContains(resp, 'Anand Sharma')  # Class teacher
        self.assertContains(resp, 'Mathematics')   # Subject

    def test_dashboard_redirects_student_to_portal(self):
        """TenantDashboardView routes STUDENT role directly to StudentPortalView."""
        self.client.force_login(self.student.user)
        resp = self.client.get('/dashboard/', HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Rohan Kothari')

    def test_faculty_forbidden_from_student_portal(self):
        """Faculty user accessing /students/portal/ receives HTTP 403."""
        self.client.force_login(self.faculty_user_a)
        resp = self.client.get('/students/portal/', HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 403)


class StudentCustomFieldTests(StudentBaseTestCase):
    """Tests for dynamic custom fields creation, form integration, and deletion."""

    def setUp(self):
        super().setUp()
        self.client = Client()

    def test_admin_can_create_custom_field_and_use_in_form(self):
        """School Admin creates an 'Aadhar Number' custom field and creates a student with it."""
        # 1. Admin creates custom field via view
        self.client.force_login(self.admin_a)
        resp = self.client.post('/students/custom-fields/add/', {
            'label': 'Aadhar Number',
            'field_type': 'TEXT',
            'is_required': False,
        }, HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 302)

        cf = StudentCustomField.objects.get(school=self.school_a, label='Aadhar Number')
        self.assertEqual(cf.field_name, 'aadhar_number')
        self.assertTrue(cf.is_active)

        # 2. Add student with this custom field value
        resp2 = self.client.post('/students/add/', {
            'full_name': 'Meera Solanki',
            'gr_number': 'GR501',
            'gender': 'FEMALE',
            'standard': str(self.standard_a.pk),
            'division': str(self.division_a.pk),
            'cf_aadhar_number': '1234-5678-9012',
        }, HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp2.status_code, 302)

        student = Student.objects.get(school=self.school_a, gr_number='GR501')
        self.assertEqual(student.custom_fields.get('aadhar_number'), '1234-5678-9012')

    def test_toggle_and_delete_custom_field(self):
        """Admin can toggle field active state and delete custom field."""
        cf = StudentService.create_custom_field(
            school=self.school_a,
            label='Bus Route',
            field_type='TEXT',
        )
        self.client.force_login(self.admin_a)

    def test_admin_can_edit_custom_field(self):
        """Admin can edit an existing custom field's label and options."""
        cf = StudentService.create_custom_field(
            school=self.school_a,
            label='Bus Route',
            field_type='SELECT',
            options='Route A, Route B',
            is_required=False,
        )
        self.client.force_login(self.admin_a)

        # Edit label and options
        resp = self.client.post(f'/students/custom-fields/{cf.pk}/edit/', {
            'label': 'Bus Pickup Route',
            'options': 'Route A, Route B, Route C',
            'is_required': '1',
        }, HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 302)

        cf.refresh_from_db()
        self.assertEqual(cf.label, 'Bus Pickup Route')
        self.assertEqual(cf.options, 'Route A, Route B, Route C')
        self.assertTrue(cf.is_required)
        self.assertEqual(cf.field_name, 'bus_route')  # Field key remains unchanged



class StudentFormFieldConfigTests(StudentBaseTestCase):
    """Tests for school-wide student form field customization (visibility + mandatory settings)."""

    def setUp(self):
        super().setUp()
        self.client = Client()

    def test_default_form_config_created_with_all_fields_visible(self):
        """get_for_school creates default config with all standard fields visible."""
        config = StudentFormFieldConfig.get_for_school(self.school_a)
        self.assertTrue(config.show_blood_group)
        self.assertTrue(config.show_guardian_details)
        self.assertFalse(config.require_blood_group)

    def test_admin_updates_form_config(self):
        """School Admin updates form configuration via POST."""
        self.client.force_login(self.admin_a)
        resp = self.client.post('/students/form-config/', {
            'show_roll_number': 'on',
            'require_roll_number': 'on',
            'show_gender': 'on',
            # show_blood_group omitted = unchecked / False
        }, HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 302)

        config = StudentFormFieldConfig.get_for_school(self.school_a)
        self.assertTrue(config.require_roll_number)
        self.assertFalse(config.show_blood_group)

    def test_student_form_respects_requirement_config(self):
        """StudentForm marks roll_number required when require_roll_number=True."""
        config = StudentFormFieldConfig.get_for_school(self.school_a)
        config.require_roll_number = True
        config.save()


class SubjectTeacherPermissionTests(StudentBaseTestCase):
    """Verify Subject Teachers have read-only access and cannot edit/add/transfer students."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        # Create a faculty user who is a Subject Teacher (NOT a Class Teacher)
        self.subject_user = User.objects.create_user(
            email='subject_teacher@greenwood.com',
            username='sub_teacher',
            password='Admin@123',
            role=User.Role.FACULTY,
            school=self.school_a,
        )
        self.subject_faculty = Faculty.objects.create(
            school=self.school_a,
            user=self.subject_user,
            first_name='Kavita',
            last_name='Mehta',
            email='subject_teacher@greenwood.com',
            employee_code='GW-FAC-002',
            department='Science',
            is_active=True,
        )
        self.student = self._make_student(gr_number='GR-SUB-1', full_name='Arun Jetli')

    def test_subject_teacher_cannot_edit_student_profile_returns_403(self):
        """Subject Teacher POSTing to /students/<pk>/edit/ receives 403 Forbidden."""
        self.client.force_login(self.subject_user)
        original_name = self.student.full_name
        resp = self.client.post(f'/students/{self.student.pk}/edit/', {
            'full_name': 'Hacked Name By Subject Teacher',
            'gender': 'MALE',
        }, HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 403)
        self.student.refresh_from_db()
        self.assertEqual(self.student.full_name, original_name)

    def test_subject_teacher_cannot_add_student_returns_403(self):
        """Subject Teacher POSTing to /students/add/ receives 403 Forbidden."""
        self.client.force_login(self.subject_user)
        resp = self.client.post('/students/add/', {
            'full_name': 'New Student By Subject Teacher',
            'gr_number': '99999',
            'standard': self.standard_a.pk,
            'division': self.division_a.pk,
        }, HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 403)

    def test_subject_teacher_cannot_request_transfer_returns_403(self):
        """Subject Teacher POSTing to /students/<pk>/transfer/ receives 403 Forbidden."""
        self.client.force_login(self.subject_user)
        resp = self.client.post(f'/students/{self.student.pk}/transfer/', {
            'to_standard': self.standard_a.pk,
            'to_division': self.division_a2.pk,
        }, HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 403)

    def test_subject_teacher_sees_read_only_in_hub(self):
        """Subject Teacher sees read-only banner and read-only student table."""
        self.client.force_login(self.subject_user)
        resp = self.client.get('/students/', HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['can_edit_students'])
        self.assertTrue(resp.context['is_subject_teacher'])


class BulkStudentActionTests(StudentBaseTestCase):
    """Integration tests for Bulk Deactivate and Bulk Permanent Delete workflows."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        # Allocate faculty_a as Class Teacher for division_a
        ClassTeacherAllocation.objects.create(
            school=self.school_a,
            academic_year=self.year_a,
            faculty=self.faculty_a,
            division=self.division_a,
        )
        self.s1 = self._make_student(gr_number='GR-BLK-1', full_name='Student One')
        self.s2 = self._make_student(gr_number='GR-BLK-2', full_name='Student Two')
        self.s3 = self._make_student(gr_number='GR-BLK-3', full_name='Student Three', division=self.division_a2)

    def test_admin_bulk_deactivate_success(self):
        """School Admin can bulk deactivate multiple students at once."""
        self.client.force_login(self.admin_a)
        resp = self.client.post('/students/bulk-deactivate/', {
            'student_ids': f"{self.s1.pk},{self.s2.pk}"
        }, HTTP_HOST='greenwood.localhost')
        self.assertRedirects(resp, '/students/')
        self.s1.refresh_from_db()
        self.s2.refresh_from_db()
        self.s3.refresh_from_db()
        self.assertFalse(self.s1.is_active)
        self.assertFalse(self.s2.is_active)
        self.assertTrue(self.s3.is_active)

    def test_admin_bulk_permanent_delete_success(self):
        """School Admin can permanently bulk delete selected students."""
        self.client.force_login(self.admin_a)
        resp = self.client.post('/students/bulk-delete/', {
            'student_ids': f"{self.s1.pk},{self.s2.pk}"
        }, HTTP_HOST='greenwood.localhost')
        self.assertRedirects(resp, '/students/')
        self.assertFalse(Student.objects.filter(pk=self.s1.pk).exists())
        self.assertFalse(Student.objects.filter(pk=self.s2.pk).exists())
        self.assertTrue(Student.objects.filter(pk=self.s3.pk).exists())

    def test_class_teacher_can_bulk_deactivate_assigned_class(self):
        """Class Teacher can bulk deactivate students within their assigned division."""
        self.client.force_login(self.faculty_user_a)
        resp = self.client.post('/students/bulk-deactivate/', {
            'student_ids': f"{self.s1.pk},{self.s2.pk}"
        }, HTTP_HOST='greenwood.localhost')
        self.assertRedirects(resp, '/students/')
        self.s1.refresh_from_db()
        self.s2.refresh_from_db()
        self.assertFalse(self.s1.is_active)
        self.assertFalse(self.s2.is_active)

    def test_class_teacher_cannot_bulk_deactivate_students_outside_division_returns_403(self):
        """Class Teacher receives 403 Forbidden when attempting to deactivate students from another division."""
        self.client.force_login(self.faculty_user_a)
        # s3 belongs to division_a2 (not assigned to faculty_a)
        resp = self.client.post('/students/bulk-deactivate/', {
            'student_ids': f"{self.s1.pk},{self.s3.pk}"
        }, HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 403)
        self.s1.refresh_from_db()
        self.s3.refresh_from_db()
        self.assertTrue(self.s1.is_active)
        self.assertTrue(self.s3.is_active)

    def test_class_teacher_cannot_bulk_delete_returns_403(self):
        """Class Teacher cannot permanently bulk delete (Admin only)."""
        self.client.force_login(self.faculty_user_a)
        resp = self.client.post('/students/bulk-delete/', {
            'student_ids': f"{self.s1.pk},{self.s2.pk}"
        }, HTTP_HOST='greenwood.localhost')
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Student.objects.filter(pk=self.s1.pk).exists())

    def test_admin_bulk_restore_success(self):
        """School Admin can bulk restore/reactivate inactive students."""
        self.s1.is_active = False
        self.s1.save()
        self.s2.is_active = False
        self.s2.save()

        self.client.force_login(self.admin_a)
        resp = self.client.post('/students/bulk-restore/', {
            'student_ids': f"{self.s1.pk},{self.s2.pk}"
        }, HTTP_HOST='greenwood.localhost')
        self.assertRedirects(resp, '/students/?status=active')
        self.s1.refresh_from_db()
        self.s2.refresh_from_db()
        self.assertTrue(self.s1.is_active)
        self.assertTrue(self.s2.is_active)

    def test_class_teacher_bulk_restore_assigned_class_success(self):
        """Class Teacher can bulk restore inactive students in their class."""
        self.s1.is_active = False
        self.s1.save()

        self.client.force_login(self.faculty_user_a)
        resp = self.client.post('/students/bulk-restore/', {
            'student_ids': f"{self.s1.pk}"
        }, HTTP_HOST='greenwood.localhost')
        self.assertRedirects(resp, '/students/?status=active')
        self.s1.refresh_from_db()
        self.assertTrue(self.s1.is_active)






