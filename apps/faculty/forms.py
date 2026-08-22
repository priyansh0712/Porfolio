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
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200/80 bg-white text-[#1d1d1f] text-sm focus:outline-none focus:ring-2 focus:ring-[#0066cc]/30 focus:border-[#0066cc] transition-all placeholder:text-[#86868b]',
            'placeholder': 'Set password (optional for login)',
        }),
        help_text="If set, this password allows the faculty member to log into their web dashboard."
    )

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
                'placeholder': 'e.g. Senior Teacher (Optional)',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        # Apply Standard Form Field Configuration
        if self.tenant:
            from apps.faculty.models import FacultyCustomField, FacultyFormFieldConfig
            config = FacultyFormFieldConfig.get_for_school(self.tenant)

            if not config.show_phone_number:
                self.fields['phone_number'].widget = forms.HiddenInput()
            self.fields['phone_number'].required = config.require_phone_number

            if not config.show_employee_code:
                self.fields['employee_code'].widget = forms.HiddenInput()
            self.fields['employee_code'].required = config.require_employee_code

            if not config.show_department:
                self.fields['department'].widget = forms.HiddenInput()
            self.fields['department'].required = config.require_department

            if not config.show_designation:
                self.fields['designation'].widget = forms.HiddenInput()
            self.fields['designation'].required = config.require_designation

            # Dynamic Custom Fields
            self.custom_field_defs = list(FacultyCustomField.objects.filter(school=self.tenant, is_active=True).order_by('order_index', 'created_at'))
            existing_custom = self.instance.custom_fields if (self.instance and self.instance.pk and self.instance.custom_fields) else {}

            for cf in self.custom_field_defs:
                field_key = f"custom_{cf.field_name}"
                initial_val = existing_custom.get(cf.field_name, '')
                field_attrs = {
                    'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200/80 bg-white text-[#1d1d1f] text-sm focus:outline-none focus:ring-2 focus:ring-[#0066cc]/30 focus:border-[#0066cc] transition-all placeholder:text-[#86868b]',
                    'placeholder': f'Enter {cf.label}'
                }

                if cf.field_type == FacultyCustomField.FieldType.NUMBER:
                    self.fields[field_key] = forms.IntegerField(label=cf.label, required=cf.is_required, initial=initial_val if initial_val != '' else None, widget=forms.NumberInput(attrs=field_attrs))
                elif cf.field_type == FacultyCustomField.FieldType.DATE:
                    field_attrs['class'] += ' apple-datepicker'
                    self.fields[field_key] = forms.CharField(label=cf.label, required=cf.is_required, initial=initial_val, widget=forms.TextInput(attrs=field_attrs))
                elif cf.field_type == FacultyCustomField.FieldType.SELECT:
                    opts = [('', f'-- Select {cf.label} --')] + [(o.strip(), o.strip()) for o in cf.options.split(',') if o.strip()]
                    self.fields[field_key] = forms.ChoiceField(label=cf.label, required=cf.is_required, choices=opts, initial=initial_val, widget=forms.Select(attrs=field_attrs))
                else:
                    self.fields[field_key] = forms.CharField(label=cf.label, required=cf.is_required, initial=initial_val, widget=forms.TextInput(attrs=field_attrs))

    def clean(self):
        cleaned_data = super().clean()
        custom_data = {}
        for cf in getattr(self, 'custom_field_defs', []):
            field_key = f"custom_{cf.field_name}"
            if field_key in cleaned_data:
                val = cleaned_data.get(field_key)
                if val is not None and str(val).strip() != '':
                    custom_data[cf.field_name] = str(val).strip()
        cleaned_data['custom_fields'] = custom_data
        return cleaned_data

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


class FacultyCustomFieldForm(forms.ModelForm):
    """Form for School Admin to define dynamic faculty custom fields."""
    class Meta:
        from apps.faculty.models import FacultyCustomField
        model = FacultyCustomField
        fields = ['label', 'field_type', 'options', 'is_required']
        widgets = {
            'label': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200/80 bg-white text-[#1d1d1f] text-sm focus:outline-none focus:ring-2 focus:ring-[#0066cc]/30 focus:border-[#0066cc] transition-all placeholder:text-[#86868b]',
                'placeholder': 'e.g. Qualification',
            }),
            'field_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200/80 bg-white text-[#1d1d1f] text-sm focus:outline-none focus:ring-2 focus:ring-[#0066cc]/30 focus:border-[#0066cc] transition-all',
                'id': 'id_faculty_custom_field_type',
            }),
            'options': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200/80 bg-white text-[#1d1d1f] text-sm focus:outline-none focus:ring-2 focus:ring-[#0066cc]/30 focus:border-[#0066cc] transition-all placeholder:text-[#86868b]',
                'placeholder': 'Option 1, Option 2 (comma separated)',
            }),
            'is_required': forms.CheckboxInput(attrs={'class': 'w-4 h-4 rounded text-[#0066cc]'}),
        }


class FacultyFormFieldConfigForm(forms.ModelForm):
    """Form for configuring visibility and required status of standard faculty fields."""
    class Meta:
        from apps.faculty.models import FacultyFormFieldConfig
        model = FacultyFormFieldConfig
        fields = [
            'show_phone_number', 'require_phone_number',
            'show_employee_code', 'require_employee_code',
            'show_department', 'require_department',
            'show_designation', 'require_designation',
        ]
        widgets = {
            'show_phone_number': forms.CheckboxInput(attrs={'class': 'w-4 h-4 rounded text-[#0066cc]'}),
            'require_phone_number': forms.CheckboxInput(attrs={'class': 'w-4 h-4 rounded text-[#0066cc]'}),
            'show_employee_code': forms.CheckboxInput(attrs={'class': 'w-4 h-4 rounded text-[#0066cc]'}),
            'require_employee_code': forms.CheckboxInput(attrs={'class': 'w-4 h-4 rounded text-[#0066cc]'}),
            'show_department': forms.CheckboxInput(attrs={'class': 'w-4 h-4 rounded text-[#0066cc]'}),
            'require_department': forms.CheckboxInput(attrs={'class': 'w-4 h-4 rounded text-[#0066cc]'}),
            'show_designation': forms.CheckboxInput(attrs={'class': 'w-4 h-4 rounded text-[#0066cc]'}),
            'require_designation': forms.CheckboxInput(attrs={'class': 'w-4 h-4 rounded text-[#0066cc]'}),
        }
