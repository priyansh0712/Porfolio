# Phase 6 Context: Face Registration & Biometric Pipeline

## Phase Scope
Implement webcam face enrollment interface for School Admins, InsightFace (ArcFace 512-d) vector extraction pipeline, and zero-raw-photo biometric storage architecture.

---

## Decisions & Locked Choices

### 1. Webcam Capture Interface & UX (Option A Approved)
- **Modal Drawer UI**: Enrollment camera opens directly inside an Apple frosted glass Modal Drawer right from the Faculty Directory / Faculty Profile Drawer (`Enroll Face ID` button).
- **Live Stream Overlay**: Browser `navigator.mediaDevices.getUserMedia` live video feed with interactive bounding box overlay:
  - Green guide rectangle when single face is properly centered & sized.
  - Red guide rectangle + helper text if 0 faces, multiple faces, or face too far/close.
- **Client-side Capture**: Canvas snapshot taken on frontend and transmitted via POST AJAX JSON (`/faculty/<id>/enroll-face/`).

### 2. Capture Quality & Multi-Frame Sampling (Multi-Frame Approved)
- **Multi-Frame Sampling**: Frontend captures 3 quality frames spaced ~300ms apart upon clicking "Capture & Enroll" (or auto-trigger when face stays stable).
- **Backend Averaging**: Backend processes the 3 frames with InsightFace, extracts three 512-d vector embeddings, averages them element-wise, and normalizes the final vector to unit length (magnitude = 1.0).
- **Validation Rules**:
  - Single-face constraint: Reject image if 0 faces or >1 face detected.
  - Min face size: Bounding box must be at least 120x120 pixels.

### 3. Zero-Raw-Photo Storage & Privacy Pipeline (Zero-Photo Approved)
- **RAM-Only Decoding**: OpenCV/PIL decodes incoming base64 frame stream purely in RAM memory.
- **Instant Photo Destruction**: Immediately after InsightFace extracts the 512-float embedding array, the raw photo byte array in RAM is deleted (`del image_bytes; gc.collect()`). Zero image files written to disk, media folder, or cloud storage.
- **Biometric Model**: `FacultyBiometric` model (linked 1-to-1 to `Faculty`, `on_delete=CASCADE`):
  - `embedding` = `JSONB` list of 512 float values (prototype approved).
  - `enrolled_at` = `DateTimeField(auto_now=True)`.
  - `enrolled_by` = `ForeignKey(User, null=True, on_delete=SET_NULL)`.
- **Faculty Status Sync**: `Faculty.is_face_enrolled` is set to `True` upon successful enrollment.

### 4. Machine Learning & Model Strategy (InsightFace Approved for Prototype)
- **Prototype Engine**: InsightFace (ArcFace model producing 512-d embedding vector) on CPU / ONNX runtime for dev/testing.
- **Production Commercial Note**: Commercial license / model validation deferred to pre-production deployment review.

### 5. Deferred Capabilities
- **Full Liveness / Presentation Attack Detection (PAD)**: Deferred to final device integration / production phase.
- **Hardware-Specific Camera Integration**: Deferred to final hardware phase (standard laptop/webcam via browser `MediaDevices` API for Phase 6).

---

## Technical Reference & Endpoints
- **GET/POST `/faculty/<id>/enroll-face/`**:
  - GET: Renders modal camera template / JSON status.
  - POST: Accepts `{ "frames": ["data:image/jpeg;base64,...", ...] }`, extracts embedding, saves `FacultyBiometric`, returns `{ "success": true, "message": "Face enrolled successfully" }`.
- **POST `/faculty/<id>/reset-face/`**:
  - POST: Deletes `FacultyBiometric` record, sets `Faculty.is_face_enrolled = False`, returns success.

---

## Next Steps
- Run `/gsd-research-phase 6` or `/gsd-plan-phase 6` to create execution plans (`06-01-PLAN.md`, etc.).
