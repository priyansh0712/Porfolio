from django.db import models
from apps.accounts.models import User
from apps.tenants.models import TenantModel


class InAppNotification(TenantModel):
    """
    Represents an in-app notification sent to a specific user (Faculty or Admin).
    Scoped to the school tenant.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="User recipient of this notification."
    )
    title = models.CharField(
        max_length=255,
        help_text="Brief subject of the notification."
    )
    message = models.TextField(
        help_text="Detailed text body of the notification."
    )
    is_read = models.BooleanField(
        default=False,
        help_text="Read/unread status."
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'In-App Notification'
        verbose_name_plural = 'In-App Notifications'

    def __str__(self):
        status_label = "Read" if self.is_read else "Unread"
        return f"{self.user.email} — {self.title} ({status_label})"
