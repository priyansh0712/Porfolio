"""
Unit tests for Faculty views (MyClassView & MySubjectsView).
"""
from datetime import date
from django.test import TestCase
from django.urls import reverse

from apps.tenants.models import School
from apps.accounts.models import User
from apps.faculty.models import Faculty
from apps.academics.models import (
    AcademicYear, Standard, Division, Subject,
    ClassTeacherAllocation, SubjectTeacherAllocation
)
from apps.students.models import Student


class FacultyDashboardViewsTest(TestCase):
    """Tests for MyClassView and MySubjectsView."""

    def setUp(self):
        self.school = School.objects.create(
            name='Oxford High School',
            subdomain='oxford',
            contact_email='admin@oxford.edu'
        )
        self.teacher_user = User.objects.create_user(
            username='teacher@oxford.edu',
            email='teacher@oxford.edu',
            password='TestPassword123!',
            first_name='Sarah',
            last_name='Connor',
            role=User.Role.FACULTY,
            school=self.school
        )
        self.faculty = Faculty.objects.create(
            school=self.school,
            user=self.teacher_user,
            first_name='Sarah',
            last_name='Connor',
            email='teacher@oxford.edu',
            employee_code='FAC-777',
            is_active=True
        )
        self.academic_year = AcademicYear.objects.create(
            school=self.school,
            name='2026-2027',
            start_date=date(2026, 6, 1),
            end_date=date(2027, 4, 30),
            is_current=True
        )
        self.standard = Standard.objects.create(school=self.school, name='Grade 10')
        self.division = Division.objects.create(school=self.school, standard=self.standard, name='A')

        self.class_alloc = ClassTeacherAllocation.objects.create(
            school=self.school,
            academic_year=self.academic_year,
            division=self.division,
            faculty=self.faculty
        )

        self.subject = Subject.objects.create(
            school=self.school,
            name='Physics',
            code='PHY-10'
        )

        self.subject_alloc = SubjectTeacherAllocation.objects.create(
            school=self.school,
            academic_year=self.academic_year,
            division=self.division,
            subject=self.subject,
            faculty=self.faculty
        )

        self.student = Student.objects.create(
            school=self.school,
            academic_year=self.academic_year,
            standard=self.standard,
            division=self.division,
            gr_number='GR-999',
            full_name='John Connor',
            roll_number=1,
            is_active=True
        )

    def test_my_class_view_access(self):
        """Assigned Class Teacher can access /faculty/my-class/ and view student roster."""
        self.client.force_login(self.teacher_user)
        response = self.client.get(reverse('faculty:my_class'), HTTP_HOST='oxford.localhost:8000')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'faculty/my_class.html')
        self.assertEqual(len(response.context['students']), 1)
        self.assertEqual(response.context['students'][0].full_name, 'John Connor')

    def test_my_subjects_view_access(self):
        """Subject Teacher can access /faculty/my-subjects/ and view taught subjects."""
        self.client.force_login(self.teacher_user)
        response = self.client.get(reverse('faculty:my_subjects'), HTTP_HOST='oxford.localhost:8000')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'faculty/my_subjects.html')
        self.assertEqual(len(response.context['subject_rosters']), 1)
        self.assertEqual(response.context['subject_rosters'][0]['allocation'].subject.name, 'Physics')


class FacultyFormFieldConfigTest(TestCase):
    """Tests for FacultyFormFieldConfig model and update endpoint."""

    def setUp(self):
        self.school = School.objects.create(
            name='Xavier School',
            subdomain='xavier',
            contact_email='admin@xavier.edu'
        )
        self.admin_user = User.objects.create_user(
            username='admin@xavier.edu',
            email='admin@xavier.edu',
            password='TestPassword123!',
            role=User.Role.SCHOOL_ADMIN,
            school=self.school
        )

    def test_default_config_creation(self):
        """Default FacultyFormFieldConfig should be created with standard defaults."""
        from apps.faculty.models import FacultyFormFieldConfig
        config = FacultyFormFieldConfig.get_for_school(self.school)
        self.assertTrue(config.show_department)
        self.assertTrue(config.require_department)

    def test_update_form_config_endpoint(self):
        """School Admin should be able to update FacultyFormFieldConfig."""
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse('faculty:form_config_update'),
            {
                'show_phone_number': 'on',
                'require_phone_number': 'on',
                'show_employee_code': 'on',
                'require_employee_code': '',
                'show_department': 'on',
                'require_department': 'on',
                'show_designation': '',
                'require_designation': '',
            },
            HTTP_HOST='xavier.localhost:8000'
        )
        self.assertRedirects(response, '/faculty/?tab=custom_fields')
        from apps.faculty.models import FacultyFormFieldConfig
        config = FacultyFormFieldConfig.get_for_school(self.school)
        self.assertTrue(config.require_phone_number)
        self.assertFalse(config.show_designation)
