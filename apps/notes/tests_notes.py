from datetime import date
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.academics.models import AcademicYear, Standard, Division, Subject, ClassTeacherAllocation, SubjectTeacherAllocation
from apps.faculty.models import Faculty
from apps.notes.models import SubjectNote
from apps.students.models import Student
from apps.tenants.models import School


class SubjectNotesTests(TestCase):
    def setUp(self):
        # Create School A
        self.school_a = School.objects.create(name="School A", subdomain="schoola")

        # Academic Setup
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

        # Class Teacher User & Faculty Profile
        self.class_teacher_user = User.objects.create_user(
            username="ct_user",
            email="ct@schoola.com",
            password="Password@123",
            role=User.Role.FACULTY,
            school=self.school_a,
        )
        self.ct_faculty = Faculty.objects.create(
            school=self.school_a,
            user=self.class_teacher_user,
            employee_code="EMP001",
            first_name="Class",
            last_name="Teacher",
            email="ct@schoola.com",
        )
        ClassTeacherAllocation.objects.create(
            school=self.school_a,
            academic_year=self.academic_year,
            division=self.div_a,
            faculty=self.ct_faculty,
        )

        # Subject Teacher User & Faculty Profile
        self.subject_teacher_user = User.objects.create_user(
            username="st_user",
            email="st@schoola.com",
            password="Password@123",
            role=User.Role.FACULTY,
            school=self.school_a,
        )
        self.st_faculty = Faculty.objects.create(
            school=self.school_a,
            user=self.subject_teacher_user,
            employee_code="EMP002",
            first_name="Subject",
            last_name="Teacher",
            email="st@schoola.com",
        )
        SubjectTeacherAllocation.objects.create(
            school=self.school_a,
            academic_year=self.academic_year,
            division=self.div_a,
            subject=self.subject_math,
            faculty=self.st_faculty,
        )

        # Student User
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

    def test_faculty_note_upload_pending(self):
        """Subject Faculty uploads a note file, creating a PENDING note record."""
        self.client.force_login(self.subject_teacher_user)

        dummy_file = SimpleUploadedFile("math_ch1.pdf", b"pdf content", content_type="application/pdf")
        post_data = {
            'division': self.div_a.pk,
            'subject': self.subject_math.pk,
            'title': 'Chapter 1: Real Numbers',
            'description': 'Read carefully for Monday test.',
            'file': dummy_file,
        }
        url = reverse('notes:upload')
        response = self.client.post(url, post_data, HTTP_HOST='schoola.localhost:8000')

        self.assertEqual(response.status_code, 302)
        note = SubjectNote.objects.get(school=self.school_a, title='Chapter 1: Real Numbers')
        self.assertEqual(note.status, SubjectNote.Status.PENDING)
        self.assertEqual(note.faculty, self.subject_teacher_user)

    def test_class_teacher_approve_note(self):
        """Class Teacher approves pending note, making it visible to students."""
        dummy_file = SimpleUploadedFile("math_ch2.pdf", b"pdf content", content_type="application/pdf")
        note = SubjectNote.objects.create(
            school=self.school_a,
            division=self.div_a,
            subject=self.subject_math,
            faculty=self.subject_teacher_user,
            title='Chapter 2: Polynomials',
            file=dummy_file,
            status=SubjectNote.Status.PENDING,
        )

        self.client.force_login(self.class_teacher_user)
        url = reverse('notes:review')
        post_data = {
            'note_id': note.pk,
            'action': 'APPROVE',
        }
        response = self.client.post(url, post_data, HTTP_HOST='schoola.localhost:8000')

        self.assertEqual(response.status_code, 302)
        note.refresh_from_db()
        self.assertEqual(note.status, SubjectNote.Status.APPROVED)
        self.assertEqual(note.reviewed_by, self.class_teacher_user)

    def test_student_portal_only_shows_approved_notes(self):
        """Student portal displays APPROVED notes, but excludes PENDING and REJECTED notes."""
        dummy_file = SimpleUploadedFile("note.pdf", b"content", content_type="application/pdf")
        
        # Approved note
        note_approved = SubjectNote.objects.create(
            school=self.school_a,
            division=self.div_a,
            subject=self.subject_math,
            faculty=self.subject_teacher_user,
            title='Approved Note',
            file=dummy_file,
            status=SubjectNote.Status.APPROVED,
        )
        # Pending note
        note_pending = SubjectNote.objects.create(
            school=self.school_a,
            division=self.div_a,
            subject=self.subject_math,
            faculty=self.subject_teacher_user,
            title='Pending Note',
            file=dummy_file,
            status=SubjectNote.Status.PENDING,
        )

        self.client.force_login(self.student_user)
        url = reverse('notes:student_notes')
        response = self.client.get(url, HTTP_HOST='schoola.localhost:8000')

        self.assertEqual(response.status_code, 200)
        notes_in_ctx = response.context['notes']
        self.assertIn(note_approved, notes_in_ctx)
        self.assertNotIn(note_pending, notes_in_ctx)
