# Phase 6 Research: Face Registration & Biometric Pipeline

## Executive Summary

Phase 6 delivers the biometric face enrollment foundation for StudentERP1. It enables School Admins to capture faculty face embeddings directly from the browser webcam within an Apple-styled frosted glass Modal Drawer (`#enroll-face-modal`), process frames in RAM using OpenCV and InsightFace ArcFace (512-d CPU/ONNX execution), average & normalize a 3-frame sample, and store the 512-float vector array in PostgreSQL JSONB while destroying all raw photo memory bytes instantly.

---

## Standard Stack

| Layer | Recommended Library / API | Purpose | Rationale |
|---|---|---|---|
| **Frontend Camera** | Browser `navigator.mediaDevices.getUserMedia` | Native Web Cam Stream | Zero third-party JS bloat; native HTML5 video/canvas capture |
| **Frame Decoding** | `OpenCV (cv2)` / `NumPy` | In-Memory JPEG decoding | `cv2.imdecode` decodes base64 bytes directly in RAM into NumPy arrays |
| **Biometric Engine** | `InsightFace` (ArcFace 512-d) | Face Detection & Embedding | SOTA 512-d vector extraction; fast CPU execution via ONNX runtime |
| **Vector Storage** | PostgreSQL `JSONB` / Django `JSONField` | 512-float Array Persistence | Portable, native PostgreSQL support without requiring custom extensions |
| **Transaction Safety** | `@transaction.atomic` | Single Atomic Enrollment | Guarantees `FacultyBiometric` create + `Faculty.is_face_enrolled=True` sync atomically |

---

## Architecture Patterns

### 1. Zero-Raw-Photo RAM Pipeline
```
[ Browser Webcam Stream ]
         │ (3 snapshots ~300ms apart)
         ▼
[ Base64 JPEG Payload ]
         │ (HTTP POST AJAX JSON)
         ▼
[ Django Memory Buffer (io.BytesIO) ]
         │ (cv2.imdecode in RAM)
         ▼
[ InsightFace 512-d Vector Extraction ]
         │ (del raw_bytes; gc.collect())
         ▼
[ Vector Averaging & L2 Normalization ]
         │ (norm_emb = avg_emb / norm)
         ▼
[ PostgreSQL JSONB Array Storage ]
```

### 2. Multi-Frame Sampling Math
```python
# 3 embeddings extracted from 3 quality frames
emb1 = faces_1[0].embedding # (512,)
emb2 = faces_2[0].embedding # (512,)
emb3 = faces_3[0].embedding # (512,)

# Element-wise mean
avg_embedding = np.mean([emb1, emb2, emb3], axis=0)

# L2 Unit Length Normalization (Magnitude = 1.0)
norm = np.linalg.norm(avg_embedding)
normalized_embedding = (avg_embedding / norm).tolist()
```

---

## Don't Hand-Roll

- **DO NOT hand-roll face alignment or crop code**: InsightFace ArcFace models expect 112x112 aligned face chips. InsightFace's `app.get(img)` automatically performs landmark detection, 5-point alignment, and normalization internally.
- **DO NOT save temporary JPEG files to `/tmp` or media folder**: Use `io.BytesIO` and `cv2.imdecode` to decode in memory. File I/O creates disk persistence risks and potential biometric data leakage.
- **DO NOT write custom vector normalization**: Use standard `np.linalg.norm(vec)` L2 normalization so cosine distance during Phase 7 matching equals dot product `np.dot(vec1, vec2)`.

---

## Common Pitfalls

1. **Memory Leaks from NumPy & ONNX Runtime**: ONNX runtime and OpenCV buffers can accumulate in memory if frames are processed continuously.
   - *Mitigation*: Process only discrete requested 3-frame snapshots; explicitly call Python garbage collection after vector extraction.
2. **Multiple Faces in Background**: A student walking behind a teacher during face registration can poison the captured vector or trigger invalid detection.
   - *Mitigation*: Enforce `len(faces) == 1` strictly. If `len(faces) > 1` or `len(faces) == 0`, reject the capture with an explicit error message.
3. **Face Too Small / Far Away**: Low-resolution face chips yield noisy 512-d embeddings.
   - *Mitigation*: Check bounding box dimensions `(bbox[2]-bbox[0]) >= 120` and `(bbox[3]-bbox[1]) >= 120`.

---

## Code Examples

### 1. In-Memory Frame Processing & Vector Extraction (`apps/biometrics/services.py`)

```python
import base64
import gc
import cv2
import numpy as np
from django.db import transaction
from insightface.app import FaceAnalysis

class BiometricService:
    _app = None

    @classmethod
    def get_face_analyzer(cls):
        """Lazy singleton initialization of InsightFace ArcFace model."""
        if cls._app is None:
            cls._app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
            cls._app.prepare(ctx_id=0, det_size=(640, 640))
        return cls._app

    @classmethod
    def decode_base64_frame(cls, base64_str):
        """Decodes a base64 image string into a NumPy BGR image in RAM."""
        if ',' in base64_str:
            base64_str = base64_str.split(',')[1]
        img_bytes = base64.b64decode(base64_str)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        # Clear temporary byte buffer from RAM
        del img_bytes, nparr
        return img

    @classmethod
    @transaction.atomic
    def enroll_faculty_face(cls, school, faculty, base64_frames, user=None):
        """
        Processes 3 frames in RAM, extracts & averages 512-d ArcFace vectors,
        saves FacultyBiometric JSONB, and sets faculty.is_face_enrolled = True.
        """
        analyzer = cls.get_face_analyzer()
        embeddings = []

        for idx, b64_frame in enumerate(base64_frames):
            img = cls.decode_base64_frame(b64_frame)
            try:
                faces = analyzer.get(img)
                if len(faces) == 0:
                    raise ValueError(f"Frame {idx+1}: No face detected. Please face the camera clearly.")
                if len(faces) > 1:
                    raise ValueError(f"Frame {idx+1}: Multiple faces detected ({len(faces)}). Please ensure only one person is in frame.")
                
                face = faces[0]
                bbox = face.bbox.astype(int)
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                if w < 120 or h < 120:
                    raise ValueError(f"Frame {idx+1}: Face is too far away. Please move closer to the camera.")

                embeddings.append(face.embedding)
            finally:
                del img
                gc.collect()

        # Average vectors across frames & L2 normalize
        avg_emb = np.mean(embeddings, axis=0)
        norm = np.linalg.norm(avg_emb)
        if norm == 0:
            raise ValueError("Failed to compute valid face vector magnitude.")
        normalized_vector = (avg_emb / norm).tolist()

        # Save to DB
        from apps.biometrics.models import FacultyBiometric
        biometric, _created = FacultyBiometric.objects.update_or_create(
            school=school,
            faculty=faculty,
            defaults={
                'embedding': normalized_vector,
                'enrolled_by': user,
            }
        )

        faculty.is_face_enrolled = True
        faculty.save(update_fields=['is_face_enrolled'])

        return biometric
```

### 2. Frontend Webcam & 3-Frame Sampler (`templates/faculty/includes/enroll_face_modal.html`)

```javascript
async function startEnrollmentCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" }
    });
    const video = document.getElementById('enroll-video');
    video.srcObject = stream;
  } catch (err) {
    alert("Unable to access camera: " + err.message);
  }
}

async function captureAndEnrollFace(facultyId) {
  const video = document.getElementById('enroll-video');
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext('2d');

  const frames = [];
  // Sample 3 snapshots spaced 300ms apart
  for (let i = 0; i < 3; i++) {
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    frames.push(canvas.toDataURL('image/jpeg', 0.85));
    if (i < 2) await new Promise(r => setTimeout(r, 300));
  }

  // Send AJAX request with strict Content-Type: application/json
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
  const response = await fetch(`/faculty/${facultyId}/enroll-face/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      'X-CSRFToken': csrfToken
    },
    body: JSON.stringify({ frames: frames })
  });
  const data = await response.json();
  if (data.success) {
    spawnToast("Face enrolled successfully!", "success");
  } else {
    spawnToast(data.error, "error");
  }
}
```

---

## Production & Security Notes

1. **Strict Payload & Frame Validation**:
   - Endpoint MUST validate `len(frames) == 3`. Reject requests with `< 3` or `> 3` frames.
   - Max body size validation (e.g. 5MB total payload limit).
   - Base64 format validation, invalid image format handling, and graceful HTTP 400 error responses.
2. **Prototype vs Production Biometric Architecture Separation**:
   - **Prototype (Phase 6 & 7)**: Browser Webcam → In-Memory OpenCV → InsightFace (ArcFace 512-d) → JSONB Vector → Attendance Engine.
   - **Production (Future Phase)**: Dedicated Kiosk/Hardware Device → Device Adapter → Biometric Verification → Attendance Engine.
   - Commercial licensing / model validation deferred to pre-production review.
3. **WSGI Worker Memory Footprint**:
   - Process-level lazy singleton (`_app = None`) is acceptable for local dev and single-worker execution.
   - Multi-worker Gunicorn deployments will load model weights per worker process (~300MB RAM each). Re-evaluating standalone microservice / shared worker memory is deferred to deployment phase.

---

## Verification Plan

- Check `insightface` and `opencv-python-headless` dependencies.
- Unit test `BiometricService.enroll_faculty_face` with dummy numpy images and mock ArcFace vectors.
- Test 1-to-1 CASCADE delete behavior (deleting `Faculty` removes `FacultyBiometric`).
- Test multi-tenant scoping (School A admin cannot enroll face for School B faculty ID).
