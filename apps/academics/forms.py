"""
Academics Management Forms.

All forms enforce strict tenant-level queryset filtering and clean validation.
"""
from django import forms
from django.core.exceptions import ValidationError

from apps.academics.models import (
    AcademicYear,
    Standard,
    Division,
    Subject,
    ClassCurriculum,
    ClassTeacherAllocation,
    SubjectTeacherAllocation,
)
from apps.faculty.models import Faculty


class AcademicYearForm(forms.ModelForm):
    class Meta:
        model = AcademicYear
        fields = ['name', 'start_date', 'end_date', 'is_current']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20',
                'placeholder': 'e.g. 2026-2027',
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20',
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20',
            }),
            'is_current': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-[#0066cc] focus:ring-[#0066cc] h-4 w-4',
            }),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        self.tenant = tenant
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError('Academic Year name is required.')
        qs = AcademicYear.objects.filter(name__iexact=name)
        if self.tenant:
            qs = qs.filter(school=self.tenant)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f"An Academic Year with the name '{name}' already exists.")
        return name

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and start_date >= end_date:
            self.add_error('end_date', 'End date must be strictly after start date.')
        return cleaned_data


class StandardForm(forms.ModelForm):
    class Meta:
        model = Standard
        fields = ['name', 'order_index', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20',
                'placeholder': 'e.g. Standard 10, Grade 1, UKG',
            }),
            'order_index': forms.NumberInput(attrs={
                'class': 'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20',
                'min': '0',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-[#0066cc] focus:ring-[#0066cc] h-4 w-4',
            }),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        self.tenant = tenant
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError('Standard name is required.')
        qs = Standard.objects.filter(name__iexact=name)
        if self.tenant:
            qs = qs.filter(school=self.tenant)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f"A Standard with the name '{name}' already exists in your school.")
        return name


class DivisionForm(forms.ModelForm):
    class Meta:
        model = Division
        fields = ['standard', 'name', 'is_active']
        widgets = {
            'standard': forms.Select(attrs={
                'class': 'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20',
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20',
                'placeholder': 'e.g. A, B, C, Rose',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-[#0066cc] focus:ring-[#0066cc] h-4 w-4',
            }),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        self.tenant = tenant
        super().__init__(*args, **kwargs)
        if self.tenant:
            self.fields['standard'].queryset = Standard.objects.filter(school=self.tenant, is_active=True)

    def clean_name(self):
        return self.cleaned_data.get('name', '').strip().upper()

    def clean(self):
        cleaned_data = super().clean()
        standard = cleaned_data.get('standard')
        name = cleaned_data.get('name')
        if standard and name:
            qs = Division.objects.filter(standard=standard, name__iexact=name)
            if self.tenant:
                qs = qs.filter(school=self.tenant)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('name', f"Division '{name}' already exists for {standard.name}.")
        return cleaned_data


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'code', 'subject_type', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20',
                'placeholder': 'e.g. Mathematics, English, Science',
            }),
            'code': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20 uppercase',
                'placeholder': 'e.g. MATH-01, ENG-01',
            }),
            'subject_type': forms.Select(attrs={
                'class': 'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-[#0066cc] focus:ring-[#0066cc] h-4 w-4',
            }),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        self.tenant = tenant
        super().__init__(*args, **kwargs)
        self.fields['code'].required = False

    def clean_code(self):
        code = self.cleaned_data.get('code', '')
        if code:
            code = code.strip().upper()
        else:
            code = ''
        if code:
            qs = Subject.objects.filter(code__iexact=code)
            if self.tenant:
                qs = qs.filter(school=self.tenant)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(f"A Subject with code '{code}' already exists in your school.")
        return code


class ClassCurriculumForm(forms.ModelForm):
    class Meta:
        model = ClassCurriculum
        fields = ['academic_year', 'standard', 'subject']
        widgets = {
            'academic_year': forms.Select(attrs={
                'class': 'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20',
            }),
            'standard': forms.Select(attrs={
                'class': 'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20',
            }),
            'subject': forms.Select(attrs={
                'class': 'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20',
            }),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        self.tenant = tenant
        super().__init__(*args, **kwargs)
        if self.tenant:
            self.fields['academic_year'].queryset = AcademicYear.objects.filter(school=self.tenant)
            self.fields['standard'].queryset = Standard.objects.filter(school=self.tenant, is_active=True).order_by('order_index', 'name')
            self.fields['subject'].queryset = Subject.objects.filter(school=self.tenant, is_active=True).order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        academic_year = cleaned_data.get('academic_year')
        standard = cleaned_data.get('standard')
        subject = cleaned_data.get('subject')

        if academic_year and standard and subject and self.tenant:
            qs = ClassCurriculum.objects.filter(
                school=self.tenant,
                academic_year=academic_year,
                standard=standard,
                subject=subject,
            )
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(f"'{subject.name}' is already assigned to {standard.name} for {academic_year.name}.")
        return cleaned_data


class ClassTeacherAllocationForm(forms.ModelForm):
    class Meta:
        model = ClassTeacherAllocation
        fields = ['academic_year', 'division', 'faculty']
        widgets = {
            'academic_year': forms.Select(attrs={
                'class': 'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20',
            }),
            'division': forms.Select(attrs={
                'class': 'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20',
            }),
            'faculty': forms.Select(attrs={
                'class': 'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20',
            }),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        self.tenant = tenant
        super().__init__(*args, **kwargs)
        if self.tenant:
            self.fields['academic_year'].queryset = AcademicYear.objects.filter(school=self.tenant)
            self.fields['division'].queryset = Division.objects.filter(school=self.tenant, is_active=True).select_related('standard')
            self.fields['faculty'].queryset = Faculty.objects.filter(school=self.tenant, is_active=True)


class SubjectTeacherAllocationForm(forms.ModelForm):
    class Meta:
        model = SubjectTeacherAllocation
        fields = ['academic_year', 'division', 'subject', 'faculty']
        widgets = {
            'academic_year': forms.Select(attrs={
                'class': 'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20',
            }),
            'division': forms.Select(attrs={
                'class': 'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20',
            }),
            'subject': forms.Select(attrs={
                'class': 'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20',
            }),
            'faculty': forms.Select(attrs={
                'class': 'w-full rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20',
            }),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        self.tenant = tenant
        super().__init__(*args, **kwargs)
        if self.tenant:
            self.fields['academic_year'].queryset = AcademicYear.objects.filter(school=self.tenant)
            self.fields['division'].queryset = Division.objects.filter(school=self.tenant, is_active=True).select_related('standard')
            self.fields['subject'].queryset = Subject.objects.filter(school=self.tenant, is_active=True)
            self.fields['faculty'].queryset = Faculty.objects.filter(school=self.tenant, is_active=True)

