"""
Faculty Management Test Suite.

Covers:
  1. Tenant query scoping
  2. Cross-tenant ID manipulation blocked
  3. Faculty creation + linked User provisioning
  4. Faculty dashboard login restriction
  5. Sequence counter + auto-code generation
  6. Status toggle + SET_NULL integrity
"""
from django.test import TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware

from apps.accounts.models import User
from apps.faculty.models import Faculty, TenantSequence
from apps.faculty.services import FacultyCodeService, FacultyService
from apps.tenants.models import School


class FacultyTestBase(TestCase):
    """Shared fixtures for faculty tests."""

    @classmethod
    def setUpTestData(cls):
        # Create two schools (tenants)
        cls.school_a = School.objects.create(
            name='Greenwood Academy',
            subdomain='greenwood',
            contact_email='admin@greenwood.edu',
            is_active=True,
        )
        cls.school_b = School.objects.create(
            name='Blueridge School',
            subdomain='blueridge',
            contact_email='admin@blueridge.edu',
            is_active=True,
        )

        # School Admin users
        cls.admin_a = User.objects.create_user(
            username='admin_a@greenwood.edu',
            email='admin_a@greenwood.edu',
            password='TestPass123!',
            first_name='Admin',
            last_name='A',
            role=User.Role.SCHOOL_ADMIN,
            school=cls.school_a,
        )
        cls.admin_b = User.objects.create_user(
            username='admin_b@blueridge.edu',
            email='admin_b@blueridge.edu',
            password='TestPass123!',
            first_name='Admin',
            last_name='B',
            role=User.Role.SCHOOL_ADMIN,
            school=cls.school_b,
        )


class TenantQueryScopingTests(FacultyTestBase):
    """Test 1: School A admin sees only School A faculty."""

    def test_faculty_scoped_to_tenant(self):
        """Faculty queryset filtered by school returns only that school's faculty."""
        FacultyService.create_faculty(self.school_a, {
            'first_name': 'Alice', 'last_name': 'Smith',
            'email': 'alice@greenwood.edu', 'phone_number': '',
            'department': 'Science', 'designation': 'Teacher',
        })
        FacultyService.create_faculty(self.school_b, {
            'first_name': 'Bob', 'last_name': 'Jones',
            'email': 'bob@blueridge.edu', 'phone_number': '',
            'department': 'Math', 'designation': 'Teacher',
        })

        school_a_faculty = Faculty.objects.filter(school=self.school_a)
        school_b_faculty = Faculty.objects.filter(school=self.school_b)

        self.assertEqual(school_a_faculty.count(), 1)
        self.assertEqual(school_b_faculty.count(), 1)
        self.assertEqual(school_a_faculty.first().email, 'alice@greenwood.edu')
        self.assertEqual(school_b_faculty.first().email, 'bob@blueridge.edu')


class CrossTenantBlockedTests(FacultyTestBase):
    """Test 2: Cross-tenant ID manipulation is blocked."""

    def test_cross_tenant_queryset_returns_empty(self):
        """Querying School B faculty with School A filter returns nothing."""
        faculty_b = FacultyService.create_faculty(self.school_b, {
            'first_name': 'Charlie', 'last_name': 'Brown',
            'email': 'charlie@blueridge.edu', 'phone_number': '',
            'department': 'English', 'designation': 'HOD',
        })

        # School A admin tries to access School B faculty
        result = Faculty.objects.filter(school=self.school_a, pk=faculty_b.pk)
        self.assertEqual(result.count(), 0)


class FacultyCreationLinkedUserTests(FacultyTestBase):
    """Test 3: Faculty creation provisions linked User correctly."""

    def test_linked_user_created_with_correct_attributes(self):
        """Creating faculty auto-creates User with FACULTY role, unusable password."""
        faculty = FacultyService.create_faculty(self.school_a, {
            'first_name': 'Diana', 'last_name': 'Prince',
            'email': 'diana@greenwood.edu', 'phone_number': '+91 98765 43210',
            'department': 'History', 'designation': 'Senior Teacher',
        })

        self.assertIsNotNone(faculty.user)
        self.assertEqual(faculty.user.email, 'diana@greenwood.edu')
        self.assertEqual(faculty.user.role, User.Role.FACULTY)
        self.assertEqual(faculty.user.school, self.school_a)
        self.assertTrue(faculty.user.is_active)
        self.assertFalse(faculty.user.has_usable_password())

    def test_employee_code_auto_generated(self):
        """Employee code auto-generated when not provided."""
        faculty = FacultyService.create_faculty(self.school_a, {
            'first_name': 'Eve', 'last_name': 'Adams',
            'email': 'eve@greenwood.edu', 'phone_number': '',
            'department': 'Art', 'designation': 'Teacher',
        })
        self.assertTrue(faculty.employee_code.startswith('GREENWOOD-FAC-'))


class FacultyLoginRestrictionTests(FacultyTestBase):
    """Test 4: Faculty users cannot log into the dashboard."""

    def test_faculty_user_cannot_login_with_password(self):
        """Faculty User has unusable password — login attempt fails."""
        faculty = FacultyService.create_faculty(self.school_a, {
            'first_name': 'Frank', 'last_name': 'Castle',
            'email': 'frank@greenwood.edu', 'phone_number': '',
            'department': 'PE', 'designation': 'Coach',
        })
        # Attempt login with the faculty user's email
        login_success = self.client.login(
            email='frank@greenwood.edu',
            password='anything',
        )
        self.assertFalse(login_success)


class SequenceCounterAutoCodeTests(FacultyTestBase):
    """Test 5: FacultyCodeService generates sequential codes correctly."""

    def test_sequential_code_generation(self):
        """Auto-generates GREENWOOD-FAC-001, GREENWOOD-FAC-002 etc."""
        code1 = FacultyCodeService.generate_next_code(self.school_a)
        code2 = FacultyCodeService.generate_next_code(self.school_a)

        self.assertEqual(code1, 'GREENWOOD-FAC-001')
        self.assertEqual(code2, 'GREENWOOD-FAC-002')

    def test_different_schools_have_independent_sequences(self):
        """School A and School B counters are independent."""
        code_a = FacultyCodeService.generate_next_code(self.school_a)
        code_b = FacultyCodeService.generate_next_code(self.school_b)

        self.assertEqual(code_a, 'GREENWOOD-FAC-001')
        self.assertEqual(code_b, 'BLUERIDGE-FAC-001')

    def test_sequence_counter_persists(self):
        """Counter increments persist across calls."""
        FacultyCodeService.generate_next_code(self.school_a)
        FacultyCodeService.generate_next_code(self.school_a)
        code3 = FacultyCodeService.generate_next_code(self.school_a)

        self.assertEqual(code3, 'GREENWOOD-FAC-003')
        seq = TenantSequence.objects.get(school=self.school_a, sequence_type='FACULTY')
        self.assertEqual(seq.last_value, 3)


class StatusToggleSetNullTests(FacultyTestBase):
    """Test 6: Status toggle + SET_NULL integrity."""

    def test_toggle_deactivates_faculty_and_user(self):
        """Toggling active faculty deactivates both Faculty and User."""
        faculty = FacultyService.create_faculty(self.school_a, {
            'first_name': 'Grace', 'last_name': 'Hopper',
            'email': 'grace@greenwood.edu', 'phone_number': '',
            'department': 'CS', 'designation': 'Professor',
        })
        self.assertTrue(faculty.is_active)

        FacultyService.toggle_status(faculty)
        faculty.refresh_from_db()

        self.assertFalse(faculty.is_active)
        self.assertFalse(faculty.user.is_active)

    def test_toggle_reactivates(self):
        """Toggling inactive faculty reactivates both."""
        faculty = FacultyService.create_faculty(self.school_a, {
            'first_name': 'Hedy', 'last_name': 'Lamarr',
            'email': 'hedy@greenwood.edu', 'phone_number': '',
            'department': 'Engineering', 'designation': 'Fellow',
        })
        FacultyService.toggle_status(faculty)  # Deactivate
        FacultyService.toggle_status(faculty)  # Reactivate
        faculty.refresh_from_db()

        self.assertTrue(faculty.is_active)
        self.assertTrue(faculty.user.is_active)

    def test_set_null_on_user_delete(self):
        """Deleting linked User sets faculty.user to None (SET_NULL)."""
        faculty = FacultyService.create_faculty(self.school_a, {
            'first_name': 'Irene', 'last_name': 'Curie',
            'email': 'irene@greenwood.edu', 'phone_number': '',
            'department': 'Physics', 'designation': 'Researcher',
        })
        user_id = faculty.user.pk
        faculty.user.delete()

        faculty.refresh_from_db()
        self.assertIsNone(faculty.user)
        # Faculty record still exists
        self.assertTrue(Faculty.objects.filter(pk=faculty.pk).exists())
        # User is gone
        self.assertFalse(User.objects.filter(pk=user_id).exists())


class OptionalDesignationAndCSVImportTests(FacultyTestBase):
    """Test 7: Optional Designation + CSV Bulk Import Service."""

    def test_create_faculty_without_designation(self):
        """Designation is optional and defaults to empty string."""
        faculty = FacultyService.create_faculty(self.school_a, {
            'first_name': 'Optional', 'last_name': 'Designation',
            'email': 'optional@greenwood.edu', 'phone_number': '',
            'department': 'Library',
            # designation is omitted
        })
        self.assertEqual(faculty.designation, '')
        self.assertEqual(faculty.department, 'Library')

    def test_import_faculty_from_csv(self):
        """CSV Bulk Import parses rows, skips invalid/duplicates, and auto-creates faculty."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        csv_content = (
            "first_name,last_name,email,department,designation,phone_number,employee_code\n"
            "Aarav,Shah,aarav@greenwood.edu,Science,Teacher,+919876543210,\n"
            "Bhavya,Mehta,bhavya@greenwood.edu,Maths,,+919876543211,\n"
            "Aarav,Shah,aarav@greenwood.edu,Science,Teacher,, Duplicate Email Row\n"
        ).encode('utf-8')

        csv_file = SimpleUploadedFile("test_import.csv", csv_content, content_type="text/csv")
        result = FacultyService.import_from_csv(self.school_a, csv_file)

        self.assertEqual(result['success_count'], 2)
        self.assertEqual(result['skipped_count'], 1)
        self.assertEqual(Faculty.objects.filter(school=self.school_a).count(), 2)

        # Check optional designation on Bhavya
        bhavya = Faculty.objects.get(email='bhavya@greenwood.edu')
        self.assertEqual(bhavya.designation, '')
        self.assertTrue(bhavya.employee_code.startswith('GREENWOOD-FAC-'))

