from django.views.generic import TemplateView, FormView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from apps.tenants.forms import SchoolRegistrationForm
from apps.tenants.services import SchoolRegistrationService
from apps.tenants.models import School

class LandingPageView(TemplateView):
    """
    Renders the main public marketing landing page for StudentERP.
    """
    template_name = 'public/landing.html'


class SchoolRegistrationView(FormView):
    """
    Handles school self-registration onboarding.
    """
    template_name = 'public/register.html'
    form_class = SchoolRegistrationForm
    success_url = reverse_lazy('public:register_success')

    def form_valid(self, form):
        try:
            school, admin_user = SchoolRegistrationService.register_school(form.cleaned_data)
            messages.success(
                self.request,
                f"Welcome to StudentERP! '{school.name}' has been registered successfully."
            )
            self.request.session['registered_subdomain'] = school.subdomain
            return super().form_valid(form)
        except Exception as e:
            form.add_error(None, f"An error occurred during registration: {str(e)}")
            return self.form_invalid(form)


class RegistrationSuccessView(TemplateView):
    """
    Renders the registration success and onboarding confirmation page.
    """
    template_name = 'public/register_success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subdomain = self.request.session.get('registered_subdomain') or self.request.GET.get('subdomain')
        if subdomain:
            school = School.objects.filter(subdomain=subdomain).first()
            context['school'] = school
            if school:
                host = self.request.get_host().lower()
                scheme = self.request.scheme
                if 'localhost' in host:
                    port = f":{host.split(':')[1]}" if ':' in host else ''
                    context['school_login_url'] = f"{scheme}://{school.subdomain}.localhost{port}/login/"
                else:
                    context['school_login_url'] = f"{scheme}://{school.full_domain}/login/"
        return context
