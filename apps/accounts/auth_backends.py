from django.contrib.auth.backends import ModelBackend

from apps.accounts.models import User


class TenantAwareAuthBackend(ModelBackend):
    """
    Custom authentication backend enforcing tenant-subdomain isolation.

    Defense-in-Depth Layer 1b (Auth Level):
      - School Admin / Faculty can only log in on their own school's subdomain.
      - Super Admin can only log in on the root domain (request.tenant is None).
      - Cross-tenant login attempts are silently rejected (returns None).

    This is the primary authentication backend. Django's ModelBackend is kept
    as a fallback only for Django admin (superuser) access.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate email + password and enforce subdomain-role isolation.

        Args:
            request: Django HttpRequest (must have request.tenant set by TenantMiddleware).
            username: Treated as email address.
            password: User's plaintext password.

        Returns:
            User instance if credentials are valid and subdomain matches role.
            None if authentication fails or subdomain-role mismatch detected.
        """
        # Support both username= and email= keyword argument forms
        email = username or kwargs.get('email')
        if not email:
            return None

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # Run default password hasher to prevent timing attacks
            User().set_password(password)
            return None

        # Verify password
        if not user.check_password(password):
            return None

        # Verify user account is active
        if not self.user_can_authenticate(user):
            return None

        # --- Tenant-Subdomain Isolation Enforcement ---
        if request is not None:
            active_tenant = getattr(request, 'tenant', None)

            if active_tenant is not None:
                # Request on a school subdomain
                if user.role == User.Role.SUPER_ADMIN:
                    # Super Admin cannot log in on a school's subdomain
                    return None
                if user.school_id != active_tenant.pk:
                    # Cross-tenant login: user belongs to a different school
                    return None
            else:
                # Request on root domain (tenant is None)
                if user.role != User.Role.SUPER_ADMIN:
                    # Tenant users (School Admin / Faculty) cannot log in on root domain
                    return None

        return user

    def get_user(self, user_id):
        """Return user by pk for session-based auth."""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
