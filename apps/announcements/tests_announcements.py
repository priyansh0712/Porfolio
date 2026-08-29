from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.announcements.models import SchoolAnnouncement
from apps.students.models import Student
from apps.tenants.models import School


class AnnouncementsTests(TestCase):
    def setUp(self):
        self.school_a = School.objects.create(name="School A", subdomain="schoola")

        self.admin_user = User.objects.create_user(
            username="admin_a",
            email="admin@schoola.com",
            password="AdminPassword@123",
            role=User.Role.SCHOOL_ADMIN,
            school=self.school_a,
        )

        self.student_user = User.objects.create_user(
            username="GR1001",
            email="gr1001@schoola.com",
            password="Admin@123",
            role=User.Role.STUDENT,
            school=self.school_a,
        )

    def test_admin_create_announcement(self):
        """School Admin creates an active broadcast announcement."""
        self.client.force_login(self.admin_user)

        post_data = {
            'title': 'Annual Sports Day 2026',
            'content': 'Sports day events start at 8:00 AM on Monday.',
            'target_audience': 'ALL',
            'is_active': 'on',
        }
        url = reverse('announcements:manage')
        response = self.client.post(url, post_data, HTTP_HOST='schoola.localhost:8000')

        self.assertEqual(response.status_code, 302)
        ann = SchoolAnnouncement.objects.get(school=self.school_a, title='Annual Sports Day 2026')
        self.assertEqual(ann.author, self.admin_user)
        self.assertTrue(ann.is_active)

    def test_student_announcements_view(self):
        """Student views published active announcements targeted to ALL or STUDENTS."""
        SchoolAnnouncement.objects.create(
            school=self.school_a,
            author=self.admin_user,
            title='General Notice',
            content='School remains closed tomorrow.',
            target_audience=SchoolAnnouncement.TargetAudience.ALL,
            is_active=True,
        )
        SchoolAnnouncement.objects.create(
            school=self.school_a,
            author=self.admin_user,
            title='Faculty Staff Meeting',
            content='Meeting at 3 PM in Conference Room.',
            target_audience=SchoolAnnouncement.TargetAudience.FACULTY,
            is_active=True,
        )

        self.client.force_login(self.student_user)
        url = reverse('announcements:student_list')
        response = self.client.get(url, HTTP_HOST='schoola.localhost:8000')

        self.assertEqual(response.status_code, 200)
        announcements_in_ctx = response.context['announcements']
        self.assertEqual(len(announcements_in_ctx), 1)
        self.assertEqual(announcements_in_ctx[0].title, 'General Notice')
