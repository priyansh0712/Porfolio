from django.contrib import admin

from apps.biometrics.models import FacultyBiometric


@admin.register(FacultyBiometric)
class FacultyBiometricAdmin(admin.ModelAdmin):
    """Admin registration for FacultyBiometric (read-only by design)."""
    list_display = ('faculty', 'school', 'enrolled_at', 'enrolled_by')
    list_filter = ('school',)
    search_fields = ('faculty__first_name', 'faculty__last_name', 'faculty__email')
    readonly_fields = ('embedding', 'enrolled_at')
    raw_id_fields = ('faculty', 'enrolled_by')
