"""
Comprehensive tests for TenantMiddleware subdomain resolution,
invalid subdomain redirect, reserved subdomain handling,
and TenantModel auto-scoped query isolation.
"""
from django.test import TestCase, RequestFactory, override_settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpResponse
from django.db import models

from apps.tenants.models import School, TenantModel
from apps.tenants.middleware import TenantMiddleware, RESERVED_SUBDOMAINS
from apps.tenants.context import set_current_tenant, get_current_tenant


# ---------------------------------------------------------------------------
# Dummy concrete model for TenantModel query scoping tests
# ---------------------------------------------------------------------------
class DummyTenantEntity(TenantModel):
    """Concrete model that inherits TenantModel for testing query scoping."""
    label = models.CharField(max_length=100)

    class Meta:
        app_label = 'tenants'


# ---------------------------------------------------------------------------
# Helper: attach session + messages middleware to a RequestFactory request
# ---------------------------------------------------------------------------
def _prepare_request(request):
    """Add session and message backends to a bare RequestFactory request."""
    session_mw = SessionMiddleware(lambda r: HttpResponse())
    session_mw.process_request(request)
    request.session.save()
    messages_mw = MessageMiddleware(lambda r: HttpResponse())
    messages_mw.process_request(request)
    # FallbackStorage is needed so messages work without full middleware chain
    setattr(request, '_messages', FallbackStorage(request))
    return request


# ---------------------------------------------------------------------------
# TenantMiddleware Tests
# ---------------------------------------------------------------------------
@override_settings(ALLOWED_HOSTS=['*'])
class TenantMiddlewareTests(TestCase):
    """Tests for host-header subdomain parsing and tenant resolution."""

    def setUp(self):
        self.factory = RequestFactory()
        self.dummy_response = HttpResponse('OK')
        self.middleware = TenantMiddleware(lambda request: self.dummy_response)

        # Create a test school tenant
        self.school_alpha = School.objects.create(
            name='Alpha School',
            subdomain='alpha',
            contact_email='admin@alpha.test',
            is_active=True,
        )

    # ----- Root domain tests -----

    def test_root_domain_localhost(self):
        """Root domain localhost → request.tenant is None."""
        request = self.factory.get('/', HTTP_HOST='localhost:8000')
        _prepare_request(request)
        self.middleware(request)
        self.assertIsNone(request.tenant)

    def test_root_domain_127(self):
        """Root domain 127.0.0.1 → request.tenant is None."""
        request = self.factory.get('/', HTTP_HOST='127.0.0.1:8000')
        _prepare_request(request)
        self.middleware(request)
        self.assertIsNone(request.tenant)

    def test_root_domain_production(self):
        """Root domain ourapp.com → request.tenant is None."""
        request = self.factory.get('/', HTTP_HOST='ourapp.com')
        _prepare_request(request)
        self.middleware(request)
        self.assertIsNone(request.tenant)

    # ----- Valid subdomain tests -----

    def test_valid_subdomain_localhost(self):
        """Valid subdomain alpha.localhost → request.tenant is school_alpha."""
        request = self.factory.get('/', HTTP_HOST='alpha.localhost:8000')
        _prepare_request(request)
        self.middleware(request)
        self.assertEqual(request.tenant, self.school_alpha)

    def test_valid_subdomain_production(self):
        """Valid subdomain alpha.ourapp.com → request.tenant is school_alpha."""
        request = self.factory.get('/', HTTP_HOST='alpha.ourapp.com')
        _prepare_request(request)
        self.middleware(request)
        self.assertEqual(request.tenant, self.school_alpha)

    # ----- Invalid subdomain tests -----

    def test_invalid_subdomain_redirects(self):
        """Unknown subdomain → 302 redirect to root domain."""
        request = self.factory.get('/', HTTP_HOST='nonexistent.localhost:8000')
        _prepare_request(request)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('localhost', response.url)

    def test_invalid_subdomain_production_redirects(self):
        """Unknown subdomain on production → 302 redirect to root domain."""
        request = self.factory.get('/', HTTP_HOST='badschool.ourapp.com')
        _prepare_request(request)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('ourapp.com', response.url)

    # ----- Reserved subdomain tests -----

    def test_reserved_subdomain_www(self):
        """Reserved subdomain www → request.tenant is None (not resolved)."""
        request = self.factory.get('/', HTTP_HOST='www.localhost:8000')
        _prepare_request(request)
        self.middleware(request)
        self.assertIsNone(request.tenant)

    def test_reserved_subdomain_admin(self):
        """Reserved subdomain admin → request.tenant is None (not resolved)."""
        request = self.factory.get('/', HTTP_HOST='admin.localhost:8000')
        _prepare_request(request)
        self.middleware(request)
        self.assertIsNone(request.tenant)

    def test_reserved_subdomain_api(self):
        """Reserved subdomain api → request.tenant is None (not resolved)."""
        request = self.factory.get('/', HTTP_HOST='api.ourapp.com')
        _prepare_request(request)
        self.middleware(request)
        self.assertIsNone(request.tenant)

    # ----- Inactive school tests -----

    def test_inactive_school_redirects(self):
        """Inactive school subdomain → treated as invalid, redirects."""
        self.school_alpha.is_active = False
        self.school_alpha.save()

        request = self.factory.get('/', HTTP_HOST='alpha.localhost:8000')
        _prepare_request(request)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 302)

    # ----- Context cleanup tests -----

    def test_context_cleaned_after_request(self):
        """Active tenant context is reset to None after request completes."""
        request = self.factory.get('/', HTTP_HOST='alpha.localhost:8000')
        _prepare_request(request)
        self.middleware(request)
        # After middleware completes, context should be None
        self.assertIsNone(get_current_tenant())


# ---------------------------------------------------------------------------
# TenantModel Query Scoping Tests
# ---------------------------------------------------------------------------
@override_settings(ALLOWED_HOSTS=['*'])
class TenantModelQueryScopingTests(TestCase):
    """Tests for TenantManager automatic query scoping by active tenant."""

    @classmethod
    def setUpClass(cls):
        # Create the dummy table for testing
        from django.db import connection
        with connection.schema_editor() as schema_editor:
            try:
                schema_editor.create_model(DummyTenantEntity)
            except Exception:
                pass  # Table may already exist from a previous run
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        # Django's test runner destroys the in-memory SQLite DB automatically.
        # Manual schema cleanup is skipped to avoid SQLite FK constraint issues.
        super().tearDownClass()

    def setUp(self):
        self.school_a = School.objects.create(
            name='School A', subdomain='schoola',
            contact_email='a@test.com', is_active=True,
        )
        self.school_b = School.objects.create(
            name='School B', subdomain='schoolb',
            contact_email='b@test.com', is_active=True,
        )
        # Create entities for each school
        self.entity_a = DummyTenantEntity.objects.create(
            school=self.school_a, label='Entity A',
        )
        self.entity_b = DummyTenantEntity.objects.create(
            school=self.school_b, label='Entity B',
        )
        # Reset context after creation
        set_current_tenant(None)

    def tearDown(self):
        set_current_tenant(None)

    def test_scoped_query_school_a(self):
        """With tenant A active, only tenant A's entities are returned."""
        set_current_tenant(self.school_a)
        results = list(DummyTenantEntity.objects.all())
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].label, 'Entity A')

    def test_scoped_query_school_b(self):
        """With tenant B active, only tenant B's entities are returned."""
        set_current_tenant(self.school_b)
        results = list(DummyTenantEntity.objects.all())
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].label, 'Entity B')

    def test_no_tenant_returns_all(self):
        """With no tenant active (None), all entities are returned."""
        set_current_tenant(None)
        results = list(DummyTenantEntity.objects.all())
        self.assertEqual(len(results), 2)

    def test_unscoped_returns_all(self):
        """unscoped() always returns all entities regardless of active tenant."""
        set_current_tenant(self.school_a)
        results = list(DummyTenantEntity.objects.unscoped())
        self.assertEqual(len(results), 2)


# ---------------------------------------------------------------------------
# Context Module Tests
# ---------------------------------------------------------------------------
class TenantContextTests(TestCase):
    """Tests for the contextvars-based tenant context module."""

    def tearDown(self):
        set_current_tenant(None)

    def test_default_is_none(self):
        """Default tenant context is None."""
        self.assertIsNone(get_current_tenant())

    def test_set_and_get(self):
        """set_current_tenant / get_current_tenant round-trip works."""
        school = School.objects.create(
            name='Test', subdomain='test',
            contact_email='test@test.com',
        )
        set_current_tenant(school)
        self.assertEqual(get_current_tenant(), school)

    def test_reset_to_none(self):
        """Setting tenant to None clears the context."""
        set_current_tenant('something')
        set_current_tenant(None)
        self.assertIsNone(get_current_tenant())
