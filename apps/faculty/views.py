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

from apps.accounts.permissions import SchoolAdminRequiredMixin
from apps.faculty.forms import FacultyForm
from apps.faculty.models import Faculty
from apps.faculty.services import FacultyService


class FacultyListView(SchoolAdminRequiredMixin, ListView):
    """
    Faculty directory with tenant-scoped queryset.
    Passes department list and form for the modal drawer.
    """
    model = Faculty
    template_name = 'faculty/faculty_list.html'
    context_object_name = 'faculty_list'

    def get_queryset(self):
        """Layer 3: Scope to current tenant."""
        return Faculty.objects.filter(school=self.request.tenant)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        ctx['departments'] = sorted(
            qs.values_list('department', flat=True).distinct()
        )
        ctx['total_count'] = qs.count()
        ctx['active_count'] = qs.filter(is_active=True).count()
        ctx['inactive_count'] = qs.filter(is_active=False).count()
        ctx['form'] = FacultyForm(tenant=self.request.tenant)
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
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sample_faculty_import.csv"'

        import csv
        writer = csv.writer(response)
        writer.writerow(['first_name', 'last_name', 'email', 'department', 'designation', 'phone_number', 'employee_code'])
        writer.writerow(['Rajesh', 'Sharma', 'rajesh.sharma@school.edu', 'Science', 'Senior Teacher', '+919876543210', ''])
        writer.writerow(['Priya', 'Patel', 'priya.patel@school.edu', 'Mathematics', '', '+919876543211', ''])
        return response

