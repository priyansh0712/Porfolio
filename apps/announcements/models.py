"""
School Announcements Models — Broadcast announcements created by School Admin / Principal.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.tenants.models import TenantModel


class SchoolAnnouncement(TenantModel):
    """
    Represents a school-wide or targeted broadcast announcement published by the Principal / School Admin.
    """

    class TargetAudience(models.TextChoices):
        ALL = 'ALL', 'Everyone'
        STUDENTS = 'STUDENTS', 'Students only'
        FACULTY = 'FACULTY', 'Faculty only'

    title = models.CharField(
        max_length=200,
        help_text='Headline or title of the announcement / notice',
    )
    content = models.TextField(
        help_text='Detailed announcement message / body',
    )
    target_audience = models.CharField(
        max_length=20,
        choices=TargetAudience.choices,
        default=TargetAudience.ALL,
        help_text='Audience scope for this announcement (Everyone, Students only, Faculty only)',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this announcement is currently active and visible',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='announcements',
        help_text='School Admin / Principal user who created the announcement',
    )
    published_at = models.DateTimeField(
        default=timezone.now,
        help_text='Publication date and time',
    )

    class Meta:
        ordering = ['-published_at']
        verbose_name = 'School Announcement'
        verbose_name_plural = 'School Announcements'

    def __str__(self):
        return f"{self.title} ({self.get_target_audience_display()})"


class AnnouncementAcknowledgment(TenantModel):
    """
    Tracks which users have viewed and dismissed the one-time login popup for a given announcement.
    """
    announcement = models.ForeignKey(
        SchoolAnnouncement,
        on_delete=models.CASCADE,
        related_name='acknowledgments',
        help_text='Announcement that was acknowledged',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='announcement_acknowledgments',
        help_text='User who viewed / acknowledged the popup',
    )
    acknowledged_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Timestamp when popup was dismissed',
    )

    class Meta:
        ordering = ['-acknowledged_at']
        verbose_name = 'Announcement Acknowledgment'
        verbose_name_plural = 'Announcement Acknowledgments'
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'announcement', 'user'],
                name='unique_announcement_ack_per_user',
            )
        ]

    def __str__(self):
        return f"{self.user.email} acknowledged '{self.announcement.title}' at {self.acknowledged_at}"
