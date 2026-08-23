import io
from PIL import Image
from django.test import TestCase, Client, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.tenants.models import School
from apps.tenants.services import SchoolRegistrationService

User = get_user_model()


def create_test_image(filename="test.png", size=(100, 100), color="blue"):
    file_obj = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(file_obj, format="PNG")
    file_obj.seek(0)
    return SimpleUploadedFile(filename, file_obj.read(), content_type="image/png")


@override_settings(ALLOWED_HOSTS=['*'])
class SchoolBrandingTests(TestCase):

    def setUp(self):
        from apps.accounts.models import User
        self.super_admin = User.objects.create_user(
            username='super@studenterp.com',
            email='super@studenterp.com',
            password='SuperPassword123!',
            role=User.Role.SUPER_ADMIN,
        )

        # Create School A
        self.school_a, self.admin_a = SchoolRegistrationService.register_school({
            'school_name': 'Alpha Academy',
            'subdomain': 'alpha',
            'contact_email': 'admin@alpha.edu',
            'admin_full_name': 'Alpha Admin',
            'password': 'Password123!',
        })

        # Create School B
        self.school_b, self.admin_b = SchoolRegistrationService.register_school({
            'school_name': 'Beta High',
            'subdomain': 'beta',
            'contact_email': 'admin@beta.edu',
            'admin_full_name': 'Beta Admin',
            'password': 'Password123!',
        })

        # Create Faculty user for School A
        self.faculty_a = User.objects.create_user(
            username='faculty_alpha',
            email='faculty@alpha.edu',
            password='Password123!',
            role=User.Role.FACULTY,
            school=self.school_a,
        )

        self.client = Client()

    def test_school_registration_with_image_and_logo(self):
        """Registering a new school with image and logo stores them properly."""
        self.client.force_login(self.super_admin)
        img = create_test_image("hero.png")
        logo = create_test_image("logo.png")

        post_data = {
            'school_name': 'Gamma College',
            'subdomain': 'gamma',
            'contact_email': 'admin@gamma.edu',
            'admin_full_name': 'Gamma Admin',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
            'school_image': img,
            'school_logo': logo,
        }
        response = self.client.post(reverse('public:register'), post_data)
        self.assertEqual(response.status_code, 302)

        gamma_school = School.objects.get(subdomain='gamma')
        self.assertTrue(bool(gamma_school.school_image))
        self.assertTrue(bool(gamma_school.school_logo))
        self.assertIn('school_branding/images/', gamma_school.school_image.name)
        self.assertIn('school_branding/logos/', gamma_school.school_logo.name)

    def test_invalid_image_extension_rejected(self):
        """Non-image file uploads should fail form validation."""
        self.client.force_login(self.super_admin)
        fake_txt = SimpleUploadedFile("malicious.txt", b"not an image", content_type="text/plain")

        post_data = {
            'school_name': 'Delta School',
            'subdomain': 'delta',
            'contact_email': 'admin@delta.edu',
            'admin_full_name': 'Delta Admin',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
            'school_image': fake_txt,
        }
        response = self.client.post(reverse('public:register'), post_data)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertTrue('school_image' in form.errors)

    def test_file_size_limit_validation(self):
        """Files exceeding 5MB should fail validation."""
        self.client.force_login(self.super_admin)
        large_content = b'0' * (6 * 1024 * 1024)  # 6MB
        large_file = SimpleUploadedFile("huge.jpg", large_content, content_type="image/jpeg")

        post_data = {
            'school_name': 'Epsilon School',
            'subdomain': 'epsilon',
            'contact_email': 'admin@epsilon.edu',
            'admin_full_name': 'Epsilon Admin',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
            'school_image': large_file,
        }
        response = self.client.post(reverse('public:register'), post_data)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertTrue('school_image' in form.errors)

    def test_school_admin_can_update_branding(self):
        """School Admin can update school image and logo from settings."""
        self.client.force_login(self.admin_a)

        new_image = create_test_image("new_hero.png")
        new_logo = create_test_image("new_logo.png")

        response = self.client.post(
            reverse('schedules:settings'),
            {
                'action': 'update_branding',
                'school_image': new_image,
                'school_logo': new_logo,
            },
            HTTP_HOST='alpha.localhost'
        )
        self.assertEqual(response.status_code, 302)

        self.school_a.refresh_from_db()
        self.assertTrue(bool(self.school_a.school_image))
        self.assertTrue(bool(self.school_a.school_logo))

    def test_tenant_isolation_school_a_cannot_modify_school_b_branding(self):
        """School A admin modifying settings only alters School A, not School B."""
        self.client.force_login(self.admin_a)

        new_image = create_test_image("alpha_hero.png")

        # Post update under School A domain
        self.client.post(
            reverse('schedules:settings'),
            {
                'action': 'update_branding',
                'school_image': new_image,
            },
            HTTP_HOST='alpha.localhost'
        )

        self.school_a.refresh_from_db()
        self.school_b.refresh_from_db()

        self.assertTrue(bool(self.school_a.school_image))
        self.assertFalse(bool(self.school_b.school_image))

    def test_faculty_cannot_modify_branding(self):
        """Faculty member attempting to post branding update is redirected/denied."""
        self.client.force_login(self.faculty_a)

        response = self.client.post(
            reverse('schedules:settings'),
            {
                'action': 'update_branding',
                'school_image': create_test_image("test.png"),
            },
            HTTP_HOST='alpha.localhost'
        )
        # SchoolAdminRequiredMixin redirects or returns 403
        self.assertIn(response.status_code, [302, 403])

        self.school_a.refresh_from_db()
        self.assertFalse(bool(self.school_a.school_image))

    def test_login_page_renders_school_image_when_present(self):
        """Login page displays school image if configured for tenant."""
        self.school_a.school_image = create_test_image("hero.png")
        self.school_a.save()

        response = self.client.get('/login/', HTTP_HOST='alpha.localhost')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.school_a.school_image.url)

    def test_login_page_fallback_when_no_school_image(self):
        """Login page uses fallback when school image is not present."""
        response = self.client.get('/login/', HTTP_HOST='beta.localhost')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'school_branding/images/')
        self.assertContains(response, 'Beta High')
