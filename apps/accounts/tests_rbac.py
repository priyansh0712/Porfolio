"""
Comprehensive automated test suite for Phase 4 RBAC.

Tests cover:
  1. UserModelTests            — Role/school constraints (DB + clean() validation)
  2. TenantAwareAuthBackendTests — Subdomain-role isolation in authentication
  3. DefenseInDepthRBACTests   — Middleware Layer 1, Mixin Layer 2 enforcement

All tests follow the 3-Layer Defense-in-Depth design from 04-CONTEXT.md.
"""
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponseForbidden
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from apps.accounts.auth_backends import TenantAwareAuthBackend
from apps.accounts.middleware import TenantRoleAccessMiddleware
from apps.accounts.models import User
from apps.accounts.permissions import SchoolAdminRequiredMixin, SuperAdminRequiredMixin
from apps.tenants.models import School


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_school(name='Test School', subdomain='testschool'):
    return School.objects.create(
        name=name,
        subdomain=subdomain,
        contact_email=f'admin@{subdomain}.com',
        is_active=True,
    )


def make_user(email, role, school=None, password='TestPass123!'):
    user = User(
        username=email.split('@')[0],
        email=email,
        first_name='Test',
        last_name='User',
        role=role,
        school=school,
    )
    user.set_password(password)
    user.save()
    return user


# ---------------------------------------------------------------------------
# 1. User Model Tests
# ---------------------------------------------------------------------------

class UserModelTests(TestCase):
    """Verify User model role/school constraints and clean() validation."""

    def setUp(self):
        self.school = make_school()

    def test_super_admin_created_without_school_succeeds(self):
        """Super Admin with school=None must succeed."""
        user = make_user('superadmin@platform.com', User.Role.SUPER_ADMIN, school=None)
        self.assertIsNotNone(user.pk)
        self.assertIsNone(user.school)
        self.assertTrue(user.is_super_admin)

    def test_school_admin_created_with_school_succeeds(self):
        """School Admin with a valid school must succeed."""
        user = make_user('admin@school.com', User.Role.SCHOOL_ADMIN, school=self.school)
        self.assertIsNotNone(user.pk)
        self.assertEqual(user.school, self.school)
        self.assertTrue(user.is_school_admin)

    def test_faculty_created_with_school_succeeds(self):
        """Faculty with a valid school must succeed."""
        user = make_user('faculty@school.com', User.Role.FACULTY, school=self.school)
        self.assertIsNotNone(user.pk)
        self.assertTrue(user.is_faculty)

    def test_super_admin_clean_raises_when_school_set(self):
        """Super Admin with school set must raise ValidationError via clean()."""
        user = User(
            username='superadminbad',
            email='superadminbad@platform.com',
            role=User.Role.SUPER_ADMIN,
            school=self.school,
        )
        user.set_password('TestPass123!')
        with self.assertRaises(ValidationError) as ctx:
            user.full_clean()
        self.assertIn('school', ctx.exception.message_dict)

    def test_school_admin_clean_raises_without_school(self):
        """School Admin with school=None must raise ValidationError via clean()."""
        user = User(
            username='adminnoschool',
            email='adminnoschool@school.com',
            role=User.Role.SCHOOL_ADMIN,
            school=None,
        )
        user.set_password('TestPass123!')
        with self.assertRaises(ValidationError) as ctx:
            user.full_clean()
        self.assertIn('school', ctx.exception.message_dict)

    def test_faculty_clean_raises_without_school(self):
        """Faculty with school=None must raise ValidationError via clean()."""
        user = User(
            username='facultynoschool',
            email='facultynoschool@school.com',
            role=User.Role.FACULTY,
            school=None,
        )
        user.set_password('TestPass123!')
        with self.assertRaises(ValidationError) as ctx:
            user.full_clean()
        self.assertIn('school', ctx.exception.message_dict)

    def test_role_convenience_properties(self):
        """is_super_admin, is_school_admin, is_faculty properties return correct values."""
        sa = make_user('sa@p.com', User.Role.SUPER_ADMIN, school=None)
        admin = make_user('admin@s.com', User.Role.SCHOOL_ADMIN, school=self.school)
        fac = make_user('fac@s.com', User.Role.FACULTY, school=self.school)

        self.assertTrue(sa.is_super_admin)
        self.assertFalse(sa.is_school_admin)
        self.assertTrue(admin.is_school_admin)
        self.assertFalse(admin.is_super_admin)
        self.assertTrue(fac.is_faculty)
        self.assertFalse(fac.is_school_admin)


# ---------------------------------------------------------------------------
# 2. TenantAwareAuthBackend Tests
# ---------------------------------------------------------------------------

class TenantAwareAuthBackendTests(TestCase):
    """Verify authentication backend enforces subdomain-role isolation."""

    def setUp(self):
        self.school_a = make_school('School A', 'schoola')
        self.school_b = make_school('School B', 'schoolb')
        self.backend = TenantAwareAuthBackend()

        self.school_admin = make_user(
            'admin@schoola.com', User.Role.SCHOOL_ADMIN,
            school=self.school_a, password='SchoolPass123!'
        )
        self.super_admin = make_user(
            'super@platform.com', User.Role.SUPER_ADMIN,
            school=None, password='SuperPass123!'
        )

    def _make_request(self, tenant=None):
        request = HttpRequest()
        request.tenant = tenant
        return request

    def test_school_admin_login_on_correct_subdomain_succeeds(self):
        """School Admin authenticating on their school's subdomain must succeed."""
        request = self._make_request(tenant=self.school_a)
        user = self.backend.authenticate(
            request, username='admin@schoola.com', password='SchoolPass123!'
        )
        self.assertIsNotNone(user)
        self.assertEqual(user.pk, self.school_admin.pk)

    def test_school_admin_login_on_wrong_subdomain_fails(self):
        """School Admin authenticating on a different school's subdomain must return None."""
        request = self._make_request(tenant=self.school_b)
        user = self.backend.authenticate(
            request, username='admin@schoola.com', password='SchoolPass123!'
        )
        self.assertIsNone(user)

    def test_super_admin_login_on_school_subdomain_fails(self):
        """Super Admin must be rejected when attempting login on a school subdomain."""
        request = self._make_request(tenant=self.school_a)
        user = self.backend.authenticate(
            request, username='super@platform.com', password='SuperPass123!'
        )
        self.assertIsNone(user)

    def test_super_admin_login_on_root_domain_succeeds(self):
        """Super Admin authenticating on root domain (tenant=None) must succeed."""
        request = self._make_request(tenant=None)
        user = self.backend.authenticate(
            request, username='super@platform.com', password='SuperPass123!'
        )
        self.assertIsNotNone(user)
        self.assertEqual(user.pk, self.super_admin.pk)

    def test_school_admin_login_on_root_domain_fails(self):
        """School Admin must be rejected when attempting login on the root domain."""
        request = self._make_request(tenant=None)
        user = self.backend.authenticate(
            request, username='admin@schoola.com', password='SchoolPass123!'
        )
        self.assertIsNone(user)

    def test_wrong_password_fails(self):
        """Incorrect password must return None regardless of role."""
        request = self._make_request(tenant=self.school_a)
        user = self.backend.authenticate(
            request, username='admin@schoola.com', password='WRONGPASSWORD'
        )
        self.assertIsNone(user)

    def test_nonexistent_email_fails(self):
        """Non-existent email must return None."""
        request = self._make_request(tenant=self.school_a)
        user = self.backend.authenticate(
            request, username='nobody@nowhere.com', password='TestPass123!'
        )
        self.assertIsNone(user)


# ---------------------------------------------------------------------------
# 3. Defense-in-Depth RBAC Tests
# ---------------------------------------------------------------------------

class TenantRoleAccessMiddlewareTests(TestCase):
    """Layer 1: Verify TenantRoleAccessMiddleware blocks unauthorized paths."""

    def setUp(self):
        self.factory = RequestFactory()
        self.school = make_school()
        self.super_admin = make_user('super@platform.com', User.Role.SUPER_ADMIN, school=None)
        self.school_admin = make_user('admin@school.com', User.Role.SCHOOL_ADMIN, school=self.school)

        # Dummy get_response for middleware
        def get_response(request):
            from django.http import HttpResponse
            return HttpResponse('OK')

        self.middleware = TenantRoleAccessMiddleware(get_response)

    def _make_request(self, path, user, tenant=None):
        request = self.factory.get(path)
        request.user = user
        request.tenant = tenant
        return request

    def test_super_admin_blocked_from_faculty_path(self):
        """Super Admin on /faculty/ must receive HTTP 403."""
        request = self._make_request('/faculty/', self.super_admin, tenant=self.school)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_super_admin_blocked_from_attendance_path(self):
        """Super Admin on /attendance/ must receive HTTP 403."""
        request = self._make_request('/attendance/', self.super_admin, tenant=self.school)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_super_admin_blocked_from_biometrics_path(self):
        """Super Admin on /biometrics/ must receive HTTP 403."""
        request = self._make_request('/biometrics/', self.super_admin, tenant=self.school)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_super_admin_blocked_from_reports_path(self):
        """Super Admin on /reports/ must receive HTTP 403."""
        request = self._make_request('/reports/', self.super_admin, tenant=self.school)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_super_admin_blocked_from_dashboard_path(self):
        """Super Admin on /dashboard/ must receive HTTP 403."""
        request = self._make_request('/dashboard/', self.super_admin, tenant=self.school)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_school_admin_blocked_from_superadmin_path(self):
        """School Admin on /superadmin/ must receive HTTP 403."""
        request = self._make_request('/superadmin/', self.school_admin, tenant=self.school)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_school_admin_allowed_on_dashboard(self):
        """School Admin on /dashboard/ must NOT be blocked by middleware (passes through)."""
        request = self._make_request('/dashboard/', self.school_admin, tenant=self.school)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_super_admin_allowed_on_superadmin_path(self):
        """Super Admin on /superadmin/ must NOT be blocked by middleware."""
        request = self._make_request('/superadmin/', self.super_admin, tenant=None)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)


class SchoolAdminRequiredMixinTests(TestCase):
    """Layer 2: Verify SchoolAdminRequiredMixin enforces view-level RBAC."""

    def setUp(self):
        self.factory = RequestFactory()
        self.school_a = make_school('School A', 'schoola')
        self.school_b = make_school('School B', 'schoolb')
        self.school_admin = make_user('admin@schoola.com', User.Role.SCHOOL_ADMIN, school=self.school_a)
        self.super_admin = make_user('super@platform.com', User.Role.SUPER_ADMIN, school=None)
        self.faculty = make_user('fac@schoola.com', User.Role.FACULTY, school=self.school_a)

        # Minimal CBV using the mixin
        from django.views import View
        from django.http import HttpResponse

        class ProtectedView(SchoolAdminRequiredMixin, View):
            def get(self, request, *args, **kwargs):
                return HttpResponse('Protected Content')

        self.view = ProtectedView.as_view()

    def _make_request(self, user, tenant=None):
        request = self.factory.get('/some-protected-url/')
        request.user = user
        request.tenant = tenant
        return request

    def test_school_admin_on_correct_tenant_allowed(self):
        """School Admin on their school's tenant must receive 200."""
        request = self._make_request(self.school_admin, tenant=self.school_a)
        response = self.view(request)
        self.assertEqual(response.status_code, 200)

    def test_school_admin_on_wrong_tenant_denied(self):
        """School Admin on a different school's tenant must receive 403."""
        request = self._make_request(self.school_admin, tenant=self.school_b)
        response = self.view(request)
        self.assertEqual(response.status_code, 403)

    def test_super_admin_denied(self):
        """Super Admin must receive 403 from SchoolAdminRequiredMixin."""
        request = self._make_request(self.super_admin, tenant=None)
        response = self.view(request)
        self.assertEqual(response.status_code, 403)

    def test_faculty_denied(self):
        """Faculty must receive 403 — mixin is SCHOOL_ADMIN specific."""
        request = self._make_request(self.faculty, tenant=self.school_a)
        response = self.view(request)
        self.assertEqual(response.status_code, 403)


class SuperAdminRequiredMixinTests(TestCase):
    """Layer 2: Verify SuperAdminRequiredMixin enforces view-level RBAC."""

    def setUp(self):
        self.factory = RequestFactory()
        self.school = make_school()
        self.super_admin = make_user('super@platform.com', User.Role.SUPER_ADMIN, school=None)
        self.school_admin = make_user('admin@school.com', User.Role.SCHOOL_ADMIN, school=self.school)

        from django.views import View
        from django.http import HttpResponse

        class SuperProtectedView(SuperAdminRequiredMixin, View):
            def get(self, request, *args, **kwargs):
                return HttpResponse('Super Admin Only')

        self.view = SuperProtectedView.as_view()

    def _make_request(self, user, tenant=None):
        request = self.factory.get('/superadmin/')
        request.user = user
        request.tenant = tenant
        return request

    def test_super_admin_on_root_domain_allowed(self):
        """Super Admin on root domain (tenant=None) must receive 200."""
        request = self._make_request(self.super_admin, tenant=None)
        response = self.view(request)
        self.assertEqual(response.status_code, 200)

    def test_super_admin_on_subdomain_denied(self):
        """Super Admin on a school subdomain must receive 403 (wrong domain)."""
        request = self._make_request(self.super_admin, tenant=self.school)
        response = self.view(request)
        self.assertEqual(response.status_code, 403)

    def test_school_admin_denied(self):
        """School Admin must receive 403 from SuperAdminRequiredMixin."""
        request = self._make_request(self.school_admin, tenant=self.school)
        response = self.view(request)
        self.assertEqual(response.status_code, 403)
