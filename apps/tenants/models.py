from django.db import models

from apps.core.models import TimeStampedModel
from apps.tenants.managers import TenantManager


class School(models.Model):
    """
    Represents a school tenant organization in the multi-tenant SaaS application.
    """
    name = models.CharField(max_length=255, help_text="Official name of the school")
    subdomain = models.SlugField(
        max_length=63,
        unique=True,
        db_index=True,
        help_text="Unique subdomain slug (e.g. greenwood for greenwood.ourapp.com)"
    )
    contact_email = models.EmailField(help_text="Primary administrative contact email")
    is_active = models.BooleanField(default=True, help_text="Whether this school account is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'School Tenant'
        verbose_name_plural = 'School Tenants'

    def __str__(self):
        return f"{self.name} ({self.subdomain})"

    @property
    def full_domain(self):
        return f"{self.subdomain}.ourapp.com"


class TenantModel(TimeStampedModel):
    """
    Abstract base class for all tenant-scoped entities.

    Provides:
      - school ForeignKey for tenant association
      - TenantManager as default manager (auto-scopes queries to active tenant)
      - Inherits created_at / updated_at from TimeStampedModel
    """
    school = models.ForeignKey(
        'tenants.School',
        on_delete=models.CASCADE,
        related_name='%(class)s_set',
        verbose_name='School Tenant',
    )

    objects = TenantManager()

    class Meta:
        abstract = True

