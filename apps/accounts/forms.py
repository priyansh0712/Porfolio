from django import forms
from django.contrib.auth.forms import AuthenticationForm


class TenantLoginForm(AuthenticationForm):
    """
    Login form using email address instead of username.

    Overrides the default Django AuthenticationForm to present
    an email field as the primary identifier.
    """
    username = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 bg-white/50 '
                     'focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent '
                     'placeholder-gray-400 text-gray-900 transition-all duration-200',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email',
            'autofocus': True,
            'id': 'id_email',
        })
    )
    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 bg-white/50 '
                     'focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent '
                     'placeholder-gray-400 text-gray-900 transition-all duration-200',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
            'id': 'id_password',
        })
    )

    error_messages = {
        'invalid_login': (
            'Please enter a correct email address and password. '
            'Note that both fields are case-sensitive.'
        ),
        'inactive': 'This account is inactive.',
    }
