"""
Super Admin platform management views.

These views are accessible ONLY on the root domain (/superadmin/) and are
protected by SuperAdminRequiredMixin (Layer 2). They expose only school
tenant metadata — NEVER faculty, biometric, or attendance records.
"""
from django.views import View
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from apps.accounts.permissions import SuperAdminRequiredMixin
from apps.tenants.models import School
from apps.tenants.features import FEATURE_CATALOG, FeatureService


class SuperAdminDashboardView(SuperAdminRequiredMixin, TemplateView):
    """
    Platform Super Admin dashboard listing all registered school tenants.

    Privacy boundary (AUTH-02):
      - Only displays school-level metadata (name, subdomain, contact, status, created date).
      - Does NOT query, display, or expose any faculty records, biometric data,
        face embeddings, or attendance records.
      - This is enforced explicitly here and at middleware layer (Layer 1).
    """
    template_name = 'accounts/superadmin_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Query school metadata ONLY — no faculty or attendance lookups
        schools = School.objects.all().order_by('-created_at')

        # Prepare per-school feature configurations for Super Admin UI
        school_feature_map = {}
        for s in schools:
            school_feature_map[s.pk] = FeatureService.get_school_features(s)

        context['schools'] = schools
        context['school_count'] = schools.count()
        context['active_count'] = schools.filter(is_active=True).count()
        context['inactive_count'] = schools.filter(is_active=False).count()
        context['feature_catalog'] = FEATURE_CATALOG
        context['school_feature_map'] = school_feature_map
        return context


from django.http import JsonResponse
import json


class SuperAdminSchoolFeatureToggleView(SuperAdminRequiredMixin, View):
    """
    POST API / View: Allows Super Admin to enable or disable features for an individual school.
    Supports both standard form submissions and AJAX/JSON requests.
    """
    def post(self, request, school_id):
        school = get_object_or_404(School, pk=school_id)
        
        # Determine payload source (JSON vs Form Data)
        is_json = request.content_type == 'application/json' or request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('accept') == 'application/json'
        
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body.decode('utf-8'))
            except Exception:
                data = {}
            feature_key = data.get('feature_key')
            raw_enabled = data.get('is_enabled')
        else:
            feature_key = request.POST.get('feature_key')
            raw_enabled = request.POST.get('is_enabled')

        if not feature_key or feature_key not in FEATURE_CATALOG:
            err_msg = f"Invalid feature key '{feature_key}'."
            if is_json:
                return JsonResponse({'success': False, 'error': err_msg}, status=400)
            messages.error(request, err_msg)
            return redirect('accounts:superadmin_dashboard')

        # Determine target state
        if raw_enabled is not None:
            if isinstance(raw_enabled, bool):
                is_enabled = raw_enabled
            elif isinstance(raw_enabled, str):
                is_enabled = raw_enabled.lower() in ['true', '1', 'on']
            else:
                is_enabled = bool(raw_enabled)
        else:
            current_status = FeatureService.is_enabled(school, feature_key)
            is_enabled = not current_status

        FeatureService.set_feature_status(school, feature_key, is_enabled)
        feature_label = FEATURE_CATALOG[feature_key]['label']
        status_str = 'enabled' if is_enabled else 'disabled'
        msg = f"Feature '{feature_label}' has been {status_str} for {school.name}."

        if is_json:
            return JsonResponse({
                'success': True,
                'school_id': school.pk,
                'feature_key': feature_key,
                'feature_label': feature_label,
                'is_enabled': is_enabled,
                'message': msg
            })

        messages.success(request, msg)
        return redirect('accounts:superadmin_dashboard')
