"""
Academics Business Logic Services.

Provides helpers for session resolution, curriculum matrices, and teacher allocations.
"""
from collections import defaultdict
from django.db import transaction
from django.core.exceptions import ValidationError

from apps.academics.models import (
    AcademicYear,
    Standard,
    Division,
    Subject,
    ClassCurriculum,
    ClassTeacherAllocation,
    SubjectTeacherAllocation,
)


class AcademicService:
    """
    Service layer for academic structure, grade-wise curriculum, and teacher allocation operations.
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
    def get_class_curriculum_matrix(school, academic_year):
        """
        Returns grade-wise curriculum assignments for the specified academic year.
        Structured as:
          [
            {
              'standard': Standard,
              'curriculum_subjects': [ClassCurriculum, ...],
              'subject_count': int,
            },
            ...
          ]
        """
        if not academic_year:
            return []

        standards = list(Standard.objects.filter(school=school, is_active=True).order_by('order_index', 'name'))
        curriculums = list(
            ClassCurriculum.objects.filter(
                school=school,
                academic_year=academic_year,
                is_active=True,
            ).select_related('subject', 'standard').order_by('subject__name')
        )

        std_curriculum_map = defaultdict(list)
        for curr in curriculums:
            std_curriculum_map[curr.standard_id].append(curr)

        matrix = []
        for std in standards:
            curr_list = std_curriculum_map.get(std.id, [])
            matrix.append({
                'standard': std,
                'curriculum_subjects': curr_list,
                'subject_count': len(curr_list),
            })
        return matrix

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
        Assigns a Subject Teacher to a Division + Subject for an Academic Year.
        Validates that the subject is part of the class's curriculum if curriculum is configured.
        Supports multi-teacher allocation (co-teaching).
        """
        has_curriculum = ClassCurriculum.objects.filter(
            school=school,
            academic_year=academic_year,
            standard=division.standard,
        ).exists()
        if has_curriculum and not ClassCurriculum.objects.filter(
            school=school,
            academic_year=academic_year,
            standard=division.standard,
            subject=subject,
            is_active=True,
        ).exists():
            raise ValidationError(
                f"'{subject.name}' is not part of the curriculum for {division.standard.name} in {academic_year.name}."
            )

        allocation, created = SubjectTeacherAllocation.objects.get_or_create(
            school=school,
            academic_year=academic_year,
            division=division,
            subject=subject,
            faculty=faculty,
        )
        return allocation, created

    @staticmethod
    def get_allocation_matrix(school, academic_year):
        """
        Builds an optimized tree structure of Standards -> Divisions -> Curriculum Subjects -> Allocations
        for rendering the Teacher Allocation Matrix in the School Admin UI.
        Only shows subjects configured in each grade's curriculum for that academic year.
        """
        if not academic_year:
            return []

        standards = Standard.objects.filter(school=school, is_active=True).prefetch_related(
            'divisions'
        ).order_by('order_index', 'name')

        # Fetch all curriculum subjects for this academic year grouped by standard_id
        curriculums = ClassCurriculum.objects.filter(
            school=school,
            academic_year=academic_year,
            is_active=True,
        ).select_related('subject').order_by('subject__name')

        std_curriculum_subjects = defaultdict(list)
        for curr in curriculums:
            std_curriculum_subjects[curr.standard_id].append(curr.subject)

        # Fetch all class teacher allocations for this year
        class_allocations = {
            alloc.division_id: alloc
            for alloc in ClassTeacherAllocation.objects.filter(
                school=school,
                academic_year=academic_year,
            ).select_related('faculty', 'division')
        }

        # Fetch all subject teacher allocations for this year grouped by (division_id, subject_id)
        subject_allocations = defaultdict(list)
        for alloc in SubjectTeacherAllocation.objects.filter(
            school=school,
            academic_year=academic_year,
        ).select_related('faculty', 'division', 'subject').order_by('id'):
            subject_allocations[(alloc.division_id, alloc.subject_id)].append(alloc)

        matrix = []
        for std in standards:
            curr_subjects = std_curriculum_subjects.get(std.id, [])
            divisions_data = []
            for div in std.divisions.filter(is_active=True).order_by('name'):
                div_subjects = []
                for sub in curr_subjects:
                    allocs = subject_allocations.get((div.id, sub.id), [])
                    div_subjects.append({
                        'subject': sub,
                        'allocations': allocs,
                        'assigned_faculties': [a.faculty for a in allocs],
                        'is_assigned': len(allocs) > 0,
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
                'has_curriculum': len(curr_subjects) > 0,
                'curriculum_subjects_count': len(curr_subjects),
            })

        return matrix

