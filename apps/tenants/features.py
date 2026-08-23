"""
Feature Registry & Feature Service Layer for Multi-Tenant Feature Management.
"""
from typing import Dict


FEATURE_CATALOG: Dict[str, Dict[str, str | bool]] = {
    'faculty_attendance': {
        'label': 'Faculty Attendance',
        'description': 'Webcam biometric face scan, attendance check-in/out, kiosk, and logs',
        'default': True,
    },
    'faculty_leave': {
        'label': 'Faculty Leave Management',
        'description': 'Leave application submission, leave balance, and administrative approval workflow',
        'default': True,
    },
    'reports': {
        'label': 'Attendance Reports',
        'description': 'Detailed attendance summaries, report dashboards, and CSV export functionality',
        'default': True,
    },
    'notifications': {
        'label': 'Notifications',
        'description': 'System notifications, check-in alerts, and administrative broadcast messages',
        'default': True,
    },
    'school_branding': {
        'label': 'School Branding',
        'description': 'Custom school logo and login page cover image branding',
        'default': True,
    },
    'academics': {
        'label': 'Academic Management',
        'description': 'Academic years, standards, divisions, subjects, and curriculum allocations',
        'default': True,
    },
    'students': {
        'label': 'Student Management',
        'description': 'Student directory, profiles, enrollments, and transfer requests',
        'default': True,
    },
    # Future extension feature flags (default OFF)
    'student_attendance': {
        'label': 'Student Attendance',
        'description': 'Student classroom attendance tracking (Future module)',
        'default': False,
    },
    'bus_management': {
        'label': 'Bus Management',
        'description': 'School transport and bus route management (Future module)',
        'default': False,
    },
    'parent_portal': {
        'label': 'Parent Portal',
        'description': 'Parent login and student progress tracking (Future module)',
        'default': False,
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
