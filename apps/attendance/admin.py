from django.contrib import admin

from apps.attendance.models import AttendanceLog


@admin.register(AttendanceLog)
class AttendanceLogAdmin(admin.ModelAdmin):
    list_display = [
        'faculty', 'school', 'date', 'check_in_time',
        'check_out_time', 'status', 'match_confidence',
    ]
    list_filter = ['status', 'date', 'school']
    search_fields = [
        'faculty__first_name', 'faculty__last_name',
        'faculty__employee_code',
    ]
    readonly_fields = [
        'check_in_time', 'check_out_time', 'last_scan_at',
        'match_confidence', 'device_info',
    ]
    date_hierarchy = 'date'
    ordering = ['-date', '-check_in_time']
