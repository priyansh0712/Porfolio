"""
Automated Integration Tests for Tenant Feature Management & Feature Flags.
"""
from django.test import TestCase, Client
from django.urls import reverse

from apps.tenants.models import School, SchoolFeature
from apps.accounts.models import User
from apps.tenants.features import FeatureService, FEATURE_CATALOG


class TenantFeatureManagementTest(TestCase):
    """
    Verifies Super Admin feature toggles, per-school storage,
    multi-tenant isolation, and backend security URL blocking.
    """

    def setUp(self):
        # 1. Create Super Admin
        self.super_admin = User.objects.create_user(
            username='super@platform.com',
            email='super@platform.com',
            password='SuperPassword123!',
            role=User.Role.SUPER_ADMIN,
        )

        # 2. Create School A
        self.school_a = School.objects.create(
            name='Alpha Academy',
            subdomain='alpha',
            contact_email='admin@alpha.edu',
            is_active=True
        )
        self.admin_a = User.objects.create_user(
            username='admin@alpha.edu',
            email='admin@alpha.edu',
            password='Password123!',
            role=User.Role.SCHOOL_ADMIN,
            school=self.school_a
        )

        # 3. Create School B
        self.school_b = School.objects.create(
            name='Beta High',
            subdomain='beta',
            contact_email='admin@beta.edu',
            is_active=True
        )
        self.admin_b = User.objects.create_user(
            username='admin@beta.edu',
            email='admin@beta.edu',
            password='Password123!',
            role=User.Role.SCHOOL_ADMIN,
            school=self.school_b
        )

    def test_default_features_enabled_for_existing_schools(self):
        """Standard V1/V2 catalog features should default to True for schools."""
        features_a = FeatureService.get_school_features(self.school_a)
        self.assertTrue(features_a['faculty_attendance'])
        self.assertTrue(features_a['faculty_leave'])
        self.assertTrue(features_a['reports'])
        self.assertTrue(features_a['notifications'])
        self.assertFalse(features_a['student_attendance'])  # Future flag defaults to False

    def test_super_admin_can_toggle_feature(self):
        """Super Admin POST endpoint toggles a feature flag for a specific school."""
        client = Client()
        client.force_login(self.super_admin)

        # Disable faculty_leave for School A
        response = client.post(
            reverse('accounts:superadmin_toggle_feature', kwargs={'school_id': self.school_a.pk}),
            {'feature_key': 'faculty_leave', 'is_enabled': 'false'},
            HTTP_HOST='localhost:8000'
        )
        self.assertRedirects(response, reverse('accounts:superadmin_dashboard'))

        # Verify DB status
        self.assertFalse(FeatureService.is_enabled(self.school_a, 'faculty_leave'))

    def test_multi_tenant_feature_isolation(self):
        """Disabling a feature for School A must NOT affect School B."""
        FeatureService.set_feature_status(self.school_a, 'faculty_leave', False)
        FeatureService.set_feature_status(self.school_b, 'faculty_leave', True)

        self.assertFalse(FeatureService.is_enabled(self.school_a, 'faculty_leave'))
        self.assertTrue(FeatureService.is_enabled(self.school_b, 'faculty_leave'))

    def test_backend_security_blocks_disabled_feature_url(self):
        """Direct URL access to a disabled feature returns 403 Forbidden."""
        # Disable faculty_leave for School A
        FeatureService.set_feature_status(self.school_a, 'faculty_leave', False)

        client = Client()
        client.force_login(self.admin_a)

        # Attempt direct access to leaves request page on School A
        response = client.get(
            reverse('leaves:admin_requests'),
            HTTP_HOST='alpha.localhost:8000'
        )
        self.assertEqual(response.status_code, 403)

    def test_backend_security_allows_enabled_feature_url(self):
        """Direct URL access to an enabled feature returns 200 OK."""
        # Ensure faculty_leave is ON for School B
        FeatureService.set_feature_status(self.school_b, 'faculty_leave', True)

        client = Client()
        client.force_login(self.admin_b)

        response = client.get(
            reverse('leaves:admin_requests'),
            HTTP_HOST='beta.localhost:8000'
        )
        self.assertEqual(response.status_code, 200)

    def test_unauthorized_user_cannot_toggle_features(self):
        """School Admins or unauthenticated users cannot access superadmin toggle endpoint."""
        client = Client()
        client.force_login(self.admin_a)

        response = client.post(
            reverse('accounts:superadmin_toggle_feature', kwargs={'school_id': self.school_a.pk}),
            {'feature_key': 'faculty_leave', 'is_enabled': 'false'},
            HTTP_HOST='alpha.localhost:8000'
        )
        self.assertEqual(response.status_code, 403)
