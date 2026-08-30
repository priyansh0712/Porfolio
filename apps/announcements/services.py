"""
School Announcements & Principal Notice Services.

Provides:
  - AnnouncementService: Handles audience targeting, broadcast dispatching, InAppNotification generation,
    and one-time login popup acknowledgment tracking.
"""
from typing import Optional, List
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.announcements.models import SchoolAnnouncement, AnnouncementAcknowledgment
from apps.notifications.models import InAppNotification


class AnnouncementService:
    """
    Service for managing broadcast notices and user acknowledgments.
    """

    @classmethod
    @transaction.atomic
    def broadcast_notice(
        cls,
        school,
        author: User,
        title: str,
        content: str,
        target_audience: str = SchoolAnnouncement.TargetAudience.ALL,
        is_active: bool = True,
    ) -> SchoolAnnouncement:
        """
        Creates a SchoolAnnouncement record and automatically dispatches InAppNotifications
        to all eligible targeted users belonging strictly to the school tenant.
        """
        announcement = SchoolAnnouncement.objects.create(
            school=school,
            author=author,
            title=title.strip(),
            content=content.strip(),
            target_audience=target_audience,
            is_active=is_active,
            published_at=timezone.now(),
        )

        # Target user scoping
        users_qs = User.objects.filter(school=school, is_active=True)
        if target_audience == SchoolAnnouncement.TargetAudience.STUDENTS:
            users_qs = users_qs.filter(role=User.Role.STUDENT)
        elif target_audience == SchoolAnnouncement.TargetAudience.FACULTY:
            users_qs = users_qs.filter(role=User.Role.FACULTY)
        else:  # ALL / Everyone
            users_qs = users_qs.filter(role__in=[User.Role.STUDENT, User.Role.FACULTY, User.Role.SCHOOL_ADMIN])

        # Bulk create in-app notifications for persistent notification history
        notifs = [
            InAppNotification(
                school=school,
                user=u,
                title=f"Notice: {announcement.title}",
                message=announcement.content,
                is_read=False,
            )
            for u in users_qs
        ]
        if notifs:
            InAppNotification.objects.bulk_create(notifs)

        return announcement

    @classmethod
    def acknowledge_notice(
        cls,
        school,
        announcement: SchoolAnnouncement,
        user: User,
    ) -> AnnouncementAcknowledgment:
        """
        Records that a user has viewed and dismissed the one-time popup for this notice.
        Also marks the corresponding InAppNotification as read.
        """
        ack, _ = AnnouncementAcknowledgment.objects.get_or_create(
            school=school,
            announcement=announcement,
            user=user,
        )

        # Mark matching in-app notification as read
        InAppNotification.objects.filter(
            school=school,
            user=user,
            title=f"Notice: {announcement.title}",
        ).update(is_read=True)

        return ack

    @classmethod
    def get_pending_popup_notice(
        cls,
        user: User,
        school,
    ) -> Optional[SchoolAnnouncement]:
        """
        Queries the earliest active notice targeted to the user's role in the current tenant
        that has not yet been acknowledged by this user.
        """
        if not user.is_authenticated or not school:
            return None

        role = getattr(user, 'role', None)
        if role == User.Role.STUDENT:
            allowed_audiences = [
                SchoolAnnouncement.TargetAudience.ALL,
                SchoolAnnouncement.TargetAudience.STUDENTS,
            ]
        elif role == User.Role.FACULTY:
            allowed_audiences = [
                SchoolAnnouncement.TargetAudience.ALL,
                SchoolAnnouncement.TargetAudience.FACULTY,
            ]
        else:
            # School Admins create notices and do not receive popup interruptions
            return None

        return SchoolAnnouncement.objects.filter(
            school=school,
            is_active=True,
            target_audience__in=allowed_audiences,
        ).exclude(
            acknowledgments__user=user
        ).select_related('author').order_by('published_at').first()
