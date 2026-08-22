"""
TenantMiddleware — Resolves the active school tenant from the request's
Host header subdomain and binds it to request.tenant and contextvars.

Routing rules:
  - Root domain (localhost, 127.0.0.1, ourapp.com) → request.tenant = None (public pages).
  - Valid subdomain (e.g. schoola.localhost) → request.tenant = School instance.
  - Invalid subdomain (not in DB) → redirect to root domain with flash error.
  - Reserved subdomains (www, api, admin, etc.) → treated as root domain.
"""
import ipaddress
from django.shortcuts import redirect
from django.contrib import messages

from apps.tenants.models import School
from apps.tenants.context import set_current_tenant

# Subdomains that must never resolve to a school tenant
RESERVED_SUBDOMAINS = frozenset({
    'www', 'api', 'admin', 'app', 'static', 'media',
})

# Hosts that are always root domain (no subdomain extraction)
ROOT_HOSTS = frozenset({
    'localhost', '127.0.0.1', 'ourapp.com',
})


class TenantMiddleware:
    """
    Django middleware for multi-tenant subdomain resolution.

    Placed after MessageMiddleware in the MIDDLEWARE chain so that
    django.contrib.messages is available for flash error alerts.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':')[0].lower()
        subdomain = self._extract_subdomain(host)

        tenant = None
        if subdomain:
            tenant = School.objects.filter(subdomain=subdomain, is_active=True).first()
            if tenant is None:
                # Subdomain present but not found in database → redirect to root
                messages.error(request, "School tenant not found.")
                root_host = self._build_root_host(request)
                return redirect(f"{request.scheme}://{root_host}/")

        request.tenant = tenant
        token = set_current_tenant(tenant)

        try:
            response = self.get_response(request)
        finally:
            # Always reset the context to prevent tenant leakage between requests
            set_current_tenant(None)

        return response

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_subdomain(host):
        """
        Extract subdomain from hostname, returning None for root domains.

        Examples:
          'localhost'               → None
          '127.0.0.1'              → None
          'schoola.localhost'      → 'schoola'
          'schoola.ourapp.com'     → 'schoola'
          'www.localhost'          → None  (reserved)
          'admin.ourapp.com'       → None  (reserved)
        """
        if host in ROOT_HOSTS:
            return None

        # Ignore raw IP addresses (e.g. 192.168.x.x, 127.0.0.1)
        try:
            ipaddress.ip_address(host)
            return None
        except ValueError:
            pass

        parts = host.split('.')

        # Handle .localhost domains (local dev: schoola.localhost)
        if parts[-1] == 'localhost' and len(parts) == 2:
            candidate = parts[0]
            if candidate not in RESERVED_SUBDOMAINS:
                return candidate
            return None

        # Handle production domains (schoola.ourapp.com)
        if len(parts) >= 3:
            candidate = parts[0]
            if candidate not in RESERVED_SUBDOMAINS:
                return candidate
            return None

        return None

    @staticmethod
    def _build_root_host(request):
        """Build the root host string for redirect, preserving port in dev."""
        full_host = request.get_host().lower()
        host_without_port = full_host.split(':')[0]

        # Determine root domain
        if 'localhost' in host_without_port:
            root_domain = 'localhost'
        else:
            try:
                ipaddress.ip_address(host_without_port)
                root_domain = host_without_port
            except ValueError:
                # Production: strip subdomain, keep domain + TLD
                parts = host_without_port.split('.')
                root_domain = '.'.join(parts[-2:]) if len(parts) >= 2 else host_without_port

        # Preserve port if present
        if ':' in full_host:
            port = full_host.split(':')[1]
            return f"{root_domain}:{port}"
        return root_domain
