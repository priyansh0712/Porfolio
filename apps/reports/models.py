"""
Reports & Audit Log Models.

Contains:
  - AttendanceCorrection: Immutable audit log tracking manual admin corrections
    to attendance records. Preserves original status, check-in, and check-out values
    alongside admin User ID, timestamp, and mandatory reason explanation.
"""
from django.db import models

from apps.accounts.models import User
from apps.attendance.models import AttendanceLog
from apps.tenants.models import TenantModel


class AttendanceCorrection(TenantModel):
    """
    Immutable audit log entry for a manual attendance record correction.

    Architecture (AUDIT-01):
      - Preserves original values before correction.
      - Requires a non-empty explanation reason string.
      - Links to the School Admin user who performed the correction.
      - Read-only once created — editing or deleting audit log records is prohibited.
    """
    attendance = models.ForeignKey(
        AttendanceLog,
        on_delete=models.CASCADE,
        related_name='corrections',
        help_text='Attendance record being corrected',
    )
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='performed_corrections',
        help_text='School Admin who authorized and saved this correction',
    )
    old_status = models.CharField(
        max_length=20,
        help_text='Original status before correction',
    )
    new_status = models.CharField(
        max_length=20,
        help_text='Updated status after correction',
    )
    old_check_in_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Original check-in timestamp',
    )
    new_check_in_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Updated check-in timestamp',
    )
    old_check_out_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Original check-out timestamp',
    )
    new_check_out_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Updated check-out timestamp',
    )
    reason = models.CharField(
        max_length=255,
        help_text='Mandatory business reason / explanation for audit trail',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Attendance Correction Audit Log'
        verbose_name_plural = 'Attendance Correction Audit Logs'

    def __str__(self):
        admin_email = self.performed_by.email if self.performed_by else 'system'
        return (
            f"Correction({self.attendance.faculty.full_name}, {self.attendance.date}): "
            f"{self.old_status} → {self.new_status} by {admin_email}"
        )
