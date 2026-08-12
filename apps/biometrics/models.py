"""
Biometrics Models — Zero-Raw-Photo Face Vector Storage.

Contains:
  - FacultyBiometric: Stores normalized 512-d ArcFace embedding vectors
    in PostgreSQL JSONB. Linked 1-to-1 with Faculty via CASCADE delete.
    No raw facial photos are ever persisted to disk or database.
"""
from django.db import models

from apps.accounts.models import User
from apps.faculty.models import Faculty
from apps.tenants.models import TenantModel


class FacultyBiometric(TenantModel):
    """
    Stores a single normalized 512-d ArcFace face embedding vector for a faculty member.

    Privacy architecture:
      - Raw webcam frames are decoded in RAM only (OpenCV cv2.imdecode).
      - InsightFace extracts 512-float embedding; raw bytes destroyed immediately.
      - Only the normalized vector array is persisted in JSONB.
      - Deleting the Faculty record cascades and removes this biometric record.

    Fields:
      - faculty: 1-to-1 link (CASCADE) to Faculty model.
      - embedding: JSONB list of 512 float values (L2-normalized, magnitude 1.0).
      - enrolled_at: Auto-updated timestamp of last enrollment.
      - enrolled_by: Optional FK to the User (School Admin) who performed enrollment.
    """
    faculty = models.OneToOneField(
        Faculty,
        on_delete=models.CASCADE,
        related_name='biometric',
        help_text='Faculty member this biometric belongs to',
    )
    embedding = models.JSONField(
        help_text='512-dimensional normalized ArcFace float embedding vector (JSONB)',
    )
    enrolled_at = models.DateTimeField(
        auto_now=True,
        help_text='Timestamp of last face enrollment or re-enrollment',
    )
    enrolled_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='enrolled_biometrics',
        help_text='School Admin who performed the enrollment',
    )

    class Meta:
        verbose_name = 'Faculty Biometric'
        verbose_name_plural = 'Faculty Biometrics'

    def __str__(self):
        status = 'enrolled' if self.embedding else 'empty'
        return f"Biometric({self.faculty.full_name}, {status})"
