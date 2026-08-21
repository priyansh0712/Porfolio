"""
Automated Unit and Integration Tests for Academics App.

Tests cover:
  - Multi-tenant isolation for all academic models.
  - AcademicYear single-active session atomic toggle.
  - Standard, Division, and Subject validation & constraints.
  - ClassTeacherAllocation and SubjectTeacherAllocation constraint integrity.
  - Cross-tenant and inactive faculty assignment prevention.
  - Multi-tenant form scoping and validation.
  - View-level authorization and role permissions (SchoolAdminRequiredMixin, TenantRoleAccessMiddleware).
  - Academic Hub CRUD views and Allocation workflows.
"""
from datetime import date, timedelta
from django.test import TestCase, Client
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.tenants.models import School
from apps.tenants.context import set_current_tenant
from apps.accounts.models import User
from apps.faculty.models import Faculty
from apps.academics.models import (
    AcademicYear,
    Standard,
    Division,
    Subject,
    ClassCurriculum,
    ClassTeacherAllocation,
    SubjectTeacherAllocation,
)
from apps.academics.forms import (
    AcademicYearForm,
    StandardForm,
    DivisionForm,
    SubjectForm,
    ClassCurriculumForm,
    ClassTeacherAllocationForm,
    SubjectTeacherAllocationForm,
)
from apps.academics.services import AcademicService


class AcademicsBaseTestCase(TestCase):
    """Base setup with two isolated school tenants and test faculty."""

    def setUp(self):
        super().setUp()
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

        # Users
        self.admin_user_a = User.objects.create_user(
            email='admin@greenwood.com',
            username='admin_gw',
            password='Password@123',
            role=User.Role.SCHOOL_ADMIN,
            school=self.school_a,
        )
        self.admin_user_b = User.objects.create_user(
            email='admin@oakridge.com',
            username='admin_oak',
            password='Password@123',
            role=User.Role.SCHOOL_ADMIN,
            school=self.school_b,
        )
        self.faculty_user_a = User.objects.create_user(
            email='anand.sharma@greenwood.com',
            username='anand_gw',
            password='Password@123',
            role=User.Role.FACULTY,
            school=self.school_a,
        )
        self.superadmin_user = User.objects.create_user(
            email='super@ourapp.com',
            username='superadmin',
            password='Password@123',
            role=User.Role.SUPER_ADMIN,
            school=None,
        )

        # Create active faculty for School A
        self.faculty_a1 = Faculty.objects.create(
            school=self.school_a,
            user=self.faculty_user_a,
            first_name='Anand',
            last_name='Sharma',
            email='anand.sharma@greenwood.com',
            employee_code='GW-FAC-001',
            department='Mathematics',
            is_active=True,
        )
        self.faculty_a2 = Faculty.objects.create(
            school=self.school_a,
            first_name='Pooja',
            last_name='Patel',
            email='pooja.patel@greenwood.com',
            employee_code='GW-FAC-002',
            department='Science',
            is_active=True,
        )
        self.faculty_a_inactive = Faculty.objects.create(
            school=self.school_a,
            first_name='Rohan',
            last_name='Mehta',
            email='rohan.mehta@greenwood.com',
            employee_code='GW-FAC-003',
            department='English',
            is_active=False,
        )

        # Create faculty for School B
        self.faculty_b = Faculty.objects.create(
            school=self.school_b,
            first_name='Vikram',
            last_name='Singh',
            email='vikram.singh@oakridge.com',
            employee_code='OAK-FAC-001',
            department='Mathematics',
            is_active=True,
        )

    def tearDown(self):
        set_current_tenant(None)
        super().tearDown()


class AcademicModelTests(AcademicsBaseTestCase):
    """Unit tests for AcademicYear, Standard, Division, and Subject models."""

    def test_academic_year_single_active_atomic_toggle(self):
        """Setting a new AcademicYear as is_current=True auto-deactivates previous active years."""
        set_current_tenant(self.school_a)

        year1 = AcademicYear.objects.create(
            school=self.school_a,
            name='2025-2026',
            start_date=date(2025, 6, 1),
            end_date=date(2026, 4, 30),
            is_current=True,
        )
        self.assertTrue(year1.is_current)

        year2 = AcademicYear.objects.create(
            school=self.school_a,
            name='2026-2027',
            start_date=date(2026, 6, 1),
            end_date=date(2027, 4, 30),
            is_current=True,
        )

        year1.refresh_from_db()
        year2.refresh_from_db()
        self.assertFalse(year1.is_current, "Year 1 must be deactivated when Year 2 is set active.")
        self.assertTrue(year2.is_current, "Year 2 must be the active year.")

    def test_academic_year_date_validation(self):
        """AcademicYear raises ValidationError if start_date >= end_date."""
        year = AcademicYear(
            school=self.school_a,
            name='Invalid Dates',
            start_date=date(2026, 6, 1),
            end_date=date(2026, 5, 1),
        )
        with self.assertRaises(ValidationError):
            year.clean()

    def test_standards_ordering_and_unique_constraint(self):
        """Standards sort by order_index and enforce unique name per school."""
        set_current_tenant(self.school_a)

        std10 = Standard.objects.create(school=self.school_a, name='Standard 10', order_index=10)
        std1 = Standard.objects.create(school=self.school_a, name='Standard 1', order_index=1)
        std_ukg = Standard.objects.create(school=self.school_a, name='UKG', order_index=0)

        standards = list(Standard.objects.filter(school=self.school_a))
        self.assertEqual(standards, [std_ukg, std1, std10], "Standards must sort chronologically by order_index.")

        # Duplicate Standard name in same school raises IntegrityError
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Standard.objects.create(school=self.school_a, name='Standard 10', order_index=11)

    def test_division_uniqueness_and_hierarchy(self):
        """Divisions belong to Standards with uniqueness on [school, standard, name]."""
        set_current_tenant(self.school_a)

        std10 = Standard.objects.create(school=self.school_a, name='Standard 10', order_index=10)
        div_a = Division.objects.create(school=self.school_a, standard=std10, name='A')

        self.assertEqual(str(div_a), 'Standard 10 - A')

        # Duplicate division under same standard in same school fails
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Division.objects.create(school=self.school_a, standard=std10, name='A')

        # Same division name under a different standard succeeds
        std9 = Standard.objects.create(school=self.school_a, name='Standard 9', order_index=9)
        div_9a = Division.objects.create(school=self.school_a, standard=std9, name='A')
        self.assertIsNotNone(div_9a.pk)

    def test_subject_code_uppercase_and_uniqueness(self):
        """Subject codes are auto-uppercased and unique per school when provided."""
        set_current_tenant(self.school_a)

        subj = Subject.objects.create(
            school=self.school_a,
            name='Mathematics',
            code='math-01',
            subject_type=Subject.SubjectType.CORE,
        )
        self.assertEqual(subj.code, 'MATH-01', "Code must be auto-uppercased.")

        # Duplicate code in same school fails
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Subject.objects.create(
                    school=self.school_a,
                    name='Higher Mathematics',
                    code='MATH-01',
                )

    def test_subject_code_optional_and_multiple_blank_allowed(self):
        """Subject code is optional. Multiple subjects can have empty code without constraint collision."""
        set_current_tenant(self.school_a)

        s1 = Subject.objects.create(school=self.school_a, name='Drawing', code='')
        s2 = Subject.objects.create(school=self.school_a, name='Music', code='')

        self.assertEqual(s1.code, '')
        self.assertEqual(s2.code, '')
        self.assertEqual(str(s1), 'Drawing')

        # Form validation allows blank code
        form = SubjectForm(data={'name': 'Physical Education', 'code': '', 'subject_type': 'CORE', 'is_active': True}, tenant=self.school_a)
        self.assertTrue(form.is_valid(), form.errors)

    def test_multi_tenant_isolation(self):
        """Records from School A must not appear in School B queries."""
        set_current_tenant(self.school_a)
        AcademicYear.objects.create(school=self.school_a, name='2026-2027', start_date=date(2026, 6, 1), end_date=date(2027, 4, 30))
        Standard.objects.create(school=self.school_a, name='Standard 10', order_index=10)

        # Switch context to School B
        set_current_tenant(self.school_b)
        self.assertEqual(AcademicYear.objects.count(), 0)
        self.assertEqual(Standard.objects.count(), 0)


class AllocationModelTests(AcademicsBaseTestCase):
    """Unit tests for ClassTeacherAllocation and SubjectTeacherAllocation constraints."""

    def setUp(self):
        super().setUp()
        set_current_tenant(self.school_a)
        self.year = AcademicYear.objects.create(
            school=self.school_a,
            name='2026-2027',
            start_date=date(2026, 6, 1),
            end_date=date(2027, 4, 30),
            is_current=True,
        )
        self.standard = Standard.objects.create(school=self.school_a, name='Standard 10', order_index=10)
        self.division = Division.objects.create(school=self.school_a, standard=self.standard, name='A')
        self.subject = Subject.objects.create(school=self.school_a, name='Mathematics', code='MATH-10')

    def test_class_teacher_unique_allocation_per_division_year(self):
        """Strictly 1 Class Teacher per division per academic year."""
        alloc1 = ClassTeacherAllocation.objects.create(
            school=self.school_a,
            academic_year=self.year,
            division=self.division,
            faculty=self.faculty_a1,
        )
        self.assertIsNotNone(alloc1.pk)

        # Attempting duplicate create raises IntegrityError
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                ClassTeacherAllocation.objects.create(
                    school=self.school_a,
                    academic_year=self.year,
                    division=self.division,
                    faculty=self.faculty_a2,
                )

        # Reassignment using AcademicService.assign_class_teacher updates cleanly
        alloc2, created = AcademicService.assign_class_teacher(
            self.school_a,
            self.year,
            self.division,
            self.faculty_a2,
        )
        self.assertFalse(created, "Reassigning existing class teacher updates the row rather than creating duplicate.")
        self.assertEqual(alloc2.faculty, self.faculty_a2)

    def test_subject_teacher_multi_allocation_and_uniqueness(self):
        """Allows multiple teachers (co-teaching) per subject+division, but prevents exact duplicates."""
        alloc1 = SubjectTeacherAllocation.objects.create(
            school=self.school_a,
            academic_year=self.year,
            division=self.division,
            subject=self.subject,
            faculty=self.faculty_a1,
        )
        self.assertIsNotNone(alloc1.pk)

        # Adding a second teacher (co-teacher) to the same subject and division succeeds
        alloc2, created = AcademicService.assign_subject_teacher(
            self.school_a,
            self.year,
            self.division,
            self.subject,
            self.faculty_a2,
        )
        self.assertTrue(created)
        self.assertEqual(
            SubjectTeacherAllocation.objects.filter(
                school=self.school_a,
                academic_year=self.year,
                division=self.division,
                subject=self.subject,
            ).count(),
            2,
            "Must support 2 or more co-teachers for the same subject in the same class.",
        )

        # Duplicate assignment of the SAME faculty to the SAME subject+division raises IntegrityError
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                SubjectTeacherAllocation.objects.create(
                    school=self.school_a,
                    academic_year=self.year,
                    division=self.division,
                    subject=self.subject,
                    faculty=self.faculty_a1,
                )

    def test_cross_tenant_faculty_assignment_prevented(self):
        """Assigning faculty from School B to School A raises ValidationError."""
        alloc = ClassTeacherAllocation(
            school=self.school_a,
            academic_year=self.year,
            division=self.division,
            faculty=self.faculty_b,
        )
        with self.assertRaises(ValidationError):
            alloc.clean()

    def test_inactive_faculty_assignment_prevented(self):
        """Assigning inactive faculty raises ValidationError."""
        alloc = ClassTeacherAllocation(
            school=self.school_a,
            academic_year=self.year,
            division=self.division,
            faculty=self.faculty_a_inactive,
        )
        with self.assertRaises(ValidationError):
            alloc.clean()


class AcademicFormTests(AcademicsBaseTestCase):
    """Unit tests for Academic Forms validation and tenant scoping."""

    def test_academic_year_form_validation(self):
        """AcademicYearForm validates unique name within tenant and date ordering."""
        form = AcademicYearForm(
            data={
                'name': '2026-2027',
                'start_date': '2026-06-01',
                'end_date': '2026-05-01',
                'is_current': True,
            },
            tenant=self.school_a,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('end_date', form.errors)

    def test_standard_and_subject_forms(self):
        """StandardForm and SubjectForm validate required fields and codes."""
        std_form = StandardForm(
            data={'name': 'Standard 10', 'order_index': 10, 'is_active': True},
            tenant=self.school_a,
        )
        self.assertTrue(std_form.is_valid())

        subj_form = SubjectForm(
            data={'name': 'Mathematics', 'code': 'math-01', 'subject_type': 'CORE', 'is_active': True},
            tenant=self.school_a,
        )
        self.assertTrue(subj_form.is_valid())
        self.assertEqual(subj_form.cleaned_data['code'], 'MATH-01')


class AcademicViewSecurityTests(AcademicsBaseTestCase):
    """Integration tests for view security, authentication, and role authorization."""

    def test_unauthenticated_user_redirected_to_login(self):
        """Unauthenticated request to /academics/ is redirected to login."""
        response = self.client.get('/academics/', HTTP_HOST='greenwood.localhost')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_super_admin_forbidden_from_academics(self):
        """Platform Super Admin is forbidden (HTTP 403) from accessing tenant academic hub."""
        self.client.force_login(self.superadmin_user)
        response = self.client.get('/academics/', HTTP_HOST='greenwood.localhost')
        self.assertEqual(response.status_code, 403)

    def test_faculty_forbidden_from_academics_hub(self):
        """Faculty user is forbidden (HTTP 403) from accessing school admin academic hub."""
        self.client.force_login(self.faculty_user_a)
        response = self.client.get('/academics/', HTTP_HOST='greenwood.localhost')
        self.assertEqual(response.status_code, 403)

    def test_school_admin_access_allowed(self):
        """School Admin of School A can access School A academic hub."""
        self.client.force_login(self.admin_user_a)
        response = self.client.get('/academics/', HTTP_HOST='greenwood.localhost')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Academic Management")

    def test_cross_tenant_school_admin_forbidden(self):
        """School Admin of School B cannot access School A academic hub."""
        self.client.force_login(self.admin_user_b)
        response = self.client.get('/academics/', HTTP_HOST='greenwood.localhost')
        self.assertEqual(response.status_code, 403)


class AcademicCRUDViewTests(AcademicsBaseTestCase):
    """Integration tests for CRUD endpoints and allocation workflows."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin_user_a)

    def test_academic_year_crud_and_set_current(self):
        """Admin can create, edit, set current, and delete AcademicYear via views."""
        # 1. Create AcademicYear
        create_resp = self.client.post(
            '/academics/years/create/',
            {
                'name': '2026-2027',
                'start_date': '2026-06-01',
                'end_date': '2027-04-30',
                'is_current': True,
            },
            HTTP_HOST='greenwood.localhost',
        )
        self.assertEqual(create_resp.status_code, 302)

        set_current_tenant(self.school_a)
        year = AcademicYear.objects.get(school=self.school_a, name='2026-2027')
        self.assertTrue(year.is_current)

        # 2. Create second AcademicYear and set it active
        self.client.post(
            '/academics/years/create/',
            {
                'name': '2027-2028',
                'start_date': '2027-06-01',
                'end_date': '2028-04-30',
                'is_current': False,
            },
            HTTP_HOST='greenwood.localhost',
        )
        year2 = AcademicYear.objects.get(school=self.school_a, name='2027-2028')
        self.assertFalse(year2.is_current)

        # Toggle year2 as current
        self.client.post(f'/academics/years/{year2.id}/set-current/', HTTP_HOST='greenwood.localhost')
        year.refresh_from_db()
        year2.refresh_from_db()
        self.assertFalse(year.is_current)
        self.assertTrue(year2.is_current)

    def test_standard_and_division_views(self):
        """Admin can create Standards and Divisions via views."""
        # Create Standard
        std_resp = self.client.post(
            '/academics/standards/create/',
            {
                'name': 'Standard 10',
                'order_index': 10,
                'is_active': True,
            },
            HTTP_HOST='greenwood.localhost',
        )
        self.assertEqual(std_resp.status_code, 302)

        set_current_tenant(self.school_a)
        std = Standard.objects.get(school=self.school_a, name='Standard 10')

        # Create Division under Standard 10
        div_resp = self.client.post(
            '/academics/divisions/create/',
            {
                'standard': std.id,
                'name': 'A',
                'is_active': True,
            },
            HTTP_HOST='greenwood.localhost',
        )
        self.assertEqual(div_resp.status_code, 302)
        self.assertTrue(Division.objects.filter(school=self.school_a, standard=std, name='A').exists())

    def test_subject_and_allocation_views(self):
        """Admin can create Subjects and allocate Class and Subject Teachers."""
        set_current_tenant(self.school_a)
        year = AcademicYear.objects.create(
            school=self.school_a,
            name='2026-2027',
            start_date=date(2026, 6, 1),
            end_date=date(2027, 4, 30),
            is_current=True,
        )
        std = Standard.objects.create(school=self.school_a, name='Standard 10', order_index=10)
        div = Division.objects.create(school=self.school_a, standard=std, name='A')

        # Create Subject
        self.client.post(
            '/academics/subjects/create/',
            {
                'name': 'Science',
                'code': 'SCI-10',
                'subject_type': 'CORE',
                'is_active': True,
            },
            HTTP_HOST='greenwood.localhost',
        )
        sub = Subject.objects.get(school=self.school_a, code='SCI-10')

        # Assign Class Teacher
        alloc_resp = self.client.post(
            '/academics/allocations/class-teacher/',
            {
                'academic_year': year.id,
                'division': div.id,
                'faculty': self.faculty_a1.id,
            },
            HTTP_HOST='greenwood.localhost',
        )
        self.assertEqual(alloc_resp.status_code, 302)
        self.assertTrue(ClassTeacherAllocation.objects.filter(school=self.school_a, division=div, faculty=self.faculty_a1).exists())

        # Assign Subject Teacher
        sub_alloc_resp = self.client.post(
            '/academics/allocations/subject-teacher/',
            {
                'academic_year': year.id,
                'division': div.id,
                'subject': sub.id,
                'faculty': self.faculty_a1.id,
            },
            HTTP_HOST='greenwood.localhost',
        )
        self.assertEqual(sub_alloc_resp.status_code, 302)
        alloc = SubjectTeacherAllocation.objects.get(school=self.school_a, division=div, subject=sub, faculty=self.faculty_a1)

        # Edit Subject Teacher allocation via SubjectTeacherUpdateView
        edit_resp = self.client.post(
            f'/academics/allocations/{alloc.id}/edit-subject-teacher/',
            {
                'faculty': self.faculty_a2.id,
            },
            HTTP_HOST='greenwood.localhost',
        )
        self.assertEqual(edit_resp.status_code, 302)
        alloc.refresh_from_db()
        self.assertEqual(alloc.faculty, self.faculty_a2)

        # Delete Subject Teacher allocation via SubjectTeacherDeleteView
        del_resp = self.client.post(
            f'/academics/allocations/{alloc.id}/delete-subject-teacher/',
            HTTP_HOST='greenwood.localhost',
        )
        self.assertEqual(del_resp.status_code, 302)
        self.assertFalse(SubjectTeacherAllocation.objects.filter(pk=alloc.id).exists())


class ClassCurriculumWorkflowTests(AcademicsBaseTestCase):
    """
    Tests for Grade/Class-wise Curriculum Management:
      1. Grade 1 vs Grade 2 curriculum isolation (Math, English, EVS vs Math, English, Science, Hindi).
      2. Grade 1 does not show Science or Hindi.
      3. Grade 2 does not show EVS unless assigned.
      4. Mathematics can exist in both grades without duplicating the global Subject Master.
      5. Changing academic year isolates curriculum assignments.
      6. Teaching assignments only show subjects belonging to that grade's curriculum.
      7. Duplicate Grade + Subject + Academic Year is rejected.
      8. Multi-tenant isolation for curriculum.
      9. Curriculum CRUD views (assign, remove with allocation protection).
    """

    def setUp(self):
        super().setUp()
        set_current_tenant(self.school_a)
        self.client.force_login(self.admin_user_a)

        # Academic Years
        self.year_2026 = AcademicYear.objects.create(
            school=self.school_a,
            name='2026-2027',
            start_date=date(2026, 6, 1),
            end_date=date(2027, 4, 30),
            is_current=True,
        )
        self.year_2027 = AcademicYear.objects.create(
            school=self.school_a,
            name='2027-2028',
            start_date=date(2027, 6, 1),
            end_date=date(2028, 4, 30),
            is_current=False,
        )

        # Standards / Grades
        self.grade_1 = Standard.objects.create(school=self.school_a, name='Grade 1', order_index=1)
        self.grade_2 = Standard.objects.create(school=self.school_a, name='Grade 2', order_index=2)

        # Divisions
        self.div_1a = Division.objects.create(school=self.school_a, standard=self.grade_1, name='A')
        self.div_2a = Division.objects.create(school=self.school_a, standard=self.grade_2, name='A')

        # Global Subject Master records
        self.sub_math = Subject.objects.create(school=self.school_a, name='Mathematics', code='MATH-10', subject_type='CORE')
        self.sub_eng = Subject.objects.create(school=self.school_a, name='English', code='ENG-10', subject_type='CORE')
        self.sub_evs = Subject.objects.create(school=self.school_a, name='EVS', code='EVS-10', subject_type='CORE')
        self.sub_sci = Subject.objects.create(school=self.school_a, name='Science', code='SCI-10', subject_type='CORE')
        self.sub_hin = Subject.objects.create(school=self.school_a, name='Hindi', code='HIN-10', subject_type='ELECTIVE')

    def test_grade_1_and_grade_2_curriculum_setup(self):
        """
        Grade 1 is assigned Math, English, EVS.
        Grade 2 is assigned Math, English, Science, Hindi.
        Grade 1 must not contain Science or Hindi.
        Grade 2 must not contain EVS.
        Math is shared across both grades using a single Subject master record.
        """
        # Assign Grade 1 curriculum
        c1 = ClassCurriculum.objects.create(school=self.school_a, academic_year=self.year_2026, standard=self.grade_1, subject=self.sub_math)
        c2 = ClassCurriculum.objects.create(school=self.school_a, academic_year=self.year_2026, standard=self.grade_1, subject=self.sub_eng)
        c3 = ClassCurriculum.objects.create(school=self.school_a, academic_year=self.year_2026, standard=self.grade_1, subject=self.sub_evs)

        # Assign Grade 2 curriculum
        c4 = ClassCurriculum.objects.create(school=self.school_a, academic_year=self.year_2026, standard=self.grade_2, subject=self.sub_math)
        c5 = ClassCurriculum.objects.create(school=self.school_a, academic_year=self.year_2026, standard=self.grade_2, subject=self.sub_eng)
        c6 = ClassCurriculum.objects.create(school=self.school_a, academic_year=self.year_2026, standard=self.grade_2, subject=self.sub_sci)
        c7 = ClassCurriculum.objects.create(school=self.school_a, academic_year=self.year_2026, standard=self.grade_2, subject=self.sub_hin)

        # Verify Grade 1 subjects
        g1_subjects = list(Subject.objects.filter(class_curriculums__standard=self.grade_1, class_curriculums__academic_year=self.year_2026))
        self.assertIn(self.sub_math, g1_subjects)
        self.assertIn(self.sub_eng, g1_subjects)
        self.assertIn(self.sub_evs, g1_subjects)
        self.assertNotIn(self.sub_sci, g1_subjects)
        self.assertNotIn(self.sub_hin, g1_subjects)
        self.assertEqual(len(g1_subjects), 3)

        # Verify Grade 2 subjects
        g2_subjects = list(Subject.objects.filter(class_curriculums__standard=self.grade_2, class_curriculums__academic_year=self.year_2026))
        self.assertIn(self.sub_math, g2_subjects)
        self.assertIn(self.sub_eng, g2_subjects)
        self.assertIn(self.sub_sci, g2_subjects)
        self.assertIn(self.sub_hin, g2_subjects)
        self.assertNotIn(self.sub_evs, g2_subjects)
        self.assertEqual(len(g2_subjects), 4)

        # Verify Global Subject Master was NOT duplicated
        math_count = Subject.objects.filter(school=self.school_a, code='MATH-10').count()
        self.assertEqual(math_count, 1)

    def test_curriculum_matrix_service(self):
        """AcademicService.get_class_curriculum_matrix returns structured grade-by-grade curriculums."""
        ClassCurriculum.objects.create(school=self.school_a, academic_year=self.year_2026, standard=self.grade_1, subject=self.sub_math)
        ClassCurriculum.objects.create(school=self.school_a, academic_year=self.year_2026, standard=self.grade_1, subject=self.sub_eng)
        ClassCurriculum.objects.create(school=self.school_a, academic_year=self.year_2026, standard=self.grade_2, subject=self.sub_sci)

        matrix = AcademicService.get_class_curriculum_matrix(self.school_a, self.year_2026)
        self.assertEqual(len(matrix), 2)

        g1_data = next(m for m in matrix if m['standard'] == self.grade_1)
        self.assertEqual(g1_data['subject_count'], 2)
        g1_sub_names = [c.subject.name for c in g1_data['curriculum_subjects']]
        self.assertEqual(sorted(g1_sub_names), ['English', 'Mathematics'])

        g2_data = next(m for m in matrix if m['standard'] == self.grade_2)
        self.assertEqual(g2_data['subject_count'], 1)
        self.assertEqual(g2_data['curriculum_subjects'][0].subject.name, 'Science')

    def test_academic_year_isolation(self):
        """Curriculum assignments in 2026-2027 do not carry to 2027-2028 unless explicitly created."""
        ClassCurriculum.objects.create(school=self.school_a, academic_year=self.year_2026, standard=self.grade_1, subject=self.sub_math)

        # 2026-2027 has 1 subject
        matrix_2026 = AcademicService.get_class_curriculum_matrix(self.school_a, self.year_2026)
        g1_2026 = next(m for m in matrix_2026 if m['standard'] == self.grade_1)
        self.assertEqual(g1_2026['subject_count'], 1)

        # 2027-2028 has 0 subjects
        matrix_2027 = AcademicService.get_class_curriculum_matrix(self.school_a, self.year_2027)
        g1_2027 = next(m for m in matrix_2027 if m['standard'] == self.grade_1)
        self.assertEqual(g1_2027['subject_count'], 0)

    def test_allocation_matrix_only_shows_grade_curriculum_subjects(self):
        """Teaching Assignment allocation matrix must only list subjects configured in that grade's curriculum."""
        # Grade 1 has only Math
        ClassCurriculum.objects.create(school=self.school_a, academic_year=self.year_2026, standard=self.grade_1, subject=self.sub_math)
        # Grade 2 has Science and Hindi
        ClassCurriculum.objects.create(school=self.school_a, academic_year=self.year_2026, standard=self.grade_2, subject=self.sub_sci)
        ClassCurriculum.objects.create(school=self.school_a, academic_year=self.year_2026, standard=self.grade_2, subject=self.sub_hin)

        matrix = AcademicService.get_allocation_matrix(self.school_a, self.year_2026)

        g1_matrix = next(m for m in matrix if m['standard'] == self.grade_1)
        div_1a_data = g1_matrix['divisions'][0]
        g1_subject_names = [s['subject'].name for s in div_1a_data['subjects']]
        self.assertEqual(g1_subject_names, ['Mathematics'])
        self.assertNotIn('Science', g1_subject_names)
        self.assertNotIn('Hindi', g1_subject_names)

        g2_matrix = next(m for m in matrix if m['standard'] == self.grade_2)
        div_2a_data = g2_matrix['divisions'][0]
        g2_subject_names = [s['subject'].name for s in div_2a_data['subjects']]
        self.assertEqual(sorted(g2_subject_names), ['Hindi', 'Science'])
        self.assertNotIn('Mathematics', g2_subject_names)

    def test_duplicate_curriculum_assignment_prevented(self):
        """Assigning the same Subject to the same Grade in the same Academic Year must be rejected."""
        ClassCurriculum.objects.create(
            school=self.school_a,
            academic_year=self.year_2026,
            standard=self.grade_1,
            subject=self.sub_math,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClassCurriculum.objects.create(
                    school=self.school_a,
                    academic_year=self.year_2026,
                    standard=self.grade_1,
                    subject=self.sub_math,
                )

    def test_curriculum_views_add_and_delete(self):
        """Admin can assign and remove a subject from a grade curriculum via POST views."""
        # 1. Add subject via POST view
        resp = self.client.post(
            '/academics/curriculum/add/',
            {
                'academic_year': self.year_2026.id,
                'standard': self.grade_1.id,
                'subject': self.sub_math.id,
            },
            HTTP_HOST='greenwood.localhost',
        )
        self.assertEqual(resp.status_code, 302)
        curr = ClassCurriculum.objects.get(school=self.school_a, academic_year=self.year_2026, standard=self.grade_1, subject=self.sub_math)
        self.assertIsNotNone(curr)

        # 2. Delete subject via POST view
        del_resp = self.client.post(
            f'/academics/curriculum/{curr.id}/delete/',
            HTTP_HOST='greenwood.localhost',
        )
        self.assertEqual(del_resp.status_code, 302)
        self.assertFalse(ClassCurriculum.objects.filter(pk=curr.id).exists())

    def test_curriculum_deletion_prevented_when_teacher_assigned(self):
        """Curriculum subject cannot be removed if active teacher allocations exist for that subject in that year."""
        curr = ClassCurriculum.objects.create(
            school=self.school_a,
            academic_year=self.year_2026,
            standard=self.grade_1,
            subject=self.sub_math,
        )
        SubjectTeacherAllocation.objects.create(
            school=self.school_a,
            academic_year=self.year_2026,
            division=self.div_1a,
            subject=self.sub_math,
            faculty=self.faculty_a1,
        )

        del_resp = self.client.post(
            f'/academics/curriculum/{curr.id}/delete/',
            HTTP_HOST='greenwood.localhost',
        )
        self.assertEqual(del_resp.status_code, 302)
        # Verify it was NOT deleted
        self.assertTrue(ClassCurriculum.objects.filter(pk=curr.id).exists())

    def test_cross_tenant_curriculum_prevented(self):
        """School A cannot assign a subject or standard belonging to School B."""
        std_b = Standard.objects.create(school=self.school_b, name='Grade 1 B')
        sub_b = Subject.objects.create(school=self.school_b, name='French', code='FR-01')

        with self.assertRaises(ValidationError):
            curr = ClassCurriculum(
                school=self.school_a,
                academic_year=self.year_2026,
                standard=std_b,  # belongs to school B!
                subject=self.sub_math,
            )
            curr.clean()

