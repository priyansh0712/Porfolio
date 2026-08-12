from django.contrib import admin

from apps.faculty.models import Faculty, TenantSequence


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = [
        'employee_code', 'full_name', 'email', 'department',
        'designation', 'is_active', 'is_face_enrolled', 'school',
    ]
    list_filter = ['is_active', 'is_face_enrolled', 'department', 'school']
    search_fields = ['first_name', 'last_name', 'email', 'employee_code']
    readonly_fields = ['date_joined']


@admin.register(TenantSequence)
class TenantSequenceAdmin(admin.ModelAdmin):
    list_display = ['school', 'sequence_type', 'last_value']
    list_filter = ['sequence_type']
