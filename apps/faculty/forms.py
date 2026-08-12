"""
Faculty Forms — tenant-aware validation.

FacultyForm validates:
  - Global email uniqueness (matches User.email constraint)
  - Per-school employee code uniqueness
  - employee_code is optional (auto-generated if blank)
"""
from django import forms

from apps.accounts.models import User
from apps.faculty.models import Faculty


class FacultyForm(forms.ModelForm):
    """
    ModelForm for creating/editing Faculty members.

    Usage:
        form = FacultyForm(data=request.POST, tenant=school)
        form = FacultyForm(data=request.POST, tenant=school, instance=faculty)

    The `tenant` kwarg is required for school-scoped validation.
    """

    class Meta:
        model = Faculty
        fields = [
            'first_name', 'last_name', 'email',
            'phone_number', 'employee_code',
            'department', 'designation',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200/80 bg-white text-[#1d1d1f] text-sm focus:outline-none focus:ring-2 focus:ring-[#0066cc]/30 focus:border-[#0066cc] transition-all placeholder:text-[#86868b]',
                'placeholder': 'First name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200/80 bg-white text-[#1d1d1f] text-sm focus:outline-none focus:ring-2 focus:ring-[#0066cc]/30 focus:border-[#0066cc] transition-all placeholder:text-[#86868b]',
                'placeholder': 'Last name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200/80 bg-white text-[#1d1d1f] text-sm focus:outline-none focus:ring-2 focus:ring-[#0066cc]/30 focus:border-[#0066cc] transition-all placeholder:text-[#86868b]',
                'placeholder': 'faculty@school.edu',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200/80 bg-white text-[#1d1d1f] text-sm focus:outline-none focus:ring-2 focus:ring-[#0066cc]/30 focus:border-[#0066cc] transition-all placeholder:text-[#86868b]',
                'placeholder': '+91 XXXXX XXXXX',
            }),
            'employee_code': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200/80 bg-gray-50/80 text-[#1d1d1f] text-sm focus:outline-none focus:ring-2 focus:ring-[#0066cc]/30 focus:border-[#0066cc] transition-all placeholder:text-[#86868b]',
                'placeholder': 'Auto-generated if left blank',
            }),
            'department': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200/80 bg-white text-[#1d1d1f] text-sm focus:outline-none focus:ring-2 focus:ring-[#0066cc]/30 focus:border-[#0066cc] transition-all placeholder:text-[#86868b]',
                'placeholder': 'e.g. Science, Mathematics',
            }),
            'designation': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200/80 bg-white text-[#1d1d1f] text-sm focus:outline-none focus:ring-2 focus:ring-[#0066cc]/30 focus:border-[#0066cc] transition-all placeholder:text-[#86868b]',
                'placeholder': 'e.g. Senior Teacher, HOD',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        self.fields['employee_code'].required = False

    def clean_email(self):
        """Enforce global email uniqueness (matches User.email constraint)."""
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise forms.ValidationError('Email is required.')

        # Exclude current instance on edit
        qs = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk and self.instance.user:
            qs = qs.exclude(pk=self.instance.user.pk)
        if qs.exists():
            raise forms.ValidationError(
                'A user with this email already exists. '
                'Each faculty member must have a unique email address.'
            )
        return email

    def clean_employee_code(self):
        """Enforce per-school employee code uniqueness (if provided)."""
        code = self.cleaned_data.get('employee_code', '').strip()
        if not code:
            return code  # Auto-generation handled in service layer

        if self.tenant:
            qs = Faculty.objects.filter(
                school=self.tenant,
                employee_code__iexact=code,
            )
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f'Employee code "{code}" is already assigned to '
                    f'another faculty member in this school.'
                )
        return code
