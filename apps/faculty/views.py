"""
Faculty Management Views — 3-Layer Security Architecture.

Layer 1: TenantMiddleware (request.tenant)
Layer 2: SchoolAdminRequiredMixin (role-based access)
Layer 3: Queryset scoping (school=request.tenant)
"""
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView

from django.contrib.auth.mixins import LoginRequiredMixin
from apps.accounts.permissions import SchoolAdminRequiredMixin
from apps.academics.models import AcademicYear, ClassTeacherAllocation, SubjectTeacherAllocation
from apps.faculty.forms import FacultyForm
from apps.faculty.models import Faculty
from apps.faculty.services import FacultyService
from apps.students.models import Student


class MyClassView(LoginRequiredMixin, ListView):
    """
    Dedicated dashboard for Class Teachers displaying assigned division details,
    student roster, quick-add student modal, live search, and scoped student profile edit.
    """
    model = Student
    template_name = 'faculty/my_class.html'
    context_object_name = 'students'
    paginate_by = 10

    def get_paginate_by(self, queryset):
        per_page = self.request.GET.get('per_page', '10')
        if per_page == 'all':
            return queryset.count() or 1
        try:
            val = int(per_page)
            return val if val > 0 else 10
        except (ValueError, TypeError):
            return 10

    def get_queryset(self):
        faculty = getattr(self.request.user, 'faculty_profile', None)
        if not faculty:
            return Student.objects.none()

        curr_ay = AcademicYear.objects.filter(school=self.request.tenant, is_current=True).first()
        if not curr_ay:
            return Student.objects.none()

        allocation = ClassTeacherAllocation.objects.filter(
            school=self.request.tenant,
            academic_year=curr_ay,
            faculty=faculty
        ).select_related('division', 'division__standard').first()

        if not allocation:
            return Student.objects.none()

        qs = Student.objects.filter(
            school=self.request.tenant,
            academic_year=curr_ay,
            division=allocation.division,
        ).select_related('standard', 'division', 'user').order_by('roll_number', 'full_name')

        status_filter = self.request.GET.get('status', 'active')
        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

        q = self.request.GET.get('q', '').strip()
        if q:
            from django.db.models import Q
            qs = qs.filter(
                Q(full_name__icontains=q) |
                Q(gr_number__icontains=q) |
                Q(roll_number__icontains=q) |
                Q(guardian_phone__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.request.tenant
        faculty = getattr(self.request.user, 'faculty_profile', None)
        curr_ay = AcademicYear.objects.filter(school=tenant, is_current=True).first()
        allocation = ClassTeacherAllocation.objects.filter(
            school=tenant,
            academic_year=curr_ay,
            faculty=faculty
        ).select_related('division', 'division__standard').first() if (faculty and curr_ay) else None

        from apps.students.models import StudentCustomField, StudentFormFieldConfig
        from apps.academics.models import Standard, Division
        custom_fields_qs = StudentCustomField.objects.filter(school=tenant).order_by('order_index', 'created_at')
        form_config = StudentFormFieldConfig.get_for_school(tenant)

        context['allocation'] = allocation
        context['academic_year'] = curr_ay
        context['total_students'] = Student.objects.filter(
            school=tenant,
            academic_year=curr_ay,
            division=allocation.division,
            is_active=True
        ).count() if allocation else 0
        context['search'] = self.request.GET.get('q', '')
        context['per_page'] = self.request.GET.get('per_page', '10')
        context['status_filter'] = self.request.GET.get('status', 'active')
        context['can_edit_students'] = True  # Class teacher can edit students in their class
        context['is_admin'] = False
        context['ct_division'] = allocation.division if allocation else None
        context['standards'] = Standard.objects.filter(school=tenant).order_by('order_index', 'name')
        context['divisions'] = Division.objects.filter(school=tenant).order_by('standard__order_index', 'name')
        context['custom_fields'] = custom_fields_qs
        context['active_custom_fields'] = [cf for cf in custom_fields_qs if cf.is_active]
        context['form_config'] = form_config

        return context


class MySubjectsView(LoginRequiredMixin, ListView):
    """
    Subject Teacher view showing assigned classes, subjects taught, and read-only student rosters.
    """
    model = SubjectTeacherAllocation
    template_name = 'faculty/my_subjects.html'
    context_object_name = 'allocations'

    def get_queryset(self):
        faculty = getattr(self.request.user, 'faculty_profile', None)
        if not faculty:
            return SubjectTeacherAllocation.objects.none()

        curr_ay = AcademicYear.objects.filter(school=self.request.tenant, is_current=True).first()
        return SubjectTeacherAllocation.objects.filter(
            school=self.request.tenant,
            academic_year=curr_ay,
            faculty=faculty
        ).select_related('division', 'division__standard', 'subject').order_by('division__standard__order_index', 'division__name', 'subject__name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.request.tenant
        curr_ay = AcademicYear.objects.filter(school=tenant, is_current=True).first()
        context['academic_year'] = curr_ay

        allocations = list(self.get_queryset())
        
        # Calculate student count for each allocation for selector tabs
        allocations_list = []
        for alloc in allocations:
            count = Student.objects.filter(
                school=tenant,
                academic_year=curr_ay,
                division=alloc.division,
                is_active=True
            ).count()
            allocations_list.append({
                'allocation': alloc,
                'count': count,
            })
        context['allocations_list'] = allocations_list

        # Determine active / selected allocation
        selected_alloc_id = self.request.GET.get('subject')
        selected_item = None
        if selected_alloc_id:
            for item in allocations_list:
                if str(item['allocation'].pk) == str(selected_alloc_id):
                    selected_item = item
                    break

        if not selected_item and allocations_list:
            selected_item = allocations_list[0]

        context['selected_item'] = selected_item

        # Paginate student roster for the selected subject/class
        from django.core.paginator import Paginator
        per_page_param = self.request.GET.get('per_page', '10')
        try:
            per_page_val = int(per_page_param) if per_page_param != 'all' else 9999
        except (ValueError, TypeError):
            per_page_val = 10

        search_q = self.request.GET.get('q', '').strip()
        context['search'] = search_q
        context['per_page'] = per_page_param

        if selected_item:
            alloc = selected_item['allocation']
            roster_qs = Student.objects.filter(
                school=tenant,
                academic_year=curr_ay,
                division=alloc.division,
                is_active=True
            ).order_by('roll_number', 'full_name')

            if search_q:
                from django.db.models import Q
                roster_qs = roster_qs.filter(
                    Q(full_name__icontains=search_q) |
                    Q(gr_number__icontains=search_q) |
                    Q(roll_number__icontains=search_q) |
                    Q(guardian_phone__icontains=search_q)
                )

            total_count = roster_qs.count()
            paginator = Paginator(roster_qs, per_page_val if per_page_val > 0 else 10)
            page_num = self.request.GET.get('page', 1)
            page_obj = paginator.get_page(page_num)

            context['students'] = page_obj
            context['page_obj'] = page_obj
            context['total_count'] = total_count
        else:
            context['students'] = []
            context['page_obj'] = None
            context['total_count'] = 0

        # Backwards-compatibility for existing tests/templates
        context['subject_rosters'] = [
            {
                'allocation': selected_item['allocation'],
                'students': context['students'],
                'page_obj': context['page_obj'],
                'count': selected_item['count'],
            }
        ] if selected_item else []

        return context


class FacultyListView(SchoolAdminRequiredMixin, ListView):
    """
    Faculty directory with tenant-scoped queryset.
    Passes department list and form for the modal drawer.
    """
    model = Faculty
    template_name = 'faculty/faculty_list.html'
    context_object_name = 'faculty_list'
    paginate_by = 10

    def get_paginate_by(self, queryset):
        per_page = self.request.GET.get('per_page', '10')
        if per_page == 'all':
            return queryset.count() or 1
        try:
            val = int(per_page)
            return val if val > 0 else 10
        except (ValueError, TypeError):
            return 10

    def get_queryset(self):
        """Layer 3: Scope to current tenant with optional filtering."""
        qs = Faculty.objects.filter(school=self.request.tenant)
        q = self.request.GET.get('q', '').strip()
        dept = self.request.GET.get('department', '').strip()
        status = self.request.GET.get('status', '').strip()

        if q:
            from django.db.models import Q
            qs = qs.filter(
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(email__icontains=q) |
                Q(employee_code__icontains=q)
            )
        if dept:
            qs = qs.filter(department=dept)
        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)

        return qs.order_by('first_name', 'last_name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        all_qs = Faculty.objects.filter(school=self.request.tenant)
        ctx['departments'] = sorted(
            all_qs.values_list('department', flat=True).distinct()
        )
        ctx['total_count'] = all_qs.count()
        ctx['active_count'] = all_qs.filter(is_active=True).count()
        ctx['inactive_count'] = all_qs.filter(is_active=False).count()
        ctx['form'] = FacultyForm(tenant=self.request.tenant)
        ctx['per_page'] = self.request.GET.get('per_page', '10')
        ctx['q'] = self.request.GET.get('q', '')
        ctx['selected_dept'] = self.request.GET.get('department', '')
        ctx['status_filter'] = self.request.GET.get('status', 'all')

        # Custom Fields Context
        from apps.faculty.models import FacultyCustomField, FacultyFormFieldConfig
        from apps.faculty.forms import FacultyCustomFieldForm, FacultyFormFieldConfigForm
        form_config = FacultyFormFieldConfig.get_for_school(self.request.tenant)
        custom_fields_qs = FacultyCustomField.objects.filter(school=self.request.tenant).order_by('order_index', 'created_at')
        ctx['form_config'] = form_config
        ctx['form_config_form'] = FacultyFormFieldConfigForm(instance=form_config)
        ctx['custom_fields'] = custom_fields_qs
        ctx['custom_field_form'] = FacultyCustomFieldForm()
        ctx['active_custom_fields'] = [cf for cf in custom_fields_qs if cf.is_active]
        ctx['active_tab'] = self.request.GET.get('tab', 'faculty')
        return ctx


class FacultyCreateView(SchoolAdminRequiredMixin, CreateView):
    """
    Handles both modal AJAX and standard POST faculty creation.
    Delegates to FacultyService for atomic User + Faculty creation.
    """
    model = Faculty
    form_class = FacultyForm
    template_name = 'faculty/faculty_list.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        try:
            faculty = FacultyService.create_faculty(
                school=self.request.tenant,
                data=form.cleaned_data,
            )
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'{faculty.full_name} added successfully.',
                    'faculty': {
                        'id': faculty.pk,
                        'full_name': faculty.full_name,
                        'email': faculty.email,
                        'employee_code': faculty.employee_code,
                        'department': faculty.department,
                        'designation': faculty.designation,
                        'is_active': faculty.is_active,
                        'is_face_enrolled': faculty.is_face_enrolled,
                    },
                })
            messages.success(
                self.request,
                f'{faculty.full_name} has been added as faculty.'
            )
            return redirect('faculty:list')
        except Exception as e:
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
            messages.error(self.request, f'Error creating faculty: {e}')
            return redirect('faculty:list')

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors,
            }, status=400)
        messages.error(self.request, 'Please correct the errors below.')
        return redirect('faculty:list')


class FacultyUpdateView(SchoolAdminRequiredMixin, UpdateView):
    """
    Handles faculty edit via modal/AJAX.
    Layer 3: queryset scoped to tenant.
    """
    model = Faculty
    form_class = FacultyForm
    template_name = 'faculty/faculty_list.html'

    def get_queryset(self):
        """Layer 3: Only allow editing within own tenant."""
        return Faculty.objects.filter(school=self.request.tenant)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        try:
            faculty = FacultyService.update_faculty(
                faculty=self.get_object(),
                data=form.cleaned_data,
            )
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'{faculty.full_name} updated successfully.',
                })
            messages.success(self.request, f'{faculty.full_name} updated.')
            return redirect('faculty:list')
        except Exception as e:
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
            messages.error(self.request, f'Error updating faculty: {e}')
            return redirect('faculty:list')

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors,
            }, status=400)
        messages.error(self.request, 'Please correct the errors below.')
        return redirect('faculty:list')


class FacultyToggleStatusView(SchoolAdminRequiredMixin, View):
    """POST-only: Toggle faculty active/inactive status. Tenant-scoped."""

    def post(self, request, pk):
        faculty = get_object_or_404(
            Faculty, pk=pk, school=request.tenant
        )
        faculty = FacultyService.toggle_status(faculty)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'is_active': faculty.is_active,
                'message': (
                    f'{faculty.full_name} has been '
                    f'{"activated" if faculty.is_active else "deactivated"}.'
                ),
            })
        status_str = 'activated' if faculty.is_active else 'deactivated'
        messages.success(request, f'{faculty.full_name} has been {status_str}.')
        return redirect('faculty:list')


class FacultyDetailAPIView(SchoolAdminRequiredMixin, View):
    """GET-only: Returns faculty details as JSON for edit/view modal."""

    def get(self, request, pk):
        faculty = get_object_or_404(
            Faculty, pk=pk, school=request.tenant
        )
        return JsonResponse({
            'id': faculty.pk,
            'first_name': faculty.first_name,
            'last_name': faculty.last_name,
            'full_name': faculty.full_name,
            'email': faculty.email,
            'phone_number': faculty.phone_number,
            'employee_code': faculty.employee_code,
            'department': faculty.department,
            'designation': faculty.designation,
            'is_active': faculty.is_active,
            'is_face_enrolled': faculty.is_face_enrolled,
            'date_joined': faculty.date_joined.strftime('%B %d, %Y') if faculty.date_joined else '—',
            'custom_fields': faculty.custom_fields or {},
        })


class FacultyDeleteView(SchoolAdminRequiredMixin, View):
    """POST-only: Safely deletes a faculty member and linked user account."""

    def post(self, request, pk):
        faculty = get_object_or_404(
            Faculty, pk=pk, school=request.tenant
        )
        name = faculty.full_name
        user = faculty.user

        # Delete faculty and linked user
        faculty.delete()
        if user:
            user.delete()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'{name} has been removed from faculty directory.',
            })
        messages.success(request, f'{name} has been deleted.')
        return redirect('faculty:list')


class FacultyExportCSVView(SchoolAdminRequiredMixin, View):
    """GET: Exports tenant's faculty directory to a CSV file."""

    def get(self, request):
        from django.http import HttpResponse
        import csv

        filename = f"{request.tenant.subdomain}_faculty_directory.csv"
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow([
            'employee_code', 'first_name', 'last_name', 'email',
            'phone_number', 'department', 'designation', 'date_joined',
            'is_active', 'is_face_enrolled',
        ])

        qs = Faculty.objects.filter(school=request.tenant).order_by('first_name', 'last_name')
        for f in qs:
            writer.writerow([
                f.employee_code,
                f.first_name,
                f.last_name,
                f.email,
                f.phone_number,
                f.department,
                f.designation,
                f.date_joined.strftime('%Y-%m-%d') if f.date_joined else '',
                'Active' if f.is_active else 'Inactive',
                'Enrolled' if f.is_face_enrolled else 'Pending',
            ])

        return response


class FacultyBulkImportView(SchoolAdminRequiredMixin, View):
    """POST: Handles CSV bulk upload for faculty creation."""

    def post(self, request):
        if 'csv_file' not in request.FILES:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'No CSV file uploaded.'}, status=400)
            messages.error(request, 'Please select a CSV file to upload.')
            return redirect('faculty:list')

        csv_file = request.FILES['csv_file']
        if not csv_file.name.endswith('.csv'):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'File must be a .csv file.'}, status=400)
            messages.error(request, 'Uploaded file must be a .csv file.')
            return redirect('faculty:list')

        result = FacultyService.import_from_csv(request.tenant, csv_file)

        msg = f"Bulk import complete: {result['success_count']} added, {result['skipped_count']} skipped."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': msg,
                'details': result,
            })

        if result['success_count'] > 0:
            messages.success(request, msg)
        if result['errors']:
            for err in result['errors'][:5]:  # Show first 5 errors
                messages.warning(request, err)

        return redirect('faculty:list')


class FacultySampleCSVView(SchoolAdminRequiredMixin, View):
    """GET: Downloads sample CSV file for bulk faculty upload."""

    def get(self, request):
        from django.http import HttpResponse
        import csv
        from apps.faculty.models import FacultyCustomField

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sample_faculty_import.csv"'

        writer = csv.writer(response)
        headers = ['first_name', 'last_name', 'email', 'department', 'designation', 'phone_number', 'employee_code']
        sample_row1 = ['Rajesh', 'Sharma', 'rajesh.sharma@school.edu', 'Science', 'Senior Teacher', '+919876543210', '']
        sample_row2 = ['Priya', 'Patel', 'priya.patel@school.edu', 'Mathematics', '', '+919876543211', '']

        custom_fields = list(FacultyCustomField.objects.filter(school=request.tenant, is_active=True).order_by('order_index', 'created_at'))
        for cf in custom_fields:
            headers.append(cf.label)
            sample_row1.append(f"Sample {cf.label}")
            sample_row2.append(f"Sample {cf.label}")

        writer.writerow(headers)
        writer.writerow(sample_row1)
        writer.writerow(sample_row2)
        return response


class FacultyCustomFieldCreateView(SchoolAdminRequiredMixin, View):
    """POST: Create a new dynamic custom field definition for Faculty."""
    def post(self, request):
        from apps.faculty.forms import FacultyCustomFieldForm
        form = FacultyCustomFieldForm(request.POST)
        if form.is_valid():
            FacultyService.create_custom_field(
                school=request.tenant,
                label=form.cleaned_data['label'],
                field_type=form.cleaned_data['field_type'],
                options=form.cleaned_data.get('options', ''),
                is_required=form.cleaned_data.get('is_required', False)
            )
            messages.success(request, 'Faculty custom field created successfully.')
        else:
            messages.error(request, 'Failed to create custom field. Please check errors.')
        return redirect('/faculty/?tab=custom_fields')


class FacultyCustomFieldUpdateView(SchoolAdminRequiredMixin, View):
    """POST: Update an existing Faculty custom field definition."""
    def post(self, request, pk):
        from apps.faculty.models import FacultyCustomField
        from apps.faculty.forms import FacultyCustomFieldForm
        cf = get_object_or_404(FacultyCustomField, pk=pk, school=request.tenant)
        form = FacultyCustomFieldForm(request.POST, instance=cf)
        if form.is_valid():
            FacultyService.update_custom_field(
                custom_field=cf,
                label=form.cleaned_data['label'],
                field_type=form.cleaned_data['field_type'],
                options=form.cleaned_data.get('options', ''),
                is_required=form.cleaned_data.get('is_required', False)
            )
            messages.success(request, f'Custom field "{cf.label}" updated.')
        else:
            messages.error(request, 'Failed to update custom field.')
        return redirect('/faculty/?tab=custom_fields')


class FacultyCustomFieldToggleView(SchoolAdminRequiredMixin, View):
    """POST: Toggle active status of a Faculty custom field."""
    def post(self, request, pk):
        from apps.faculty.models import FacultyCustomField
        cf = get_object_or_404(FacultyCustomField, pk=pk, school=request.tenant)
        FacultyService.toggle_custom_field(cf)
        status_str = 'activated' if cf.is_active else 'deactivated'
        messages.success(request, f'Custom field "{cf.label}" {status_str}.')
        return redirect('/faculty/?tab=custom_fields')


class FacultyCustomFieldDeleteView(SchoolAdminRequiredMixin, View):
    """POST: Delete a Faculty custom field definition."""
    def post(self, request, pk):
        from apps.faculty.models import FacultyCustomField
        cf = get_object_or_404(FacultyCustomField, pk=pk, school=request.tenant)
        name = cf.label
        FacultyService.delete_custom_field(cf)
        messages.success(request, f'Custom field "{name}" deleted.')
        return redirect('/faculty/?tab=custom_fields')


class FacultyFormFieldConfigUpdateView(SchoolAdminRequiredMixin, View):
    """POST: Updates standard form field configuration (visibility & requirement)."""

    def post(self, request):
        from apps.faculty.models import FacultyFormFieldConfig
        from apps.faculty.forms import FacultyFormFieldConfigForm
        config = FacultyFormFieldConfig.get_for_school(request.tenant)
        form = FacultyFormFieldConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Faculty form field settings updated successfully.')
        else:
            messages.error(request, 'Failed to update form field settings.')
        return redirect('/faculty/?tab=custom_fields')

