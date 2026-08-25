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
        blank=True,
        default='',
        help_text='Job title (e.g. Senior Teacher, HOD) — optional',
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

    custom_fields = models.JSONField(
        'Custom Fields',
        default=dict,
        blank=True,
        help_text='Dynamic custom field values stored as JSON dict',
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

    @property
    def initials(self):
        """Return up to 2-letter uppercase initials for avatar display."""
        f = (self.first_name or '').strip()
        l = (self.last_name or '').strip()
        if f and l:
            return f"{f[0]}{l[0]}".upper()
        if f:
            return f[:2].upper()
        return "FA"

    @property
    def current_class_teacher_division(self):
        """Return current assigned Class Teacher division name if active."""
        alloc = self.class_teacher_allocations.filter(academic_year__is_current=True).select_related('division__standard').first()
        if alloc:
            return f"{alloc.division.standard.name} — {alloc.division.name}"
        return None

    @property
    def current_taught_subjects(self):
        """Return list of subjects taught in current academic year."""
        allocs = self.subject_teacher_allocations.filter(academic_year__is_current=True).select_related('subject', 'division__standard')
        return [f"{a.subject.name} ({a.division.standard.name}-{a.division.name})" for a in allocs]


class FacultyCustomField(models.Model):
    """
    Custom field definition dynamically configured by School Admin for Faculty records.
    (e.g. Qualification, Aadhar Number, Experience, etc.)
    """
    class FieldType(models.TextChoices):
        TEXT = 'TEXT', 'Text'
        NUMBER = 'NUMBER', 'Number'
        DATE = 'DATE', 'Date'
        SELECT = 'SELECT', 'Dropdown Select'

    school = models.ForeignKey(
        'tenants.School',
        on_delete=models.CASCADE,
        related_name='faculty_custom_fields',
    )
    label = models.CharField('Field Label', max_length=100)
    field_name = models.SlugField('Field Key', max_length=100)
    field_type = models.CharField('Field Type', max_length=10, choices=FieldType.choices, default=FieldType.TEXT)
    options = models.CharField('Dropdown Options', max_length=500, blank=True, help_text='Comma-separated options for Dropdown Select type')
    is_required = models.BooleanField('Required', default=False)
    is_active = models.BooleanField('Active', default=True)
    order_index = models.PositiveIntegerField('Order', default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Faculty Custom Field'
        verbose_name_plural = 'Faculty Custom Fields'
        ordering = ['order_index', 'created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'field_name'],
                name='unique_school_faculty_custom_field',
            ),
        ]

    def __str__(self):
        return f"{self.school.name} - {self.label} ({self.field_type})"


class FacultyFormFieldConfig(models.Model):
    """
    Per-school configuration for which standard faculty fields are enabled/visible
    and whether they are required on faculty forms.
    """
    school = models.OneToOneField(
        'tenants.School',
        on_delete=models.CASCADE,
        related_name='faculty_form_config',
    )

    # Field Visibility Toggles (True = shown on form, False = hidden)
    show_phone_number = models.BooleanField('Show Phone Number', default=True)
    show_employee_code = models.BooleanField('Show Employee Code', default=True)
    show_department = models.BooleanField('Show Department', default=True)
    show_designation = models.BooleanField('Show Designation', default=True)

    # Field Required Toggles (True = mandatory, False = optional)
    require_phone_number = models.BooleanField('Require Phone Number', default=False)
    require_employee_code = models.BooleanField('Require Employee Code', default=False)
    require_department = models.BooleanField('Require Department', default=True)
    require_designation = models.BooleanField('Require Designation', default=False)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Faculty Form Field Configuration'
        verbose_name_plural = 'Faculty Form Field Configurations'

    def __str__(self):
        return f'Faculty Form Config — {self.school.name}'

    @classmethod
    def get_for_school(cls, school):
        """Retrieve or create default form field configuration for a school."""
        config, _ = cls.objects.get_or_create(school=school)
        return config
