import re
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import School

from .validators import validate_image_file_size, validate_image_extension

RESERVED_SUBDOMAINS = {
    'www', 'admin', 'api', 'app', 'mail', 'static', 'media',
    'support', 'help', 'public', 'superadmin', 'dashboard',
    'portal', 'billing', 'system', 'root', 'login', 'logout'
}

class SchoolRegistrationForm(forms.Form):
    school_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors',
            'placeholder': 'e.g. Greenwood High School',
        })
    )
    subdomain = forms.CharField(
        max_length=63,
        min_length=3,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors pl-4 pr-32',
            'placeholder': 'greenwood',
        }),
        help_text="Your unique domain prefix: [subdomain].ourapp.com"
    )
    contact_email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors',
            'placeholder': 'admin@greenwood.edu',
        })
    )
    school_image = forms.ImageField(
        required=False,
        validators=[validate_image_file_size, validate_image_extension],
        widget=forms.FileInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg text-xs file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100',
            'accept': 'image/*'
        }),
        help_text="Cover/hero image for login page (Max 5MB)"
    )
    school_logo = forms.ImageField(
        required=False,
        validators=[validate_image_file_size, validate_image_extension],
        widget=forms.FileInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg text-xs file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100',
            'accept': 'image/*'
        }),
        help_text="School logo for portal header (Max 5MB)"
    )
    admin_full_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors',
            'placeholder': 'Principal Jane Doe',
        })
    )
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors',
            'placeholder': '••••••••',
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors',
            'placeholder': '••••••••',
        })
    )

    def clean_subdomain(self):
        subdomain = self.cleaned_data.get('subdomain', '').lower().strip()
        
        # Format validation
        if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', subdomain):
            raise ValidationError("Subdomain can only contain lowercase letters, numbers, and hyphens.")

        # Reserved subdomain check
        if subdomain in RESERVED_SUBDOMAINS:
            raise ValidationError(f"'{subdomain}' is a reserved system name and cannot be used.")

        # Existing check
        if School.objects.filter(subdomain=subdomain).exists():
            raise ValidationError(f"The subdomain '{subdomain}.ourapp.com' is already registered. Please choose another.")

        return subdomain

    def clean_contact_email(self):
        email = self.cleaned_data.get('contact_email', '').lower().strip()
        User = get_user_model()
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")

        return cleaned_data


class SchoolBrandingForm(forms.ModelForm):
    """Form for updating school branding (Image & Logo) in School Admin settings."""
    class Meta:
        model = School
        fields = ['school_image', 'school_logo']
        widgets = {
            'school_image': forms.FileInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg text-xs file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-[#5A2132]/10 file:text-[#5A2132] hover:file:bg-[#5A2132]/20 transition-all',
                'accept': 'image/*'
            }),
            'school_logo': forms.FileInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg text-xs file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-[#5A2132]/10 file:text-[#5A2132] hover:file:bg-[#5A2132]/20 transition-all',
                'accept': 'image/*'
            }),
        }
