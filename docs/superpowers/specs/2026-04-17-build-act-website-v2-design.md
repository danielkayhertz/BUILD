# Illinois BUILD Act Advocacy Website v2 — Design Spec

*2026-04-17 · Status: Approved*

---

## Overview

v2 is a significant visual and UX upgrade to the v1 BUILD Act advocacy site. The content strategy and structure are unchanged; this release focuses on richer visual presentation, data visualization, and mobile experience. v2 lives in the `v2/` subfolder.

**Goal:** Make the same content more compelling, scannable, and shareable through photography, Chart.js data visualization, scroll animations, and a redesigned community result card.

**Output location:** `C:\Users\bpi\Documents\Claude Code\BUILD\website\v2\`

---

## Architecture

**Stack:** Static HTML + CSS + vanilla JS. No build framework. Chart.js 4.x via CDN.

**Files:**
- `v2/index.html` — full single-page site (complete rewrite)
- `v2/build_data.py` — updated data pipeline with 3 new export fields
- `v2/data/community-data.json` — regenerated with new fields

**Security constraint:** A write hook (`security_reminder_hook.py`) blocks any file containing `innerHTML` with dynamic content. ALL JS DOM manipulation must use `document.createElement()` + `.textContent` + `.appendChild()`. No `innerHTML` with variable data anywhere.

**CSS approach:** Class-based styles via stylesheet. No inline `style` attributes set from JavaScript. JS adds/removes CSS classes only.

---

## Data Pipeline Changes (`build_data.py`)

Three new fields added to each JSON record:

| Field | Description |
|-------|-------------|
| `home_value_start` | Raw Zillow ZHVI value at earliest 2014 month, rounded to integer |
| `home_value_end` | Raw Zillow ZHVI value at latest 2024 month, rounded to integer |
| `avg_units_per_1000_per_year` | `(units_built_2014_2024 / avg_population / 10) * 1000`, using BPS `population` field averaged across available years |

Population is available in `bps_permits.population` (one row per year per municipality). Use average population across 2014–2024 rows for each municipality. If a municipality has no BPS rows, set `avg_units_per_1000_per_year: null`.

**Updated JSON schema per municipality:**
```json
{
  "name": "Naperville",
  "county": "DuPage",
  "affordability_pct": 10.3,
  "is_exempt": true,
  "units_built_2014_2024": 4886,
  "home_value_change_pct": 61.4,
  "home_value_start": 243000,
  "home_value_end": 391000,
  "avg_units_per_1000_per_year": 5.1
}
```

---

## Visual Design

### Color Palette (unchanged from v1)
| Role | Hex | Usage |
|------|-----|-------|
| Amber | `#F59E0B` | Headings, buttons, accents |
| Amber dark | `#D97706` | Button hover |
| Amber light | `#FEF3C7` | Card backgrounds |
| Forest green | `#2D6A4F` | Success/compliant states |
| Green light | `#F0FDF4` | Solution section background |
| Off-white | `#FFF9F0` | Page background |
| Deep teal | `#1B3A4B` | Hero + CTA backgrounds |
| Teal dark | `#122839` | Hero gradient end |
| Dark slate | `#1F2937` | Body text |
| Slate mid | `#4B5563` | Secondary text |

### Typography (unchanged)
- Font: Inter via Google Fonts (400, 600, 700)
- Body: 18px, 1.7 line-height

### New in v2
- Scroll animations: `.fade-in` elements animate in on IntersectionObserver trigger
- Pillar card hover lift
- Smooth FAQ accordion via `max-height` CSS transition
- Frosted glass stat box in hero

---

## Page Sections

### 1. Navigation
**Changes from v1:** Pure CSS hamburger menu for mobile.

- Desktop: sticky top nav with logo left, links right (unchanged)
- Mobile: hamburger icon — `<input type="checkbox" id="nav-toggle">` + `<label for="nav-toggle">` with 3-bar CSS icon. Nav links hidden behind `max-height: 0 → max-height: 300px` transition. No JavaScript.

### 2. Hero
**Background:** Unsplash photo of a residential neighborhood / streetcar suburb scene.
- Photo via `background-image: url(...)` on hero element
- Dark gradient overlay: `linear-gradient(to right, rgba(27,58,75,0.85) 50%, rgba(27,58,75,0.4))`

**Layout (desktop):** Left side: headline + subtext + 2 CTA buttons. Right side: frosted glass stat box.
- Frosted glass: `backdrop-filter: blur(12px); background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.2); border-radius: 16px`
- Stat box content:
  - "Illinois needs **45,000** homes/year."
  - "We're building **19,000**."
  - "That's a gap of **26,000 homes** every year."

**Mobile:** Stat box stacks below hero text, loses frosted glass (solid teal background).

Copy (unchanged from v1):
- Headline: **"Let's Solve Illinois' Housing Crisis."**
- Sub: "Prices are up 37%. Inventory is down 64%. Families across Illinois can't find a home they can afford. The BUILD Act is common-sense reform to help fix that."
- CTA 1: "Learn What BUILD Does" → scrolls to solution section
- CTA 2: "Contact Your Legislator" → scrolls to CTA section

### 3. The Problem
**Background:** Off-white (`#FFF9F0`)

**Stat cards (unchanged from v1):** 4 cards — 142,000 homes short / 37% price increase / 64% fewer listings / 19,000 vs. 45,000 needed. Apply `.fade-in` scroll animation.

**Gap Bar Chart (new):**
- Chart.js 4.x horizontal bar chart (indexAxis: 'y')
- Two bars:
  - "Built" — 19,000 — amber (`#F59E0B`)
  - "Needed" — 45,000 — teal (`#1B3A4B`)
- No legend; labels are on the bars
- SVG overlay (positioned absolute over chart container) with whiteboard-style annotation:
  - Arrow (`<line>` + `<polygon>` arrowhead) pointing at the gap area between the bars
  - Annotation text: "Fewer starter homes · Fewer construction jobs · More bidding wars · Less affordability"
  - Style: slightly rotated, informal handwriting feel via `font-style: italic; fill: #D97706`

**Impact callout boxes (new):** 3 boxes in a row (desktop), stacked (mobile):
1. "🏠 Fewer starter homes — First-time buyers compete for the same shrinking inventory"
2. "👷 Fewer construction jobs — Illinois loses building trades work to states that build"
3. "⚡ More bidding wars — Prices rise when demand outpaces supply every single year"

**Community Lookup Widget (same as v1):**
- Search input + "Look Up" button
- On result: shows the redesigned 3-column result card (see below)
- Fuzzy name matching, case-insensitive

### 4. Community Result Card (redesigned)
**Layout:** 3 equal columns.

**Column 1 — Affordability Donut:**
- Chart.js doughnut chart: `affordability_pct` filled (green if `is_exempt`, amber/red if not) vs. remainder (light gray)
- Label below chart: "**X%** of homes are affordable"
- Status line: 
  - If `is_exempt`: "Compliant with state affordability standards" (green)
  - If not: "Below state affordability standards" (amber/red)
- **Never say "meets threshold" or any variant thereof**

**Column 2 — Building Rate:**
- Large amber number: the `avg_units_per_1000_per_year` value (e.g., "5.1")
- Label: "new homes per 1,000 residents per year"
- Sub-label: "Built 2014–2024"
- If null: "Building rate data not available"

**Column 3 — Home Value Change:**
- Large text: "+61%" (the `home_value_change_pct`, with + prefix)
- Sub: "From $243,000 → $391,000" (formatted with commas, no decimals)
- If `home_value_change_pct` is null: "Price data not available"

### 5. What BUILD Does
**Background:** Light green-tinted (`#F0FDF4`) — unchanged from v1.

**Changes from v1:**
- Apply `.fade-in` scroll animation to section heading + each card
- Hover lift effect on each pillar card:
  ```css
  .pillar-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 32px rgba(0,0,0,0.12);
  }
  ```
  Transition: `transform 0.2s ease, box-shadow 0.2s ease`

Content (unchanged from v1): 4 cards — More Homes by Right / Backyard Cottages / Cut the Red Tape / $250M Investment.

### 6. Common Questions (FAQ)
**Changes from v1:** Replace `display:none/block` toggle with smooth `max-height` CSS transition.

```css
.faq-answer {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease;
}
.faq-answer.open {
  max-height: 600px;
}
```

JS: toggle `.open` class on answer div when button clicked. First item open by default.

Content (unchanged from v1): 5 questions.

### 7. Take Action (CTA)
**Background:** Deep teal (`#1B3A4B`) — unchanged from v1.

Legislator lookup via Google Civic Information API — identical to v1.

### 8. Footer
Identical to v1.

---

## Scroll Animations

```css
.fade-in {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}
.fade-in.visible {
  opacity: 1;
  transform: translateY(0);
}
```

Applied via `IntersectionObserver` (threshold: 0.1). Elements with `.fade-in` class become `.visible` when they enter the viewport.

Apply to: stat cards, gap chart container, impact callout boxes, community result card, pillar cards, FAQ items.

Prefers-reduced-motion: if `window.matchMedia('(prefers-reduced-motion: reduce)').matches`, skip animation (add `.visible` immediately).

---

## Language Rules

- **Never say:** "meets threshold," "meets IHDA threshold," or any variant
- **Compliant (is_exempt = true):** "Compliant with state affordability standards"
- **Non-compliant (is_exempt = false):** "Below state affordability standards"
- Affordability framing: "X% of homes are affordable"

---

## Verification

1. `cd v2 && python build_data.py` — confirms JSON generates with `home_value_start`, `home_value_end`, `avg_units_per_1000_per_year` fields
2. Spot-check Naperville: all 8 fields present, values plausible
3. `python -m http.server 8001` → `http://localhost:8001`
4. Community lookup: "Naperville" → 3-column card with donut + per-1,000 rate + $X→$Y
5. Community lookup: "Chicago" → result
6. Community lookup: "xyznotaplace" → graceful no-result message
7. Gap chart renders; SVG annotation visible
8. Hamburger nav works at 375px width; no horizontal overflow
9. Scroll animations fire as sections enter viewport
10. FAQ accordion animates smoothly; no jump
11. Pillar cards lift on hover
12. Legislator lookup: ZIP 60601 → two legislators with call/email buttons
13. Grep for "meets threshold" → zero results in v2/index.html
14. Grep for `innerHTML` with variable data → zero results in v2/index.html
