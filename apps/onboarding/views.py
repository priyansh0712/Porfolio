"""
Bulk Onboarding Views — Stepper Wizard UI, AJAX Validation & Download Endpoints.

Layer 1: TenantMiddleware (request.tenant)
Layer 2: SchoolAdminRequiredMixin (role-based access)
Layer 3: Queryset scoping (school=request.tenant)
"""
import json
import logging
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.permissions import SchoolAdminRequiredMixin
from apps.onboarding.services import (
    SampleTemplateService, BulkImportParser,
    BulkValidationService, BulkCommitService
)

logger = logging.getLogger(__name__)


class OnboardingWizardView(SchoolAdminRequiredMixin, TemplateView):
    """Renders the 4-Step Stepper Wizard UI."""
    template_name = 'onboarding/wizard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school = self.request.tenant
        context['school'] = school
        context['active_step'] = int(self.request.GET.get('step', 1))

        # Dynamic Columns per step based on school tenant config
        step_columns = {}
        for step in (1, 2, 3, 4):
            headers, _ = SampleTemplateService.get_template_headers_and_data(step, school=school)
            step_columns[step] = headers
        context['step_columns_json'] = json.dumps(step_columns)
        return context


class SampleTemplateDownloadView(SchoolAdminRequiredMixin, View):
    """GET endpoint streaming downloadable sample templates (.xlsx & .csv)."""

    def get(self, request, step, fmt):
        if step not in (1, 2, 3, 4) or fmt not in ('csv', 'xlsx'):
            return HttpResponse('Invalid template parameter.', status=400)

        filename = f"step_{step}_sample_template.{fmt}"

        if fmt == 'csv':
            content = SampleTemplateService.generate_csv(step, school=request.tenant)
            response = HttpResponse(content, content_type='text/csv')
        else:
            content = SampleTemplateService.generate_xlsx(step, school=request.tenant)
            response = HttpResponse(
                content,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class OnboardingValidateAPIView(SchoolAdminRequiredMixin, View):
    """POST AJAX endpoint parsing uploaded file and returning row-by-row validation JSON."""

    def post(self, request):
        step_str = request.POST.get('step')
        uploaded_file = request.FILES.get('file')

        if not step_str or not uploaded_file:
            return JsonResponse({'success': False, 'error': 'Missing step or file.'}, status=400)

        try:
            step = int(step_str)
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid step number.'}, status=400)

        try:
            raw_rows = BulkImportParser.parse(uploaded_file, uploaded_file.name)
            if not raw_rows:
                return JsonResponse({'success': False, 'error': 'No data rows found in uploaded file.'}, status=400)

            validation_results = BulkValidationService.validate(request.tenant, step, raw_rows)
            valid_count = sum(1 for r in validation_results if r['status'] == 'VALID')
            error_count = sum(1 for r in validation_results if r['status'] == 'ERROR')

            return JsonResponse({
                'success': True,
                'step': step,
                'total_rows': len(validation_results),
                'valid_count': valid_count,
                'error_count': error_count,
                'results': validation_results,
            })
        except Exception as e:
            logger.exception("Error during bulk import validation for step %s", step_str)
            return JsonResponse({'success': False, 'error': f'Parsing error: {str(e)}'}, status=500)


class OnboardingCommitAPIView(SchoolAdminRequiredMixin, View):
    """POST AJAX endpoint executing atomic database commits for validated rows."""

    def post(self, request):
        try:
            payload = json.loads(request.body)
        except Exception:
            return JsonResponse({'success': False, 'error': 'Invalid JSON body.'}, status=400)

        step = payload.get('step')
        valid_rows = payload.get('valid_rows', [])

        if not step or not valid_rows:
            return JsonResponse({'success': False, 'error': 'No valid rows provided for commit.'}, status=400)

        try:
            count = 0
            if step == 1:
                count = BulkCommitService.commit_step_1_faculty(request.tenant, valid_rows)
            elif step == 2:
                count = BulkCommitService.commit_step_2_classes(request.tenant, valid_rows)
            elif step == 3:
                count = BulkCommitService.commit_step_3_subjects(request.tenant, valid_rows)
            elif step == 4:
                count = BulkCommitService.commit_step_4_students(request.tenant, valid_rows)

            return JsonResponse({
                'success': True,
                'message': f'Successfully imported {count} records for Step {step}!',
                'count': count,
            })
        except Exception as e:
            logger.exception("Error during bulk import commit for step %s", step)
            return JsonResponse({'success': False, 'error': f'Database error: {str(e)}'}, status=500)
