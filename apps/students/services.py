"""
StudentService — atomic business logic for student management.

Handles student provisioning, user account creation, soft-delete,
and the transfer request lifecycle (request → approve / reject).
"""
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

User = get_user_model()


class StudentService:
    """
    Business logic layer for student operations.

    All methods operate within explicit @transaction.atomic blocks to ensure
    data integrity across related Student + User records.
    """

    DEFAULT_PASSWORD = 'Admin@123'

    @staticmethod
    def _build_student_username(school, gr_number):
        """Build a unique, deterministic internal username for a student user."""
        code = (getattr(school, 'code', None) or str(school.pk)).lower()
        return f'gr_{code}_{gr_number}'.lower()

    @staticmethod
    def _build_student_email(school, gr_number):
        """Build a unique internal email placeholder for a student user."""
        code = (getattr(school, 'code', None) or str(school.pk)).lower()
        return f'gr_{code}_{gr_number}@student.local'.lower()

    @classmethod
    @transaction.atomic
    def create_student(
        cls,
        school,
        academic_year,
        standard,
        division,
        gr_number,
        full_name,
        roll_number=None,
        dob=None,
        gender='MALE',
        blood_group='',
        guardian_name='',
        guardian_phone='',
        emergency_contact='',
        address='',
        admission_date=None,
        custom_fields=None,
    ):
        """
        Create a new Student record and provision a linked User account.

        Returns:
            Student: The created student instance.

        Raises:
            ValueError: If GR number is already used within the school.
        """
        from apps.students.models import Student

        # Validate GR uniqueness
        if Student.objects.filter(school=school, gr_number=gr_number).exists():
            raise ValueError(f"GR Number '{gr_number}' is already registered in this school.")

        # Provision User account
        username = cls._build_student_username(school, gr_number)
        email = cls._build_student_email(school, gr_number)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=cls.DEFAULT_PASSWORD,
            first_name=full_name.split()[0] if full_name.split() else full_name,
            last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else '',
            role=User.Role.STUDENT,
            school=school,
        )

        # Create Student record
        student = Student.objects.create(
            school=school,
            user=user,
            gr_number=gr_number,
            roll_number=roll_number,
            full_name=full_name,
            dob=dob,
            gender=gender,
            blood_group=blood_group,
            guardian_name=guardian_name,
            guardian_phone=guardian_phone,
            emergency_contact=emergency_contact,
            address=address,
            academic_year=academic_year,
            standard=standard,
            division=division,
            admission_date=admission_date or timezone.now().date(),
            custom_fields=custom_fields or {},
            is_active=True,
        )

        return student

    @staticmethod
    @transaction.atomic
    def update_student(student, allow_gr_edit=False, **fields):
        """
        Update student fields. GR number can only be changed if allow_gr_edit=True.

        Args:
            student: Student instance to update.
            allow_gr_edit: Only School Admin passes True; Class Teacher must never pass True.
            **fields: Field names and values to update.

        Returns:
            Student: The updated student instance.
        """
        if not allow_gr_edit:
            fields.pop('gr_number', None)

        for field, value in fields.items():
            setattr(student, field, value)
        student.save()

        # Sync full_name to linked user's first/last name if changed
        if 'full_name' in fields and student.user:
            parts = fields['full_name'].split()
            student.user.first_name = parts[0] if parts else ''
            student.user.last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''
            student.user.save(update_fields=['first_name', 'last_name'])

        return student

    @staticmethod
    @transaction.atomic
    def soft_delete_student(student):
        """
        Soft-deactivate a student. Sets is_active=False and deactivates linked user.

        Args:
            student: Student instance to deactivate.
        """
        student.is_active = False
        student.save(update_fields=['is_active', 'updated_at'])

        if student.user:
            student.user.is_active = False
            student.user.save(update_fields=['is_active'])

    @staticmethod
    @transaction.atomic
    def bulk_soft_delete_students(student_ids, school):
        """
        Bulk soft-deactivate students for a school. Sets is_active=False and deactivates linked users.

        Args:
            student_ids: List or QuerySet of student primary keys.
            school: Tenant school instance for security scoping.

        Returns:
            int: Number of students deactivated.
        """
        from apps.students.models import Student
        students = list(Student.objects.filter(school=school, pk__in=student_ids))
        if not students:
            return 0

        user_ids = [s.user_id for s in students if s.user_id]

        # Update students
        Student.objects.filter(school=school, pk__in=[s.pk for s in students]).update(
            is_active=False,
            updated_at=timezone.now()
        )

        # Deactivate associated users
        if user_ids:
            from apps.accounts.models import User
            User.objects.filter(school=school, pk__in=user_ids).update(is_active=False)

        return len(students)

    @staticmethod
    @transaction.atomic
    def hard_delete_student(student):
        """
        Permanently delete a student and their associated user account.

        Args:
            student: Student instance to permanently delete.
        """
        user = student.user
        student.delete()
        if user and user.role == User.Role.STUDENT:
            user.delete()

    @staticmethod
    @transaction.atomic
    def bulk_hard_delete_students(student_ids, school):
        """
        Permanently delete students and their associated user accounts.

        Args:
            student_ids: List or QuerySet of student primary keys.
            school: Tenant school instance for security scoping.

        Returns:
            int: Number of students permanently deleted.
        """
        from apps.students.models import Student
        from apps.accounts.models import User

        students = list(Student.objects.filter(school=school, pk__in=student_ids))
        if not students:
            return 0

        user_ids = [s.user_id for s in students if s.user_id]
        pks = [s.pk for s in students]

        # Delete students first
        Student.objects.filter(school=school, pk__in=pks).delete()

        # Delete associated student user accounts
        if user_ids:
            User.objects.filter(school=school, pk__in=user_ids, role=User.Role.STUDENT).delete()

        return len(students)

    @staticmethod
    @transaction.atomic
    def restore_student(student):
        """Reactivate a soft-deleted student and restore their user account."""
        student.is_active = True
        student.save(update_fields=['is_active', 'updated_at'])

        if student.user:
            student.user.is_active = True
            student.user.save(update_fields=['is_active'])

    @staticmethod
    @transaction.atomic
    def bulk_restore_students(student_ids, school):
        """
        Bulk reactivate soft-deleted students and restore their user accounts.

        Args:
            student_ids: List or QuerySet of student primary keys.
            school: Tenant school instance for security scoping.

        Returns:
            int: Number of students reactivated.
        """
        from apps.students.models import Student
        from apps.accounts.models import User

        students = list(Student.objects.filter(school=school, pk__in=student_ids))
        if not students:
            return 0

        user_ids = [s.user_id for s in students if s.user_id]
        pks = [s.pk for s in students]

        # Reactivate students
        Student.objects.filter(school=school, pk__in=pks).update(
            is_active=True,
            updated_at=timezone.now()
        )

        # Reactivate associated user accounts
        if user_ids:
            User.objects.filter(school=school, pk__in=user_ids).update(is_active=True)

        return len(students)

    @staticmethod
    @transaction.atomic
    def request_transfer(student, to_standard, to_division, requested_by, reason=''):
        """
        Create a transfer request for a student by their Class Teacher.

        Args:
            student: Student to transfer.
            to_standard: Target Standard.
            to_division: Target Division (must belong to to_standard).
            requested_by: Faculty instance initiating the request.
            reason: Optional reason text.

        Returns:
            StudentTransferRequest: The created transfer request.

        Raises:
            ValueError: If a PENDING transfer already exists for this student.
        """
        from apps.students.models import StudentTransferRequest

        # Prevent duplicate pending requests
        if StudentTransferRequest.objects.filter(
            student=student,
            status=StudentTransferRequest.Status.PENDING,
        ).exists():
            raise ValueError('A transfer request is already pending for this student.')

        return StudentTransferRequest.objects.create(
            school=student.school,
            student=student,
            from_division=student.division,
            to_standard=to_standard,
            to_division=to_division,
            requested_by=requested_by,
            reason=reason,
        )

    @staticmethod
    @transaction.atomic
    def approve_transfer(transfer_request, reviewed_by):
        """
        Approve a transfer request and atomically update student's placement.

        Args:
            transfer_request: StudentTransferRequest with status PENDING.
            reviewed_by: User (School Admin) approving the request.

        Raises:
            ValueError: If request is not in PENDING status.
        """
        from apps.students.models import Student, StudentTransferRequest

        if transfer_request.status != StudentTransferRequest.Status.PENDING:
            raise ValueError('Only PENDING transfer requests can be approved.')

        # Update student placement atomically
        student = transfer_request.student

        # Check if roll_number collides in destination division
        from django.db.models import Max
        existing_roll = False
        if student.roll_number:
            existing_roll = Student.objects.filter(
                school=student.school,
                academic_year=student.academic_year,
                division=transfer_request.to_division,
                roll_number=student.roll_number,
                is_active=True,
            ).exclude(pk=student.pk).exists()

        update_fields = ['standard', 'division', 'updated_at']
        if existing_roll or not student.roll_number:
            max_roll = Student.objects.filter(
                school=student.school,
                academic_year=student.academic_year,
                division=transfer_request.to_division,
                is_active=True,
            ).aggregate(Max('roll_number'))['roll_number__max'] or 0
            student.roll_number = max_roll + 1
            update_fields.append('roll_number')

        student.standard = transfer_request.to_standard
        student.division = transfer_request.to_division
        student.save(update_fields=update_fields)

        # Mark transfer approved
        transfer_request.status = StudentTransferRequest.Status.APPROVED
        transfer_request.reviewed_by = reviewed_by
        transfer_request.reviewed_at = timezone.now()
        transfer_request.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])

    @staticmethod
    @transaction.atomic
    def reject_transfer(transfer_request, reviewed_by, rejection_reason=''):
        """
        Reject a transfer request without modifying student placement.

        Args:
            transfer_request: StudentTransferRequest with status PENDING.
            reviewed_by: User (School Admin) rejecting the request.
            rejection_reason: Optional explanation for rejection.

        Raises:
            ValueError: If request is not in PENDING status.
        """
        from apps.students.models import StudentTransferRequest

        if transfer_request.status != StudentTransferRequest.Status.PENDING:
            raise ValueError('Only PENDING transfer requests can be rejected.')

        transfer_request.status = StudentTransferRequest.Status.REJECTED
        transfer_request.reviewed_by = reviewed_by
        transfer_request.reviewed_at = timezone.now()
        transfer_request.rejection_reason = rejection_reason
        transfer_request.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'rejection_reason'])

    # -----------------------------------------------------------------------
    # Custom Field Management (School Admin / Principal)
    # -----------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def create_custom_field(school, label, field_type, options='', is_required=False):
        """
        Create a new dynamic custom field definition for the school.
        Generates a clean slug for field_name.
        """
        from django.utils.text import slugify
        from apps.students.models import StudentCustomField

        base_slug = slugify(label).replace('-', '_')
        field_name = base_slug
        counter = 1
        while StudentCustomField.objects.filter(school=school, field_name=field_name).exists():
            field_name = f'{base_slug}_{counter}'
            counter += 1

        order = StudentCustomField.objects.filter(school=school).count()
        return StudentCustomField.objects.create(
            school=school,
            label=label,
            field_name=field_name,
            field_type=field_type,
            options=options,
            is_required=is_required,
            is_active=True,
            order_index=order,
        )

    @staticmethod
    @transaction.atomic
    def update_custom_field(custom_field, label, field_type=None, options='', is_required=False):
        """
        Update an existing custom field's label, field_type, options, and required flag.
        Field key (field_name) is preserved to keep database references consistent.
        """
        custom_field.label = label.strip()
        if field_type:
            custom_field.field_type = field_type
        custom_field.options = options.strip()
        custom_field.is_required = is_required
        custom_field.save(update_fields=['label', 'field_type', 'options', 'is_required'])
        return custom_field

    @staticmethod
    @transaction.atomic
    def toggle_custom_field(custom_field):
        """Toggle active/inactive status of a custom field definition."""
        custom_field.is_active = not custom_field.is_active
        custom_field.save(update_fields=['is_active'])
        return custom_field

    @staticmethod
    @transaction.atomic
    def delete_custom_field(custom_field):
        """Delete a custom field definition from the school."""
        custom_field.delete()


