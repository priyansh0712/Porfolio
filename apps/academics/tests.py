"""
Automated Unit and Integration Tests for Academics App.

Tests cover:
  - Multi-tenant isolation for all academic models.
  - AcademicYear single-active session atomic toggle.
  - Standard, Division, and Subject validation & constraints.
  - ClassTeacherAllocation and SubjectTeacherAllocation constraint integrity.
  - Cross-tenant and inactive faculty assignment prevention.
  - Multi-tenant form scoping and validation.
"""
from datetime import date, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.tenants.models import School
from apps.tenants.context import set_current_tenant
from apps.accounts.models import User
from apps.faculty.models import Faculty
from apps.academics.models import (
    AcademicYear,
    Standard,
    Division,
    Subject,
    ClassTeacherAllocation,
    SubjectTeacherAllocation,
)
from apps.academics.forms import (
    AcademicYearForm,
    StandardForm,
    DivisionForm,
    SubjectForm,
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

        # Create active faculty for School A
        self.faculty_a1 = Faculty.objects.create(
            school=self.school_a,
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
        """Subject codes are auto-uppercased and unique per school."""
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

    def test_subject_teacher_unique_allocation(self):
        """Strictly 1 primary Subject Teacher per division + subject per academic year."""
        alloc1 = SubjectTeacherAllocation.objects.create(
            school=self.school_a,
            academic_year=self.year,
            division=self.division,
            subject=self.subject,
            faculty=self.faculty_a1,
        )
        self.assertIsNotNone(alloc1.pk)

        # Duplicate create raises IntegrityError
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                SubjectTeacherAllocation.objects.create(
                    school=self.school_a,
                    academic_year=self.year,
                    division=self.division,
                    subject=self.subject,
                    faculty=self.faculty_a2,
                )

        # Reassignment using AcademicService.assign_subject_teacher updates cleanly
        alloc2, created = AcademicService.assign_subject_teacher(
            self.school_a,
            self.year,
            self.division,
            self.subject,
            self.faculty_a2,
        )
        self.assertFalse(created)
        self.assertEqual(alloc2.faculty, self.faculty_a2)

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
