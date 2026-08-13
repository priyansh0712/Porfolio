from django.contrib import admin

from apps.schedules.models import WorkingSchedule, HolidayException


@admin.register(WorkingSchedule)
class WorkingScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'school', 'day_of_week', 'is_working_day',
        'start_time', 'end_time', 'grace_period_minutes',
    ]
    list_filter = ['is_working_day', 'school']
    ordering = ['school', 'day_of_week']


@admin.register(HolidayException)
class HolidayExceptionAdmin(admin.ModelAdmin):
    list_display = ['school', 'date', 'description', 'is_recurring_yearly']
    list_filter = ['is_recurring_yearly', 'school']
    search_fields = ['description']
    ordering = ['-date']
