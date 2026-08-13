"""
Punctuality Calculator Engine.

Evaluates check-in/check-out timestamps against school tenant working schedules
and holiday exceptions to calculate attendance status (PRESENT, LATE, HALF_DAY)
and early departure flags.
"""
import logging
from datetime import datetime, time, timedelta

from apps.attendance.models import AttendanceLog
from apps.schedules.models import WorkingSchedule, HolidayException

logger = logging.getLogger(__name__)


class PunctualityCalculator:
    """
    Business rules engine for calculating faculty attendance punctuality.
    """

    @classmethod
    def calculate_status(cls, school, date, check_in_time, check_out_time=None):
        """
        Calculates status and early departure flag for an attendance event.

        Args:
            school: The School tenant instance.
            date: DateField (calendar date of attendance).
            check_in_time: DateTimeField (check-in timestamp).
            check_out_time: Optional DateTimeField (check-out timestamp).

        Returns:
            dict: {
                'status': AttendanceLog.Status choice,
                'early_departure': bool,
                'reason': str,
            }
        """
        # ── 1. Holiday Exception Check ──
        holiday = HolidayException.objects.filter(school=school, date=date).first()
        if not holiday:
            # Check yearly recurring holiday
            holiday = HolidayException.objects.filter(
                school=school,
                date__month=date.month,
                date__day=date.day,
                is_recurring_yearly=True,
            ).first()

        if holiday:
            logger.info("Date %s is a holiday (%s) for %s", date, holiday.description, school.subdomain)
            return {
                'status': AttendanceLog.Status.PRESENT,
                'early_departure': False,
                'reason': f"Holiday: {holiday.description}",
            }

        # ── 2. Working Schedule Lookup ──
        weekday = date.weekday()  # 0=Mon .. 6=Sun
        schedule = WorkingSchedule.objects.filter(school=school, day_of_week=weekday).first()

        if not schedule or not schedule.is_working_day:
            return {
                'status': AttendanceLog.Status.PRESENT,
                'early_departure': False,
                'reason': "Non-working day",
            }

        from django.utils import timezone
        if timezone_is_aware(check_in_time):
            check_in_time = timezone.localtime(check_in_time)
        if check_out_time and timezone_is_aware(check_out_time):
            check_out_time = timezone.localtime(check_out_time)

        # ── 3. Grace Period & Late Check ──
        start_time = schedule.start_time
        grace = timedelta(minutes=schedule.grace_period_minutes)

        # Combine date and start_time into datetime in local timezone
        start_dt = datetime.combine(date, start_time)
        if timezone_is_aware(check_in_time):
            start_dt = timezone.make_aware(start_dt, check_in_time.tzinfo)

        late_cutoff = start_dt + grace

        if check_in_time > late_cutoff:
            status = AttendanceLog.Status.LATE
            reason = f"Late check-in (after {late_cutoff.strftime('%H:%M')})"
        else:
            status = AttendanceLog.Status.PRESENT
            reason = "On-time check-in"

        # ── 4. Half-Day Check (Shift-relative) ──
        end_time = schedule.end_time
        end_dt = datetime.combine(date, end_time)
        if timezone_is_aware(check_in_time):
            end_dt = timezone.make_aware(end_dt, check_in_time.tzinfo)

        shift_duration_seconds = max(0, (end_dt - start_dt).total_seconds())
        shift_duration_hours = shift_duration_seconds / 3600.0 if shift_duration_seconds > 0 else 8.0

        # Midpoint of scheduled shift (e.g. 12:00 PM for 8am-4pm, or 17:50 for 17:45-17:55)
        shift_midpoint = start_dt + timedelta(seconds=shift_duration_seconds / 2.0)

        # Arrival late cutoff for half-day: 3 hours late after start_time OR after shift midpoint
        half_day_late_cutoff = min(start_dt + timedelta(hours=3), shift_midpoint)

        # Arrival after half-day cutoff triggers Half-Day
        arrived_late_half_day = check_in_time > half_day_late_cutoff

        # Working duration less than half of scheduled shift duration triggers Half-Day
        short_duration = False
        if check_out_time and check_in_time:
            actual_duration = (check_out_time - check_in_time).total_seconds() / 3600.0
            # For 8h shift, threshold is 4h; for short test shifts, threshold is half shift
            half_shift_threshold = max(0.05, shift_duration_hours / 2.0)
            if actual_duration < half_shift_threshold:
                short_duration = True

        if arrived_late_half_day or short_duration:
            status = AttendanceLog.Status.HALF_DAY
            reason = "Half-day threshold met (late arrival or worked less than half shift)"

        # ── 5. Early Departure Check ──
        early_departure = False
        if check_out_time:
            end_time = schedule.end_time
            end_dt = datetime.combine(date, end_time)
            if timezone_is_aware(check_out_time):
                from django.utils import timezone
                end_dt = timezone.make_aware(end_dt, check_out_time.tzinfo)

            early_cutoff = end_dt - grace
            if check_out_time < early_cutoff:
                early_departure = True

        return {
            'status': status,
            'early_departure': early_departure,
            'reason': reason,
        }


def timezone_is_aware(value):
    return getattr(value, 'tzinfo', None) is not None and value.tzinfo.utcoffset(value) is not None
