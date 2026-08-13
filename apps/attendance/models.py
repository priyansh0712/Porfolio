"""
Attendance Models — Tenant-Scoped Check-In / Check-Out Log.

Contains:
  - AttendanceLog: Records daily faculty attendance with check-in/check-out
    timestamps. Uses unique_together (school, faculty, date) to enforce
    one record per faculty member per calendar day per tenant.

State Machine:
  1st scan of day → Creates record with check_in_time.
  2nd scan of day → Updates check_out_time.
  Subsequent scans → Updates check_out_time to latest timestamp.
"""
from django.db import models
from django.utils import timezone

from apps.faculty.models import Faculty
from apps.tenants.models import TenantModel


class AttendanceLog(TenantModel):
    """
    Daily attendance record for a faculty member within a school tenant.

    Architecture:
      - One record per (school, faculty, date) enforced by DB constraint.
      - check_in_time: Set on first valid face scan of the day.
      - check_out_time: Set on second valid scan; updated on subsequent scans.
      - last_scan_at: DateTime of the most recent scan attempt (for cooldown lock).
      - status: Calculated by Phase 8 Working Schedule rules (defaults to PRESENT).
      - match_confidence: Cosine similarity score from the identification engine.

    Fields follow timezone-aware datetime handling for multi-region support.
    """

    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        LATE = 'LATE', 'Late'
        HALF_DAY = 'HALF_DAY', 'Half Day'
        EARLY_DEPARTURE = 'EARLY_DEPARTURE', 'Early Departure'

    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.CASCADE,
        related_name='attendance_logs',
        help_text='Faculty member this attendance record belongs to',
    )
    date = models.DateField(
        help_text='Calendar date of attendance (timezone.localdate)',
    )
    check_in_time = models.DateTimeField(
        help_text='Timestamp of first face scan (check-in)',
    )
    check_out_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp of last face scan (check-out)',
    )
    last_scan_at = models.DateTimeField(
        help_text='Timestamp of the most recent scan attempt (for cooldown lock)',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PRESENT,
        help_text='Attendance status (calculated by schedule rules in Phase 8)',
    )
    early_departure = models.BooleanField(
        default=False,
        help_text='Whether check-out occurred before scheduled end_time minus grace period',
    )
    match_confidence = models.FloatField(
        default=0.0,
        help_text='Cosine similarity score from face identification (0.0 to 1.0)',
    )
    device_info = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Browser/device User-Agent string for audit trail',
    )

    class Meta:
        ordering = ['-date', '-check_in_time']
        verbose_name = 'Attendance Log'
        verbose_name_plural = 'Attendance Logs'
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'faculty', 'date'],
                name='unique_attendance_per_faculty_per_day',
            ),
        ]

    def __str__(self):
        status_label = self.get_status_display()
        return (
            f"{self.faculty.full_name} — {self.date} — "
            f"{status_label} (in: {self.check_in_time:%H:%M})"
        )

    @property
    def has_checked_out(self):
        """Whether this attendance record has a check-out timestamp."""
        return self.check_out_time is not None

    @property
    def duration(self):
        """Duration between check-in and check-out, or None if not checked out."""
        if self.check_out_time and self.check_in_time:
            return self.check_out_time - self.check_in_time
        return None
