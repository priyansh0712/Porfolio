"""
Global Context Processor for exposing tenant feature configurations to templates.
"""
from apps.tenants.features import FeatureService


def school_features(request):
    """
    Exposes a `school_features` dictionary to all templates.
    Allows template conditions like `{% if school_features.faculty_leave %}`.
    """
    tenant = getattr(request, 'tenant', None)
    return {
        'school_features': FeatureService.get_school_features(tenant)
    }
