"""
Faculty Management Models.

Contains:
  - TenantSequence: Tenant-scoped sequence counter with DB row locking
    for concurrency-safe employee code auto-generation.
  - Faculty: Tenant-scoped faculty member record with linked User account.
"""
from django.db import models

from apps.accounts.models import User
from apps.tenants.models import TenantModel


class TenantSequence(TenantModel):
    """
    Tenant-scoped sequence counter for concurrency-safe sequential code generation.

    Uses select_for_update() row-level locking inside @transaction.atomic
    to prevent race conditions during concurrent faculty creation requests.

    Each (school, sequence_type) pair maintains an independent monotonic counter.
    """
    sequence_type = models.CharField(
        max_length=50,
        default='FACULTY',
        help_text='Sequence category (e.g. FACULTY, DEPARTMENT)',
    )
    last_value = models.PositiveIntegerField(
        default=0,
        help_text='Last assigned sequence number',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'sequence_type'],
                name='unique_tenant_sequence_type',
            )
        ]
        verbose_name = 'Tenant Sequence'
        verbose_name_plural = 'Tenant Sequences'

    def __str__(self):
        return f"{self.school.subdomain}:{self.sequence_type} → {self.last_value}"


class Faculty(TenantModel):
    """
    Represents a faculty member (teacher/staff) within a school tenant.

    Architecture decisions (from 05-CONTEXT.md):
      - user FK uses SET_NULL to preserve historical attendance data if User is deleted.
      - email is globally unique (matches User.email for authentication consistency).
      - employee_code is unique per school tenant (DB constraint).
      - is_face_enrolled is a Phase 6 integration hook (no fake enrollment in Phase 5).
      - Faculty User accounts use set_unusable_password() — no web dashboard login.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        related_name='faculty_profile',
        null=True,
        blank=True,
        help_text='Linked User account (identity-only, no password login)',
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(
        unique=True,
        help_text='Globally unique email (matches User.email)',
    )
    phone_number = models.CharField(max_length=20, blank=True, default='')
    employee_code = models.CharField(
        max_length=50,
        db_index=True,
        help_text='Auto-generated or manual employee identifier',
    )
    department = models.CharField(
        max_length=100,
        help_text='Academic department (e.g. Science, Mathematics)',
    )
    designation = models.CharField(
        max_length=100,
        help_text='Job title (e.g. Senior Teacher, HOD)',
    )
    date_joined = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(
        default=True,
        help_text='Active employment status (deactivation preserves history)',
    )
    is_face_enrolled = models.BooleanField(
        default=False,
        help_text='Phase 6 architecture hook — face vector enrollment status',
    )

    class Meta:
        ordering = ['first_name', 'last_name']
        verbose_name = 'Faculty Member'
        verbose_name_plural = 'Faculty Members'
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'employee_code'],
                name='unique_faculty_code_per_school',
            ),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.employee_code})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
