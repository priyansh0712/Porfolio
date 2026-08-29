"""
Academic Management Models.

Defines:
  - AcademicYear: Multi-tenant academic session with atomic is_current toggle.
  - Standard: Grade level master records (1-12, Nursery, UKG) with natural order index.
  - Division: Section master records (A, B, C) linked to a Standard.
  - Subject: Subject master records (Core vs Elective) with unique uppercase code.
  - ClassTeacherAllocation: 1-to-1 mapping of Division to Class Teacher per Academic Year.
  - SubjectTeacherAllocation: 1-to-1 mapping of Division + Subject to Subject Teacher per Academic Year.
"""
from django.db import models, transaction
from django.core.exceptions import ValidationError

from apps.tenants.models import TenantModel


class AcademicYear(TenantModel):
    """
    Represents an academic session / school year within a tenant school.

    Rules:
      - Only one AcademicYear can be active (is_current=True) per school tenant.
      - Setting is_current=True atomically deactivates all other academic years for the tenant.
      - start_date must be strictly before end_date.
    """
    name = models.CharField(
        max_length=50,
        help_text='Display name of the academic year (e.g. 2026-2027, 2026-27)',
    )
    start_date = models.DateField(
        help_text='Session start date',
    )
    end_date = models.DateField(
        help_text='Session end date',
    )
    is_current = models.BooleanField(
        default=False,
        help_text='Flag indicating the active academic year for attendance and class operations',
    )

    class Meta:
        ordering = ['-start_date', 'name']
        verbose_name = 'Academic Year'
        verbose_name_plural = 'Academic Years'
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'name'],
                name='unique_academic_year_name_per_school',
            ),
        ]

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError({
                'end_date': 'End date must be strictly after start date.'
            })

    @transaction.atomic
    def save(self, *args, **kwargs):
        self.clean()
        if self.is_current and self.school_id:
            # Atomically unset is_current for any other academic year of this school
            AcademicYear.objects.filter(
                school=self.school,
                is_current=True,
            ).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    def __str__(self):
        status = ' (Current)' if self.is_current else ''
        return f"{self.name}{status}"


class Standard(TenantModel):
    """
    Represents a grade/standard master record (e.g., Standard 1 to 12, UKG, LKG).

    Uses order_index for natural educational sorting (e.g. Nursery=0, LKG=1, Std 1=3, Std 10=12).
    """
    name = models.CharField(
        max_length=50,
        help_text='Grade / Standard name (e.g. Standard 10, Grade 1, UKG)',
    )
    order_index = models.PositiveIntegerField(
        default=0,
        help_text='Numerical index for sequential sorting and promotion order',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this standard is active for current academic operations',
    )

    class Meta:
        ordering = ['order_index', 'name']
        verbose_name = 'Standard'
        verbose_name_plural = 'Standards'
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'name'],
                name='unique_standard_name_per_school',
            ),
        ]

    def __str__(self):
        return self.name


class Division(TenantModel):
    """
    Represents a class division/section (e.g. A, B, C, Rose) linked to a Standard.
    """
    standard = models.ForeignKey(
        Standard,
        on_delete=models.PROTECT,
        related_name='divisions',
        help_text='Standard / Grade this division belongs to',
    )
    name = models.CharField(
        max_length=20,
        help_text='Division section code/name (e.g. A, B, C, Rose, Lotus)',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this division is currently active',
    )

    class Meta:
        ordering = ['standard__order_index', 'name']
        verbose_name = 'Division'
        verbose_name_plural = 'Divisions'
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'standard', 'name'],
                name='unique_division_per_standard_per_school',
            ),
        ]

    def __str__(self):
        return f"{self.standard.name} - {self.name}"


class Subject(TenantModel):
    """
    Represents a school subject (e.g. Mathematics, Science, English, Gujarati).
    """
    class SubjectType(models.TextChoices):
        CORE = 'CORE', 'Core Subject'
        ELECTIVE = 'ELECTIVE', 'Elective / Optional'

    name = models.CharField(
        max_length=100,
        help_text='Subject title (e.g. Mathematics, Science, Social Studies)',
    )
    code = models.CharField(
        max_length=30,
        blank=True,
        default='',
        help_text='Optional unique subject identifier code (e.g. MATH-01, SCI-10)',
    )
    subject_type = models.CharField(
        max_length=20,
        choices=SubjectType.choices,
        default=SubjectType.CORE,
        help_text='Categorization of subject',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this subject is currently taught',
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Subject'
        verbose_name_plural = 'Subjects'
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'code'],
                condition=~models.Q(code=''),
                name='unique_subject_code_per_school',
            ),
        ]

    def clean(self):
        super().clean()
        if self.code:
            self.code = self.code.strip().upper()
        else:
            self.code = ''

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.code:
            return f"{self.name} ({self.code})"
        return self.name


class ClassCurriculum(TenantModel):
    """
    Represents the assignment of a Subject from the Global Subject Master
    to a specific Standard / Grade level for a specific Academic Year.

    Rules:
      - A Subject can be assigned to multiple Standards across multiple Academic Years.
      - A Standard has an explicit set of subjects taught in a specific Academic Year.
      - Enforces uniqueness on (school, academic_year, standard, subject).
      - Multi-tenant isolated via TenantModel.
    """
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name='curriculum_subjects',
        help_text='Academic session for this curriculum assignment',
    )
    standard = models.ForeignKey(
        Standard,
        on_delete=models.CASCADE,
        related_name='curriculum_subjects',
        help_text='Grade / Standard to which the subject is assigned',
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name='class_curriculums',
        help_text='Subject from Global Subject Master',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this subject is currently active in this grade curriculum',
    )

    class Meta:
        ordering = ['standard__order_index', 'subject__name']
        verbose_name = 'Class Curriculum'
        verbose_name_plural = 'Class Curriculums'
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'academic_year', 'standard', 'subject'],
                name='unique_curriculum_per_standard_year',
            ),
        ]

    def clean(self):
        super().clean()
        if self.academic_year_id and self.school_id:
            if self.academic_year.school_id != self.school_id:
                raise ValidationError({
                    'academic_year': 'Academic Year must belong to the same school tenant.'
                })
        if self.standard_id and self.school_id:
            if self.standard.school_id != self.school_id:
                raise ValidationError({
                    'standard': 'Standard must belong to the same school tenant.'
                })
        if self.subject_id and self.school_id:
            if self.subject.school_id != self.school_id:
                raise ValidationError({
                    'subject': 'Subject must belong to the same school tenant.'
                })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.academic_year.name}: {self.standard.name} → {self.subject.name} ({self.subject.code})"


class ClassTeacherAllocation(TenantModel):
    """
    Represents the 1-to-1 allocation of a Faculty member as Class Teacher
    for a specific Division in a specific Academic Year.

    Enforces strictly 1 Class Teacher per division per academic year per tenant school.
    """
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name='class_teacher_allocations',
        help_text='Academic year for this class assignment',
    )
    division = models.ForeignKey(
        Division,
        on_delete=models.PROTECT,
        related_name='class_teacher_allocations',
        help_text='Assigned class division',
    )
    faculty = models.ForeignKey(
        'faculty.Faculty',
        on_delete=models.PROTECT,
        related_name='class_teacher_allocations',
        help_text='Assigned Class Teacher',
    )

    class Meta:
        verbose_name = 'Class Teacher Allocation'
        verbose_name_plural = 'Class Teacher Allocations'
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'academic_year', 'division'],
                name='unique_class_teacher_per_division_year',
            ),
        ]

    def clean(self):
        super().clean()
        if self.faculty_id and self.school_id:
            if self.faculty.school_id != self.school_id:
                raise ValidationError({
                    'faculty': 'Faculty member must belong to the same school tenant.'
                })
            if not self.faculty.is_active:
                raise ValidationError({
                    'faculty': 'Cannot assign an inactive faculty member as Class Teacher.'
                })
        if self.division_id and self.school_id:
            if self.division.school_id != self.school_id:
                raise ValidationError({
                    'division': 'Division must belong to the same school tenant.'
                })
        if self.academic_year_id and self.school_id:
            if self.academic_year.school_id != self.school_id:
                raise ValidationError({
                    'academic_year': 'Academic year must belong to the same school tenant.'
                })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.academic_year.name}: {self.division} → {self.faculty.full_name}"


class SubjectTeacherAllocation(TenantModel):
    """
    Represents the allocation of a Faculty member to teach a specific Subject
    in a specific Division during an Academic Year.

    Enforces strictly 1 primary Subject Teacher per Division + Subject per Academic Year.
    """
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name='subject_teacher_allocations',
        help_text='Academic year for this subject assignment',
    )
    division = models.ForeignKey(
        Division,
        on_delete=models.PROTECT,
        related_name='subject_teacher_allocations',
        help_text='Class division',
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name='subject_teacher_allocations',
        help_text='Subject taught',
    )
    faculty = models.ForeignKey(
        'faculty.Faculty',
        on_delete=models.PROTECT,
        related_name='subject_teacher_allocations',
        help_text='Assigned Subject Teacher',
    )

    class Meta:
        verbose_name = 'Subject Teacher Allocation'
        verbose_name_plural = 'Subject Teacher Allocations'
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'academic_year', 'division', 'subject', 'faculty'],
                name='unique_subject_teacher_allocation',
            ),
        ]

    def clean(self):
        super().clean()
        if self.faculty_id and self.school_id:
            if self.faculty.school_id != self.school_id:
                raise ValidationError({
                    'faculty': 'Faculty member must belong to the same school tenant.'
                })
            if not self.faculty.is_active:
                raise ValidationError({
                    'faculty': 'Cannot assign an inactive faculty member as Subject Teacher.'
                })
        if self.division_id and self.school_id:
            if self.division.school_id != self.school_id:
                raise ValidationError({
                    'division': 'Division must belong to the same school tenant.'
                })
        if self.subject_id and self.school_id:
            if self.subject.school_id != self.school_id:
                raise ValidationError({
                    'subject': 'Subject must belong to the same school tenant.'
                })
        if self.academic_year_id and self.school_id:
            if self.academic_year.school_id != self.school_id:
                raise ValidationError({
                    'academic_year': 'Academic year must belong to the same school tenant.'
                })
        if self.division_id and self.subject_id and self.academic_year_id and self.school_id:
            # If curriculum is configured for this standard and year, enforce subject membership
            has_curriculum = ClassCurriculum.objects.filter(
                school=self.school,
                academic_year=self.academic_year,
                standard=self.division.standard,
            ).exists()
            if has_curriculum and not ClassCurriculum.objects.filter(
                school=self.school,
                academic_year=self.academic_year,
                standard=self.division.standard,
                subject=self.subject,
                is_active=True,
            ).exists():
                raise ValidationError({
                    'subject': f"'{self.subject.name}' is not in the curriculum for {self.division.standard.name} in {self.academic_year.name}."
                })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.academic_year.name}: {self.division} [{self.subject.name}] → {self.faculty.full_name}"


class ClassTimetable(TenantModel):
    """
    Represents weekly period timetable slot for a specific Division.
    """

    class DayOfWeek(models.IntegerChoices):
        MONDAY = 1, 'Monday'
        TUESDAY = 2, 'Tuesday'
        WEDNESDAY = 3, 'Wednesday'
        THURSDAY = 4, 'Thursday'
        FRIDAY = 5, 'Friday'
        SATURDAY = 6, 'Saturday'

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name='timetables',
        help_text='Academic session for this timetable',
    )
    division = models.ForeignKey(
        Division,
        on_delete=models.CASCADE,
        related_name='timetables',
        help_text='Class division schedule',
    )
    day_of_week = models.IntegerField(
        choices=DayOfWeek.choices,
        help_text='Day of the week (1=Mon, 6=Sat)',
    )
    period_number = models.PositiveIntegerField(
        help_text='Period number / sequence (e.g. 1, 2, 3...)',
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name='timetable_periods',
        help_text='Subject taught during this period',
    )
    faculty = models.ForeignKey(
        'faculty.Faculty',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='timetable_periods',
        help_text='Faculty assigned to teach this period',
    )
    start_time = models.TimeField(
        null=True,
        blank=True,
        help_text='Period start time',
    )
    end_time = models.TimeField(
        null=True,
        blank=True,
        help_text='Period end time',
    )

    class Meta:
        ordering = ['day_of_week', 'period_number']
        verbose_name = 'Class Timetable Slot'
        verbose_name_plural = 'Class Timetable Slots'
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'academic_year', 'division', 'day_of_week', 'period_number'],
                name='unique_period_per_division_day_year',
            ),
        ]

    def __str__(self):
        return f"{self.division} | {self.get_day_of_week_display()} P{self.period_number}: {self.subject.name}"

