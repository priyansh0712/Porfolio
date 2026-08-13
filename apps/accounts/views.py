from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from django.utils.decorators import method_decorator
from apps.accounts.forms import TenantLoginForm
from apps.accounts.models import User
from apps.core.ratelimit import rate_limit


@method_decorator(rate_limit(key_prefix='login', limit=5, period_seconds=60), name='dispatch')
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
        return self.get_redirect_url() or '/dashboard/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tenant'] = getattr(self.request, 'tenant', None)
        return context


class TenantLogoutView(LogoutView):
    """Logs out user and redirects to /login/ on the current subdomain."""
    next_page = '/login/'


from apps.reports.views import AdminDashboardView

class TenantDashboardView(AdminDashboardView):
    """
    Primary School Admin Dashboard view for tenant subdomains.
    Delivers KPI summary cards, live activity feed, and quick actions.
    """
    pass
