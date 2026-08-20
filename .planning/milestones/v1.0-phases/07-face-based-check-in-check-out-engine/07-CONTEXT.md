# Phase 7 Context: Face-Based Check-In & Check-Out Engine

## Overview
Phase 7 delivers the real-time webcam scanning interface, face vector matching engine, scan state transition machine, and dedicated kiosk view for school faculty check-in and check-out attendance.

---

## Locked Implementation Decisions

### 1. Camera Scanning Interface
- **Mode**: Continuous real-time auto-scanning with dynamic visual bounding frame feedback.
- **Frame Sampling**: Client-side Vanilla JS canvas frame extraction sampling every ~500ms to evaluate face presence before transmitting embedding request.
- **UI State**: Instant feedback status badge overlay (Scanning..., Face Detected, Verified, Unrecognized, Cooldown Lock).

### 2. Attendance State Machine & Debounce Rules
- **State Logic**:
  - **First valid scan of calendar day**: Creates `Attendance` record with status `Check-In` (`check_in_time = now()`).
  - **Second valid scan of calendar day**: Updates record with `check_out_time = now()` (`Check-Out`).
  - **Subsequent scans on same day**: Updates existing `check_out_time` to latest timestamp, subject to cooldown lock.
- **Cooldown Lock**: 30-second scan debounce lock per faculty member to prevent duplicate scan creation from consecutive camera frames.

### 3. Feedback & Audio Cues
- **Visual**: Green/blue success status badge displaying faculty name, designation, timestamp, and status. Automatically resets scanner state after 3 seconds.
- **Audio**: Soft Web Audio API audio chime on successful match; subtle warning tone on unrecognized face.

### 4. Hosting & Kiosk Mode
- **URL Endpoint**: Dedicated Kiosk View at `/attendance/kiosk/`.
- **Features**: Fullscreen kiosk layout, live clock widget, tenant organization badge, automatic camera stream reconnect handling, and screen wake lock support.

---

## Requirements Traceability
- **ATT-01**: Real-time webcam scanning interface with status cues and face detection feedback.
- **ATT-02**: Check-in and check-out attendance state engine with cooldown debounce locks.
- **ATT-03**: Exception and edge case handling (unrecognized face, scan state transitions, camera disconnect).
