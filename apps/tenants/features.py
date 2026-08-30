"""
Feature Registry & Feature Service Layer for Multi-Tenant Feature Management.
"""
from typing import Dict


FEATURE_CATALOG: Dict[str, Dict[str, str | bool]] = {
    'faculty_attendance': {
        'label': 'Faculty Attendance & Biometrics',
        'description': 'Webcam face recognition check-in/out, kiosk station, and real-time logs',
        'icon': '📷',
        'default': True,
    },
    'faculty_leave': {
        'label': 'Faculty Leave Management',
        'description': 'Leave applications, allowance balances, and administrative approval workflow',
        'icon': '🌴',
        'default': True,
    },
    'reports': {
        'label': 'Attendance Reports & Analytics',
        'description': 'Detailed attendance summaries, report dashboards, and CSV data export',
        'icon': '📊',
        'default': True,
    },
    'students': {
        'label': 'Student Hub & Directory',
        'description': 'Student directory, dynamic profiles, custom fields, and form configurations',
        'icon': '🎒',
        'default': True,
    },
    'academics': {
        'label': 'Academic Structure & Allocations',
        'description': 'Academic sessions, standards, divisions, subjects, and teacher allocations',
        'icon': '🏫',
        'default': True,
    },
    'timetable': {
        'label': 'Class Timetables & Schedules',
        'description': 'Weekly period timetables, manual schedule planner, and bulk Excel timetable uploads',
        'icon': '🗓️',
        'default': True,
    },
    'school_branding': {
        'label': 'School Branding & Customization',
        'description': 'Custom school logo, institute title, and login page cover customization',
        'icon': '🎨',
        'default': True,
    },
}


class FeatureService:
    """
    Centralized service for managing and evaluating tenant feature flags.
    """

    @staticmethod
    def get_school_features(school) -> Dict[str, bool]:
        """
        Retrieves feature dictionary for a given school tenant.
        Falls back to catalog defaults if no record exists.
        """
        if not school:
            return {key: info['default'] for key, info in FEATURE_CATALOG.items()}

        from apps.tenants.models import SchoolFeature

        # Fetch existing overrides from database
        db_features = dict(
            SchoolFeature.objects.filter(school=school).values_list('feature_key', 'is_enabled')
        )

        result = {}
        for key, info in FEATURE_CATALOG.items():
            if key in db_features:
                result[key] = db_features[key]
            else:
                result[key] = bool(info['default'])
        return result

    @staticmethod
    def is_enabled(school, feature_key: str) -> bool:
        """
        Evaluates whether a specific feature is enabled for a given school tenant.
        """
        if not school:
            default_val = FEATURE_CATALOG.get(feature_key, {}).get('default', True)
            return bool(default_val)

        from apps.tenants.models import SchoolFeature

        try:
            record = SchoolFeature.objects.get(school=school, feature_key=feature_key)
            return record.is_enabled
        except SchoolFeature.DoesNotExist:
            # Fall back to catalog default
            return bool(FEATURE_CATALOG.get(feature_key, {}).get('default', True))

    @staticmethod
    def set_feature_status(school, feature_key: str, is_enabled: bool):
        """
        Enables or disables a feature for a specific school tenant.
        """
        if feature_key not in FEATURE_CATALOG:
            raise ValueError(f"Unknown feature key '{feature_key}'. Must be one of {list(FEATURE_CATALOG.keys())}")

        from apps.tenants.models import SchoolFeature

        feature_record, _ = SchoolFeature.objects.get_or_create(
            school=school,
            feature_key=feature_key,
            defaults={'is_enabled': is_enabled}
        )
        if feature_record.is_enabled != is_enabled:
            feature_record.is_enabled = is_enabled
            feature_record.save(update_fields=['is_enabled', 'updated_at'])
        return feature_record

    @staticmethod
    def sync_default_features_for_school(school):
        """
        Ensures default feature records are stored in DB for a school.
        """
        from apps.tenants.models import SchoolFeature

        for key, info in FEATURE_CATALOG.items():
            SchoolFeature.objects.get_or_create(
                school=school,
                feature_key=key,
                defaults={'is_enabled': bool(info['default'])}
            )
