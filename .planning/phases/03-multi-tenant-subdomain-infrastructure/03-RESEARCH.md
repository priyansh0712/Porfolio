# Phase 3: Multi-Tenant Subdomain Infrastructure - Research

**Phase:** 3 - Multi-Tenant Subdomain Infrastructure  
**Date:** 2026-08-11  
**Status:** Complete

---

## Standard Stack

| Layer | Recommended Technology | Rationale |
|-------|-----------------------|-----------|
| **Middleware** | Custom Django `TenantMiddleware` | Lightweight, zero-overhead host header parsing and `request.tenant` binding. |
| **Context Isolation** | Python `contextvars.ContextVar` | Thread-safe and async-safe tracking of current tenant across threads/coroutines. |
| **Data Scoping** | `TenantModel` + `TenantManager` / `TenantQuerySet` | Transparent row-level query filtering enforcing 100% tenant isolation across all models. |
| **Routing Guardrails** | Host-aware Middleware Redirects | Enforces strict domain separation (root domain = public, subdomain = tenant). |

---

## Architecture Patterns

### 1. Host Resolution & Subdomain Normalization
- Parse `request.get_host()` to extract hostname without port (`split(':')[0]`).
- Exclude root domains (`localhost`, `127.0.0.1`, `ourapp.com`) and reserved subdomains (`www`, `api`, `admin`, `app`).
- Query `School.objects.filter(subdomain=subdomain).first()`.
- If match found: bind `request.tenant = school` and set `contextvars` current tenant.
- If subdomain present but not in database: redirect to root domain (`http://localhost:8000/`) with Django message alert (`messages.error(request, "School tenant not found.")`).

### 2. Thread-Safe Tenant Context (`contextvars`)
```python
import contextvars

_current_tenant = contextvars.ContextVar('current_tenant', default=None)

def set_current_tenant(tenant):
    return _current_tenant.set(tenant)

def get_current_tenant():
    return _current_tenant.get()
```

### 3. Tenant QuerySet & Manager Auto-Scoping
```python
from django.db import models

class TenantQuerySet(models.QuerySet):
    def for_tenant(self, tenant):
        if tenant is None:
            return self.none()
        return self.filter(school=tenant)

class TenantManager(models.Manager):
    def get_queryset(self):
        from apps.tenants.context import get_current_tenant
        qs = TenantQuerySet(self.model, using=self._db)
        tenant = get_current_tenant()
        if tenant is not None:
            return qs.for_tenant(tenant)
        return qs
```

### 4. Middleware Execution Order
Place `TenantMiddleware` in `config/settings/base.py` after `SessionMiddleware` and `AuthenticationMiddleware`, but before view resolution:
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'apps.tenants.middleware.TenantMiddleware', # <--- Early resolution & context binding
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

---

## Don't Hand-Roll

- **Don't use global variables for active tenant**: Global variables break under gunicorn/uwsgi concurrency and async tasks. Use `contextvars`.
- **Don't hardcode ports or protocol**: Strip ports dynamically using `get_host().split(':')[0]`.
- **Don't build custom SQL parsers**: Use Django ORM Manager / QuerySet override for clean, safe query filtering.

---

## Common Pitfalls

1. **Host Header Port Inclusion**: `request.get_host()` returns `schoola.localhost:8000` in dev. Must split on `:` to extract hostname `schoola.localhost`.
2. **Infinite Redirect Loops**: If invalid subdomain redirects to `/`, middleware must recognize `/` on root domain is public and NOT redirect again.
3. **Reserved Subdomain Conflicts**: `www.localhost:8000` should not look up a school named `www`. Use a `RESERVED_SUBDOMAINS` set (`www`, `app`, `api`, `admin`, `static`, `media`).
4. **Bypassing Tenant Filter in Admin/Management Commands**: Management scripts or Super Admin tools may need `.unscoped()` manager method to query across all tenants explicitly when needed.

---

## Code Examples

### `apps/tenants/middleware.py`
```python
from django.shortcuts import redirect
from django.contrib import messages
from apps.tenants.models import School
from apps.tenants.context import set_current_tenant, get_current_tenant

RESERVED_SUBDOMAINS = {'www', 'api', 'admin', 'app', 'static', 'media'}

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':')[0].lower()
        parts = host.split('.')

        subdomain = None
        if len(parts) >= 2 and parts[-1] in ('localhost', 'com') and parts[0] not in RESERVED_SUBDOMAINS:
            if parts[-1] == 'localhost' and len(parts) == 2 and parts[0] != 'localhost':
                subdomain = parts[0]
            elif parts[-1] == 'com' and len(parts) >= 3:
                subdomain = parts[0]

        tenant = None
        if subdomain:
            tenant = School.objects.filter(subdomain=subdomain).first()
            if not tenant:
                # Invalid subdomain -> redirect to root domain landing
                messages.error(request, "School tenant not found.")
                root_host = 'localhost:8000' if 'localhost' in host else 'ourapp.com'
                return redirect(f"{request.scheme}://{root_host}/")

        request.tenant = tenant
        token = set_current_tenant(tenant)

        try:
            response = self.get_response(request)
        finally:
            set_current_tenant(None)

        return response
```

---

## Downstream Guidance for `/gsd-plan-phase 3`

- **Plan 03-01**: `TenantMiddleware`, `contextvars` context manager, `TenantModel` base mixin, and `TenantManager` query scoping in `apps/tenants/`.
- **Plan 03-02**: Middleware registration in `config/settings/base.py`, invalid subdomain redirect handling, and comprehensive unit test suite (`apps/tenants/tests_middleware.py`).
