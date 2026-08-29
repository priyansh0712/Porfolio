"""
Subject Notes Models — Faculty Upload, Class Teacher Approval Pipeline, Student Access.
"""
from django.db import models
from django.utils import timezone

from apps.tenants.models import TenantModel
from apps.notes.validators import validate_note_file_extension, validate_note_file_size


class SubjectNote(TenantModel):
    """
    Represents a study note uploaded by Subject Faculty for a specific Division and Subject.

    Status Workflow:
      1. Uploaded by Subject Faculty → Status: PENDING ("Waiting for Approval")
      2. Reviewed by Class Teacher:
         - Approve → Status: APPROVED (Visible in Student Portal)
         - Reject → Status: REJECTED (Reason recorded, hidden from Student Portal)
    """

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Waiting for Approval'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    division = models.ForeignKey(
        'academics.Division',
        on_delete=models.CASCADE,
        related_name='subject_notes',
        help_text='Class division this note is intended for',
    )
    subject = models.ForeignKey(
        'academics.Subject',
        on_delete=models.PROTECT,
        related_name='subject_notes',
        help_text='Academic subject of the note',
    )
    faculty = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='uploaded_notes',
        help_text='Faculty member who uploaded the note',
    )
    title = models.CharField(
        max_length=150,
        help_text='Title / Chapter name of the note',
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text='Optional description or instructions',
    )
    file = models.FileField(
        upload_to='school_notes/%Y/%m/',
        validators=[validate_note_file_extension, validate_note_file_size],
        help_text='Document file (PDF, DOCX, PPTX, Images)',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text='Approval status of the note',
    )
    rejection_reason = models.TextField(
        blank=True,
        default='',
        help_text='Reason provided by Class Teacher if rejected',
    )
    reviewed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_notes',
        help_text='Class Teacher user who approved or rejected the note',
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp when note was approved or rejected',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Subject Note'
        verbose_name_plural = 'Subject Notes'

    def __str__(self):
        return f"{self.subject.name} - {self.title} ({self.get_status_display()})"
