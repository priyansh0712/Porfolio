"""
Academics Business Logic Services.

Provides helpers for session resolution, teacher allocations, and matrix generation.
"""
from django.db import transaction

from apps.academics.models import (
    AcademicYear,
    Standard,
    Division,
    Subject,
    ClassTeacherAllocation,
    SubjectTeacherAllocation,
)


class AcademicService:
    """
    Service layer for academic structure and teacher allocation operations.
    """

    @staticmethod
    def get_current_academic_year(school):
        """
        Returns the active AcademicYear (is_current=True) for a school.
        Falls back to the most recent academic year if none is marked active.
        """
        active = AcademicYear.objects.filter(school=school, is_current=True).first()
        if active:
            return active
        return AcademicYear.objects.filter(school=school).order_by('-start_date').first()

    @staticmethod
    @transaction.atomic
    def assign_class_teacher(school, academic_year, division, faculty):
        """
        Assigns or reallocates a Class Teacher to a Division for an Academic Year.
        Replaces any existing allocation atomically.
        """
        allocation, created = ClassTeacherAllocation.objects.update_or_create(
            school=school,
            academic_year=academic_year,
            division=division,
            defaults={'faculty': faculty},
        )
        return allocation, created

    @staticmethod
    @transaction.atomic
    def assign_subject_teacher(school, academic_year, division, subject, faculty):
        """
        Assigns or reallocates a Subject Teacher to a Division + Subject for an Academic Year.
        """
        allocation, created = SubjectTeacherAllocation.objects.update_or_create(
            school=school,
            academic_year=academic_year,
            division=division,
            subject=subject,
            defaults={'faculty': faculty},
        )
        return allocation, created

    @staticmethod
    def get_allocation_matrix(school, academic_year):
        """
        Builds an optimized tree structure of Standards -> Divisions -> Allocations
        for rendering the Teacher Allocation Matrix in the School Admin UI.
        """
        if not academic_year:
            return []

        standards = Standard.objects.filter(school=school, is_active=True).prefetch_related(
            'divisions'
        ).order_by('order_index', 'name')

        subjects = list(Subject.objects.filter(school=school, is_active=True).order_by('name'))

        # Fetch all class teacher allocations for this year
        class_allocations = {
            alloc.division_id: alloc
            for alloc in ClassTeacherAllocation.objects.filter(
                school=school,
                academic_year=academic_year,
            ).select_related('faculty', 'division')
        }

        # Fetch all subject teacher allocations for this year
        subject_allocations = {
            (alloc.division_id, alloc.subject_id): alloc
            for alloc in SubjectTeacherAllocation.objects.filter(
                school=school,
                academic_year=academic_year,
            ).select_related('faculty', 'division', 'subject')
        }

        matrix = []
        for std in standards:
            divisions_data = []
            for div in std.divisions.filter(is_active=True).order_by('name'):
                div_subjects = []
                for sub in subjects:
                    alloc = subject_allocations.get((div.id, sub.id))
                    div_subjects.append({
                        'subject': sub,
                        'allocation': alloc,
                        'assigned_faculty': alloc.faculty if alloc else None,
                    })

                divisions_data.append({
                    'division': div,
                    'class_teacher_allocation': class_allocations.get(div.id),
                    'class_teacher': class_allocations.get(div.id).faculty if class_allocations.get(div.id) else None,
                    'subjects': div_subjects,
                })

            matrix.append({
                'standard': std,
                'divisions': divisions_data,
            })

        return matrix
