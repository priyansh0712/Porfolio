"""
School Announcements Models — Broadcast announcements created by School Admin.
"""
from django.db import models
from django.utils import timezone

from apps.tenants.models import TenantModel


class SchoolAnnouncement(TenantModel):
    """
    Represents a school-wide or targeted broadcast announcement published by School Admin.
    """

    class TargetAudience(models.TextChoices):
        ALL = 'ALL', 'Everyone (All Roles)'
        STUDENTS = 'STUDENTS', 'Students Only'
        FACULTY = 'FACULTY', 'Faculty Only'

    title = models.CharField(
        max_length=200,
        help_text='Headline or title of the announcement',
    )
    content = models.TextField(
        help_text='Detailed announcement message / body',
    )
    target_audience = models.CharField(
        max_length=20,
        choices=TargetAudience.choices,
        default=TargetAudience.ALL,
        help_text='Audience scope for this announcement',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this announcement is currently active and visible',
    )
    author = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='announcements',
        help_text='School Admin user who created the announcement',
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
