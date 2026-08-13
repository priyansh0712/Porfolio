"""
Schedule Service Layer — Default Schedule Initializer.

Seeds 7 day-of-week WorkingSchedule records for a new school tenant.
"""
import logging
from datetime import time

from django.db import transaction

from apps.schedules.models import WorkingSchedule

logger = logging.getLogger(__name__)


class ScheduleService:
    """Service for initializing and managing school tenant working schedules."""

    DEFAULT_CONFIG = [
        {'day_of_week': 0, 'is_working_day': True, 'start_time': time(8, 0), 'end_time': time(16, 0), 'grace_period_minutes': 15},
        {'day_of_week': 1, 'is_working_day': True, 'start_time': time(8, 0), 'end_time': time(16, 0), 'grace_period_minutes': 15},
        {'day_of_week': 2, 'is_working_day': True, 'start_time': time(8, 0), 'end_time': time(16, 0), 'grace_period_minutes': 15},
        {'day_of_week': 3, 'is_working_day': True, 'start_time': time(8, 0), 'end_time': time(16, 0), 'grace_period_minutes': 15},
        {'day_of_week': 4, 'is_working_day': True, 'start_time': time(8, 0), 'end_time': time(16, 0), 'grace_period_minutes': 15},
        {'day_of_week': 5, 'is_working_day': True, 'start_time': time(8, 0), 'end_time': time(12, 0), 'grace_period_minutes': 15},
        {'day_of_week': 6, 'is_working_day': False, 'start_time': time(8, 0), 'end_time': time(16, 0), 'grace_period_minutes': 15},
    ]

    @classmethod
    @transaction.atomic
    def initialize_default_schedules(cls, school):
        """
        Ensures all 7 day-of-week WorkingSchedule records exist for the given school.

        Creates missing records with default 08:00-16:00 shift & 15m grace period.

        Args:
            school: The School tenant instance.

        Returns:
            list: List of 7 WorkingSchedule instances (0=Monday .. 6=Sunday).
        """
        schedules = []
        for config in cls.DEFAULT_CONFIG:
            schedule, created = WorkingSchedule.objects.get_or_create(
                school=school,
                day_of_week=config['day_of_week'],
                defaults={
                    'is_working_day': config['is_working_day'],
                    'start_time': config['start_time'],
                    'end_time': config['end_time'],
                    'grace_period_minutes': config['grace_period_minutes'],
                },
            )
            schedules.append(schedule)
            if created:
                logger.info(
                    "Created default WorkingSchedule for %s (Day %d)",
                    school.subdomain, config['day_of_week'],
                )
        return schedules
