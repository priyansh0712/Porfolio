"""
Bulk Onboarding Unit Tests — Parsers, Validation Engine, Sample Generators & Stepper Wizard Views.
"""
from datetime import date
from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.tenants.models import School
from apps.accounts.models import User
from apps.faculty.models import Faculty
from apps.academics.models import AcademicYear, Standard, Division, Subject
from apps.students.models import Student
from apps.onboarding.services import (
    SampleTemplateService, BulkImportParser,
    BulkValidationService, BulkCommitService
)


class OnboardingTestBase(TestCase):
    """Base setup for onboarding tests."""

    def setUp(self):
        self.school = School.objects.create(
            name='St. Xavier School',
            subdomain='xavier',
            contact_email='admin@xavier.edu'
        )
        self.admin_user = User.objects.create_user(
            username='xavier_admin',
            email='admin@xavier.edu',
            password='TestPassword123!',
            first_name='Xavier',
            last_name='Admin',
            role=User.Role.SCHOOL_ADMIN,
            school=self.school
        )
        self.academic_year = AcademicYear.objects.create(
            school=self.school,
            name='2026-2027',
            start_date=date(2026, 6, 1),
            end_date=date(2027, 4, 30),
            is_current=True
        )


class SampleTemplateServiceTest(OnboardingTestBase):
    """Tests for SampleTemplateService generator."""

    def test_csv_generation(self):
        """Should generate non-empty CSV bytes for steps 1-4."""
        for step in (1, 2, 3, 4):
            content = SampleTemplateService.generate_csv(step)
            self.assertTrue(len(content) > 0)
            self.assertIn(b'First Name' if step in (1, 4) else b'Standard Name', content)

    def test_xlsx_generation(self):
        """Should generate valid non-empty XLSX bytes for steps 1-4."""
        for step in (1, 2, 3, 4):
            content = SampleTemplateService.generate_xlsx(step)
            self.assertTrue(len(content) > 0)
            self.assertTrue(content.startswith(b'PK'))  # Zip format header for xlsx


class BulkImportParserTest(OnboardingTestBase):
    """Tests for BulkImportParser."""

    def test_parse_csv(self):
        """Should parse raw CSV into row index and dict pairs."""
        csv_data = b"First Name,Last Name,Email,Employee Code,Department,Designation\nJohn,Doe,john@xavier.edu,FAC-101,Math,Teacher"
        f = SimpleUploadedFile("faculty.csv", csv_data, content_type="text/csv")
        parsed = BulkImportParser.parse(f, f.name)

        self.assertEqual(len(parsed), 1)
        r_idx, row_dict = parsed[0]
        self.assertEqual(r_idx, 2)
        self.assertEqual(row_dict['First Name'], 'John')
        self.assertEqual(row_dict['Email'], 'john@xavier.edu')


class BulkValidationServiceTest(OnboardingTestBase):
    """Tests for row-by-row validation across all 4 steps."""

    def test_step_1_validation(self):
        """Step 1 should validate required fields and detect duplicate emails/codes."""
        # Create existing faculty
        Faculty.objects.create(
            school=self.school,
            first_name='Existing',
            last_name='Teacher',
            email='existing@xavier.edu',
            employee_code='FAC-000',
            is_active=True
        )

        rows = [
            (2, {'First Name': 'Valid', 'Last Name': 'User', 'Email': 'new@xavier.edu', 'Employee Code': 'FAC-001', 'Department': 'Mathematics'}),
            (3, {'First Name': '', 'Last Name': 'Invalid', 'Email': 'existing@xavier.edu', 'Employee Code': 'FAC-000', 'Department': 'Mathematics'}),
        ]

        results = BulkValidationService.validate(self.school, 1, rows)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['status'], 'VALID')
        self.assertEqual(results[1]['status'], 'ERROR')
        self.assertIn("First Name is required", results[1]['errors'][0])

    def test_step_4_validation(self):
        """Step 4 student validation should check GR number uniqueness and class existence."""
        std = Standard.objects.create(school=self.school, name='Grade 10')
        div = Division.objects.create(school=self.school, standard=std, name='A')

        rows = [
            (2, {'GR Number': 'GR-100', 'First Name': 'Bob', 'Last Name': 'Marley', 'Standard Name': 'Grade 10', 'Division Name': 'A'}),
            (3, {'GR Number': 'GR-100', 'First Name': 'Alice', 'Last Name': 'Smith', 'Standard Name': 'Grade 99', 'Division Name': 'Z'}),
        ]

        results = BulkValidationService.validate(self.school, 4, rows)
        self.assertEqual(results[0]['status'], 'VALID')
        self.assertEqual(results[1]['status'], 'ERROR')


class BulkCommitServiceTest(OnboardingTestBase):
    """Tests for BulkCommitService atomic database actions."""

    def test_commit_step_1_faculty(self):
        """Commit step 1 should create Faculty and User records."""
        valid_rows = [{
            'row_index': 2,
            'data': {'First Name': 'Mark', 'Last Name': 'Twain', 'Email': 'mark@xavier.edu', 'Employee Code': 'FAC-999', 'Department': 'English'},
            'status': 'VALID',
            'errors': []
        }]

        count = BulkCommitService.commit_step_1_faculty(self.school, valid_rows)
        self.assertEqual(count, 1)
        self.assertTrue(Faculty.objects.filter(school=self.school, employee_code='FAC-999').exists())
        user = User.objects.get(username='mark@xavier.edu')
        self.assertTrue(user.check_password('Admin@123'))

    def test_commit_step_4_students(self):
        """Commit step 4 should create Student records and Student User logins."""
        std = Standard.objects.create(school=self.school, name='Grade 10')
        div = Division.objects.create(school=self.school, standard=std, name='A')

        valid_rows = [{
            'row_index': 2,
            'data': {'GR Number': 'GR-500', 'First Name': 'Sam', 'Last Name': 'Altman', 'Standard Name': 'Grade 10', 'Division Name': 'A', 'Roll Number': '15'},
            'status': 'VALID',
            'errors': []
        }]

        count = BulkCommitService.commit_step_4_students(self.school, valid_rows)
        self.assertEqual(count, 1)
        student = Student.objects.get(school=self.school, gr_number='GR-500')
        self.assertEqual(student.full_name, 'Sam Altman')
        self.assertIsNotNone(student.user)
        self.assertTrue(student.user.check_password('Admin@123'))

    def test_sibling_student_import_no_conflict(self):
        """Step 4 should successfully import siblings sharing the same parent email."""
        std = Standard.objects.create(school=self.school, name='Grade 10')
        div = Division.objects.create(school=self.school, standard=std, name='A')

        valid_rows = [
            {
                'row_index': 2,
                'data': {'GR Number': 'GR-101', 'First Name': 'Aryan', 'Last Name': 'Shah', 'Standard Name': 'Grade 10', 'Division Name': 'A', 'Parent Email': 'shah.family@gmail.com'},
                'status': 'VALID',
                'errors': []
            },
            {
                'row_index': 3,
                'data': {'GR Number': 'GR-102', 'First Name': 'Ananya', 'Last Name': 'Shah', 'Standard Name': 'Grade 10', 'Division Name': 'A', 'Parent Email': 'shah.family@gmail.com'},
                'status': 'VALID',
                'errors': []
            }
        ]

        count = BulkCommitService.commit_step_4_students(self.school, valid_rows)
        self.assertEqual(count, 2)
        s1 = Student.objects.get(school=self.school, gr_number='GR-101')
        s2 = Student.objects.get(school=self.school, gr_number='GR-102')
        self.assertIsNotNone(s1.user)
        self.assertIsNotNone(s2.user)


class OnboardingViewsTest(OnboardingTestBase):
    """Tests for onboarding views and AJAX endpoints."""

    def test_wizard_view_access(self):
        """Wizard view should render for School Admin with dynamic step columns context."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('onboarding:wizard'), HTTP_HOST='xavier.localhost:8000')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'onboarding/wizard.html')
        self.assertIn('step_columns_json', response.context)

    def test_sample_download_endpoint(self):
        """Sample download endpoint should return attachment response."""
        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse('onboarding:sample-download', kwargs={'step': 1, 'fmt': 'csv'}),
            HTTP_HOST='xavier.localhost:8000'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_custom_fields_sample_download_and_commit(self):
        """Step 4 sample template should dynamically include active StudentCustomField headers."""
        from apps.students.models import StudentCustomField
        StudentCustomField.objects.create(
            school=self.school,
            label='Aadhar Number',
            field_name='aadhar_number',
            field_type=StudentCustomField.FieldType.TEXT,
            is_active=True
        )

        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse('onboarding:sample-download', kwargs={'step': 4, 'fmt': 'csv'}),
            HTTP_HOST='xavier.localhost:8000'
        )
        self.assertEqual(response.status_code, 200)
        csv_content = response.content.decode('utf-8')
        self.assertIn('Aadhar Number', csv_content)

    def test_faculty_custom_fields_sample_download(self):
        """Step 1 sample template should dynamically include active FacultyCustomField headers."""
        from apps.faculty.models import FacultyCustomField
        FacultyCustomField.objects.create(
            school=self.school,
            label='Qualification',
            field_name='qualification',
            field_type=FacultyCustomField.FieldType.TEXT,
            is_active=True
        )

        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse('onboarding:sample-download', kwargs={'step': 1, 'fmt': 'csv'}),
            HTTP_HOST='xavier.localhost:8000'
        )
        self.assertEqual(response.status_code, 200)
        csv_content = response.content.decode('utf-8')
        self.assertIn('Qualification', csv_content)

    def test_dynamic_form_config_student_template(self):
        """Toggling student form field visibility in StudentFormFieldConfig should reflect in sample template."""
        from apps.students.models import StudentFormFieldConfig
        config = StudentFormFieldConfig.get_for_school(self.school)
        config.show_dob = False
        config.show_gender = False
        config.save()

        headers, _ = SampleTemplateService.get_template_headers_and_data(4, school=self.school)
        self.assertNotIn('Date of Birth', headers)
        self.assertNotIn('Gender', headers)
        self.assertIn('GR Number', headers)
        self.assertIn('First Name', headers)
