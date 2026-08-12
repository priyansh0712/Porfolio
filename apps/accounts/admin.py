from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin panel for the User model."""

    list_display = ('email', 'first_name', 'last_name', 'role', 'school', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff', 'school')
    search_fields = ('email', 'first_name', 'last_name', 'username')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Role & Tenant'), {'fields': ('role', 'school')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'role', 'school', 'password1', 'password2'),
        }),
    )
