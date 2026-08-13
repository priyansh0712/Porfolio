"""
Schedule Settings Views — Tenant Working Hours & Holiday Exceptions (3-Layer Security).

Layer 1: TenantMiddleware (request.tenant)
Layer 2: SchoolAdminRequiredMixin (role-based access)
Layer 3: Queryset scoping (school=request.tenant)

Endpoint: /settings/schedule/
"""
import logging
from datetime import datetime

from django.contrib import messages
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.permissions import SchoolAdminRequiredMixin
from apps.schedules.models import WorkingSchedule, HolidayException
from apps.schedules.services import ScheduleService

logger = logging.getLogger(__name__)


class ScheduleSettingsView(SchoolAdminRequiredMixin, TemplateView):
    """
    Renders the Apple-aesthetic Schedule & Holiday Settings dashboard.

    Allows School Admins to:
      - Update day-of-week working hours, working status, and grace periods.
      - Add and remove holiday exception dates.
    """
    template_name = 'schedules/schedule_settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school = self.request.tenant

        # Ensure default schedules exist (0=Monday .. 6=Sunday)
        schedules = ScheduleService.initialize_default_schedules(school)

        holidays = HolidayException.objects.filter(school=school).order_by('-date')

        context.update({
            'schedules': schedules,
            'holidays': holidays,
            'days': WorkingSchedule.DAY_CHOICES,
        })
        return context

    def post(self, request, *args, **kwargs):
        school = request.tenant
        action = request.POST.get('action')

        if action == 'update_schedule':
            # ── Update day-of-week working schedule ──
            day_of_week = request.POST.get('day_of_week')
            is_working_day = request.POST.get('is_working_day') == 'on'
            start_time_str = request.POST.get('start_time', '08:00')
            end_time_str = request.POST.get('end_time', '16:00')
            grace_period = request.POST.get('grace_period_minutes', 15)

            try:
                day_num = int(day_of_week)
                grace_num = max(0, int(grace_period))
                start_time = datetime.strptime(start_time_str, '%H:%M').time()
                end_time = datetime.strptime(end_time_str, '%H:%M').time()

                schedule, _ = WorkingSchedule.objects.update_or_create(
                    school=school,
                    day_of_week=day_num,
                    defaults={
                        'is_working_day': is_working_day,
                        'start_time': start_time,
                        'end_time': end_time,
                        'grace_period_minutes': grace_num,
                    },
                )
                day_name = dict(WorkingSchedule.DAY_CHOICES).get(day_num, str(day_num))
                messages.success(request, f"Working schedule updated for {day_name}.")
                logger.info("Updated WorkingSchedule day %d for school %s", day_num, school.subdomain)

            except (ValueError, TypeError) as e:
                messages.error(request, f"Invalid schedule data: {e}")

        elif action == 'add_holiday':
            # ── Add holiday exception ──
            date_str = request.POST.get('date')
            description = request.POST.get('description', '').strip()
            is_recurring = request.POST.get('is_recurring_yearly') == 'on'

            if not date_str or not description:
                messages.error(request, "Date and holiday description are required.")
            else:
                try:
                    holiday_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    HolidayException.objects.update_or_create(
                        school=school,
                        date=holiday_date,
                        defaults={
                            'description': description,
                            'is_recurring_yearly': is_recurring,
                        },
                    )
                    messages.success(request, f"Holiday '{description}' added for {holiday_date}.")
                    logger.info("Added HolidayException %s for school %s", holiday_date, school.subdomain)
                except ValueError:
                    messages.error(request, "Invalid date format. Use YYYY-MM-DD.")

        elif action == 'delete_holiday':
            # ── Delete holiday exception ──
            holiday_id = request.POST.get('holiday_id')
            deleted_count, _ = HolidayException.objects.filter(
                school=school, id=holiday_id
            ).delete()
            if deleted_count > 0:
                messages.success(request, "Holiday exception removed.")
            else:
                messages.error(request, "Holiday exception not found.")

        return redirect('schedules:settings')
