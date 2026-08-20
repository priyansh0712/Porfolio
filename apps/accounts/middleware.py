"""
Defense-in-Depth Layer 1: TenantRoleAccessMiddleware.

This middleware is Layer 1 of the 3-Layer Security architecture. It provides
a fast, request-level guard rejecting obviously-mismatched role/path combinations
BEFORE they reach any view or business logic.

IMPORTANT (from 04-CONTEXT.md):
  This middleware is NOT the sole security boundary. Views MUST ALSO apply
  SchoolAdminRequiredMixin / SuperAdminRequiredMixin (Layer 2) and queries
  MUST scope by tenant (Layer 3). This middleware serves as a defense-in-depth
  fast-fail guard, not a replacement for view-level authorization.

Blocked paths:
  - Super Admin on: /faculty/, /biometrics/, /attendance/, /reports/, /dashboard/
  - Tenant users (School Admin / Faculty) on: /superadmin/
"""
from django.http import HttpResponseForbidden

from apps.accounts.models import User

# Paths that Super Admin must NEVER access (biometric & faculty privacy boundary)
TENANT_SCOPED_PREFIXES = (
    '/faculty/',
    '/biometrics/',
    '/attendance/',
    '/reports/',
    '/dashboard/',
    '/leaves/',
    '/academics/',
)

# Paths that tenant users must NEVER access
SUPERADMIN_PREFIXES = (
    '/superadmin/',
)


class TenantRoleAccessMiddleware:
    """
    Layer 1 (Middleware) security guard.

    Runs after AuthenticationMiddleware and TenantMiddleware to access
    both request.user and request.tenant.

    Enforcement:
      - Unauthenticated requests are passed through (handled by LoginRequiredMixin at view level).
      - Super Admin attempting to access tenant-scoped paths → HTTP 403 immediately.
      - Tenant users attempting to access superadmin paths → HTTP 403 immediately.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user

        # Only enforce for authenticated users
        if user.is_authenticated:
            path = request.path_info

            if user.role == User.Role.SUPER_ADMIN:
                # Super Admin is STRICTLY prohibited from accessing tenant-scoped resources
                if any(path.startswith(prefix) for prefix in TENANT_SCOPED_PREFIXES):
                    return HttpResponseForbidden(
                        'Access denied: Super Admin is strictly prohibited from accessing '
                        'tenant faculty, biometric, and attendance records (AUTH-02 privacy boundary). '
                        f'Attempted path: {path}'
                    )

            elif user.role in (User.Role.SCHOOL_ADMIN, User.Role.FACULTY):
                # Tenant users cannot access Super Admin platform management
                if any(path.startswith(prefix) for prefix in SUPERADMIN_PREFIXES):
                    return HttpResponseForbidden(
                        'Access denied: Platform management (/superadmin/) is restricted '
                        'to Platform Super Admin only.'
                    )

        return self.get_response(request)
