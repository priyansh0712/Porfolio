"""
Defense-in-Depth Layer 2: View-level permission mixins and function-based decorators.

Architecture Decision (from 04-CONTEXT.md):
  Middleware alone is NOT sufficient as a security boundary. Every
  view requiring tenant or role authorization must ALSO apply a
  permission mixin or decorator here. This is Layer 2 of 3-Layer security.

Mixins available:
  - SchoolAdminRequiredMixin   — for school admin CBVs
  - SuperAdminRequiredMixin    — for super admin CBVs

Decorators available:
  - @school_admin_required     — for school admin FBVs
  - @super_admin_required      — for super admin FBVs
"""
import functools

from django.contrib.auth.mixins import AccessMixin
from django.http import HttpResponseForbidden

from apps.accounts.models import User


# ---------------------------------------------------------------------------
# Class-Based View Mixins
# ---------------------------------------------------------------------------

class SchoolAdminRequiredMixin(AccessMixin):
    """
    CBV mixin: Allows access only to authenticated School Admins belonging
    to the active tenant (request.tenant).

    Checks:
      1. User must be authenticated.
      2. User role must be SCHOOL_ADMIN.
      3. User's school must match the active request.tenant.

    Returns HTTP 403 Forbidden on any failure (does NOT silently redirect
    to login — security must be explicit, not forgettable).
    """

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        active_tenant = getattr(request, 'tenant', None)

        if not user.is_authenticated:
            return self.handle_no_permission()

        if user.role != User.Role.SCHOOL_ADMIN:
            return HttpResponseForbidden(
                'Access denied: School Admin authorization required. '
                f'Your role ({user.get_role_display()}) does not have permission to access this resource.'
            )

        if user.school_id is None or user.school != active_tenant:
            return HttpResponseForbidden(
                'Access denied: You are not authorized to access this school\'s resources. '
                'Cross-tenant access is strictly prohibited.'
            )

        return super().dispatch(request, *args, **kwargs)


class SuperAdminRequiredMixin(AccessMixin):
    """
    CBV mixin: Allows access only to authenticated Super Admin on the root domain.

    Checks:
      1. User must be authenticated.
      2. User role must be SUPER_ADMIN.
      3. request.tenant must be None (root domain — not a school subdomain).

    Returns HTTP 403 Forbidden on any failure.
    """

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        active_tenant = getattr(request, 'tenant', None)

        if not user.is_authenticated:
            return self.handle_no_permission()

        if user.role != User.Role.SUPER_ADMIN:
            return HttpResponseForbidden(
                'Access denied: Platform Super Admin authorization required.'
            )

        if active_tenant is not None:
            return HttpResponseForbidden(
                'Access denied: Super Admin platform management is only accessible '
                'on the root domain, not on school subdomains.'
            )

        return super().dispatch(request, *args, **kwargs)


class FacultyRequiredMixin(AccessMixin):
    """
    CBV mixin: Allows access only to authenticated Faculty members belonging
    to the active tenant (request.tenant).
    """

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        active_tenant = getattr(request, 'tenant', None)

        if not user.is_authenticated:
            return self.handle_no_permission()

        if user.role != User.Role.FACULTY:
            return HttpResponseForbidden(
                'Access denied: Faculty authorization required. '
                f'Your role ({user.get_role_display()}) does not have permission.'
            )

        if user.school_id is None or user.school != active_tenant:
            return HttpResponseForbidden(
                'Access denied: You are not authorized to access this school\'s resources.'
            )

        return super().dispatch(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Function-Based View Decorators
# ---------------------------------------------------------------------------

def school_admin_required(view_func):
    """
    Decorator for FBVs: restricts access to School Admin users belonging
    to the active request.tenant.

    Returns HTTP 403 on any authorization failure.
    """
    @functools.wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        active_tenant = getattr(request, 'tenant', None)

        if not user.is_authenticated:
            from django.conf import settings
            from django.shortcuts import redirect
            return redirect(settings.LOGIN_URL)

        if user.role != User.Role.SCHOOL_ADMIN:
            return HttpResponseForbidden(
                'Access denied: School Admin authorization required.'
            )

        if user.school_id is None or user.school != active_tenant:
            return HttpResponseForbidden(
                'Access denied: Cross-tenant access is strictly prohibited.'
            )

        return view_func(request, *args, **kwargs)
    return _wrapped_view


def super_admin_required(view_func):
    """
    Decorator for FBVs: restricts access to Super Admin users on the root domain.

    Returns HTTP 403 on any authorization failure.
    """
    @functools.wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        active_tenant = getattr(request, 'tenant', None)

        if not user.is_authenticated:
            from django.conf import settings
            from django.shortcuts import redirect
            return redirect(settings.LOGIN_URL)

        if user.role != User.Role.SUPER_ADMIN:
            return HttpResponseForbidden(
                'Access denied: Platform Super Admin authorization required.'
            )

        if active_tenant is not None:
            return HttpResponseForbidden(
                'Access denied: Super Admin management is root domain only.'
            )

        return view_func(request, *args, **kwargs)
    return _wrapped_view


def faculty_required(view_func):
    """
    Decorator for FBVs: restricts access to Faculty users belonging
    to the active request.tenant.
    """
    @functools.wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        active_tenant = getattr(request, 'tenant', None)

        if not user.is_authenticated:
            from django.conf import settings
            from django.shortcuts import redirect
            return redirect(settings.LOGIN_URL)

        if user.role != User.Role.FACULTY:
            return HttpResponseForbidden(
                'Access denied: Faculty authorization required.'
            )

        if user.school_id is None or user.school != active_tenant:
            return HttpResponseForbidden(
                'Access denied: Cross-tenant access is strictly prohibited.'
            )

        return view_func(request, *args, **kwargs)
    return _wrapped_view


class FeatureRequiredMixin(AccessMixin):
    """
    CBV Mixin: Restricts access if a specified feature is disabled for request.tenant.
    Set `feature_key` on your View class.
    """
    feature_key = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        tenant = getattr(request, 'tenant', None)
        if tenant and self.feature_key:
            from apps.tenants.features import FeatureService
            if not FeatureService.is_enabled(tenant, self.feature_key):
                return HttpResponseForbidden(
                    f"Access Denied: The '{self.feature_key}' feature is disabled for this institution."
                )

        return super().dispatch(request, *args, **kwargs)


def feature_required(feature_key):
    """
    Decorator for FBVs: restricts access if feature_key is disabled for request.tenant.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.conf import settings
                from django.shortcuts import redirect
                return redirect(settings.LOGIN_URL)

            tenant = getattr(request, 'tenant', None)
            if tenant and feature_key:
                from apps.tenants.features import FeatureService
                if not FeatureService.is_enabled(tenant, feature_key):
                    return HttpResponseForbidden(
                        f"Access Denied: The '{feature_key}' feature is disabled for this institution."
                    )

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

