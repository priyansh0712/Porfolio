"""
Schedules Unit Tests — Working Schedule, PunctualityCalculator, and Admin Settings.

Test Coverage:
  - ScheduleService: Default 7 day-of-week schedule auto-initialization.
  - PunctualityCalculator:
      - On-time check-in → PRESENT
      - Check-in past grace period → LATE
      - Check-in after 11:00 AM or <4h duration → HALF_DAY
      - Early departure before end_time - grace → early_departure = True
      - Holiday date check-in → PRESENT (no penalty)
      - Non-working day check-in → PRESENT
  - ScheduleSettingsView: Access control, GET context, POST updates & holiday CRUD.
"""
from datetime import date, datetime, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.attendance.models import AttendanceLog
from apps.schedules.calculator import PunctualityCalculator
from apps.schedules.models import WorkingSchedule, HolidayException
from apps.schedules.services import ScheduleService
from apps.tenants.models import School


class SchedulesTestBase(TestCase):
    """Base setup for schedules unit tests."""

    def setUp(self):
        self.school = School.objects.create(
            name='Greenwood Academy',
            subdomain='greenwood-acad',
            contact_email='admin@greenwood-acad.edu',
        )
        self.admin_user = User.objects.create_user(
            username='greenwood_admin',
            email='admin@greenwood-acad.edu',
            password='TestPassword123!',
            first_name='Greenwood',
            last_name='Admin',
            role=User.Role.SCHOOL_ADMIN,
            school=self.school,
        )
        # Initialize default 7 schedules
        self.schedules = ScheduleService.initialize_default_schedules(self.school)


class ScheduleServiceTest(SchedulesTestBase):
    """Tests for ScheduleService default schedule initialization."""

    def test_initialize_default_schedules_creates_7_days(self):
        """Should create exactly 7 WorkingSchedule records (0=Mon..6=Sun)."""
        count = WorkingSchedule.objects.filter(school=self.school).count()
        self.assertEqual(count, 7)

        # Mon-Fri should be working days
        for day_num in range(5):
            sched = WorkingSchedule.objects.get(school=self.school, day_of_week=day_num)
            self.assertTrue(sched.is_working_day)
            self.assertEqual(sched.start_time, time(8, 0))
            self.assertEqual(sched.end_time, time(16, 0))
            self.assertEqual(sched.grace_period_minutes, 15)

        # Sunday (6) should be non-working
        sun_sched = WorkingSchedule.objects.get(school=self.school, day_of_week=6)
        self.assertFalse(sun_sched.is_working_day)

    def test_idempotent_initialization(self):
        """Calling initialize_default_schedules multiple times should not create duplicates."""
        ScheduleService.initialize_default_schedules(self.school)
        count = WorkingSchedule.objects.filter(school=self.school).count()
        self.assertEqual(count, 7)


class PunctualityCalculatorTest(SchedulesTestBase):
    """Tests for the PunctualityCalculator business rules engine."""

    def setUp(self):
        super().setUp()
        # Monday date for testing (2026-08-10 is a Monday)
        self.monday_date = date(2026, 8, 10)

    def test_on_time_check_in_returns_present(self):
        """Check-in at 08:05 AM (start=08:00, grace=15m) should return PRESENT."""
        check_in = timezone.make_aware(datetime.combine(self.monday_date, time(8, 5)))
        calc = PunctualityCalculator.calculate_status(
            school=self.school, date=self.monday_date, check_in_time=check_in,
        )
        self.assertEqual(calc['status'], AttendanceLog.Status.PRESENT)
        self.assertFalse(calc['early_departure'])

    def test_late_check_in_past_grace_period_returns_late(self):
        """Check-in at 08:20 AM (start=08:00, grace=15m) should return LATE."""
        check_in = timezone.make_aware(datetime.combine(self.monday_date, time(8, 20)))
        calc = PunctualityCalculator.calculate_status(
            school=self.school, date=self.monday_date, check_in_time=check_in,
        )
        self.assertEqual(calc['status'], AttendanceLog.Status.LATE)

    def test_late_check_in_after_11am_returns_half_day(self):
        """Check-in at 11:30 AM should return HALF_DAY."""
        check_in = timezone.make_aware(datetime.combine(self.monday_date, time(11, 30)))
        calc = PunctualityCalculator.calculate_status(
            school=self.school, date=self.monday_date, check_in_time=check_in,
        )
        self.assertEqual(calc['status'], AttendanceLog.Status.HALF_DAY)

    def test_short_duration_on_checkout_returns_half_day(self):
        """Working for < 4 hours total should return HALF_DAY on check-out."""
        check_in = timezone.make_aware(datetime.combine(self.monday_date, time(8, 0)))
        check_out = timezone.make_aware(datetime.combine(self.monday_date, time(11, 30))) # 3.5h
        calc = PunctualityCalculator.calculate_status(
            school=self.school, date=self.monday_date,
            check_in_time=check_in, check_out_time=check_out,
        )
        self.assertEqual(calc['status'], AttendanceLog.Status.HALF_DAY)

    def test_early_departure_flag(self):
        """Check-out at 15:00 (end=16:00, grace=15m) should set early_departure = True and status = EARLY_DEPARTURE."""
        check_in = timezone.make_aware(datetime.combine(self.monday_date, time(8, 0)))
        check_out = timezone.make_aware(datetime.combine(self.monday_date, time(15, 0)))
        calc = PunctualityCalculator.calculate_status(
            school=self.school, date=self.monday_date,
            check_in_time=check_in, check_out_time=check_out,
        )
        self.assertTrue(calc['early_departure'])
        self.assertEqual(calc['status'], AttendanceLog.Status.EARLY_DEPARTURE)

    def test_holiday_exception_returns_present(self):
        """Check-in on a registered holiday date should return PRESENT without penalties."""
        HolidayException.objects.create(
            school=self.school,
            date=self.monday_date,
            description='Independence Day',
        )
        check_in = timezone.make_aware(datetime.combine(self.monday_date, time(10, 0)))
        calc = PunctualityCalculator.calculate_status(
            school=self.school, date=self.monday_date, check_in_time=check_in,
        )
        self.assertEqual(calc['status'], AttendanceLog.Status.PRESENT)
        self.assertIn('Holiday', calc['reason'])

    def test_non_working_day_returns_present(self):
        """Check-in on Sunday (2026-08-16) should return PRESENT."""
        sunday_date = date(2026, 8, 16)
        check_in = timezone.make_aware(datetime.combine(sunday_date, time(9, 0)))
        calc = PunctualityCalculator.calculate_status(
            school=self.school, date=sunday_date, check_in_time=check_in,
        )
        self.assertEqual(calc['status'], AttendanceLog.Status.PRESENT)


class ScheduleSettingsViewTest(SchedulesTestBase):
    """Tests for ScheduleSettingsView admin UI."""

    def test_unauthenticated_redirects(self):
        """Unauthenticated user should be redirected to login."""
        response = self.client.get(reverse('schedules:settings'))
        self.assertEqual(response.status_code, 302)

    def test_admin_get_renders_settings_page(self):
        """School Admin should see the schedule settings dashboard."""
        self.client.force_login(self.admin_user)
        # Mock request.tenant
        session = self.client.session
        session.save()

        # Add tenant context via HTTP host header
        response = self.client.get(
            reverse('schedules:settings'),
            HTTP_HOST='greenwood-acad.localhost:8000',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'schedules/schedule_settings.html')
        self.assertEqual(len(response.context['schedules']), 7)

    def test_update_schedule_post(self):
        """POST updating Monday working hours should save to database."""
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse('schedules:settings'),
            {
                'action': 'update_schedule',
                'day_of_week': '0',
                'is_working_day': 'on',
                'start_time': '07:30',
                'end_time': '15:30',
                'grace_period_minutes': '20',
            },
            HTTP_HOST='greenwood-acad.localhost:8000',
        )
        self.assertRedirects(response, reverse('schedules:settings'))
        mon_sched = WorkingSchedule.objects.get(school=self.school, day_of_week=0)
        self.assertEqual(mon_sched.start_time, time(7, 30))
        self.assertEqual(mon_sched.grace_period_minutes, 20)

    def test_add_and_delete_holiday_post(self):
        """POST adding and deleting a holiday exception should update database."""
        self.client.force_login(self.admin_user)

        # ── Add Holiday ──
        response = self.client.post(
            reverse('schedules:settings'),
            {
                'action': 'add_holiday',
                'date': '2026-12-25',
                'description': 'Christmas Day',
                'is_recurring_yearly': 'on',
            },
            HTTP_HOST='greenwood-acad.localhost:8000',
        )
        self.assertRedirects(response, reverse('schedules:settings'))
        holiday = HolidayException.objects.get(school=self.school, date=date(2026, 12, 25))
        self.assertEqual(holiday.description, 'Christmas Day')
        self.assertTrue(holiday.is_recurring_yearly)

        # ── Delete Holiday ──
        response = self.client.post(
            reverse('schedules:settings'),
            {
                'action': 'delete_holiday',
                'holiday_id': str(holiday.id),
            },
            HTTP_HOST='greenwood-acad.localhost:8000',
        )
        self.assertRedirects(response, reverse('schedules:settings'))
        self.assertFalse(HolidayException.objects.filter(id=holiday.id).exists())
