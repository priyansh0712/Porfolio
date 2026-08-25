"""
Student Management Views — Role-scoped CRUD + Transfer Workflow.

Security layers:
  - SchoolStaffRequiredMixin (Layer 2): allows SCHOOL_ADMIN and FACULTY.
  - StudentRequiredMixin (Layer 2): allows only STUDENT role.
  - All queries are scoped to request.tenant (Layer 3).
"""
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.models import User
from apps.accounts.permissions import SchoolAdminRequiredMixin
from apps.academics.models import (
    AcademicYear, Standard, Division,
    ClassTeacherAllocation, SubjectTeacherAllocation,
)
from apps.academics.services import AcademicService
from apps.faculty.models import Faculty
from apps.students.forms import StudentForm, StudentTransferRequestForm, TransferRejectForm
from apps.students.models import Student, StudentTransferRequest
from apps.students.services import StudentService


# ---------------------------------------------------------------------------
# Permission Mixins
# ---------------------------------------------------------------------------

class SchoolStaffRequiredMixin:
    """
    Layer 2 guard: allows SCHOOL_ADMIN and FACULTY on the active tenant.
    Unauthenticated → redirect to login.
    Wrong role / wrong tenant → 403.
    """
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        active_tenant = getattr(request, 'tenant', None)

        if not user.is_authenticated:
            from django.conf import settings
            return redirect(settings.LOGIN_URL)

        if user.role not in (User.Role.SCHOOL_ADMIN, User.Role.FACULTY):
            return HttpResponseForbidden('Access denied: School staff authorization required.')

        if user.school_id is None or user.school != active_tenant:
            return HttpResponseForbidden('Access denied: Cross-tenant access is prohibited.')

        return super().dispatch(request, *args, **kwargs)


class StudentRequiredMixin:
    """
    Layer 2 guard: allows only STUDENT role on the active tenant.
    """
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        active_tenant = getattr(request, 'tenant', None)

        if not user.is_authenticated:
            from django.conf import settings
            return redirect(settings.LOGIN_URL)

        if user.role != User.Role.STUDENT:
            return HttpResponseForbidden('Access denied: Student portal is for students only.')

        if user.school_id is None or user.school != active_tenant:
            return HttpResponseForbidden('Access denied: Cross-tenant access is prohibited.')

        return super().dispatch(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Helper: resolve faculty's class teacher division and faculty profile
# ---------------------------------------------------------------------------

def _get_faculty_profile(user, tenant):
    """Return active Faculty model for user, or None."""
    if user.role != User.Role.FACULTY:
        return None
    try:
        return Faculty.objects.get(school=tenant, user=user, is_active=True)
    except Faculty.DoesNotExist:
        return None


def _get_class_teacher_division(user, tenant, academic_year):
    """
    Return the Division this faculty member is assigned as Class Teacher,
    or None if not a class teacher in the current year.
    """
    if user.role != User.Role.FACULTY:
        return None
    try:
        faculty = Faculty.objects.get(school=tenant, user=user, is_active=True)
        alloc = ClassTeacherAllocation.objects.select_related('division').get(
            school=tenant,
            academic_year=academic_year,
            faculty=faculty,
        )
        return alloc.division
    except (Faculty.DoesNotExist, ClassTeacherAllocation.DoesNotExist):
        return None


# ---------------------------------------------------------------------------
# Student Hub — list + CRUD for Admin / Faculty Class Teacher
# ---------------------------------------------------------------------------

class StudentHubView(SchoolStaffRequiredMixin, TemplateView):
    """
    Main Student Hub with two tabs:
      1. students — Roster with search, standard/division filter, active toggle.
      2. transfers — Pending / resolved transfer requests.

    Scoping rules:
      - School Admin: sees all students in the school (Full CRUD).
      - Class Teacher: sees only students in their assigned division (Scoped Edit).
      - Subject Teacher: sees only students in their taught divisions (Read-Only).
    """
    template_name = 'students/student_hub.html'

    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(**kwargs)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('ajax') == '1'
        if is_ajax and ctx.get('active_tab') == 'students':
            from django.shortcuts import render
            return render(request, 'students/partials/tab_students_table.html', ctx)
        return self.render_to_response(ctx)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tenant = self.request.tenant
        user = self.request.user

        # Tabs
        active_tab = self.request.GET.get('tab', 'students')
        if active_tab not in ('students', 'transfers', 'custom_fields'):
            active_tab = 'students'
        ctx['active_tab'] = active_tab

        # Current academic year
        academic_year = AcademicService.get_current_academic_year(tenant)
        ctx['academic_year'] = academic_year
        ctx['academic_years'] = AcademicYear.objects.filter(school=tenant).order_by('-start_date')

        # Role flags & scoping
        is_admin = user.role == User.Role.SCHOOL_ADMIN
        ctx['is_admin'] = is_admin

        ct_division = None
        can_edit_students = is_admin
        is_subject_teacher = False

        if not is_admin and academic_year:
            ct_division = _get_class_teacher_division(user, tenant, academic_year)
            if ct_division:
                can_edit_students = True
            else:
                is_subject_teacher = True
                can_edit_students = False

        ctx['ct_division'] = ct_division
        ctx['can_edit_students'] = can_edit_students
        ctx['is_subject_teacher'] = is_subject_teacher

        # Standards & Divisions for filters / forms
        standards = Standard.objects.filter(school=tenant).order_by('order_index', 'name')
        divisions = Division.objects.filter(school=tenant).order_by('standard__order_index', 'name')
        ctx['standards'] = standards
        ctx['divisions'] = divisions

        from apps.students.models import StudentCustomField, StudentFormFieldConfig
        from apps.students.forms import StudentForm, StudentCustomFieldForm, StudentFormFieldConfigForm
        custom_fields_qs = StudentCustomField.objects.filter(school=tenant).order_by('order_index', 'created_at')
        form_config = StudentFormFieldConfig.get_for_school(tenant)
        ctx['custom_fields'] = custom_fields_qs
        ctx['custom_field_form'] = StudentCustomFieldForm()
        ctx['active_custom_fields'] = [cf for cf in custom_fields_qs if cf.is_active]
        ctx['form_config'] = form_config
        ctx['form_config_form'] = StudentFormFieldConfigForm(instance=form_config)

        # --- Students tab ---
        if academic_year:
            qs = Student.objects.filter(
                school=tenant,
                academic_year=academic_year,
            ).select_related('standard', 'division', 'user').order_by(
                'standard__order_index', 'division__name', 'roll_number', 'full_name'
            )

            # Scoping:
            if is_admin:
                pass  # Admin sees all
            elif ct_division:
                qs = qs.filter(division=ct_division)
            else:
                # Subject Teacher: filter to taught divisions
                faculty = _get_faculty_profile(user, tenant)
                if faculty:
                    sub_div_ids = SubjectTeacherAllocation.objects.filter(
                        school=tenant,
                        academic_year=academic_year,
                        faculty=faculty,
                    ).values_list('division_id', flat=True).distinct()
                    qs = qs.filter(division_id__in=sub_div_ids)
                else:
                    qs = Student.objects.none()

            # Filters from GET params
            status_param = self.request.GET.get('status')
            inactive_param = self.request.GET.get('inactive')

            if status_param == 'inactive' or inactive_param == '1':
                qs = qs.filter(is_active=False)
                ctx['status_filter'] = 'inactive'
                ctx['show_inactive'] = True
            elif status_param == 'all':
                ctx['status_filter'] = 'all'
                ctx['show_inactive'] = False
            else:
                qs = qs.filter(is_active=True)
                ctx['status_filter'] = 'active'
                ctx['show_inactive'] = False

            std_filter = self.request.GET.get('standard')
            if std_filter and is_admin:
                qs = qs.filter(standard_id=std_filter)

            div_filter = self.request.GET.get('division')
            if div_filter and is_admin:
                qs = qs.filter(division_id=div_filter)

            search = self.request.GET.get('q', '').strip()
            if search:
                from django.db.models import Q
                qs = qs.filter(
                    Q(full_name__icontains=search) |
                    Q(gr_number__icontains=search) |
                    Q(roll_number__icontains=search)
                )
            ctx['search'] = search

            # Pagination
            from django.core.paginator import Paginator
            per_page_param = self.request.GET.get('per_page', '10')
            total_count = qs.count()

            if per_page_param == 'all':
                page_obj = qs
                is_paginated = False
            else:
                try:
                    per_page_val = int(per_page_param)
                    if per_page_val <= 0:
                        per_page_val = 10
                except (ValueError, TypeError):
                    per_page_val = 10
                paginator = Paginator(qs, per_page_val)
                page_number = self.request.GET.get('page', 1)
                page_obj = paginator.get_page(page_number)
                is_paginated = page_obj.has_other_pages()

            ctx['students'] = page_obj
            ctx['page_obj'] = page_obj
            ctx['is_paginated'] = is_paginated
            ctx['total_students_count'] = total_count
            ctx['per_page'] = per_page_param

            # --- Dynamic KPIs calculation for Student Hub ---
            kpi_total = total_count
            kpi_boys = qs.filter(gender=Student.Gender.MALE).count()
            kpi_girls = qs.filter(gender=Student.Gender.FEMALE).count()
            if kpi_total > 0:
                kpi_boys_pct = round((kpi_boys / kpi_total) * 100)
                kpi_girls_pct = round((kpi_girls / kpi_total) * 100)
            else:
                kpi_boys_pct = 0
                kpi_girls_pct = 0

            kpi_standards_count = qs.values('standard').distinct().count()
            kpi_divisions_count = qs.values('division').distinct().count()

            selected_division_obj = None
            class_teacher_name = None
            target_div_id = div_filter if div_filter else (ct_division.id if ct_division else None)
            if target_div_id:
                try:
                    selected_division_obj = Division.objects.select_related('standard').get(id=target_div_id, school=tenant)
                    ct_alloc = ClassTeacherAllocation.objects.filter(
                        school=tenant,
                        academic_year=academic_year,
                        division=selected_division_obj,
                    ).select_related('faculty__user').first()
                    if ct_alloc and ct_alloc.faculty and ct_alloc.faculty.user:
                        raw_name = ct_alloc.faculty.user.get_full_name() or ct_alloc.faculty.user.username
                        class_teacher_name = raw_name.strip().title() if raw_name else None
                except Division.DoesNotExist:
                    selected_division_obj = None

            selected_standard_obj = None
            if std_filter:
                try:
                    selected_standard_obj = Standard.objects.get(id=std_filter, school=tenant)
                except Standard.DoesNotExist:
                    selected_standard_obj = None

            ctx['kpi_total_students'] = kpi_total
            ctx['kpi_boys_count'] = kpi_boys
            ctx['kpi_girls_count'] = kpi_girls
            ctx['kpi_boys_pct'] = kpi_boys_pct
            ctx['kpi_girls_pct'] = kpi_girls_pct
            ctx['kpi_standards_count'] = kpi_standards_count
            ctx['kpi_divisions_count'] = kpi_divisions_count
            ctx['selected_division_obj'] = selected_division_obj
            ctx['selected_standard_obj'] = selected_standard_obj
            ctx['class_teacher_name'] = class_teacher_name
        else:
            ctx['students'] = Student.objects.none()
            ctx['page_obj'] = None
            ctx['is_paginated'] = False
            ctx['total_students_count'] = 0
            ctx['per_page'] = '10'
            ctx['kpi_total_students'] = 0
            ctx['kpi_boys_count'] = 0
            ctx['kpi_girls_count'] = 0
            ctx['kpi_boys_pct'] = 0
            ctx['kpi_girls_pct'] = 0
            ctx['kpi_standards_count'] = 0
            ctx['kpi_divisions_count'] = 0
            ctx['selected_division_obj'] = None
            ctx['selected_standard_obj'] = None
            ctx['class_teacher_name'] = None

        # --- Transfers tab ---
        transfer_qs = StudentTransferRequest.objects.filter(
            school=tenant,
        ).select_related('student', 'from_division', 'to_division', 'requested_by', 'reviewed_by')

        if ct_division:
            transfer_qs = transfer_qs.filter(from_division=ct_division)
        elif not is_admin:
            transfer_qs = StudentTransferRequest.objects.none()

        ctx['transfers'] = transfer_qs.order_by('-created_at')
        ctx['pending_transfer_count'] = transfer_qs.filter(
            status=StudentTransferRequest.Status.PENDING
        ).count()

        # Forms
        allow_gr = is_admin
        ctx['student_form'] = StudentForm(tenant=tenant, academic_year=academic_year,
                                          allow_gr_edit=allow_gr,
                                          locked_division=ct_division if not is_admin else None)
        ctx['transfer_form'] = StudentTransferRequestForm(tenant=tenant)
        ctx['reject_form'] = TransferRejectForm()
        return ctx


class StudentCreateView(SchoolStaffRequiredMixin, View):
    """POST: create a new student via StudentService."""

    def post(self, request):
        tenant = request.tenant
        user = request.user
        is_admin = user.role == User.Role.SCHOOL_ADMIN

        academic_year = AcademicService.get_current_academic_year(tenant)
        ct_division = None
        if not is_admin:
            if not academic_year:
                messages.error(request, 'No active academic year found.')
                return redirect('/students/')
            ct_division = _get_class_teacher_division(user, tenant, academic_year)
            if ct_division is None:
                return HttpResponseForbidden('Access denied: Subject teachers cannot add students. Only Class Teachers and School Administrators can add students.')

        form = StudentForm(
            request.POST,
            tenant=tenant,
            academic_year=academic_year,
            allow_gr_edit=is_admin,
            locked_division=ct_division if not is_admin else None,
        )

        if not form.is_valid():
            err_list = [f"{f}: {', '.join([str(e) for e in errs])}" for f, errs in form.errors.items()]
            messages.error(request, f"Please correct: {'; '.join(err_list)}")
            return redirect(request.META.get('HTTP_REFERER', '/students/'))

        data = form.cleaned_data
        try:
            # If class teacher — enforce their division regardless of form value
            division = ct_division if ct_division else data['division']
            standard = division.standard if ct_division else data['standard']

            StudentService.create_student(
                school=tenant,
                academic_year=academic_year,
                standard=standard,
                division=division,
                gr_number=data['gr_number'],
                full_name=data['full_name'],
                roll_number=data.get('roll_number'),
                dob=data.get('dob'),
                gender=data.get('gender', 'MALE'),
                blood_group=data.get('blood_group', ''),
                guardian_name=data.get('guardian_name', ''),
                guardian_phone=data.get('guardian_phone', ''),
                emergency_contact=data.get('emergency_contact', ''),
                address=data.get('address', ''),
                admission_date=data.get('admission_date'),
                custom_fields=data.get('custom_fields', {}),
            )
            messages.success(request, f"Student '{data['full_name']}' added successfully.")
        except ValueError as e:
            messages.error(request, str(e))
        return redirect('/students/')


class StudentUpdateView(SchoolStaffRequiredMixin, View):
    """POST: update an existing student."""

    def post(self, request, pk):
        tenant = request.tenant
        user = request.user
        is_admin = user.role == User.Role.SCHOOL_ADMIN

        student = get_object_or_404(Student, pk=pk, school=tenant)

        # Subject Teachers CANNOT edit students
        if not is_admin:
            academic_year = AcademicService.get_current_academic_year(tenant)
            ct_division = _get_class_teacher_division(user, tenant, academic_year)
            if ct_division is None:
                return HttpResponseForbidden('Access denied: Subject teachers have read-only access and cannot edit student profiles.')
            if student.division != ct_division:
                return HttpResponseForbidden('Access denied: Class teachers can only edit students in their assigned division.')

        form = StudentForm(
            request.POST,
            tenant=tenant,
            is_edit=True,
            allow_gr_edit=is_admin,
        )

        if not form.is_valid():
            err_list = [f"{f}: {', '.join([str(e) for e in errs])}" for f, errs in form.errors.items()]
            messages.error(request, f"Please correct: {'; '.join(err_list)}")
            return redirect('/students/')

        data = form.cleaned_data
        update_fields = {
            'full_name': data['full_name'],
            'gender': data['gender'],
            'blood_group': data.get('blood_group', ''),
            'dob': data.get('dob'),
            'guardian_name': data.get('guardian_name', ''),
            'guardian_phone': data.get('guardian_phone', ''),
            'emergency_contact': data.get('emergency_contact', ''),
            'address': data.get('address', ''),
            'roll_number': data.get('roll_number'),
        }

        # Merge custom fields
        if 'custom_fields' in data and data['custom_fields']:
            existing_custom = student.custom_fields or {}
            existing_custom.update(data['custom_fields'])
            update_fields['custom_fields'] = existing_custom

        # Admin can also update standard/division
        if is_admin:
            if data.get('standard'):
                update_fields['standard'] = data['standard']
            if data.get('division'):
                update_fields['division'] = data['division']

        try:
            StudentService.update_student(student, allow_gr_edit=is_admin, **update_fields)
            messages.success(request, f"Student '{student.full_name}' updated successfully.")
        except Exception as e:
            messages.error(request, str(e))
        return redirect('/students/')


class StudentDeleteView(SchoolStaffRequiredMixin, View):
    """POST: soft-deactivate a student (School Admin or Class Teacher for own class)."""

    def post(self, request, pk):
        tenant = request.tenant
        user = request.user
        is_admin = user.role == User.Role.SCHOOL_ADMIN
        student = get_object_or_404(Student, pk=pk, school=tenant)
        if not is_admin:
            academic_year = AcademicService.get_current_academic_year(tenant)
            ct_division = _get_class_teacher_division(user, tenant, academic_year)
            if ct_division is None or student.division != ct_division:
                return HttpResponseForbidden('Access denied: You can only deactivate students from your assigned class.')
        StudentService.soft_delete_student(student)
        messages.success(request, f"Student '{student.full_name}' has been deactivated.")
        return redirect('/students/')


class StudentRestoreView(SchoolStaffRequiredMixin, View):
    """POST: restore a soft-deleted student (School Admin or Class Teacher for own class)."""

    def post(self, request, pk):
        tenant = request.tenant
        user = request.user
        is_admin = user.role == User.Role.SCHOOL_ADMIN
        student = get_object_or_404(Student, pk=pk, school=tenant)
        if not is_admin:
            academic_year = AcademicService.get_current_academic_year(tenant)
            ct_division = _get_class_teacher_division(user, tenant, academic_year)
            if ct_division is None or student.division != ct_division:
                return HttpResponseForbidden('Access denied: You can only restore students from your assigned class.')
        StudentService.restore_student(student)
        messages.success(request, f"Student '{student.full_name}' has been restored.")
        return redirect('/students/')


class StudentHardDeleteView(SchoolAdminRequiredMixin, View):
    """POST: permanently delete a single student (School Admin only)."""

    def post(self, request, pk):
        tenant = request.tenant
        student = get_object_or_404(Student, pk=pk, school=tenant)
        name = student.full_name
        StudentService.bulk_hard_delete_students([student.pk], school=tenant)
        messages.success(request, f"Student '{name}' has been permanently deleted.")
        return redirect('/students/')


class StudentBulkDeactivateView(SchoolStaffRequiredMixin, View):
    """
    POST: Bulk soft-deactivate selected students.
    - School Admin can bulk deactivate any student in school.
    - Class Teacher can bulk deactivate only students in their assigned class.
    """

    def post(self, request):
        tenant = request.tenant
        user = request.user
        is_admin = user.role == User.Role.SCHOOL_ADMIN

        raw_items = request.POST.getlist('student_ids')
        student_ids = []
        for item in raw_items:
            for part in str(item).split(','):
                part = part.strip()
                if part.isdigit():
                    student_ids.append(int(part))

        if not student_ids:
            messages.warning(request, 'No students selected for deactivation.')
            return redirect('/students/')

        # Scoped permission check for Class Teacher
        if not is_admin:
            academic_year = AcademicService.get_current_academic_year(tenant)
            ct_division = _get_class_teacher_division(user, tenant, academic_year)
            if ct_division is None:
                return HttpResponseForbidden('Access denied: Only Class Teachers and School Administrators can deactivate students.')
            
            # Check if all student_ids belong to the class teacher's division
            valid_ids = set(Student.objects.filter(school=tenant, division=ct_division, pk__in=student_ids).values_list('pk', flat=True))
            if len(valid_ids) != len(student_ids):
                return HttpResponseForbidden('Access denied: You can only deactivate students from your assigned class.')

        count = StudentService.bulk_soft_delete_students(student_ids, school=tenant)
        messages.success(request, f"Successfully deactivated {count} student{'s' if count != 1 else ''}.")
        return redirect('/students/')


class StudentBulkDeleteView(SchoolAdminRequiredMixin, View):
    """
    POST: Permanently delete selected students and their accounts.
    Strictly School Admin only.
    """

    def post(self, request):
        tenant = request.tenant

        raw_items = request.POST.getlist('student_ids')
        student_ids = []
        for item in raw_items:
            for part in str(item).split(','):
                part = part.strip()
                if part.isdigit():
                    student_ids.append(int(part))

        if not student_ids:
            messages.warning(request, 'No students selected for permanent deletion.')
            return redirect('/students/')

        count = StudentService.bulk_hard_delete_students(student_ids, school=tenant)
        messages.success(request, f"Permanently deleted {count} student{'s' if count != 1 else ''}.")
        return redirect('/students/')


class StudentBulkRestoreView(SchoolStaffRequiredMixin, View):
    """
    POST: Bulk reactivate / restore soft-deleted students.
    - School Admin can bulk restore any student in school.
    - Class Teacher can bulk restore only students in their assigned class.
    """

    def post(self, request):
        tenant = request.tenant
        user = request.user
        is_admin = user.role == User.Role.SCHOOL_ADMIN

        raw_items = request.POST.getlist('student_ids')
        student_ids = []
        for item in raw_items:
            for part in str(item).split(','):
                part = part.strip()
                if part.isdigit():
                    student_ids.append(int(part))

        if not student_ids:
            messages.warning(request, 'No students selected for reactivation.')
            return redirect('/students/?status=inactive')

        # Scoped permission check for Class Teacher
        if not is_admin:
            academic_year = AcademicService.get_current_academic_year(tenant)
            ct_division = _get_class_teacher_division(user, tenant, academic_year)
            if ct_division is None:
                return HttpResponseForbidden('Access denied: Only Class Teachers and School Administrators can activate students.')

            valid_ids = set(Student.objects.filter(school=tenant, division=ct_division, pk__in=student_ids).values_list('pk', flat=True))
            if len(valid_ids) != len(student_ids):
                return HttpResponseForbidden('Access denied: You can only activate students from your assigned class.')

        count = StudentService.bulk_restore_students(student_ids, school=tenant)
        messages.success(request, f"Successfully activated {count} student{'s' if count != 1 else ''}.")
        return redirect('/students/?status=active')


# ---------------------------------------------------------------------------
# Transfer Request Views
# ---------------------------------------------------------------------------

class TransferRequestCreateView(SchoolStaffRequiredMixin, View):
    """POST: Class Teacher requests a student transfer."""

    def post(self, request, pk):
        tenant = request.tenant
        user = request.user
        is_admin = user.role == User.Role.SCHOOL_ADMIN
        student = get_object_or_404(Student, pk=pk, school=tenant, is_active=True)

        if not is_admin:
            academic_year = AcademicService.get_current_academic_year(tenant)
            ct_division = _get_class_teacher_division(user, tenant, academic_year)
            if ct_division is None:
                return HttpResponseForbidden('Access denied: Subject teachers cannot request student transfers. Only Class Teachers can request transfers.')
            if student.division != ct_division:
                return HttpResponseForbidden('Access denied: You can only transfer students from your assigned class.')

        form = StudentTransferRequestForm(request.POST, tenant=tenant)
        if not form.is_valid():
            messages.error(request, 'Invalid transfer request.')
            return redirect('/students/?tab=transfers')

        data = form.cleaned_data
        try:
            faculty = Faculty.objects.get(school=tenant, user=user, is_active=True)
        except Faculty.DoesNotExist:
            messages.error(request, 'Your faculty profile was not found.')
            return redirect('/students/?tab=transfers')

        try:
            StudentService.request_transfer(
                student=student,
                to_standard=data['to_standard'],
                to_division=data['to_division'],
                requested_by=faculty,
                reason=data.get('reason', ''),
            )
            messages.success(request, 'Transfer request submitted successfully.')
        except ValueError as e:
            messages.error(request, str(e))
        return redirect('/students/?tab=transfers')


class TransferApproveView(SchoolAdminRequiredMixin, View):
    """POST: School Admin approves a transfer request."""

    def post(self, request, pk):
        tenant = request.tenant
        tr = get_object_or_404(StudentTransferRequest, pk=pk, school=tenant)
        try:
            StudentService.approve_transfer(tr, reviewed_by=request.user)
            messages.success(request, f"Transfer for '{tr.student.full_name}' approved.")
        except Exception as e:
            messages.error(request, str(e))
        return redirect('/students/?tab=transfers')


class TransferRejectView(SchoolAdminRequiredMixin, View):
    """POST: School Admin rejects a transfer request."""

    def post(self, request, pk):
        tenant = request.tenant
        tr = get_object_or_404(StudentTransferRequest, pk=pk, school=tenant)
        form = TransferRejectForm(request.POST)
        reason = form.cleaned_data.get('rejection_reason', '') if form.is_valid() else ''
        try:
            StudentService.reject_transfer(tr, reviewed_by=request.user, rejection_reason=reason)
            messages.success(request, f"Transfer for '{tr.student.full_name}' rejected.")
        except Exception as e:
            messages.error(request, str(e))
        return redirect('/students/?tab=transfers')


# ---------------------------------------------------------------------------
# AJAX: divisions for a standard (for form dropdowns)
# ---------------------------------------------------------------------------

class DivisionsForStandardView(SchoolStaffRequiredMixin, View):
    """GET /students/api/divisions/?standard=<id> — returns JSON list of divisions."""

    def get(self, request):
        tenant = request.tenant
        standard_id = request.GET.get('standard')
        divisions = Division.objects.filter(
            school=tenant, standard_id=standard_id
        ).order_by('name').values('id', 'name')
        return JsonResponse({'divisions': list(divisions)})


# ---------------------------------------------------------------------------
# Student Portal — read-only student dashboard
# ---------------------------------------------------------------------------

class StudentPortalView(StudentRequiredMixin, TemplateView):
    """
    Read-only personal dashboard for authenticated students.

    Shows:
      - Personal info card (GR No, Name, DOB, Blood Group, Guardian)
      - Academic placement (Year, Standard, Division, Roll No)
      - Class Teacher card
      - Subject + Subject Teacher grid
    """
    template_name = 'students/student_portal.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        tenant = self.request.tenant

        try:
            student = Student.objects.select_related(
                'school', 'academic_year', 'standard', 'division'
            ).get(user=user, school=tenant, is_active=True)
        except Student.DoesNotExist:
            ctx['student'] = None
            return ctx

        ctx['student'] = student

        # Class Teacher for the student's division
        try:
            ct_alloc = ClassTeacherAllocation.objects.select_related('faculty').get(
                school=tenant,
                academic_year=student.academic_year,
                division=student.division,
            )
            ctx['class_teacher'] = ct_alloc.faculty
        except ClassTeacherAllocation.DoesNotExist:
            ctx['class_teacher'] = None

        return ctx


# ---------------------------------------------------------------------------
# Custom Field Management Views (School Admin Only)
# ---------------------------------------------------------------------------

class CustomFieldCreateView(SchoolAdminRequiredMixin, View):
    """POST: School Admin creates a new custom field definition."""

    def post(self, request):
        tenant = request.tenant
        from apps.students.forms import StudentCustomFieldForm
        form = StudentCustomFieldForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                StudentService.create_custom_field(
                    school=tenant,
                    label=data['label'],
                    field_type=data['field_type'],
                    options=data.get('options', ''),
                    is_required=data.get('is_required', False),
                )
                messages.success(request, f"Custom field '{data['label']}' added successfully.")
            except Exception as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Please check form errors.')
        return redirect('/students/?tab=custom_fields')


class CustomFieldToggleView(SchoolAdminRequiredMixin, View):
    """POST: Toggle active/inactive status of a custom field."""

    def post(self, request, pk):
        tenant = request.tenant
        from apps.students.models import StudentCustomField
        cf = get_object_or_404(StudentCustomField, pk=pk, school=tenant)
        StudentService.toggle_custom_field(cf)
        status_text = 'activated' if cf.is_active else 'deactivated'
        messages.success(request, f"Field '{cf.label}' has been {status_text}.")
        return redirect('/students/?tab=custom_fields')


class CustomFieldUpdateView(SchoolAdminRequiredMixin, View):
    """POST: School Admin edits an existing custom field definition."""

    def post(self, request, pk):
        tenant = request.tenant
        from apps.students.models import StudentCustomField
        cf = get_object_or_404(StudentCustomField, pk=pk, school=tenant)
        label = request.POST.get('label', '').strip()
        field_type = request.POST.get('field_type', '').strip()
        options = request.POST.get('options', '').strip()
        is_required = request.POST.get('is_required') in ('1', 'true', 'on', True)

        if not label:
            messages.error(request, 'Field label cannot be empty.')
            return redirect('/students/?tab=custom_fields')

        valid_types = [choice[0] for choice in StudentCustomField.FieldType.choices]
        if field_type and field_type not in valid_types:
            field_type = cf.field_type

        StudentService.update_custom_field(
            cf,
            label=label,
            field_type=field_type or cf.field_type,
            options=options,
            is_required=is_required,
        )
        messages.success(request, f"Custom field '{cf.label}' updated successfully.")
        return redirect('/students/?tab=custom_fields')


class CustomFieldDeleteView(SchoolAdminRequiredMixin, View):
    """POST: Delete a custom field definition."""

    def post(self, request, pk):
        tenant = request.tenant
        from apps.students.models import StudentCustomField
        cf = get_object_or_404(StudentCustomField, pk=pk, school=tenant)
        label = cf.label
        StudentService.delete_custom_field(cf)
        messages.success(request, f"Custom field '{label}' has been deleted.")
        return redirect('/students/?tab=custom_fields')


class StudentFormFieldConfigUpdateView(SchoolAdminRequiredMixin, View):
    """POST: Update school's student form field visibility and requirement settings."""

    def post(self, request):
        tenant = request.tenant
        from apps.students.models import StudentFormFieldConfig
        from apps.students.forms import StudentFormFieldConfigForm

        config = StudentFormFieldConfig.get_for_school(tenant)
        form = StudentFormFieldConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student form field settings updated successfully.')
        else:
            messages.error(request, 'Failed to update form field settings. Please check values.')
        return redirect('/students/?tab=custom_fields')


