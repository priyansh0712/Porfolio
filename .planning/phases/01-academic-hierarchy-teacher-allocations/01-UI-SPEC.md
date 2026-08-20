# Phase 1: Academic Hierarchy & Teacher Allocations — UI Design Contract (UI-SPEC)

**Phase:** 01-academic-hierarchy-teacher-allocations  
**Design System:** Apple Human Interface / Apple Design System (`DESIGN-apple.md`)  
**Status:** Approved UI Contract  

---

## 1. Surfaces, Canvas & Layout

- **Page Background:** `#f5f5f7` (Apple Parchment Canvas).
- **Cards & Surfaces:** `#ffffff` (Pure White) with 1px hairline border (`#e0e0e0` / `border-gray-200/80`) and smooth rounded corners (`rounded-2xl`).
- **Page Container:** `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8`.
- **Top Header Area:**
  - Page Title: "Academic Management" with tight tracking (`tracking-tight text-2xl sm:text-3xl font-bold text-[#1d1d1f]`).
  - Active Session Pill / Selector: Dropdown at top right showing `🗓️ Active Session: 2026-2027` with subtle chevron.
- **Segmented Control Tabs (Apple Style):**
  - Container: `bg-gray-200/70 p-1 rounded-xl inline-flex space-x-1`.
  - Active Tab: `bg-white text-[#1d1d1f] font-semibold shadow-xs rounded-lg px-4 py-2 text-xs sm:text-sm`.
  - Inactive Tab: `text-gray-600 hover:text-[#1d1d1f] rounded-lg px-4 py-2 text-xs sm:text-sm transition-colors`.
  - Tabs:
    1. `🗓️ Academic Years` (`?tab=years`)
    2. `🏫 Standards & Divisions` (`?tab=classes`)
    3. `📚 Subjects` (`?tab=subjects`)
    4. `👨‍🏫 Teacher Allocations` (`?tab=allocations`)

---

## 2. Component Specifications

### A. Academic Years Tab (`?tab=years`)
- Header row with "+ New Academic Year" CTA (`bg-[#0066cc] hover:bg-[#0071e3] text-white rounded-full px-4 py-2 text-xs font-semibold`).
- Table/Card list showing:
  - Year Label (e.g. `2026-2027`)
  - Date Range (`Jun 1, 2026 – Apr 30, 2027`)
  - Status Badge: `Active Current Session` (`bg-emerald-50 text-emerald-700 border border-emerald-200/80 rounded-full px-2.5 py-0.5 text-xs font-semibold`) vs `Inactive` (`bg-gray-100 text-gray-500 rounded-full px-2.5 py-0.5 text-xs`).
  - Quick Action: "Set as Current" toggle / button and Edit/Delete icons.

### B. Standards & Divisions Tab (`?tab=classes`)
- Header with "+ Add Standard" button.
- Grid of Standard Cards (`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6`):
  - Card Header: Standard Name (e.g. `Standard 10`), sort badge (`#10`), and action menu.
  - Divisions Row: Division badges (`A`, `B`, `C`) as pills with subtle hover effect and edit/delete triggers.
  - Quick CTA inside card: `+ Add Division` dashed button opening modal pre-linked to that Standard.

### C. Subjects Tab (`?tab=subjects`)
- Header with "+ Add Subject" button and search filter.
- Clean White Table with hairline dividers:
  - Columns: Subject Name, Code (`bg-gray-100 font-mono text-xs px-2 py-0.5 rounded`), Type (`Core` / `Elective`), Status (`Active`), Actions.

### D. Teacher Allocations Tab (`?tab=allocations`)
- Class Filter Dropdown (e.g., "All Classes", "Standard 10 - A", etc.).
- Class-wise Allocation Matrix:
  - Class Banner (`bg-gray-50/80 rounded-xl p-4 border border-gray-200/80`):
    - Class Title: `Standard 10 - Division A`
    - Class Teacher: Assigned Faculty badge with photo avatar, name, employee code, and `[ Change ]` action modal. If unassigned: `⚠️ No Class Teacher Assigned` amber badge with `[ + Assign ]`.
  - Subject Teachers List:
    - Interactive rows showing Subject Name, Subject Type, Assigned Subject Teacher, and `[ Assign / Edit ]` action.

---

## 3. Typography & Color Palette

- **Font Family:** `SF Pro Display`, `SF Pro Text`, `system-ui`, `-apple-system`, `Inter`, `sans-serif`.
- **Colors:**
  - Primary Action Blue: `#0066cc` (hover: `#0071e3`)
  - Text Primary: `#1d1d1f`
  - Text Muted: `#86868b` / `text-gray-500`
  - Border Hairline: `#e0e0e0` / `border-gray-200/80`
  - Canvas Background: `#f5f5f7`
  - Emerald Soft (Active): `#ecfdf5` bg, `#047857` text
  - Amber Soft (Warning/Unassigned): `#fffbeb` bg, `#b45309` text
  - Rose Soft (Error/Delete): `#fff1f2` bg, `#be123c` text

---

## 4. Modal Interactions & Responsiveness

- **Modals:** Centered backdrop blur (`fixed inset-0 bg-black/30 backdrop-blur-xs flex items-center justify-center z-50`), rounded-2xl white card with hairline border, smooth scale-in animation.
- **Form Controls:** Clean input fields with `rounded-xl border border-gray-300 focus:border-[#0066cc] focus:ring-2 focus:ring-[#0066cc]/20 px-3.5 py-2.5 text-sm`.
- **Mobile Responsive:** Segmented tabs overflow with horizontal scrollbar hidden (`overflow-x-auto no-scrollbar`), grid stacks cleanly to 1 column.
