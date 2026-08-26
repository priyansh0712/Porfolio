from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.tenants.models import School
from apps.tenants.forms import SchoolRegistrationForm
from apps.tenants.services import SchoolRegistrationService

User = get_user_model()

class SchoolTenantModelTest(TestCase):
    def test_create_school(self):
        school = School.objects.create(
            name="Greenwood High School",
            subdomain="greenwood",
            contact_email="admin@greenwood.edu"
        )
        self.assertEqual(str(school), "Greenwood High School (greenwood)")
        self.assertEqual(school.full_domain, "greenwood.ourapp.com")
        self.assertTrue(school.is_active)


class SchoolRegistrationFormTest(TestCase):
    def test_valid_form(self):
        form_data = {
            'school_name': 'Valley Academy',
            'subdomain': 'valley-academy',
            'contact_email': 'principal@valley.edu',
            'admin_full_name': 'Principal John Smith',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!'
        }
        form = SchoolRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_reserved_subdomain_rejected(self):
        form_data = {
            'school_name': 'Admin School',
            'subdomain': 'admin',
            'contact_email': 'admin@school.edu',
            'admin_full_name': 'Jane Admin',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!'
        }
        form = SchoolRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('subdomain', form.errors)

    def test_duplicate_subdomain_rejected(self):
        School.objects.create(
            name="Existing School",
            subdomain="existing",
            contact_email="contact@existing.edu"
        )
        form_data = {
            'school_name': 'New School',
            'subdomain': 'existing',
            'contact_email': 'new@school.edu',
            'admin_full_name': 'New Admin',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!'
        }
        form = SchoolRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('subdomain', form.errors)

    def test_password_mismatch_rejected(self):
        form_data = {
            'school_name': 'Mismatch School',
            'subdomain': 'mismatch',
            'contact_email': 'info@mismatch.edu',
            'admin_full_name': 'Admin User',
            'password': 'Password123!',
            'confirm_password': 'DifferentPassword456!'
        }
        form = SchoolRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('confirm_password', form.errors)


class SchoolRegistrationServiceTest(TestCase):
    def test_service_creates_school_and_admin(self):
        data = {
            'school_name': 'St. Jude School',
            'subdomain': 'stjude',
            'contact_email': 'admin@stjude.edu',
            'admin_full_name': 'Sister Mary',
            'password': 'SecurePassword789!'
        }
        school, admin_user = SchoolRegistrationService.register_school(data)

        self.assertIsNotNone(school.id)
        self.assertEqual(school.name, 'St. Jude School')
        self.assertEqual(school.subdomain, 'stjude')

        self.assertIsNotNone(admin_user.id)
        self.assertEqual(admin_user.email, 'admin@stjude.edu')
        self.assertTrue(admin_user.check_password('SecurePassword789!'))
        self.assertTrue(admin_user.is_staff)


class PublicViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        from apps.accounts.models import User
        self.super_admin = User.objects.create_user(
            username='super@studenterp.com',
            email='super@studenterp.com',
            password='SuperPassword123!',
            role=User.Role.SUPER_ADMIN,
        )

    def test_landing_page_renders_cleanly(self):
        response = self.client.get(reverse('public:landing'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "StudentERP")
        self.assertContains(response, "Sign In to Portal")

    def test_tenant_subdomain_unauthenticated_redirects_to_login(self):
        school = School.objects.create(name='St. Xavier', subdomain='st-xavier')
        response = self.client.get(reverse('public:landing'), HTTP_HOST='st-xavier.localhost:8000')
        self.assertRedirects(response, reverse('accounts:login'))

    def test_tenant_subdomain_authenticated_redirects_to_dashboard(self):
        school = School.objects.create(name='St. Xavier', subdomain='st-xavier')
        from apps.accounts.models import User
        school_admin = User.objects.create_user(
            username='admin@stxavier.edu',
            email='admin@stxavier.edu',
            password='AdminPassword123!',
            role=User.Role.SCHOOL_ADMIN,
            school=school,
        )
        self.client.force_login(school_admin)
        response = self.client.get(reverse('public:landing'), HTTP_HOST='st-xavier.localhost:8000')
        self.assertRedirects(response, reverse('accounts:dashboard'))

    def test_registration_flow(self):
        self.client.force_login(self.super_admin)
        response = self.client.post(reverse('public:register'), {
            'school_name': 'Oxford High',
            'subdomain': 'oxford-high',
            'contact_email': 'headmaster@oxford.edu',
            'admin_full_name': 'Headmaster Charles',
            'password': 'OxfordPassword123!',
            'confirm_password': 'OxfordPassword123!'
        })
        self.assertRedirects(response, reverse('public:register_success'))

        school = School.objects.get(subdomain='oxford-high')
        self.assertEqual(school.name, 'Oxford High')
