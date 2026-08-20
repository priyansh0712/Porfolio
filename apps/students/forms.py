"""
Student Management Forms.

All forms enforce strict tenant-level queryset filtering
and clean validation per the Apple Design System widget style.
"""
from django import forms
from django.core.exceptions import ValidationError

from apps.students.models import Student, StudentTransferRequest
from apps.academics.models import AcademicYear, Standard, Division

INPUT_CLASS = (
    'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm '
    'focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20 '
    'bg-white text-[#1d1d1f] placeholder-gray-400'
)
SELECT_CLASS = (
    'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm '
    'focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20 bg-white text-[#1d1d1f]'
)


DATE_INPUT_FORMATS = [
    '%Y-%m-%d',
    '%d-%m-%Y',
    '%d/%m/%Y',
    '%Y/%m/%d',
    '%d %b, %Y',
    '%d %b %Y',
    '%d %B, %Y',
    '%d %B %Y',
    '%b %d, %Y',
    '%b %d %Y',
    '%B %d, %Y',
    '%B %d %Y',
    '%m/%d/%Y',
    '%m-%d-%Y',
]


class StudentForm(forms.Form):
    """
    Unified Add/Edit student form.

    When is_edit=True and allow_gr_edit=False (Class Teacher editing):
      - gr_number field is rendered read-only and excluded from cleaned_data.

    tenant, academic_year are injected at instantiation to scope
    Standard/Division querysets to the right school + year.
    """

    full_name = forms.CharField(
        label='Full Name', max_length=255,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g. Raj Kumar Patel'}),
    )
    gr_number = forms.CharField(
        label='GR Number', max_length=50,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g. GR2026001'}),
    )
    roll_number = forms.IntegerField(
        label='Roll Number', required=False, min_value=1,
        widget=forms.NumberInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Optional'}),
    )
    gender = forms.ChoiceField(
        label='Gender', choices=Student.Gender.choices,
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )
    blood_group = forms.ChoiceField(
        label='Blood Group',
        choices=[('', 'Unknown / Not Set')] + [(v, v) for v in ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']],
        required=False,
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )
    dob = forms.DateField(
        label='Date of Birth', required=False,
        input_formats=DATE_INPUT_FORMATS,
        widget=forms.DateInput(attrs={'type': 'text', 'class': 'apple-datepicker ' + INPUT_CLASS, 'placeholder': 'Select Date of Birth', 'autocomplete': 'off'}),
    )
    standard = forms.ModelChoiceField(
        label='Standard', queryset=Standard.objects.none(),
        widget=forms.Select(attrs={'class': SELECT_CLASS, 'id': 'id_standard'}),
    )
    division = forms.ModelChoiceField(
        label='Division', queryset=Division.objects.none(),
        widget=forms.Select(attrs={'class': SELECT_CLASS, 'id': 'id_division'}),
    )
    admission_date = forms.DateField(
        label='Admission Date', required=False,
        input_formats=DATE_INPUT_FORMATS,
        widget=forms.DateInput(attrs={'type': 'text', 'class': 'apple-datepicker ' + INPUT_CLASS, 'placeholder': 'Select Admission Date', 'autocomplete': 'off'}),
    )
    guardian_name = forms.CharField(
        label='Guardian Name', max_length=255, required=False,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Parent / Guardian name'}),
    )
    guardian_phone = forms.CharField(
        label='Guardian Phone', max_length=20, required=False,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': '+91 99999 00000'}),
    )
    emergency_contact = forms.CharField(
        label='Emergency Contact', max_length=20, required=False,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Emergency phone'}),
    )
    address = forms.CharField(
        label='Address', required=False,
        widget=forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 2, 'placeholder': 'Full address'}),
    )

    def __init__(self, *args, tenant=None, academic_year=None,
                 is_edit=False, allow_gr_edit=True,
                 locked_division=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        self.is_edit = is_edit
        self.allow_gr_edit = allow_gr_edit

        # Scope Standard queryset to tenant
        if tenant:
            self.fields['standard'].queryset = Standard.objects.filter(
                school=tenant
            ).order_by('order_index', 'name')

        # Scope Division queryset
        if locked_division:
            # Class Teacher: locked to their assigned division
            self.fields['standard'].required = False
            self.fields['division'].required = False
            self.fields['division'].queryset = Division.objects.filter(pk=locked_division.pk)
            self.fields['division'].initial = locked_division
            self.fields['division'].widget.attrs['disabled'] = True
        elif tenant:
            self.fields['division'].queryset = Division.objects.filter(
                school=tenant
            ).order_by('standard__order_index', 'name')

        if is_edit:
            self.fields['gr_number'].required = False
            self.fields['standard'].required = False
            self.fields['division'].required = False

        # GR Number lock for Class Teacher editing
        if is_edit and not allow_gr_edit:
            self.fields['gr_number'].widget.attrs['readonly'] = True
            self.fields['gr_number'].widget.attrs['class'] += ' bg-gray-100 cursor-not-allowed'
            self.fields['gr_number'].required = False

        # Apply standard field visibility & requirement configs
        if tenant:
            from apps.students.models import StudentFormFieldConfig
            config = StudentFormFieldConfig.get_for_school(tenant)
            self.form_config = config

            if not is_edit:
                if 'roll_number' in self.fields:
                    self.fields['roll_number'].required = config.require_roll_number
                if 'gender' in self.fields:
                    self.fields['gender'].required = config.require_gender
                if 'dob' in self.fields:
                    self.fields['dob'].required = config.require_dob
                if 'blood_group' in self.fields:
                    self.fields['blood_group'].required = config.require_blood_group
                if 'guardian_name' in self.fields:
                    self.fields['guardian_name'].required = config.require_guardian_details
                if 'guardian_phone' in self.fields:
                    self.fields['guardian_phone'].required = config.require_guardian_details
                if 'emergency_contact' in self.fields:
                    self.fields['emergency_contact'].required = config.require_emergency_contact
                if 'admission_date' in self.fields:
                    self.fields['admission_date'].required = config.require_admission_date
                if 'address' in self.fields:
                    self.fields['address'].required = config.require_address

        # Attach active dynamic custom fields
        self.custom_field_defs = []
        if tenant:
            from apps.students.models import StudentCustomField
            self.custom_field_defs = list(StudentCustomField.objects.filter(school=tenant, is_active=True).order_by('order_index', 'created_at'))
            for cf in self.custom_field_defs:
                key = f'cf_{cf.field_name}'
                if cf.field_type == StudentCustomField.FieldType.NUMBER:
                    self.fields[key] = forms.IntegerField(
                        label=cf.label, required=cf.is_required and not is_edit,
                        widget=forms.NumberInput(attrs={'class': INPUT_CLASS, 'placeholder': cf.label}),
                    )
                elif cf.field_type == StudentCustomField.FieldType.DATE:
                    self.fields[key] = forms.DateField(
                        label=cf.label, required=cf.is_required and not is_edit,
                        input_formats=DATE_INPUT_FORMATS,
                        widget=forms.DateInput(attrs={'type': 'text', 'class': 'apple-datepicker ' + INPUT_CLASS, 'placeholder': f'Select {cf.label}', 'autocomplete': 'off'}),
                    )
                elif cf.field_type == StudentCustomField.FieldType.SELECT:
                    opts = [('', f'— Select {cf.label} —')] + [(opt, opt) for opt in cf.get_options_list()]
                    self.fields[key] = forms.ChoiceField(
                        label=cf.label, choices=opts, required=cf.is_required and not is_edit,
                        widget=forms.Select(attrs={'class': SELECT_CLASS}),
                    )
                else:
                    self.fields[key] = forms.CharField(
                        label=cf.label, required=cf.is_required and not is_edit,
                        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': cf.label}),
                    )

    def clean(self):
        cleaned_data = super().clean()
        custom_data = {}
        for cf in getattr(self, 'custom_field_defs', []):
            key = f'cf_{cf.field_name}'
            if key in cleaned_data and cleaned_data[key] not in (None, ''):
                val = cleaned_data[key]
                if hasattr(val, 'isoformat'):
                    val = val.isoformat()
                custom_data[cf.field_name] = val
        cleaned_data['custom_fields'] = custom_data
        return cleaned_data

    def clean_gr_number(self):
        # Honour the lock silently — view will strip gr_number from update call
        return self.cleaned_data.get('gr_number', '').strip()

    def clean_full_name(self):
        name = self.cleaned_data.get('full_name', '').strip()
        if not name:
            raise ValidationError('Full name is required.')
        return name


class StudentCustomFieldForm(forms.ModelForm):
    """Form for Principal / School Admin to define dynamic custom student fields."""
    class Meta:
        from apps.students.models import StudentCustomField
        model = StudentCustomField
        fields = ['label', 'field_type', 'options', 'is_required']
        widgets = {
            'label': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g. Aadhar Number, Bus Route, House'}),
            'field_type': forms.Select(attrs={'class': SELECT_CLASS, 'id': 'id_custom_field_type'}),
            'options': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Red, Blue, Green (comma-separated for Dropdown)'}),
            'is_required': forms.CheckboxInput(attrs={'class': 'rounded border-gray-300 text-[#0066cc] focus:ring-[#0066cc] h-4 w-4'}),
        }


class StudentFormFieldConfigForm(forms.ModelForm):
    """Form for Principal to customize which built-in fields are shown and required."""
    class Meta:
        from apps.students.models import StudentFormFieldConfig
        model = StudentFormFieldConfig
        fields = [
            'show_roll_number', 'require_roll_number',
            'show_gender', 'require_gender',
            'show_dob', 'require_dob',
            'show_blood_group', 'require_blood_group',
            'show_guardian_details', 'require_guardian_details',
            'show_emergency_contact', 'require_emergency_contact',
            'show_admission_date', 'require_admission_date',
            'show_address', 'require_address',
        ]
        widgets = {
            'show_roll_number': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-[#0066cc] rounded border-gray-300 focus:ring-[#0066cc]'}),
            'require_roll_number': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-[#0066cc] rounded border-gray-300 focus:ring-[#0066cc]'}),
            'show_gender': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-[#0066cc] rounded border-gray-300 focus:ring-[#0066cc]'}),
            'require_gender': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-[#0066cc] rounded border-gray-300 focus:ring-[#0066cc]'}),
            'show_dob': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-[#0066cc] rounded border-gray-300 focus:ring-[#0066cc]'}),
            'require_dob': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-[#0066cc] rounded border-gray-300 focus:ring-[#0066cc]'}),
            'show_blood_group': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-[#0066cc] rounded border-gray-300 focus:ring-[#0066cc]'}),
            'require_blood_group': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-[#0066cc] rounded border-gray-300 focus:ring-[#0066cc]'}),
            'show_guardian_details': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-[#0066cc] rounded border-gray-300 focus:ring-[#0066cc]'}),
            'require_guardian_details': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-[#0066cc] rounded border-gray-300 focus:ring-[#0066cc]'}),
            'show_emergency_contact': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-[#0066cc] rounded border-gray-300 focus:ring-[#0066cc]'}),
            'require_emergency_contact': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-[#0066cc] rounded border-gray-300 focus:ring-[#0066cc]'}),
            'show_admission_date': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-[#0066cc] rounded border-gray-300 focus:ring-[#0066cc]'}),
            'require_admission_date': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-[#0066cc] rounded border-gray-300 focus:ring-[#0066cc]'}),
            'show_address': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-[#0066cc] rounded border-gray-300 focus:ring-[#0066cc]'}),
            'require_address': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-[#0066cc] rounded border-gray-300 focus:ring-[#0066cc]'}),
        }



class StudentTransferRequestForm(forms.Form):
    """Form for Class Teacher to submit a transfer request for a student."""

    to_standard = forms.ModelChoiceField(
        label='New Standard', queryset=Standard.objects.none(),
        widget=forms.Select(attrs={'class': SELECT_CLASS, 'id': 'id_to_standard'}),
    )
    to_division = forms.ModelChoiceField(
        label='New Division', queryset=Division.objects.none(),
        widget=forms.Select(attrs={'class': SELECT_CLASS, 'id': 'id_to_division'}),
    )
    reason = forms.CharField(
        label='Reason for Transfer', required=False,
        widget=forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 3,
                                     'placeholder': 'Optional — describe the reason for this transfer'}),
    )

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant:
            self.fields['to_standard'].queryset = Standard.objects.filter(
                school=tenant
            ).order_by('order_index', 'name')
            self.fields['to_division'].queryset = Division.objects.filter(
                school=tenant
            ).order_by('standard__order_index', 'name')


class TransferRejectForm(forms.Form):
    """Form for School Admin to provide a rejection reason."""
    rejection_reason = forms.CharField(
        label='Rejection Reason', required=False,
        widget=forms.Textarea(attrs={
            'class': INPUT_CLASS, 'rows': 3,
            'placeholder': 'Explain why this transfer is being rejected (optional)',
        }),
    )

