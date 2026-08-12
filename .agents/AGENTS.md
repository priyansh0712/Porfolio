# Project UI & Design System Rules (Apple Design System)

All user interfaces across StudentERP1 must strictly adhere to the Apple Design System specification defined in `DESIGN-apple.md`.

## Core Aesthetics & UI Contract
1. **Canvas & Surfaces**:
   - Primary Background: `#f5f5f7` (Apple Parchment / Light Grey Canvas).
   - Card Background: `#ffffff` (Pure White) with 1px hairline border (`#e0e0e0` or `border-gray-200/80`).
   - Section Alternate Canvas: `#ffffff` vs `#f5f5f7` (Clean contrast, no loud gradient banners).

2. **Colors**:
   - Primary Action Color: `#0066cc` (Apple Action Blue).
   - Primary Hover/Focus: `#0071e3`.
   - Text Primary: `#1d1d1f` (Apple Off-Black Ink).
   - Text Muted: `#86868b` / `gray-500`.
   - Status Badges: Soft pastel backgrounds (e.g. `#e8f5e9` green, `#fff3e0` orange, `#ede7f6` purple) with high-contrast text.

3. **Typography**:
   - Font Stack: `SF Pro Display`, `SF Pro Text`, `system-ui`, `-apple-system`, `BlinkMacSystemFont`, `Inter`, `sans-serif`.
   - Headlines: Tight negative letter-spacing (`tracking-tight` / `-0.02em`), bold/semibold `#1d1d1f`.

4. **Buttons & Controls**:
   - Primary Buttons: Pill or smooth rounded shapes (`rounded-full` or `rounded-xl`), `#0066cc` background, white text, smooth transform transition on hover (`hover:bg-[#0071e3]`).
   - Secondary Buttons: Transparent/light grey background (`bg-gray-100 hover:bg-gray-200/80 text-[#1d1d1f]`).

5. **Navigation & Headers**:
   - Sticky Top Navbar: Semi-transparent white (`bg-white/80` or `bg-white/90`) with `backdrop-blur-md` and subtle hairline border (`border-b border-gray-200/80`).

6. **What NOT to Use**:
   - NO heavy purple/indigo/pink gradient backgrounds.
   - NO dark shadows or loud glowing card borders.
   - NO browser default input borders or unstyled buttons.
