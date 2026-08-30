from django.test import TestCase, Client
from django.urls import reverse

from apps.accounts.models import User
from apps.announcements.models import SchoolAnnouncement, AnnouncementAcknowledgment
from apps.announcements.services import AnnouncementService
from apps.notifications.models import InAppNotification
from apps.tenants.models import School


class PrincipalNoticeTestSuite(TestCase):
    """
    Complete test suite for Principal Notices:
      - Audience Targeting (Everyone, Students only, Faculty only)
      - First Login One-Time Popup & Acknowledgment
      - Multi-Tenant Isolation
      - Persistent In-App Notifications
      - Role Permissions
    """

    def setUp(self):
        self.client = Client()

        # School A (Greenwood High)
        self.school_a = School.objects.create(
            name="Greenwood High",
            subdomain="greenwood",
        )
        self.admin_a = User.objects.create_user(
            username="principal_a",
            email="principal@greenwood.edu",
            password="Password@123",
            role=User.Role.SCHOOL_ADMIN,
            school=self.school_a,
        )
        self.faculty_a = User.objects.create_user(
            username="teacher_a",
            email="teacher@greenwood.edu",
            password="Password@123",
            role=User.Role.FACULTY,
            school=self.school_a,
        )
        self.student_a = User.objects.create_user(
            username="student_a",
            email="student@greenwood.edu",
            password="Password@123",
            role=User.Role.STUDENT,
            school=self.school_a,
        )

        # School B (St Mary Academy)
        self.school_b = School.objects.create(
            name="St Mary Academy",
            subdomain="stmary",
        )
        self.admin_b = User.objects.create_user(
            username="principal_b",
            email="principal@stmary.edu",
            password="Password@123",
            role=User.Role.SCHOOL_ADMIN,
            school=self.school_b,
        )
        self.student_b = User.objects.create_user(
            username="student_b",
            email="student@stmary.edu",
            password="Password@123",
            role=User.Role.STUDENT,
            school=self.school_b,
        )

    # ══════════════════════════════════════════════════════════════════════════
    # 1. NOTICE CREATION & AUDIENCE TARGETING
    # ══════════════════════════════════════════════════════════════════════════

    def test_principal_sends_notice_to_everyone(self):
        """Notice sent to 'Everyone' reaches both students and faculty of the school."""
        self.client.force_login(self.admin_a)
        res = self.client.post(
            reverse('announcements:manage'),
            {
                'title': 'School Closed Tomorrow',
                'content': 'Heavy rains expected. School will remain closed tomorrow.',
                'target_audience': SchoolAnnouncement.TargetAudience.ALL,
                'is_active': True,
            },
            HTTP_HOST='greenwood.localhost',
        )
        self.assertEqual(res.status_code, 302)

        # Announcement created
        notice = SchoolAnnouncement.objects.filter(school=self.school_a, title='School Closed Tomorrow').first()
        self.assertIsNotNone(notice)
        self.assertEqual(notice.target_audience, SchoolAnnouncement.TargetAudience.ALL)

        # Notifications created for student and faculty in School A
        self.assertTrue(InAppNotification.objects.filter(school=self.school_a, user=self.student_a, title='Notice: School Closed Tomorrow').exists())
        self.assertTrue(InAppNotification.objects.filter(school=self.school_a, user=self.faculty_a, title='Notice: School Closed Tomorrow').exists())

        # Never sent to School B users
        self.assertFalse(InAppNotification.objects.filter(school=self.school_b, user=self.student_b).exists())

    def test_principal_sends_notice_to_students_only(self):
        """Notice sent to 'Students only' reaches only students in the school."""
        self.client.force_login(self.admin_a)
        res = self.client.post(
            reverse('announcements:manage'),
            {
                'title': 'Uniform Check on Monday',
                'content': 'All students must wear full formal uniform on Monday morning.',
                'target_audience': SchoolAnnouncement.TargetAudience.STUDENTS,
                'is_active': True,
            },
            HTTP_HOST='greenwood.localhost',
        )
        self.assertEqual(res.status_code, 302)

        self.assertTrue(InAppNotification.objects.filter(school=self.school_a, user=self.student_a, title='Notice: Uniform Check on Monday').exists())
        self.assertFalse(InAppNotification.objects.filter(school=self.school_a, user=self.faculty_a, title='Notice: Uniform Check on Monday').exists())

    def test_principal_sends_notice_to_faculty_only(self):
        """Notice sent to 'Faculty only' reaches only faculty members in the school."""
        self.client.force_login(self.admin_a)
        res = self.client.post(
            reverse('announcements:manage'),
            {
                'title': 'Staff Meeting at 3 PM',
                'content': 'Staff meeting in the conference hall today at 3 PM.',
                'target_audience': SchoolAnnouncement.TargetAudience.FACULTY,
                'is_active': True,
            },
            HTTP_HOST='greenwood.localhost',
        )
        self.assertEqual(res.status_code, 302)

        self.assertTrue(InAppNotification.objects.filter(school=self.school_a, user=self.faculty_a, title='Notice: Staff Meeting at 3 PM').exists())
        self.assertFalse(InAppNotification.objects.filter(school=self.school_a, user=self.student_a, title='Notice: Staff Meeting at 3 PM').exists())

    # ══════════════════════════════════════════════════════════════════════════
    # 2. ONE-TIME FIRST LOGIN POPUP & ACKNOWLEDGMENT
    # ══════════════════════════════════════════════════════════════════════════

    def test_first_login_popup_and_single_acknowledgment_flow(self):
        """
        1. Principal broadcasts notice.
        2. Student logs in -> popup modal is in context.
        3. Student acknowledges / dismisses popup -> acknowledgment is recorded.
        4. Student navigates to another page -> popup is NOT shown again.
        5. Notice remains in Notifications list.
        """
        notice = AnnouncementService.broadcast_notice(
            school=self.school_a,
            author=self.admin_a,
            title="Sports Day Next Friday",
            content="Annual Sports Day will be held next Friday on the main ground.",
            target_audience=SchoolAnnouncement.TargetAudience.ALL,
        )

        # 1. Student visits portal for the first time
        self.client.force_login(self.student_a)
        res1 = self.client.get(reverse('students:portal'), HTTP_HOST='greenwood.localhost')
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.context['pending_popup_notice'], notice)
        self.assertContains(res1, "Sports Day Next Friday")
        self.assertContains(res1, "principal-notice-popup-modal")

        # 2. Student acknowledges / dismisses popup
        ack_res = self.client.post(
            reverse('announcements:acknowledge', kwargs={'pk': notice.pk}),
            HTTP_HOST='greenwood.localhost',
        )
        self.assertEqual(ack_res.status_code, 200)
        self.assertTrue(AnnouncementAcknowledgment.objects.filter(school=self.school_a, announcement=notice, user=self.student_a).exists())

        # 3. Student navigates again (or refreshes) -> popup is GONE
        res2 = self.client.get(reverse('students:portal'), HTTP_HOST='greenwood.localhost')
        self.assertEqual(res2.status_code, 200)
        self.assertIsNone(res2.context['pending_popup_notice'])
        self.assertNotContains(res2, "principal-notice-popup-modal")

        # 4. Notice still exists in student announcements & notifications
        res_notif = self.client.get(reverse('notifications:notification_list'), HTTP_HOST='greenwood.localhost')
        self.assertEqual(res_notif.status_code, 200)
        self.assertContains(res_notif, "Notice: Sports Day Next Friday")

    # ══════════════════════════════════════════════════════════════════════════
    # 3. MULTI-TENANT ISOLATION
    # ══════════════════════════════════════════════════════════════════════════

    def test_multi_tenant_notice_isolation(self):
        """School A notices are strictly isolated and never shown to School B users."""
        notice_a = AnnouncementService.broadcast_notice(
            school=self.school_a,
            author=self.admin_a,
            title="School A Internal Notice",
            content="Only for School A.",
            target_audience=SchoolAnnouncement.TargetAudience.ALL,
        )

        # School B student logs into School B
        self.client.force_login(self.student_b)
        res_b = self.client.get(reverse('students:portal'), HTTP_HOST='stmary.localhost')
        self.assertEqual(res_b.status_code, 200)
        self.assertIsNone(res_b.context['pending_popup_notice'])
        self.assertNotContains(res_b, "School A Internal Notice")

        # School B student attempts to acknowledge School A notice -> 404 Not Found
        ack_res = self.client.post(
            reverse('announcements:acknowledge', kwargs={'pk': notice_a.pk}),
            HTTP_HOST='stmary.localhost',
        )
        self.assertEqual(ack_res.status_code, 404)

    # ══════════════════════════════════════════════════════════════════════════
    # 4. PERMISSIONS
    # ══════════════════════════════════════════════════════════════════════════

    def test_student_cannot_create_or_delete_notice(self):
        """Students are forbidden from creating or deleting principal notices."""
        self.client.force_login(self.student_a)
        res_create = self.client.post(
            reverse('announcements:manage'),
            {'title': 'Fake Notice', 'content': 'Content', 'target_audience': 'ALL'},
            HTTP_HOST='greenwood.localhost',
        )
        self.assertEqual(res_create.status_code, 403)

        notice = AnnouncementService.broadcast_notice(
            school=self.school_a,
            author=self.admin_a,
            title="Official Notice",
            content="Valid content",
            target_audience=SchoolAnnouncement.TargetAudience.ALL,
        )
        res_delete = self.client.post(
            reverse('announcements:delete', kwargs={'pk': notice.pk}),
            HTTP_HOST='greenwood.localhost',
        )
        self.assertEqual(res_delete.status_code, 403)
