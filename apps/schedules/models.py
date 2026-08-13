"""
Working Schedules & Holiday Exceptions Models.

Contains:
  - WorkingSchedule: Day-of-week working hours and grace period configuration.
    Enforces unique constraint on (school, day_of_week) so each tenant school
    maintains exactly 7 day records (0=Monday through 6=Sunday).
  - HolidayException: Date-specific holiday overrides (e.g. Christmas, Independence Day).
    Enforces unique constraint on (school, date).
"""
from django.db import models

from apps.tenants.models import TenantModel


class WorkingSchedule(TenantModel):
    """
    Day-of-week working schedule and punctuality rules for a school tenant.

    Fields:
      - day_of_week: 0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday.
      - is_working_day: Whether school is open on this day.
      - start_time: Official shift start time (e.g. 08:00:00).
      - end_time: Official shift end time (e.g. 16:00:00).
      - grace_period_minutes: Minutes after start_time before scan is marked LATE (default 15).
    """

    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    day_of_week = models.IntegerField(
        choices=DAY_CHOICES,
        help_text='Day of week (0=Monday .. 6=Sunday)',
    )
    is_working_day = models.BooleanField(
        default=True,
        help_text='Whether faculty are scheduled to work on this day',
    )
    start_time = models.TimeField(
        default='08:00:00',
        help_text='Scheduled shift start time',
    )
    end_time = models.TimeField(
        default='16:00:00',
        help_text='Scheduled shift end time',
    )
    grace_period_minutes = models.PositiveIntegerField(
        default=15,
        help_text='Grace period window in minutes after start_time before LATE status',
    )

    class Meta:
        ordering = ['day_of_week']
        verbose_name = 'Working Schedule'
        verbose_name_plural = 'Working Schedules'
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'day_of_week'],
                name='unique_schedule_per_day_per_school',
            ),
        ]

    def __str__(self):
        day_name = dict(self.DAY_CHOICES).get(self.day_of_week, str(self.day_of_week))
        if not self.is_working_day:
            return f"{self.school.subdomain} — {day_name}: Off"
        return (
            f"{self.school.subdomain} — {day_name}: "
            f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')} "
            f"({self.grace_period_minutes}m grace)"
        )


class HolidayException(TenantModel):
    """
    Date-specific holiday override for a school tenant.

    Scans occurring on holiday dates are recorded as PRESENT without late penalties.
    Unscanned days on holidays do not generate absent warnings.
    """
    date = models.DateField(
        help_text='Calendar date of holiday exception',
    )
    description = models.CharField(
        max_length=255,
        help_text='Holiday name / reason (e.g. Independence Day)',
    )
    is_recurring_yearly = models.BooleanField(
        default=False,
        help_text='Whether this holiday repeats every year on the same month and day',
    )

    class Meta:
        ordering = ['-date']
        verbose_name = 'Holiday Exception'
        verbose_name_plural = 'Holiday Exceptions'
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'date'],
                name='unique_holiday_per_date_per_school',
            ),
        ]

    def __str__(self):
        return f"{self.school.subdomain} — {self.description} ({self.date})"
