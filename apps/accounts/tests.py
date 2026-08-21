"""
Unit tests for Accounts app (SelfPasswordChangeView and security).
"""
from django.test import TestCase
from django.urls import reverse

from apps.tenants.models import School
from apps.accounts.models import User


class SelfPasswordChangeViewTest(TestCase):
    """Tests for SelfPasswordChangeView."""

    def setUp(self):
        self.school = School.objects.create(
            name='Cambridge School',
            subdomain='cambridge',
            contact_email='admin@cambridge.edu'
        )
        self.user = User.objects.create_user(
            username='user@cambridge.edu',
            email='user@cambridge.edu',
            password='OldPassword123!',
            first_name='Test',
            last_name='User',
            role=User.Role.FACULTY,
            school=self.school
        )

    def test_password_change_view_access(self):
        """Logged-in user can access password change view."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:password_change'), HTTP_HOST='cambridge.localhost:8000')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/password_change.html')

    def test_password_change_success(self):
        """User can successfully update password with valid old and new passwords."""
        self.client.force_login(self.user)
        post_data = {
            'old_password': 'OldPassword123!',
            'new_password1': 'NewStrongPass456!',
            'new_password2': 'NewStrongPass456!',
        }
        response = self.client.post(reverse('accounts:password_change'), post_data, HTTP_HOST='cambridge.localhost:8000')
        self.assertRedirects(response, reverse('accounts:password_change'))

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewStrongPass456!'))
