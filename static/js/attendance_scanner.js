/**
 * Attendance Scanner — Vanilla JS Camera Loop & Web Audio Feedback.
 *
 * Features:
 *   - getUserMedia camera stream with auto-reconnect handling.
 *   - Canvas frame extraction at configurable sampling intervals (~500ms).
 *   - Client-side 30-second per-faculty scan cooldown memory cache.
 *   - Web Audio API synthesizer for success/warning audio chimes.
 *   - Screen Wake Lock API to prevent display sleep during kiosk operation.
 *   - Status badge overlay UI with 3-second automatic reset.
 *
 * Architecture:
 *   Camera Stream → Canvas Snapshot → Base64 JPEG → POST /attendance/api/scan/
 *   (Note: In production, client-side InsightFace WASM or server-side frame
 *    processing would extract the 512-d vector. For Phase 7, the scan API
 *    accepts pre-extracted vectors from the biometric pipeline.)
 */
(function () {
    'use strict';

    const CONFIG = window.KIOSK_CONFIG || {};
    const SCAN_API_URL = CONFIG.scanApiUrl || '/attendance/api/scan/';
    const CSRF_TOKEN = CONFIG.csrfToken || '';
    const SCAN_INTERVAL_MS = CONFIG.scanIntervalMs || 500;
    const COOLDOWN_MS = CONFIG.cooldownMs || 30000;
    const STATUS_RESET_MS = CONFIG.statusResetMs || 3000;

    // ── State ──
    let cameraStream = null;
    let scanTimer = null;
    let isScanning = false;
    let scanCount = 0;
    let wakeLock = null;
    let audioContext = null;

    // Client-side cooldown map: faculty_id → last scan timestamp
    const cooldownMap = new Map();

    // ── DOM Refs ──
    const video = document.getElementById('camera-video');
    const canvas = document.getElementById('camera-canvas');
    const ctx = canvas ? canvas.getContext('2d') : null;
    const scanFrame = document.getElementById('scan-frame');
    const scanPulse = document.getElementById('scan-pulse');
    const statusOverlay = document.getElementById('status-overlay');
    const statusIcon = document.getElementById('status-icon');
    const statusTitle = document.getElementById('status-title');
    const statusSubtitle = document.getElementById('status-subtitle');
    const statusTime = document.getElementById('status-time');
    const cameraStatusDot = document.getElementById('camera-status-dot');
    const cameraStatusText = document.getElementById('camera-status-text');
    const scanCountEl = document.getElementById('scan-count');
    const cameraError = document.getElementById('camera-error');
    const clockEl = document.getElementById('live-clock');
    const dateEl = document.getElementById('live-date');

    // ═══════════════════════════════════════════════════════
    // Web Audio API — Chime Synthesizer
    // ═══════════════════════════════════════════════════════

    function getAudioContext() {
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        return audioContext;
    }

    /**
     * Play a success chime: E5 → B5 dual-tone chord (659.25Hz → 987.77Hz).
     * Exponential gain decay over 200ms.
     */
    function playSuccessChime() {
        try {
            const ctx = getAudioContext();
            const now = ctx.currentTime;

            // First tone: E5 (659.25 Hz)
            const osc1 = ctx.createOscillator();
            osc1.type = 'sine';
            osc1.frequency.setValueAtTime(659.25, now);
            const gain1 = ctx.createGain();
            gain1.gain.setValueAtTime(0.15, now);
            gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.2);
            osc1.connect(gain1).connect(ctx.destination);
            osc1.start(now);
            osc1.stop(now + 0.25);

            // Second tone: B5 (987.77 Hz) — delayed 50ms
            const osc2 = ctx.createOscillator();
            osc2.type = 'sine';
            osc2.frequency.setValueAtTime(987.77, now + 0.05);
            const gain2 = ctx.createGain();
            gain2.gain.setValueAtTime(0.12, now + 0.05);
            gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
            osc2.connect(gain2).connect(ctx.destination);
            osc2.start(now + 0.05);
            osc2.stop(now + 0.35);
        } catch (e) {
            console.warn('Audio chime failed:', e);
        }
    }

    /**
     * Play a warning tone: D3 (146.83 Hz) low pulse with quick cutoff.
     */
    function playWarningTone() {
        try {
            const ctx = getAudioContext();
            const now = ctx.currentTime;
            const osc = ctx.createOscillator();
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(146.83, now);
            const gain = ctx.createGain();
            gain.gain.setValueAtTime(0.1, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
            osc.connect(gain).connect(ctx.destination);
            osc.start(now);
            osc.stop(now + 0.2);
        } catch (e) {
            console.warn('Warning tone failed:', e);
        }
    }

    // ═══════════════════════════════════════════════════════
    // Live Clock
    // ═══════════════════════════════════════════════════════

    function updateClock() {
        const now = new Date();
        if (clockEl) {
            clockEl.textContent = now.toLocaleTimeString('en-US', {
                hour: '2-digit', minute: '2-digit', second: '2-digit',
                hour12: true,
            });
        }
        if (dateEl) {
            dateEl.textContent = now.toLocaleDateString('en-US', {
                weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
            });
        }
    }

    // ═══════════════════════════════════════════════════════
    // Screen Wake Lock
    // ═══════════════════════════════════════════════════════

    async function acquireWakeLock() {
        if ('wakeLock' in navigator) {
            try {
                wakeLock = await navigator.wakeLock.request('screen');
                wakeLock.addEventListener('release', () => {
                    console.log('Wake lock released');
                });
                console.log('Screen Wake Lock acquired');
            } catch (e) {
                console.warn('Wake Lock not available:', e);
            }
        }
    }

    // Re-acquire wake lock when page becomes visible again
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible' && !wakeLock) {
            acquireWakeLock();
        }
    });

    // ═══════════════════════════════════════════════════════
    // Camera Management
    // ═══════════════════════════════════════════════════════

    async function initCamera() {
        try {
            if (cameraError) cameraError.style.display = 'none';
            if (video) video.style.display = 'block';

            cameraStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'user',
                },
                audio: false,
            });

            video.srcObject = cameraStream;
            await video.play();

            // Update status
            if (cameraStatusDot) cameraStatusDot.classList.remove('error');
            if (cameraStatusText) cameraStatusText.textContent = 'Camera active — scanning';

            // Start scan loop
            startScanLoop();

            console.log('Camera initialized successfully');
        } catch (err) {
            console.error('Camera initialization failed:', err);
            if (cameraStatusDot) cameraStatusDot.classList.add('error');
            if (cameraStatusText) cameraStatusText.textContent = 'Camera error — check permissions';
            if (video) video.style.display = 'none';
            if (cameraError) cameraError.style.display = 'flex';

            // Auto-retry after 5 seconds
            setTimeout(initCamera, 5000);
        }
    }

    // ═══════════════════════════════════════════════════════
    // Status Badge UI
    // ═══════════════════════════════════════════════════════

    let statusResetTimer = null;

    function showStatus(type, icon, title, subtitle, time) {
        if (!statusOverlay) return;

        // Clear previous reset timer
        if (statusResetTimer) clearTimeout(statusResetTimer);

        // Remove all type classes
        statusOverlay.className = 'status-overlay';
        statusOverlay.classList.add(type, 'visible');

        if (statusIcon) statusIcon.textContent = icon;
        if (statusTitle) statusTitle.textContent = title;
        if (statusSubtitle) statusSubtitle.textContent = subtitle || '';
        if (statusTime) statusTime.textContent = time || '';

        // Update scan frame
        if (scanFrame) {
            scanFrame.className = 'scan-frame';
            if (type === 'success') scanFrame.classList.add('success');
            else if (type === 'warning') scanFrame.classList.add('warning');
            else if (type === 'error') scanFrame.classList.add('error');
            else if (type === 'scanning') scanFrame.classList.add('detecting');
        }

        // Auto-reset after configured duration
        statusResetTimer = setTimeout(hideStatus, STATUS_RESET_MS);
    }

    function hideStatus() {
        if (statusOverlay) {
            statusOverlay.classList.remove('visible');
        }
        if (scanFrame) {
            scanFrame.className = 'scan-frame';
        }
    }

    // ═══════════════════════════════════════════════════════
    // Scan Loop
    // ═══════════════════════════════════════════════════════

    function startScanLoop() {
        if (scanTimer) clearInterval(scanTimer);
        scanTimer = setInterval(captureAndScan, SCAN_INTERVAL_MS);
    }

    function stopScanLoop() {
        if (scanTimer) {
            clearInterval(scanTimer);
            scanTimer = null;
        }
    }

    /**
     * Capture a frame from the video stream and send to scan API.
     *
     * Note: In Phase 7, the scan API expects a pre-extracted 512-d vector.
     * For development/demo, this sends a frame capture request. In production,
     * client-side InsightFace WASM would extract vectors before transmission.
     *
     * For now, this demonstrates the UI interaction loop. The actual vector
     * extraction and matching happens server-side via the biometric pipeline.
     */
    /**
     * Capture a frame from the video stream and send to scan API for real-time face matching.
     */
    async function captureAndScan() {
        if (isScanning || !video || video.readyState < 2) return;
        isScanning = true;

        try {
            if (canvas && ctx) {
                canvas.width = video.videoWidth || 640;
                canvas.height = video.videoHeight || 480;
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                const frameData = canvas.toDataURL('image/jpeg', 0.8);
                await sendScanPayload({ frame: frameData });
            }
        } catch (e) {
            console.warn('Frame capture error:', e);
        } finally {
            isScanning = false;
        }
    }

    /**
     * Send pre-extracted vector or base64 frame payload to the scan API.
     */
    async function sendScanPayload(payload) {
        if (!payload || (!payload.vector && !payload.frame)) return;

        const now = Date.now();

        try {
            const response = await fetch(SCAN_API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN,
                },
                body: JSON.stringify({
                    ...payload,
                    device_info: navigator.userAgent,
                }),
            });

            const data = await response.json();

            if (!data.success) {
                if (data.error && !data.error.includes('Rate limit')) {
                    showStatus('error', '⚠️', 'Error', data.error, '');
                }
                return;
            }

            // Silent return if no face detected in frame
            if (data.detected === false) {
                return;
            }

            if (!data.recognized) {
                // Unrecognized face
                showStatus('warning', '❓', 'Not Recognized',
                    data.message || 'Face not enrolled in this school.',
                    new Date().toLocaleTimeString());
                playWarningTone();
                return;
            }

            const faculty = data.faculty;
            const action = data.action;

            // Client-side cooldown check
            if (cooldownMap.has(faculty.id)) {
                const lastScan = cooldownMap.get(faculty.id);
                if (now - lastScan < COOLDOWN_MS) {
                    return; // Silently skip (server will also reject)
                }
            }

            // Update cooldown map
            cooldownMap.set(faculty.id, now);

            scanCount++;
            if (scanCountEl) scanCountEl.textContent = `Scans today: ${scanCount}`;

            if (action === 'cooldown') {
                showStatus('cooldown', '⏳', 'Please Wait',
                    data.message,
                    new Date().toLocaleTimeString());
                return;
            }

            if (action === 'check_in') {
                showStatus('success', '👋', `Welcome, ${faculty.name}`,
                    `Check-in recorded • ${faculty.department}`,
                    data.attendance ? `In: ${data.attendance.check_in}` : '');
                playSuccessChime();
            } else if (action === 'check_out' || action === 'updated') {
                showStatus('success', '👋', `Goodbye, ${faculty.name}`,
                    `Check-out ${action === 'updated' ? 'updated' : 'recorded'} • ${faculty.department}`,
                    data.attendance ? `Out: ${data.attendance.check_out}` : '');
                playSuccessChime();
            }

        } catch (err) {
            console.error('Scan API error:', err);
        }
    }

    async function sendScanVector(vector) {
        return sendScanPayload({ vector: vector });
    }

    // ═══════════════════════════════════════════════════════
    // Fullscreen Toggle
    // ═══════════════════════════════════════════════════════

    function toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch(console.warn);
        } else {
            document.exitFullscreen().catch(console.warn);
        }
    }

    // ═══════════════════════════════════════════════════════
    // Initialization
    // ═══════════════════════════════════════════════════════

    function init() {
        updateClock();
        setInterval(updateClock, 1000);
        acquireWakeLock();
        initCamera();

        // Resume AudioContext on first user interaction (Chrome autoplay policy)
        document.addEventListener('click', () => {
            const ctx = getAudioContext();
            if (ctx.state === 'suspended') ctx.resume();
        }, { once: true });
    }

    // Start on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // ── Public API ──
    window.AttendanceScanner = {
        initCamera,
        toggleFullscreen,
        sendScanVector,
        stopScanLoop,
        startScanLoop,
    };

})();
