from django.test import TestCase

from apps.accounts.models import User
from apps.tenants.models import School
from apps.notifications.models import InAppNotification
from apps.tenants.context import set_current_tenant


class NotificationsModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create two school tenants
        cls.school_a = School.objects.create(
            name="Alpha School",
            subdomain="alpha",
            contact_email="admin@alpha.edu",
            is_active=True
        )
        cls.school_b = School.objects.create(
            name="Beta School",
            subdomain="beta",
            contact_email="admin@beta.edu",
            is_active=True
        )

        # Create users for School A and B
        cls.user_a = User.objects.create_user(
            username="faculty_a@alpha.edu",
            email="faculty_a@alpha.edu",
            password="FacultyPass1!",
            role=User.Role.FACULTY,
            school=cls.school_a
        )
        cls.user_b = User.objects.create_user(
            username="faculty_b@beta.edu",
            email="faculty_b@beta.edu",
            password="FacultyPass1!",
            role=User.Role.FACULTY,
            school=cls.school_b
        )

    def tearDown(self):
        set_current_tenant(None)

    def test_create_notification(self):
        """Verify notification creation, default read status, and string representation."""
        notif = InAppNotification.objects.create(
            school=self.school_a,
            user=self.user_a,
            title="Leave Submitted",
            message="Your leave request has been submitted."
        )
        self.assertFalse(notif.is_read)
        self.assertEqual(notif.title, "Leave Submitted")
        self.assertEqual(str(notif), "faculty_a@alpha.edu — Leave Submitted (Unread)")

        # Mark read
        notif.is_read = True
        notif.save()
        self.assertEqual(str(notif), "faculty_a@alpha.edu — Leave Submitted (Read)")

    def test_notification_tenant_scoping(self):
        """Verify that TenantManager automatically filters notifications by active tenant."""
        # Create notifications for both schools
        InAppNotification.objects.create(
            school=self.school_a,
            user=self.user_a,
            title="School A Alert",
            message="Alert A"
        )
        InAppNotification.objects.create(
            school=self.school_b,
            user=self.user_b,
            title="School B Alert",
            message="Alert B"
        )

        # Set tenant context to School A
        set_current_tenant(self.school_a)
        notifs_a = InAppNotification.objects.all()
        self.assertEqual(notifs_a.count(), 1)
        self.assertEqual(notifs_a.first().title, "School A Alert")

        # Set tenant context to School B
        set_current_tenant(self.school_b)
        notifs_b = InAppNotification.objects.all()
        self.assertEqual(notifs_b.count(), 1)
        self.assertEqual(notifs_b.first().title, "School B Alert")


class NotificationIntegrationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create school tenants
        cls.school_a = School.objects.create(
            name="Alpha School",
            subdomain="alpha",
            contact_email="admin@alpha.edu",
            is_active=True
        )
        cls.school_b = School.objects.create(
            name="Beta School",
            subdomain="beta",
            contact_email="admin@beta.edu",
            is_active=True
        )

        # Create users
        cls.user_a = User.objects.create_user(
            username="faculty_a@alpha.edu",
            email="faculty_a@alpha.edu",
            password="FacultyPass1!",
            role=User.Role.FACULTY,
            school=cls.school_a
        )
        cls.user_b = User.objects.create_user(
            username="faculty_b@beta.edu",
            email="faculty_b@beta.edu",
            password="FacultyPass1!",
            role=User.Role.FACULTY,
            school=cls.school_b
        )

        # Create unread notifications for user A
        cls.notif_1 = InAppNotification.objects.create(
            school=cls.school_a,
            user=cls.user_a,
            title="Leave Approved",
            message="Your leave request has been approved."
        )
        cls.notif_2 = InAppNotification.objects.create(
            school=cls.school_a,
            user=cls.user_a,
            title="Biometric Setup Complete",
            message="Your face templates have been registered."
        )
        cls.notif_3 = InAppNotification.objects.create(
            school=cls.school_a,
            user=cls.user_a,
            title="Alert Title 3",
            message="Alert Message 3"
        )

    def tearDown(self):
        set_current_tenant(None)

    def test_notification_list_access(self):
        """Verify only authenticated users can access the notification list."""
        # Unauthenticated redirects to login
        response = self.client.get("/notifications/")
        self.assertEqual(response.status_code, 302)

        # Authenticated allowed
        self.client.force_login(self.user_a)
        response = self.client.get("/notifications/", HTTP_HOST="alpha.localhost")
        self.assertEqual(response.status_code, 200)

    def test_context_processor_output(self):
        """Verify unread count is globally accessible in template context."""
        self.client.force_login(self.user_a)
        response = self.client.get("/notifications/", HTTP_HOST="alpha.localhost")
        self.assertEqual(response.context["unread_notifications_count"], 3)

    def test_mark_single_notification_read(self):
        """Verify a single POST endpoint updates status and decrements unread count."""
        self.client.force_login(self.user_a)

        # Mark first notification as read
        response = self.client.post(
            f"/notifications/{self.notif_1.pk}/read/",
            HTTP_HOST="alpha.localhost"
        )
        self.assertRedirects(response, "/notifications/")

        # Verify database update
        self.notif_1.refresh_from_db()
        self.assertTrue(self.notif_1.is_read)

        # Check context count is decremented
        response = self.client.get("/notifications/", HTTP_HOST="alpha.localhost")
        self.assertEqual(response.context["unread_notifications_count"], 2)

    def test_mark_all_notifications_read(self):
        """Verify mark all updates all user's notifications to is_read=True."""
        self.client.force_login(self.user_a)

        # Execute mass read update
        response = self.client.post(
            "/notifications/mark-all-read/",
            HTTP_HOST="alpha.localhost"
        )
        self.assertRedirects(response, "/notifications/")

        # Verify all user A notifications are read
        self.assertEqual(
            InAppNotification.objects.filter(school=self.school_a, user=self.user_a, is_read=False).count(),
            0
        )

        # Check unread badge count is 0
        response = self.client.get("/notifications/", HTTP_HOST="alpha.localhost")
        self.assertEqual(response.context["unread_notifications_count"], 0)

    def test_cross_tenant_read_blocked(self):
        """Verify user B cannot read or modify user A's notifications."""
        self.client.force_login(self.user_b)

        # POST attempt on user A's notification
        response = self.client.post(
            f"/notifications/{self.notif_1.pk}/read/",
            HTTP_HOST="beta.localhost"
        )
        self.assertEqual(response.status_code, 404)

        # Verify log A remains unread
        self.notif_1.refresh_from_db()
        self.assertFalse(self.notif_1.is_read)

