from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class User(AbstractUser):
    """
    Custom User model for the Faculty Attendance SaaS platform.

    Replaces Django's default User. Uses email as the primary login
    credential. Associates users with exactly one role:
      - SUPER_ADMIN: Platform administrator — no school tenant assigned.
      - SCHOOL_ADMIN: School-level administrator — must belong to a school.
      - FACULTY: Faculty member — must belong to a school.
      - STUDENT: Student — must belong to a school; logs in via GR number.

    Database-level CheckConstraints plus application-level clean() ensure
    the school FK is NULL for Super Admins and NOT NULL for tenant users.
    """

    class Role(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Platform Super Admin'
        SCHOOL_ADMIN = 'SCHOOL_ADMIN', 'School Administrator'
        FACULTY = 'FACULTY', 'School Faculty'
        STUDENT = 'STUDENT', 'Student'

    email = models.EmailField('Email Address', unique=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.FACULTY,
        db_index=True,
    )
    school = models.ForeignKey(
        'tenants.School',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users',
        help_text='School tenant association. Must be NULL for Super Admin; required for School Admin and Faculty.',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['email']
        constraints = [
            # Super Admin MUST NOT have a school tenant assigned
            models.CheckConstraint(
                check=(
                    models.Q(role='SUPER_ADMIN', school__isnull=True) |
                    ~models.Q(role='SUPER_ADMIN')
                ),
                name='super_admin_no_school',
            ),
            # School Admin, Faculty, and Students MUST have a school tenant assigned
            models.CheckConstraint(
                check=(
                    models.Q(role__in=['SCHOOL_ADMIN', 'FACULTY', 'STUDENT'], school__isnull=False) |
                    models.Q(role='SUPER_ADMIN')
                ),
                name='tenant_user_requires_school',
            ),
        ]

    def clean(self):
        """Application-level validation complementing DB CheckConstraints."""
        super().clean()
        if self.role == self.Role.SUPER_ADMIN and self.school_id is not None:
            raise ValidationError({
                'school': (
                    'Platform Super Admin must not be assigned to a school tenant. '
                    'Set school to blank/None for Super Admin accounts.'
                )
            })
        if self.role in (self.Role.SCHOOL_ADMIN, self.Role.FACULTY, self.Role.STUDENT) and self.school_id is None:
            raise ValidationError({
                'school': (
                    f'{self.get_role_display()} must be assigned to a school tenant. '
                    'Select a school for this user.'
                )
            })

    def __str__(self):
        return f'{self.email} ({self.get_role_display()})'

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN

    @property
    def is_school_admin(self):
        return self.role == self.Role.SCHOOL_ADMIN

    @property
    def is_faculty(self):
        return self.role == self.Role.FACULTY

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT
