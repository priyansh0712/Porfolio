"""
Subject Notes Views — Faculty Upload, Class Teacher Approval Workflow, Student Download.
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.models import User
from apps.accounts.permissions import SchoolAdminRequiredMixin
from apps.academics.models import (
    AcademicYear, Division, Subject,
    ClassTeacherAllocation, SubjectTeacherAllocation,
)
from apps.academics.services import AcademicService
from apps.faculty.models import Faculty
from apps.notes.forms import SubjectNoteUploadForm
from apps.notes.models import SubjectNote
from apps.students.views import SchoolStaffRequiredMixin, StudentRequiredMixin, _get_class_teacher_division


class SubjectFacultyNoteUploadView(SchoolStaffRequiredMixin, TemplateView):
    """
    GET: Subject Faculty selects Division & Subject, enters Title/Description, attaches note document file.
    POST: Uploads note with status PENDING ("Waiting for Approval").
    """
    template_name = 'notes/note_upload.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tenant = self.request.tenant
        user = self.request.user
        current_year = AcademicService.get_current_academic_year(tenant)

        if user.role == User.Role.FACULTY:
            faculty = Faculty.objects.filter(school=tenant, user=user, is_active=True).first()
            if faculty and current_year:
                subject_allocs = SubjectTeacherAllocation.objects.filter(
                    school=tenant,
                    academic_year=current_year,
                    faculty=faculty,
                ).select_related('division', 'division__standard', 'subject')
                ctx['subject_allocs'] = subject_allocs
                ctx['divisions'] = Division.objects.filter(pk__in=subject_allocs.values_list('division_id', flat=True)).distinct()
                ctx['subjects'] = Subject.objects.filter(pk__in=subject_allocs.values_list('subject_id', flat=True)).distinct()
            else:
                ctx['divisions'] = Division.objects.none()
                ctx['subjects'] = Subject.objects.none()
        else:
            ctx['divisions'] = Division.objects.filter(school=tenant, is_active=True)
            ctx['subjects'] = Subject.objects.filter(school=tenant, is_active=True)

        ctx['form'] = SubjectNoteUploadForm()
        return ctx

    def post(self, request):
        tenant = request.tenant
        user = request.user
        form = SubjectNoteUploadForm(request.POST, request.FILES)

        if form.is_valid():
            note = form.save(commit=False)
            note.school = tenant
            note.faculty = user
            note.status = SubjectNote.Status.PENDING
            note.save()

            messages.success(request, f"Note '{note.title}' uploaded successfully! It is now waiting for Class Teacher approval.")
            return redirect('notes:my_uploads')
        else:
            messages.error(request, 'Failed to upload note. Please check form errors below.')
            ctx = self.get_context_data()
            ctx['form'] = form
            return self.render_to_response(ctx)


class FacultyMyNotesListView(SchoolStaffRequiredMixin, TemplateView):
    """
    GET: Faculty views all notes uploaded by them and their current approval status (Pending, Approved, Rejected + reason).
    """
    template_name = 'notes/faculty_my_notes.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tenant = self.request.tenant
        user = self.request.user

        notes = SubjectNote.objects.filter(
            school=tenant,
            faculty=user,
        ).select_related('division', 'division__standard', 'subject').order_by('-created_at')

        ctx['notes'] = notes
        return ctx


class ClassTeacherNoteReviewView(SchoolStaffRequiredMixin, TemplateView):
    """
    GET: Class Teacher views PENDING notes uploaded for their assigned class division.
    POST: Action APPROVE or REJECT (with optional rejection reason).
    """
    template_name = 'notes/class_teacher_note_review.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tenant = self.request.tenant
        user = self.request.user
        current_year = AcademicService.get_current_academic_year(tenant)

        division = None
        if user.role == User.Role.FACULTY:
            division = _get_class_teacher_division(user, tenant, current_year)
        elif user.role == User.Role.SCHOOL_ADMIN:
            div_id = self.request.GET.get('division_id')
            if div_id:
                division = Division.objects.filter(school=tenant, pk=div_id).first()
            if not division:
                division = Division.objects.filter(school=tenant, is_active=True).first()

        ctx['division'] = division
        ctx['is_class_teacher'] = division is not None

        if division:
            pending_notes = SubjectNote.objects.filter(
                school=tenant,
                division=division,
                status=SubjectNote.Status.PENDING,
            ).select_related('subject', 'faculty').order_by('-created_at')

            reviewed_notes = SubjectNote.objects.filter(
                school=tenant,
                division=division,
            ).exclude(status=SubjectNote.Status.PENDING).select_related('subject', 'faculty', 'reviewed_by').order_by('-reviewed_at')[:20]

            ctx['pending_notes'] = pending_notes
            ctx['reviewed_notes'] = reviewed_notes

        return ctx

    def post(self, request):
        tenant = request.tenant
        user = request.user
        note_id = request.POST.get('note_id')
        action = request.POST.get('action')
        rejection_reason = request.POST.get('rejection_reason', '').strip()

        note = get_object_or_404(SubjectNote, pk=note_id, school=tenant)

        if action == 'APPROVE':
            note.status = SubjectNote.Status.APPROVED
            note.rejection_reason = ''
            note.reviewed_by = user
            note.reviewed_at = timezone.now()
            note.save()
            messages.success(request, f"Note '{note.title}' approved successfully and is now visible to students!")
        elif action == 'REJECT':
            note.status = SubjectNote.Status.REJECTED
            note.rejection_reason = rejection_reason or 'No reason provided.'
            note.reviewed_by = user
            note.reviewed_at = timezone.now()
            note.save()
            messages.info(request, f"Note '{note.title}' rejected.")
        else:
            messages.error(request, 'Invalid action specified.')

        return redirect('notes:review')


class StudentPortalNotesView(StudentRequiredMixin, TemplateView):
    """
    GET: Student views and downloads APPROVED study notes relevant to their assigned class division.
    """
    template_name = 'notes/student_portal_notes.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tenant = self.request.tenant
        student = getattr(self.request.user, 'student_profile', None)
        ctx['student'] = student

        if student and student.division:
            subject_id = self.request.GET.get('subject_id')

            notes_qs = SubjectNote.objects.filter(
                school=tenant,
                division=student.division,
                status=SubjectNote.Status.APPROVED,
            ).select_related('subject', 'faculty')

            if subject_id:
                notes_qs = notes_qs.filter(subject_id=subject_id)

            ctx['notes'] = notes_qs.order_by('-created_at')

            ctx['subjects'] = Subject.objects.filter(
                pk__in=SubjectNote.objects.filter(school=tenant, division=student.division, status=SubjectNote.Status.APPROVED).values_list('subject_id', flat=True)
            ).distinct()
            ctx['selected_subject_id'] = subject_id

        return ctx
