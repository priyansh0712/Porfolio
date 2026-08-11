from django.db import transaction
from django.contrib.auth import get_user_model
from .models import School

User = get_user_model()

class SchoolRegistrationService:
    """
    Handles atomic registration of a new school tenant organization
    and initial School Admin user credentials.
    """
    @staticmethod
    @transaction.atomic
    def register_school(data: dict) -> tuple[School, User]:
        """
        Creates a School tenant record and associated primary School Admin user account.
        """
        school = School.objects.create(
            name=data['school_name'],
            subdomain=data['subdomain'],
            contact_email=data['contact_email']
        )

        # Split full name into first and last name if available
        name_parts = data['admin_full_name'].strip().split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        # Create primary School Admin user
        admin_user = User.objects.create_user(
            username=f"{data['subdomain']}_admin",
            email=data['contact_email'],
            password=data['password'],
            first_name=first_name,
            last_name=last_name,
            is_staff=True
        )

        return school, admin_user
