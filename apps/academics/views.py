"""
School Admin Academic Management Views.

Implements all CBVs with SchoolAdminRequiredMixin for multi-tenant Layer 2 authorization.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView
from django.contrib import messages
from django.db.models import ProtectedError
from django.urls import reverse

from apps.accounts.permissions import SchoolAdminRequiredMixin
from apps.faculty.models import Faculty
from apps.academics.models import (
    AcademicYear,
    Standard,
    Division,
    Subject,
    ClassCurriculum,
    ClassTeacherAllocation,
    SubjectTeacherAllocation,
)
from apps.academics.forms import (
    AcademicYearForm,
    StandardForm,
    DivisionForm,
    SubjectForm,
    ClassCurriculumForm,
)
from apps.academics.services import AcademicService


class AcademicHubView(SchoolAdminRequiredMixin, TemplateView):
    """
    Main School Admin Academic Hub with 4 Apple-style segmented tabs:
      1. Academic Years (tab=years)
      2. Standards & Divisions (tab=classes)
      3. Subjects (tab=subjects)
      4. Teacher Allocations (tab=allocations)
    """
    template_name = 'academics/academic_hub.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.request.tenant

        # 1. Active Tab resolution (default to 'overview')
        default_tab = 'overview'
        active_tab = self.request.GET.get('tab', default_tab)
        if active_tab not in ['overview', 'years', 'classes', 'subjects', 'allocations']:
            active_tab = default_tab
        context['active_tab'] = active_tab

        # 2. Academic Years list & Session Switcher resolution
        academic_years = list(AcademicYear.objects.filter(school=tenant).order_by('-start_date'))
        context['academic_years'] = academic_years

        year_id = self.request.GET.get('year')
        selected_year = None
        if year_id:
            selected_year = AcademicYear.objects.filter(school=tenant, pk=year_id).first()
        if not selected_year:
            selected_year = AcademicService.get_current_academic_year(tenant)
        context['selected_year'] = selected_year

        # 3. Standards & Divisions
        standards = list(Standard.objects.filter(school=tenant).prefetch_related('divisions').order_by('order_index', 'name'))
        context['standards'] = standards

        # 4. Subjects (Global Subject Master)
        subjects = list(Subject.objects.filter(school=tenant).order_by('name'))
        context['subjects'] = subjects
        context['global_subjects'] = subjects

        # 5. Grade-wise Class Curriculum Matrix
        context['curriculum_matrix'] = AcademicService.get_class_curriculum_matrix(tenant, selected_year)

        # 6. Teacher Allocation Matrix
        context['allocation_matrix'] = AcademicService.get_allocation_matrix(tenant, selected_year)

        # 7. Active Faculty list for assignment modals
        context['active_faculty'] = list(Faculty.objects.filter(school=tenant, is_active=True).order_by('first_name', 'last_name'))

        # 8. Empty forms for modal rendering
        context['year_form'] = AcademicYearForm(tenant=tenant)
        context['standard_form'] = StandardForm(tenant=tenant)
        context['division_form'] = DivisionForm(tenant=tenant)
        context['subject_form'] = SubjectForm(tenant=tenant)
        context['curriculum_form'] = ClassCurriculumForm(tenant=tenant)

        # 9. KPI Card Counts
        context['total_divisions_count'] = Division.objects.filter(school=tenant).count()
        ct_count = ClassTeacherAllocation.objects.filter(school=tenant, academic_year=selected_year).count() if selected_year else 0
        st_count = SubjectTeacherAllocation.objects.filter(school=tenant, academic_year=selected_year).count() if selected_year else 0
        context['total_allocations_count'] = ct_count + st_count

        return context


# ---------------------------------------------------------------------------
# Academic Year Views
# ---------------------------------------------------------------------------

class AcademicYearCreateView(SchoolAdminRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = AcademicYearForm(request.POST, tenant=request.tenant)
        if form.is_valid():
            year = form.save(commit=False)
            year.school = request.tenant
            year.save()
            messages.success(request, f"Academic Year '{year.name}' created successfully.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
        return redirect(f"{reverse('academics:hub')}?tab=years")


class AcademicYearUpdateView(SchoolAdminRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        year = get_object_or_404(AcademicYear, pk=pk, school=request.tenant)
        form = AcademicYearForm(request.POST, instance=year, tenant=request.tenant)
        if form.is_valid():
            form.save()
            messages.success(request, f"Academic Year '{year.name}' updated successfully.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
        return redirect(f"{reverse('academics:hub')}?tab=years")


class AcademicYearSetCurrentView(SchoolAdminRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        year = get_object_or_404(AcademicYear, pk=pk, school=request.tenant)
        year.is_current = True
        year.save()
        messages.success(request, f"'{year.name}' is now set as the Active Current Session.")
        return redirect(f"{reverse('academics:hub')}?tab=years&year={year.id}")


class AcademicYearDeleteView(SchoolAdminRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        year = get_object_or_404(AcademicYear, pk=pk, school=request.tenant)
        try:
            name = year.name
            year.delete()
            messages.success(request, f"Academic Year '{name}' deleted successfully.")
        except ProtectedError:
            messages.error(request, f"Cannot delete '{year.name}' because it contains teacher allocations or student records.")
        return redirect(f"{reverse('academics:hub')}?tab=years")


# ---------------------------------------------------------------------------
# Standard Views
# ---------------------------------------------------------------------------

class StandardCreateView(SchoolAdminRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = StandardForm(request.POST, tenant=request.tenant)
        if form.is_valid():
            std = form.save(commit=False)
            std.school = request.tenant
            std.save()
            messages.success(request, f"Standard '{std.name}' created successfully.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
        return redirect(f"{reverse('academics:hub')}?tab=classes")


class StandardUpdateView(SchoolAdminRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        std = get_object_or_404(Standard, pk=pk, school=request.tenant)
        form = StandardForm(request.POST, instance=std, tenant=request.tenant)
        if form.is_valid():
            form.save()
            messages.success(request, f"Standard '{std.name}' updated successfully.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
        return redirect(f"{reverse('academics:hub')}?tab=classes")


class StandardDeleteView(SchoolAdminRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        std = get_object_or_404(Standard, pk=pk, school=request.tenant)
        try:
            name = std.name
            std.delete()
            messages.success(request, f"Standard '{name}' deleted successfully.")
        except ProtectedError:
            messages.error(request, f"Cannot delete '{std.name}' because it has active divisions or student records. You can deactivate it instead.")
        return redirect(f"{reverse('academics:hub')}?tab=classes")


# ---------------------------------------------------------------------------
# Division Views
# ---------------------------------------------------------------------------

class DivisionCreateView(SchoolAdminRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = DivisionForm(request.POST, tenant=request.tenant)
        if form.is_valid():
            div = form.save(commit=False)
            div.school = request.tenant
            div.save()
            messages.success(request, f"Division '{div.name}' added to {div.standard.name}.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
        return redirect(f"{reverse('academics:hub')}?tab=classes")


class DivisionUpdateView(SchoolAdminRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        div = get_object_or_404(Division, pk=pk, school=request.tenant)
        form = DivisionForm(request.POST, instance=div, tenant=request.tenant)
        if form.is_valid():
            form.save()
            messages.success(request, f"Division '{div.name}' updated successfully.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
        return redirect(f"{reverse('academics:hub')}?tab=classes")


class DivisionDeleteView(SchoolAdminRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        div = get_object_or_404(Division, pk=pk, school=request.tenant)
        try:
            name = str(div)
            div.delete()
            messages.success(request, f"Division '{name}' deleted successfully.")
        except ProtectedError:
            messages.error(request, f"Cannot delete '{div.name}' because it is linked to teacher allocations or student records. You can mark it inactive instead.")
        return redirect(f"{reverse('academics:hub')}?tab=classes")


# ---------------------------------------------------------------------------
# Subject Views
# ---------------------------------------------------------------------------

class SubjectCreateView(SchoolAdminRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = SubjectForm(request.POST, tenant=request.tenant)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.school = request.tenant
            sub.save()
            messages.success(request, f"Subject '{sub.name}' ({sub.code}) added successfully.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
        return redirect(f"{reverse('academics:hub')}?tab=subjects")


class SubjectUpdateView(SchoolAdminRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        sub = get_object_or_404(Subject, pk=pk, school=request.tenant)
        form = SubjectForm(request.POST, instance=sub, tenant=request.tenant)
        if form.is_valid():
            form.save()
            messages.success(request, f"Subject '{sub.name}' updated successfully.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
        return redirect(f"{reverse('academics:hub')}?tab=subjects")


class SubjectDeleteView(SchoolAdminRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        sub = get_object_or_404(Subject, pk=pk, school=request.tenant)
        try:
            name = sub.name
            sub.delete()
            messages.success(request, f"Subject '{name}' deleted successfully from Master.")
        except ProtectedError:
            messages.error(request, f"Cannot delete '{sub.name}' because it is assigned to class curriculums, teacher allocations, or student records.")
        return redirect(f"{reverse('academics:hub')}?tab=subjects")


# ---------------------------------------------------------------------------
# Curriculum Subject Assignment Views (Grade / Class-wise)
# ---------------------------------------------------------------------------

class CurriculumSubjectAssignView(SchoolAdminRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = ClassCurriculumForm(request.POST, tenant=request.tenant)
        year_id = request.POST.get('academic_year')
        if form.is_valid():
            curr = form.save(commit=False)
            curr.school = request.tenant
            curr.is_active = True
            curr.save()
            messages.success(
                request,
                f"Subject '{curr.subject.name}' added to {curr.standard.name} curriculum for {curr.academic_year.name}."
            )
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    field_label = "Curriculum" if field == '__all__' else field.replace('_', ' ').title()
                    messages.error(request, f"{field_label}: {error}")
        year_param = f"&year={year_id}" if year_id else ""
        return redirect(f"{reverse('academics:hub')}?tab=subjects{year_param}")


class CurriculumSubjectDeleteView(SchoolAdminRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        curr = get_object_or_404(ClassCurriculum, pk=pk, school=request.tenant)
        year_id = curr.academic_year_id
        std_name = curr.standard.name
        sub_name = curr.subject.name

        # Prevent removal if active teacher allocations exist for this grade + subject in this year
        alloc_exists = SubjectTeacherAllocation.objects.filter(
            school=request.tenant,
            academic_year=curr.academic_year,
            division__standard=curr.standard,
            subject=curr.subject,
        ).exists()
        if alloc_exists:
            messages.warning(
                request,
                f"Cannot remove '{sub_name}' from {std_name} curriculum because active teacher assignments exist in this academic year. Please remove the teacher assignments first."
            )
        else:
            curr.delete()
            messages.success(request, f"Removed '{sub_name}' from {std_name} curriculum.")

        year_param = f"&year={year_id}" if year_id else ""
        return redirect(f"{reverse('academics:hub')}?tab=subjects{year_param}")


# ---------------------------------------------------------------------------
# Teacher Allocation Views
# ---------------------------------------------------------------------------

class ClassTeacherAssignView(SchoolAdminRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        year_id = request.POST.get('academic_year')
        division_id = request.POST.get('division')
        faculty_id = request.POST.get('faculty')

        year = get_object_or_404(AcademicYear, pk=year_id, school=request.tenant)
        division = get_object_or_404(Division, pk=division_id, school=request.tenant)
        faculty = get_object_or_404(Faculty, pk=faculty_id, school=request.tenant, is_active=True)

        alloc, created = AcademicService.assign_class_teacher(
            school=request.tenant,
            academic_year=year,
            division=division,
            faculty=faculty,
        )
        action_word = "assigned" if created else "reassigned"
        messages.success(request, f"{faculty.full_name} {action_word} as Class Teacher for {division}.")
        return redirect(f"{reverse('academics:hub')}?tab=allocations&year={year.id}")


class SubjectTeacherAssignView(SchoolAdminRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        year_id = request.POST.get('academic_year')
        division_id = request.POST.get('division')
        subject_id = request.POST.get('subject')
        faculty_id = request.POST.get('faculty')

        year = get_object_or_404(AcademicYear, pk=year_id, school=request.tenant)
        division = get_object_or_404(Division, pk=division_id, school=request.tenant)
        subject = get_object_or_404(Subject, pk=subject_id, school=request.tenant, is_active=True)
        faculty = get_object_or_404(Faculty, pk=faculty_id, school=request.tenant, is_active=True)

        alloc, created = AcademicService.assign_subject_teacher(
            school=request.tenant,
            academic_year=year,
            division=division,
            subject=subject,
            faculty=faculty,
        )
        if created:
            messages.success(request, f"{faculty.full_name} assigned to teach {subject.name} in {division}.")
        else:
            messages.info(request, f"{faculty.full_name} is already assigned to teach {subject.name} in {division}.")
        return redirect(f"{reverse('academics:hub')}?tab=allocations&year={year.id}")


class SubjectTeacherUpdateView(SchoolAdminRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        alloc = get_object_or_404(SubjectTeacherAllocation, pk=pk, school=request.tenant)
        new_faculty_id = request.POST.get('faculty')
        new_faculty = get_object_or_404(Faculty, pk=new_faculty_id, school=request.tenant, is_active=True)

        if SubjectTeacherAllocation.objects.filter(
            school=request.tenant,
            academic_year=alloc.academic_year,
            division=alloc.division,
            subject=alloc.subject,
            faculty=new_faculty,
        ).exclude(pk=alloc.pk).exists():
            messages.warning(request, f"{new_faculty.full_name} is already assigned to {alloc.subject.name} in {alloc.division}.")
        else:
            alloc.faculty = new_faculty
            alloc.save()
            messages.success(request, f"Updated subject teacher for {alloc.subject.name} to {new_faculty.full_name}.")

        return redirect(f"{reverse('academics:hub')}?tab=allocations&year={alloc.academic_year_id}")


class SubjectTeacherDeleteView(SchoolAdminRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        alloc = get_object_or_404(SubjectTeacherAllocation, pk=pk, school=request.tenant)
        year_id = alloc.academic_year_id
        info = f"{alloc.subject.name} in {alloc.division}"
        alloc.delete()
        messages.success(request, f"Removed subject teacher allocation for {info}.")
        return redirect(f"{reverse('academics:hub')}?tab=allocations&year={year_id}")
