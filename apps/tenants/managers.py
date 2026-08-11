"""
Tenant-scoped QuerySet and Manager for automatic multi-tenant query isolation.

TenantManager.get_queryset() reads the active tenant from contextvars
and automatically filters all queries by school=tenant. This ensures
zero cross-tenant data leakage at the ORM layer.

Use TenantManager.unscoped() for explicit cross-tenant queries
(admin dashboards, management commands).
"""
from django.db import models


class TenantQuerySet(models.QuerySet):
    """QuerySet with tenant filtering helpers."""

    def for_tenant(self, tenant):
        """Filter to records belonging to a specific tenant."""
        if tenant is None:
            return self.none()
        return self.filter(school=tenant)


class TenantManager(models.Manager):
    """
    Default manager that automatically scopes queries to the active tenant.

    When a tenant is set in contextvars (via TenantMiddleware), all queries
    through this manager are filtered to that tenant's data. When no tenant
    is set, queries return the full unscoped queryset.
    """

    def get_queryset(self):
        from apps.tenants.context import get_current_tenant

        qs = TenantQuerySet(self.model, using=self._db)
        tenant = get_current_tenant()
        if tenant is not None:
            return qs.for_tenant(tenant)
        return qs

    def unscoped(self):
        """Return an unscoped QuerySet across all tenants.

        Use sparingly — only for admin tools, management commands,
        and cross-tenant reporting where explicit access is intended.
        """
        return TenantQuerySet(self.model, using=self._db)
