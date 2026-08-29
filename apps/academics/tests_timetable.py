from datetime import date, time
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.academics.models import AcademicYear, Standard, Division, Subject, ClassTimetable
from apps.faculty.models import Faculty
from apps.students.models import Student
from apps.tenants.models import School


class TimetableTests(TestCase):
    def setUp(self):
        self.school_a = School.objects.create(name="School A", subdomain="schoola")

        self.academic_year = AcademicYear.objects.create(
            school=self.school_a,
            name="2026-2027",
            start_date=date(2026, 6, 1),
            end_date=date(2027, 5, 31),
            is_current=True,
        )
        self.std_10 = Standard.objects.create(school=self.school_a, name="Std 10", order_index=10)
        self.div_a = Division.objects.create(school=self.school_a, standard=self.std_10, name="A")
        self.subject_math = Subject.objects.create(school=self.school_a, name="Mathematics", code="MATH101")

        self.admin_user = User.objects.create_user(
            username="admin_a",
            email="admin@schoola.com",
            password="AdminPassword@123",
            role=User.Role.SCHOOL_ADMIN,
            school=self.school_a,
        )

        self.teacher_user = User.objects.create_user(
            username="teacher_a",
            email="teacher@schoola.com",
            password="Password@123",
            role=User.Role.FACULTY,
            school=self.school_a,
        )
        self.faculty = Faculty.objects.create(
            school=self.school_a,
            user=self.teacher_user,
            employee_code="EMP101",
            first_name="Ramesh",
            last_name="Patel",
            email="teacher@schoola.com",
        )

        self.student_user = User.objects.create_user(
            username="GR1001",
            email="gr1001@schoola.com",
            password="Admin@123",
            role=User.Role.STUDENT,
            school=self.school_a,
        )
        self.student = Student.objects.create(
            school=self.school_a,
            user=self.student_user,
            gr_number="GR1001",
            roll_number=1,
            full_name="Rahul Kumar",
            academic_year=self.academic_year,
            standard=self.std_10,
            division=self.div_a,
        )

    def test_admin_timetable_slot_creation(self):
        """School Admin creates a period timetable slot for a division."""
        self.client.force_login(self.admin_user)

        post_data = {
            'division_id': self.div_a.pk,
            'day_of_week': 1,  # Monday
            'period_number': 1,
            'subject_id': self.subject_math.pk,
            'faculty_id': self.faculty.pk,
            'start_time': '08:00',
            'end_time': '08:45',
        }
        url = reverse('academics:timetable_manage')
        response = self.client.post(url, post_data, HTTP_HOST='schoola.localhost:8000')

        self.assertEqual(response.status_code, 302)
        slot = ClassTimetable.objects.get(
            school=self.school_a,
            division=self.div_a,
            day_of_week=1,
            period_number=1,
        )
        self.assertEqual(slot.subject, self.subject_math)
        self.assertEqual(slot.faculty, self.faculty)

    def test_student_timetable_portal_view(self):
        """Student views weekly timetable schedule."""
        ClassTimetable.objects.create(
            school=self.school_a,
            academic_year=self.academic_year,
            division=self.div_a,
            day_of_week=1,
            period_number=1,
            subject=self.subject_math,
            faculty=self.faculty,
            start_time=time(8, 0),
            end_time=time(8, 45),
        )

        self.client.force_login(self.student_user)
        url = reverse('academics:student_timetable')
        response = self.client.get(url, HTTP_HOST='schoola.localhost:8000')

        self.assertEqual(response.status_code, 200)
        grid = response.context['grid']
        self.assertEqual(grid[1][1].subject, self.subject_math)
