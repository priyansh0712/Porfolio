from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
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
    http_method_names = ['get', 'post', 'options']

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


from apps.reports.views import AdminDashboardView
from django.views import View
from django.http import HttpResponseForbidden

class TenantDashboardView(LoginRequiredMixin, View):
    """
    Unified landing page for all tenant logins.
    Routes School Admins to AdminDashboardView, Faculty to FacultyDashboardView,
    and Students to StudentPortalView.
    """
    def get(self, request, *args, **kwargs):
        if request.user.role == User.Role.SCHOOL_ADMIN:
            return AdminDashboardView.as_view()(request, *args, **kwargs)
        elif request.user.role == User.Role.FACULTY:
            from apps.leaves.views import FacultyDashboardView
            return FacultyDashboardView.as_view()(request, *args, **kwargs)
        elif request.user.role == User.Role.STUDENT:
            from apps.students.views import StudentPortalView
            return StudentPortalView.as_view()(request, *args, **kwargs)
        return HttpResponseForbidden("Access Denied: Invalid role for school tenant subdomain.")


from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import redirect

class SelfPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """
    Self-service password update view for logged-in users of all roles (Admin, Faculty, Student).
    """
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:password_change')

    def form_valid(self, form):
        form.save()
        update_session_auth_hash(self.request, form.user)
        messages.success(self.request, 'Your password was successfully updated!')
        return redirect(self.success_url)


