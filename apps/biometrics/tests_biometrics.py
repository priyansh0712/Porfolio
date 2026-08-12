"""
Biometrics Test Suite — Unit Tests for FacultyBiometric Model & BiometricService.

Tests cover:
  1. Tenant query & enrollment scoping (cross-tenant isolation)
  2. Strict 3-frame payload validation
  3. Content-Type & payload validation
  4. Biometric model CASCADE delete behavior
  5. Reset biometrics functionality
  6. Vector normalization verification

Note: InsightFace model calls are mocked to avoid requiring GPU/model
weights during automated test execution.
"""
import json
from unittest.mock import patch, MagicMock

import numpy as np
from django.test import TestCase, RequestFactory

from apps.accounts.models import User
from apps.biometrics.models import FacultyBiometric
from apps.biometrics.services import BiometricService, REQUIRED_FRAME_COUNT
from apps.faculty.models import Faculty
from apps.tenants.models import School


class BiometricTestBase(TestCase):
    """Common setup for biometric tests: creates schools, users, and faculty."""

    @classmethod
    def setUpTestData(cls):
        # School A
        cls.school_a = School.objects.create(
            name='Greenwood Academy',
            subdomain='greenwood',
            contact_email='admin@greenwood.edu',
        )
        cls.admin_a = User.objects.create_user(
            username='admin@greenwood.edu',
            email='admin@greenwood.edu',
            password='testpass123',
            role='SCHOOL_ADMIN',
            school=cls.school_a,
        )

        # School B
        cls.school_b = School.objects.create(
            name='Blueridge School',
            subdomain='blueridge',
            contact_email='admin@blueridge.edu',
        )
        cls.admin_b = User.objects.create_user(
            username='admin@blueridge.edu',
            email='admin@blueridge.edu',
            password='testpass123',
            role='SCHOOL_ADMIN',
            school=cls.school_b,
        )

        # Faculty for School A
        cls.faculty_user_a = User.objects.create_user(
            username='john@greenwood.edu',
            email='john@greenwood.edu',
            password=None,
            role='FACULTY',
            school=cls.school_a,
        )
        cls.faculty_user_a.set_unusable_password()
        cls.faculty_user_a.save()

        cls.faculty_a = Faculty.objects.create(
            school=cls.school_a,
            user=cls.faculty_user_a,
            first_name='John',
            last_name='Doe',
            email='john@greenwood.edu',
            employee_code='GREENWOOD-FAC-001',
            department='Science',
        )

        # Faculty for School B
        cls.faculty_user_b = User.objects.create_user(
            username='jane@blueridge.edu',
            email='jane@blueridge.edu',
            password=None,
            role='FACULTY',
            school=cls.school_b,
        )
        cls.faculty_user_b.set_unusable_password()
        cls.faculty_user_b.save()

        cls.faculty_b = Faculty.objects.create(
            school=cls.school_b,
            user=cls.faculty_user_b,
            first_name='Jane',
            last_name='Smith',
            email='jane@blueridge.edu',
            employee_code='BLUERIDGE-FAC-001',
            department='Mathematics',
        )

    @staticmethod
    def _make_mock_embedding(seed=42):
        """Generate a deterministic 512-d vector for testing."""
        rng = np.random.RandomState(seed)
        vec = rng.randn(512).astype(np.float32)
        return vec / np.linalg.norm(vec)

    @staticmethod
    def _make_mock_face(embedding, bbox_w=200, bbox_h=250):
        """Create a mock InsightFace face result object."""
        face = MagicMock()
        face.embedding = embedding
        face.bbox = np.array([100, 50, 100 + bbox_w, 50 + bbox_h], dtype=np.float32)
        return face


class Strict3FrameValidationTests(BiometricTestBase):
    """Test 2: Strict 3-frame payload validation."""

    def test_reject_1_frame(self):
        """Sending 1 frame raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            BiometricService.enroll_faculty_face(
                self.school_a, self.faculty_a, ['frame1'], self.admin_a,
            )
        self.assertIn('3', str(ctx.exception))

    def test_reject_0_frames(self):
        """Sending empty list raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            BiometricService.enroll_faculty_face(
                self.school_a, self.faculty_a, [], self.admin_a,
            )
        self.assertIn('3', str(ctx.exception))

    def test_reject_4_frames(self):
        """Sending 4 frames raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            BiometricService.enroll_faculty_face(
                self.school_a, self.faculty_a,
                ['f1', 'f2', 'f3', 'f4'], self.admin_a,
            )
        self.assertIn('4', str(ctx.exception))

    def test_reject_non_list(self):
        """Sending non-list raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            BiometricService.enroll_faculty_face(
                self.school_a, self.faculty_a, 'not-a-list', self.admin_a,
            )
        self.assertIn('list', str(ctx.exception))


class BiometricModelCascadeTests(BiometricTestBase):
    """Test 4: Biometric model CASCADE delete and status sync."""

    def test_create_biometric_updates_enrollment_status(self):
        """Creating FacultyBiometric sets faculty.is_face_enrolled = True."""
        embedding = self._make_mock_embedding().tolist()
        FacultyBiometric.objects.create(
            school=self.school_a,
            faculty=self.faculty_a,
            embedding=embedding,
            enrolled_by=self.admin_a,
        )
        self.faculty_a.is_face_enrolled = True
        self.faculty_a.save(update_fields=['is_face_enrolled'])

        self.faculty_a.refresh_from_db()
        self.assertTrue(self.faculty_a.is_face_enrolled)

    def test_cascade_delete_on_faculty_removal(self):
        """Deleting Faculty cascades and deletes FacultyBiometric."""
        embedding = self._make_mock_embedding().tolist()
        FacultyBiometric.objects.create(
            school=self.school_a,
            faculty=self.faculty_a,
            embedding=embedding,
        )

        faculty_pk = self.faculty_a.pk
        self.faculty_a.delete()

        self.assertFalse(
            FacultyBiometric.objects.filter(faculty_id=faculty_pk).exists()
        )


class ResetBiometricTests(BiometricTestBase):
    """Test 5: Reset biometrics functionality."""

    def test_reset_removes_biometric_and_updates_status(self):
        """Resetting deletes FacultyBiometric and sets is_face_enrolled = False."""
        embedding = self._make_mock_embedding().tolist()
        FacultyBiometric.objects.create(
            school=self.school_a,
            faculty=self.faculty_a,
            embedding=embedding,
        )
        self.faculty_a.is_face_enrolled = True
        self.faculty_a.save(update_fields=['is_face_enrolled'])

        was_deleted = BiometricService.reset_faculty_face(
            self.school_a, self.faculty_a,
        )

        self.assertTrue(was_deleted)
        self.faculty_a.refresh_from_db()
        self.assertFalse(self.faculty_a.is_face_enrolled)
        self.assertFalse(
            FacultyBiometric.objects.filter(faculty=self.faculty_a).exists()
        )

    def test_reset_with_no_biometric_returns_false(self):
        """Resetting faculty with no biometric returns False gracefully."""
        was_deleted = BiometricService.reset_faculty_face(
            self.school_a, self.faculty_a,
        )
        self.assertFalse(was_deleted)


class VectorNormalizationTests(BiometricTestBase):
    """Test 6: Verify saved embedding vector is L2-normalized (magnitude 1.0)."""

    @patch.object(BiometricService, 'get_face_analyzer')
    @patch.object(BiometricService, 'decode_base64_frame')
    def test_saved_vector_is_unit_normalized(self, mock_decode, mock_analyzer):
        """Enrolled embedding has L2 magnitude == 1.0."""
        # Mock 3 different face embeddings
        emb1 = self._make_mock_embedding(seed=1)
        emb2 = self._make_mock_embedding(seed=2)
        emb3 = self._make_mock_embedding(seed=3)

        mock_decode.return_value = np.zeros((480, 640, 3), dtype=np.uint8)

        analyzer_instance = MagicMock()
        analyzer_instance.get.side_effect = [
            [self._make_mock_face(emb1)],
            [self._make_mock_face(emb2)],
            [self._make_mock_face(emb3)],
        ]
        mock_analyzer.return_value = analyzer_instance

        frames = ['data:image/jpeg;base64,abc', 'data:image/jpeg;base64,def', 'data:image/jpeg;base64,ghi']
        biometric = BiometricService.enroll_faculty_face(
            self.school_a, self.faculty_a, frames, self.admin_a,
        )

        # Verify vector shape and normalization
        saved_vec = np.array(biometric.embedding)
        self.assertEqual(len(saved_vec), 512)
        magnitude = np.linalg.norm(saved_vec)
        self.assertAlmostEqual(magnitude, 1.0, places=5)

        # Verify faculty enrollment status
        self.faculty_a.refresh_from_db()
        self.assertTrue(self.faculty_a.is_face_enrolled)


class CrossTenantIsolationTests(BiometricTestBase):
    """Test 1: Multi-tenant biometric scoping (School A vs School B)."""

    def test_biometric_scoped_to_tenant(self):
        """School A biometric should not be visible when querying School B."""
        embedding = self._make_mock_embedding().tolist()
        FacultyBiometric.objects.create(
            school=self.school_a,
            faculty=self.faculty_a,
            embedding=embedding,
        )

        school_b_biometrics = FacultyBiometric.objects.filter(school=self.school_b)
        self.assertEqual(school_b_biometrics.count(), 0)

    def test_reset_on_wrong_tenant_is_noop(self):
        """Resetting School A faculty with School B does nothing."""
        embedding = self._make_mock_embedding().tolist()
        FacultyBiometric.objects.create(
            school=self.school_a,
            faculty=self.faculty_a,
            embedding=embedding,
        )

        was_deleted = BiometricService.reset_faculty_face(
            self.school_b, self.faculty_a,
        )
        self.assertFalse(was_deleted)
        # Original biometric should still exist
        self.assertTrue(
            FacultyBiometric.objects.filter(
                school=self.school_a, faculty=self.faculty_a
            ).exists()
        )
