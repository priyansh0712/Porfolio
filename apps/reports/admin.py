from django.contrib import admin

from apps.reports.models import AttendanceCorrection


@admin.register(AttendanceCorrection)
class AttendanceCorrectionAdmin(admin.ModelAdmin):
    list_display = [
        'attendance', 'school', 'old_status', 'new_status',
        'performed_by', 'reason', 'created_at',
    ]
    list_filter = ['school', 'old_status', 'new_status', 'created_at']
    search_fields = [
        'attendance__faculty__first_name',
        'attendance__faculty__last_name',
        'reason',
    ]
    readonly_fields = [
        'school', 'attendance', 'performed_by',
        'old_status', 'new_status', 'old_check_in_time',
        'new_check_in_time', 'old_check_out_time',
        'new_check_out_time', 'reason', 'created_at',
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
