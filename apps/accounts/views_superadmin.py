"""
Super Admin platform management views.

These views are accessible ONLY on the root domain (/superadmin/) and are
protected by SuperAdminRequiredMixin (Layer 2). They expose only school
tenant metadata — NEVER faculty, biometric, or attendance records.
"""
from django.views.generic import TemplateView

from apps.accounts.permissions import SuperAdminRequiredMixin
from apps.tenants.models import School


class SuperAdminDashboardView(SuperAdminRequiredMixin, TemplateView):
    """
    Platform Super Admin dashboard listing all registered school tenants.

    Privacy boundary (AUTH-02):
      - Only displays school-level metadata (name, subdomain, contact, status, created date).
      - Does NOT query, display, or expose any faculty records, biometric data,
        face embeddings, or attendance records.
      - This is enforced explicitly here and at middleware layer (Layer 1).
    """
    template_name = 'accounts/superadmin_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Query school metadata ONLY — no faculty or attendance lookups
        schools = School.objects.all().order_by('-created_at')
        context['schools'] = schools
        context['school_count'] = schools.count()
        context['active_count'] = schools.filter(is_active=True).count()
        context['inactive_count'] = schools.filter(is_active=False).count()
        return context
