"""
Faculty Services — business logic layer.

FacultyCodeService:  Race-condition-safe employee code generation
                     using PostgreSQL select_for_update() row locking.
FacultyService:      Faculty CRUD with linked User account management.
"""
from django.db import transaction, IntegrityError

from apps.accounts.models import User
from apps.faculty.models import Faculty, TenantSequence


class FacultyCodeService:
    """
    Generates unique, sequential employee codes per school tenant.

    Uses select_for_update() inside @transaction.atomic to
    guarantee no two concurrent requests get the same code,
    even under heavy parallel faculty creation.
    """

    @staticmethod
    @transaction.atomic
    def generate_next_code(school):
        """
        Returns next sequential code: '{SUBDOMAIN}-FAC-001'.
        Thread-safe via DB row-level locking.
        """
        seq, _created = (
            TenantSequence.objects
            .select_for_update()
            .get_or_create(
                school=school,
                sequence_type='FACULTY',
                defaults={'last_value': 0},
            )
        )
        seq.last_value += 1
        seq.save(update_fields=['last_value'])
        prefix = school.subdomain.upper()
        return f"{prefix}-FAC-{seq.last_value:03d}"


class FacultyService:
    """
    Faculty CRUD operations with automatic User account lifecycle.

    Architecture rules:
      - User accounts use set_unusable_password() — no dashboard login.
      - User.email = Faculty.email (globally unique).
      - User syncs first_name, last_name, email, is_active with Faculty.
    """

    @staticmethod
    @transaction.atomic
    def create_faculty(school, data):
        """
        Creates Faculty + linked User in a single atomic transaction.

        Args:
            school: School tenant instance
            data: dict with first_name, last_name, email, phone_number,
                  department, designation, and optional employee_code.

        Returns:
            Faculty instance
        """
        # Auto-generate employee code if not provided
        employee_code = data.get('employee_code', '').strip()
        if not employee_code:
            employee_code = FacultyCodeService.generate_next_code(school)

        email = data['email'].strip().lower()

        # Create identity-only User (no password login)
        user = User(
            username=email,
            email=email,
            first_name=data['first_name'].strip(),
            last_name=data['last_name'].strip(),
            role=User.Role.FACULTY,
            school=school,
        )
        user.set_unusable_password()
        user.save()

        # Create Faculty record
        faculty = Faculty.objects.create(
            school=school,
            user=user,
            first_name=data['first_name'].strip(),
            last_name=data['last_name'].strip(),
            email=email,
            phone_number=data.get('phone_number', '').strip(),
            employee_code=employee_code,
            department=data['department'].strip(),
            designation=data['designation'].strip(),
        )
        return faculty

    @staticmethod
    @transaction.atomic
    def update_faculty(faculty, data):
        """
        Updates Faculty fields and synchronizes linked User account.
        """
        faculty.first_name = data.get('first_name', faculty.first_name).strip()
        faculty.last_name = data.get('last_name', faculty.last_name).strip()
        faculty.phone_number = data.get('phone_number', faculty.phone_number).strip()
        faculty.department = data.get('department', faculty.department).strip()
        faculty.designation = data.get('designation', faculty.designation).strip()

        # Email change requires User sync
        new_email = data.get('email', '').strip().lower()
        if new_email and new_email != faculty.email:
            faculty.email = new_email

        faculty.save()

        # Synchronize linked User account
        if faculty.user:
            faculty.user.first_name = faculty.first_name
            faculty.user.last_name = faculty.last_name
            if new_email and new_email != faculty.user.email:
                faculty.user.email = new_email
                faculty.user.username = new_email
            faculty.user.save()

        return faculty

    @staticmethod
    @transaction.atomic
    def toggle_status(faculty):
        """
        Inverts is_active on Faculty and syncs to linked User.
        Returns updated Faculty.
        """
        faculty.is_active = not faculty.is_active
        faculty.save(update_fields=['is_active'])

        if faculty.user:
            faculty.user.is_active = faculty.is_active
            faculty.user.save(update_fields=['is_active'])

        return faculty
