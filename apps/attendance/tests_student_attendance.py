from datetime import date, timedelta
from django.test import TestCase, RequestFactory
from django.urls import reverse

from apps.accounts.models import User
from apps.academics.models import AcademicYear, Standard, Division, ClassTeacherAllocation
from apps.attendance.models import StudentAttendanceLog
from apps.students.models import Student
from apps.tenants.models import School


class StudentAttendanceTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        # Create School A
        self.school_a = School.objects.create(name="School A", subdomain="schoola")
        
        # Create Academic Year
        self.academic_year = AcademicYear.objects.create(
            school=self.school_a,
            name="2026-2027",
            start_date=date(2026, 6, 1),
            end_date=date(2027, 5, 31),
            is_current=True,
        )

        # Create Standard & Division
        self.std_10 = Standard.objects.create(school=self.school_a, name="Std 10", order_index=10)
        self.div_a = Division.objects.create(school=self.school_a, standard=self.std_10, name="A")
        self.div_b = Division.objects.create(school=self.school_a, standard=self.std_10, name="B")

        # Create Teacher User & Faculty Profile & Allocation
        self.teacher_user = User.objects.create_user(
            username="teacher_a",
            email="teacher_a@schoola.com",
            password="Password@123",
            role=User.Role.FACULTY,
            school=self.school_a,
        )
        from apps.faculty.models import Faculty
        self.faculty_member = Faculty.objects.create(
            school=self.school_a,
            user=self.teacher_user,
            first_name="Anita",
            last_name="Sharma",
            email="teacher_a@schoola.com",
            designation="Teacher",
        )
        ClassTeacherAllocation.objects.create(
            school=self.school_a,
            academic_year=self.academic_year,
            division=self.div_a,
            faculty=self.faculty_member,
        )

        # Create Students
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

    def test_class_teacher_attendance_marking(self):
        """Class teacher saves attendance for students in assigned division."""
        self.client.force_login(self.teacher_user)

        today_str = date.today().strftime('%Y-%m-%d')
        post_data = {
            'date': today_str,
            f'status_{self.student.pk}': 'PRESENT',
            f'remarks_{self.student.pk}': 'On time',
        }
        url = reverse('students:my_class_attendance')
        response = self.client.post(url, post_data, HTTP_HOST='schoola.localhost:8000')

        self.assertEqual(response.status_code, 302)
        log = StudentAttendanceLog.objects.get(school=self.school_a, student=self.student, date=date.today())
        self.assertEqual(log.status, 'PRESENT')
        self.assertEqual(log.remarks, 'On time')
        self.assertEqual(log.marked_by, self.teacher_user)

    def test_student_portal_attendance_view(self):
        """Student views personal attendance history and percentage."""
        # Create attendance logs for 2 days
        StudentAttendanceLog.objects.create(
            school=self.school_a,
            student=self.student,
            division=self.div_a,
            date=date.today() - timedelta(days=1),
            status=StudentAttendanceLog.Status.PRESENT,
        )
        StudentAttendanceLog.objects.create(
            school=self.school_a,
            student=self.student,
            division=self.div_a,
            date=date.today(),
            status=StudentAttendanceLog.Status.ABSENT,
        )

        self.client.force_login(self.student_user)
        url = reverse('students:portal_attendance')
        response = self.client.get(url, HTTP_HOST='schoola.localhost:8000')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_days'], 2)
        self.assertEqual(response.context['present_days'], 1)
        self.assertEqual(response.context['absent_days'], 1)
        self.assertEqual(response.context['percentage'], 50.0)
