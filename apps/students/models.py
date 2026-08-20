"""
Student data models for the Faculty Attendance SaaS platform.

Tenant-isolated student records with GR number uniqueness per school,
soft-delete support, and transfer request workflow between class divisions.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Student(models.Model):
    """
    Tenant-scoped student record with academic placement, guardian details,
    and a linked User account for portal login (GR Number + Admin@123).
    """

    class Gender(models.TextChoices):
        MALE = 'MALE', 'Male'
        FEMALE = 'FEMALE', 'Female'
        OTHER = 'OTHER', 'Other'

    class BloodGroup(models.TextChoices):
        A_POS = 'A+', 'A+'
        A_NEG = 'A-', 'A-'
        B_POS = 'B+', 'B+'
        B_NEG = 'B-', 'B-'
        O_POS = 'O+', 'O+'
        O_NEG = 'O-', 'O-'
        AB_POS = 'AB+', 'AB+'
        AB_NEG = 'AB-', 'AB-'
        UNKNOWN = '', 'Unknown / Not Set'

    # Tenant isolation
    school = models.ForeignKey(
        'tenants.School',
        on_delete=models.CASCADE,
        related_name='students',
    )

    # Linked portal user account (created automatically on student creation)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_profile',
    )

    # Identification
    gr_number = models.CharField(
        'GR Number',
        max_length=50,
        db_index=True,
        help_text='General Register number (unique per school). Cannot be changed by Class Teacher.',
    )
    roll_number = models.PositiveIntegerField(
        'Roll Number',
        null=True,
        blank=True,
        help_text='Class roll number (unique per active division in academic year).',
    )

    # Personal information
    full_name = models.CharField('Full Name', max_length=255)
    dob = models.DateField('Date of Birth', null=True, blank=True)
    gender = models.CharField('Gender', max_length=10, choices=Gender.choices, default=Gender.MALE)
    blood_group = models.CharField('Blood Group', max_length=5, choices=BloodGroup.choices, blank=True, default='')

    # Guardian / Parent details
    guardian_name = models.CharField('Guardian Name', max_length=255, blank=True, default='')
    guardian_phone = models.CharField('Guardian Phone', max_length=20, blank=True, default='')
    emergency_contact = models.CharField('Emergency Contact', max_length=20, blank=True, default='')
    address = models.TextField('Address', blank=True, default='')

    # Academic placement
    academic_year = models.ForeignKey(
        'academics.AcademicYear',
        on_delete=models.PROTECT,
        related_name='students',
    )
    standard = models.ForeignKey(
        'academics.Standard',
        on_delete=models.PROTECT,
        related_name='students',
    )
    division = models.ForeignKey(
        'academics.Division',
        on_delete=models.PROTECT,
        related_name='students',
    )
    admission_date = models.DateField('Admission Date', default=timezone.now)

    # Dynamic custom fields (configured by School Admin)
    custom_fields = models.JSONField('Custom Fields', default=dict, blank=True)

    # Soft delete
    is_active = models.BooleanField('Active', default=True, db_index=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Student'
        verbose_name_plural = 'Students'
        ordering = ['standard__order_index', 'division__name', 'roll_number', 'full_name']
        constraints = [
            # GR Number must be unique per school tenant
            models.UniqueConstraint(
                fields=['school', 'gr_number'],
                name='unique_school_student_gr_number',
            ),
            # Roll number must be unique per active student per division per academic year
            models.UniqueConstraint(
                fields=['school', 'academic_year', 'division', 'roll_number'],
                condition=models.Q(roll_number__isnull=False, is_active=True),
                name='unique_active_roll_per_division_year',
            ),
        ]

    def __str__(self):
        return f'{self.full_name} ({self.gr_number}) — {self.standard} {self.division}'

    @property
    def initials(self):
        """Return up to 2-letter initials for avatar display."""
        parts = self.full_name.strip().split()
        if len(parts) >= 2:
            return f'{parts[0][0]}{parts[-1][0]}'.upper()
        if parts:
            return parts[0][0].upper()
        return '?'

    @property
    def display_blood_group(self):
        return self.blood_group if self.blood_group else '—'

    @property
    def custom_fields_json(self):
        """Return JSON string representation of custom fields for template embedding."""
        import json
        return json.dumps(self.custom_fields or {})


class StudentTransferRequest(models.Model):
    """
    Transfer request initiated by a Class Teacher to move a student
    from their current division to another division.

    Approved by School Admin, which atomically updates student placement.
    """

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Approval'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    school = models.ForeignKey(
        'tenants.School',
        on_delete=models.CASCADE,
        related_name='student_transfer_requests',
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='transfer_requests',
    )
    from_division = models.ForeignKey(
        'academics.Division',
        on_delete=models.CASCADE,
        related_name='outgoing_transfers',
    )
    to_division = models.ForeignKey(
        'academics.Division',
        on_delete=models.CASCADE,
        related_name='incoming_transfers',
    )
    to_standard = models.ForeignKey(
        'academics.Standard',
        on_delete=models.CASCADE,
        related_name='incoming_transfer_requests',
    )
    requested_by = models.ForeignKey(
        'faculty.Faculty',
        on_delete=models.CASCADE,
        related_name='requested_transfers',
    )
    reason = models.TextField('Reason', blank=True, default='')
    status = models.CharField(
        'Status',
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_transfers',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField('Rejection Reason', blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Student Transfer Request'
        verbose_name_plural = 'Student Transfer Requests'
        ordering = ['-created_at']

    def __str__(self):
        return f'Transfer: {self.student.full_name} → {self.to_division} [{self.status}]'


class StudentCustomField(models.Model):
    """
    Custom field definition dynamically configured by School Admin / Principal.
    Allows schools to collect extra student data (e.g. Aadhar Number, Bus Route, etc.)
    """
    class FieldType(models.TextChoices):
        TEXT = 'TEXT', 'Text'
        NUMBER = 'NUMBER', 'Number'
        DATE = 'DATE', 'Date'
        SELECT = 'SELECT', 'Dropdown Select'

    school = models.ForeignKey(
        'tenants.School',
        on_delete=models.CASCADE,
        related_name='student_custom_fields',
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
        verbose_name = 'Student Custom Field'
        verbose_name_plural = 'Student Custom Fields'
        ordering = ['order_index', 'created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'field_name'],
                name='unique_school_student_custom_field',
            ),
        ]

    def __str__(self):
        return f'{self.label} ({self.field_type}) — {self.school.name}'

    def get_options_list(self):
        if self.field_type == self.FieldType.SELECT and self.options:
            return [opt.strip() for opt in self.options.split(',') if opt.strip()]
        return []


class StudentFormFieldConfig(models.Model):
    """
    Per-school configuration for which standard student fields are enabled/visible
    and whether they are required on student forms.
    """
    school = models.OneToOneField(
        'tenants.School',
        on_delete=models.CASCADE,
        related_name='student_form_config',
    )

    # Field Visibility Toggles (True = shown on form, False = hidden)
    show_roll_number = models.BooleanField('Show Roll Number', default=True)
    show_gender = models.BooleanField('Show Gender', default=True)
    show_dob = models.BooleanField('Show Date of Birth', default=True)
    show_blood_group = models.BooleanField('Show Blood Group', default=True)
    show_guardian_details = models.BooleanField('Show Guardian Details', default=True)
    show_emergency_contact = models.BooleanField('Show Emergency Contact', default=True)
    show_admission_date = models.BooleanField('Show Admission Date', default=True)
    show_address = models.BooleanField('Show Address', default=True)

    # Field Required Toggles (True = mandatory, False = optional)
    require_roll_number = models.BooleanField('Require Roll Number', default=False)
    require_gender = models.BooleanField('Require Gender', default=False)
    require_dob = models.BooleanField('Require Date of Birth', default=False)
    require_blood_group = models.BooleanField('Require Blood Group', default=False)
    require_guardian_details = models.BooleanField('Require Guardian Details', default=False)
    require_emergency_contact = models.BooleanField('Require Emergency Contact', default=False)
    require_admission_date = models.BooleanField('Require Admission Date', default=False)
    require_address = models.BooleanField('Require Address', default=False)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Student Form Field Configuration'
        verbose_name_plural = 'Student Form Field Configurations'

    def __str__(self):
        return f'Form Config — {self.school.name}'

    @classmethod
    def get_for_school(cls, school):
        """Retrieve or create default form field configuration for a school."""
        config, _ = cls.objects.get_or_create(school=school)
        return config


