from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.accounts.forms import TenantLoginForm
from apps.accounts.models import User


class TenantLoginView(LoginView):
    """
    Login view for tenant subdomains and root domain.

    Uses TenantLoginForm (email-based). Redirects on success:
      - School Admin / Faculty → /dashboard/
      - Super Admin → /superadmin/
    """
    form_class = TenantLoginForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.role == User.Role.SUPER_ADMIN:
            return '/superadmin/'
        return '/dashboard/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tenant'] = getattr(self.request, 'tenant', None)
        return context


class TenantLogoutView(LogoutView):
    """Logs out user and redirects to /login/ on the current subdomain."""
    next_page = '/login/'


class TenantDashboardView(LoginRequiredMixin, TemplateView):
    """
    School Admin / Faculty dashboard view.

    Requires login. Restricted to tenant users (SCHOOL_ADMIN / FACULTY).
    Super Admin should not be able to reach this view (Layer 2 enforced
    by SchoolAdminRequiredMixin in Plan 04-02; LoginRequired here is the
    minimum gate).
    """
    template_name = 'accounts/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tenant'] = getattr(self.request, 'tenant', None)
        context['user'] = self.request.user
        return context
