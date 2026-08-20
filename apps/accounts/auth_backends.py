from django.contrib.auth.backends import ModelBackend

from apps.accounts.models import User


class TenantAwareAuthBackend(ModelBackend):
    """
    Custom authentication backend enforcing tenant-subdomain isolation.

    Supports two authentication modes on school subdomains:
      - Email + Password: for School Admin and Faculty users.
      - GR Number + Password: for Student users (GR Number has no '@').

    Defense-in-Depth Layer 1b (Auth Level):
      - School Admin / Faculty can only log in on their own school's subdomain.
      - Students can only log in on their own school's subdomain via GR Number.
      - Super Admin can only log in on the root domain (request.tenant is None).
      - Cross-tenant login attempts are silently rejected (returns None).
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate credential + password and enforce subdomain-role isolation.

        If credential contains '@': treat as email (Staff login).
        If credential has no '@': treat as GR Number (Student login).

        Args:
            request: Django HttpRequest (must have request.tenant set by TenantMiddleware).
            username: Email address or GR Number.
            password: User's plaintext password.

        Returns:
            User instance if credentials are valid and subdomain matches role.
            None if authentication fails or subdomain-role mismatch detected.
        """
        credential = username or kwargs.get('email') or kwargs.get('username')
        if not credential:
            return None

        active_tenant = getattr(request, 'tenant', None) if request else None

        # --- GR Number login path (Student) ---
        if '@' not in str(credential):
            if active_tenant is None:
                # Student logins only valid on school subdomains
                return None
            try:
                from apps.students.models import Student
                student = Student.objects.select_related('user').get(
                    gr_number=credential,
                    school=active_tenant,
                    is_active=True,
                )
            except Student.DoesNotExist:
                User().set_password(password)
                return None

            if student.user is None:
                return None

            user = student.user
            if not user.check_password(password):
                return None
            if not self.user_can_authenticate(user):
                return None
            return user

        # --- Email login path (Staff) ---
        email = credential
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            User().set_password(password)
            return None

        if not user.check_password(password):
            return None
        if not self.user_can_authenticate(user):
            return None

        # --- Tenant-Subdomain Isolation Enforcement ---
        if request is not None:
            if active_tenant is not None:
                # Request on a school subdomain
                if user.role == User.Role.SUPER_ADMIN:
                    return None
                if user.school_id != active_tenant.pk:
                    return None
            else:
                # Request on root domain (tenant is None)
                if user.role != User.Role.SUPER_ADMIN:
                    return None

        return user

    def get_user(self, user_id):
        """Return user by pk for session-based auth."""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
