# Phase 4: UI Design System & Visual Audit Review

**Phase:** 04-faculty-student-views-password-security-integration-polish  
**Audit Date:** 2026-08-25  
**Design System Baseline:** Apple Design System (`DESIGN-apple.md` & `.agents/AGENTS.md`)  
**Scope Audited:** Faculty Dashboards (`my_class.html`, `my_subjects.html`), Password Management (`password_change.html`), and Role Navigation Headers (`navbar_faculty.html`, `navbar_student.html`, `navbar_admin.html`).

---

## Executive Summary & Scorecard

| Pillar | Score | Rating | Summary |
| :--- | :---: | :---: | :--- |
| **1. Copywriting** | **3 / 4** | Good | Clear, context-aware headings and friendly empty states; minor emoji prefixes in nav items. |
| **2. Visuals** | **3 / 4** | Good | Polished card structures, avatar badges, and crisp tables; mobile drawer missing links. |
| **3. Color** | **2 / 4** | Needs Work | **Critical violation**: Hardcoded maroon `#5A2132` used instead of Apple Action Blue `#0066cc` / theme variables. |
| **4. Typography** | **3 / 4** | Good | Clean SF Pro hierarchy and tight tracking; legacy inline font-family overrides in modal templates. |
| **5. Spacing** | **4 / 4** | Excellent | Consistent 8px grid rhythm, balanced container bounds (`max-w-6xl`, `max-w-md`), and proper mobile padding. |
| **6. Experience Design** | **3 / 4** | Good | Row-click modal editing with ESC/backdrop handling and session persistence; lacks password visibility toggle. |
| **OVERALL SCORE** | **18 / 24** | **75%** | **Solid foundation with specific styling & mobile navigation remediation required.** |

---

## 1. Copywriting (Score: 3/4)

### Strengths
- **Contextual Subheaders**: Clear indications of active academic year and class assignment (e.g., `Assigned Class: Standard 10 — A • Session 2026-2027`).
- **Helpful Empty States**: Descriptive guidance when unassigned or when no student records exist (`"No students currently enrolled in this class."`, `"You have not been assigned to teach any subjects for the active academic session."`).
- **Concise Action Labels**: High clarity in primary and secondary actions (`"Add Student"`, `"Save Changes"`, `"Update Password"`, `"Cancel"`).

### Findings & Recommendations
- [ ] **Navigation Label Polish**: Replace `🔒 Password` in `navbar_faculty.html` and `navbar_student.html` with clean SVG lock icon or text-only `"Password & Security"` matching Apple HIG.
- [ ] **Django Help Text Formatting**: Django password requirement help texts render as raw unstyled strings. Format them into discrete bullet points under the password input.

---

## 2. Visuals (Score: 3/4)

### Strengths
- **Card Hierarchy**: Distinct Apple-style surfaces (`apple-card`) with 1px hairline borders (`border-gray-200/80`) and smooth rounded corners (`rounded-2xl`).
- **Overview Stat Cards**: Three-column metric summary on Class Teacher Dashboard provides instant visual overview (Class Division, Total Students, Academic Session).
- **Avatar Badges**: Dynamic initials circle with smooth hover micro-interaction (`group-hover:scale-105 transition-transform`).

### Findings & Recommendations
- [ ] **Mobile Faculty Drawer Incompleteness**: `navbar_faculty.html` links to `students:hub` instead of `faculty:my_class` in mobile drawer, and omits "My Subjects" and "Password".
- [ ] **Subject Dashboard Scanability**: If a faculty member teaches 4+ subjects, cards stack indefinitely. Add a compact summary bar at the top with jump links or subject badges.

---

## 3. Color & Design Tokens (Score: 2/4)

### Strengths
- **Parchment Canvas**: Background adheres to Apple Parchment `#f5f5f7` with clean white card surfaces (`#ffffff`).
- **Pastel Status Badges**: Soft emerald (`bg-emerald-50 text-emerald-700`) and rose indicators used for status tags.

### Critical Violations & Recommendations
- [ ] **Rogue Maroon Hex Codes (`#5A2132` / `#481A28`)**:
  - Found hardcoded in `templates/faculty/my_class.html`, `templates/faculty/my_subjects.html`, `templates/accounts/password_change.html`, and `templates/students/partials/modals.html`.
  - **Remediation**: Replace with standard Apple Action Blue `#0066cc` (`hover:bg-[#0071e3]`, `focus:ring-[#0066cc]/20`, `focus:border-[#0066cc]`, `apple-btn-primary`) or CSS custom properties `var(--apple-blue)` and `var(--apple-ink)`.
- [ ] **Form Focus Ring Consistency**: In `password_change.html`, input focus rings use `focus:ring-[#5A2132]/20`. Update to Apple Action Blue focus ring (`focus:ring-[#0066cc]/20 focus:border-[#0066cc]`).

---

## 4. Typography (Score: 3/4)

### Strengths
- **Apple Display Tracking**: Headlines utilize tight letter tracking (`tracking-tight text-2xl sm:text-3xl font-bold text-[#1d1d1f]`).
- **Data Clarity**: Roll numbers and GR numbers use clean monospace styling (`font-mono text-xs font-semibold`).
- **Micro-labels**: Table headers and section labels use uppercase tracking (`tracking-wider text-[10px] font-semibold text-[#86868b]`).

### Findings & Recommendations
- [ ] **Inline Font Override in Shared Modals**: `templates/students/partials/modals.html` contains inline style `style="font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;"`. Remove this hardcoded font declaration to inherit the project's standard SF Pro / Inter font stack.

---

## 5. Spacing & Layout (Score: 4/4)

### Strengths
- **8px Grid Rhythm**: Margins, paddings, and gaps align to 8px base increments (`gap-4`, `p-5`, `space-y-6`, `pb-16`).
- **Container Max-Widths**: Focused max-widths (`max-w-6xl` for dashboards, `max-w-md` for password form) prevent unreadable wide input lines on large monitors.
- **Responsive Layout**: Tables gracefully scroll horizontally (`overflow-x-auto`) on narrow screens without breaking card containers.

### Findings & Recommendations
- [ ] **Button Sizing Uniformity**: Align cancel and submit button vertical/horizontal paddings in `password_change.html` (`px-5 py-2.5 rounded-full text-xs font-semibold`).

---

## 6. Experience Design & Accessibility (Score: 3/4)

### Strengths
- **Fast Roster Row-Click Editing**: Clicking any student row in `my_class.html` immediately opens the pre-populated Edit modal with propagation protection on child interactive elements (`tel:`, buttons).
- **Modal Lifecycle Management**: Built-in `Escape` key listener, backdrop click dismissal, and Lenis scroll prevention (`data-lenis-prevent`).
- **Session Continuity**: Password update uses `update_session_auth_hash` so users remain authenticated with positive feedback alerts.

### Findings & Recommendations
- [ ] **Password Visibility Toggle**: Add an eye icon button inside the password inputs in `password_change.html` to allow toggling between `type="password"` and `type="text"`.
- [ ] **Touch Target Min-Heights**: Ensure all interactive buttons and mobile navigation items maintain a minimum height of `44px` per Apple HIG standards.

---

## Top 3 Priority Fixes

1. **Remove hardcoded `#5A2132` / `#481A28` colors**: Refactor all buttons, focus rings, badges, and text highlights to standard Apple Action Blue `#0066cc` and design tokens across Phase 4 templates.
2. **Fix Mobile Navigation Drawer in `navbar_faculty.html`**: Correct `"My Class"` link to `faculty:my_class` and add missing `"My Subjects"` and `"Password & Security"` links.
3. **Add Password Visibility Toggle & Clean Font Overrides**: Implement show/hide password buttons in `password_change.html` and strip hardcoded `Plus Jakarta Sans` inline font styles from `modals.html`.
