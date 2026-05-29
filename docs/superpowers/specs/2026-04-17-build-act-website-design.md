# Illinois BUILD Act Advocacy Website — Design Spec

*2026-04-17 · Status: Approved*

---

## Overview

A single-page static advocacy website for the Illinois BUILD Act — Governor Pritzker's package of zoning reforms and housing investment introduced in February 2026. The site serves two audiences: the general public learning about the housing crisis, and state legislators being asked to support the bill.

**Goal:** Persuade visitors that BUILD is common-sense, necessary reform — not radical. Drive visitors to contact their state legislators.

**Output location:** `C:\Users\bpi\Documents\Claude Code\BUILD\website\`

---

## Architecture

**Stack:** Static HTML + CSS + vanilla JS. No build framework. Two files delivered to the user:
- `index.html` — the full single-page site
- `data/community-data.json` — municipality lookup dataset

**Data build script:** `build_data.py` — Python script that:
1. Queries `C:\Users\bpi\Documents\Claude Code\Missing Middle\missing_middle.db` for IHDA affordability + BPS permit data
2. Downloads Zillow ZHVI (Home Value Index) city-level CSV for Illinois
3. Computes % home value change 2014–2024 per municipality
4. Exports merged JSON to `data/community-data.json`

**Deployment:** Any static host (GitHub Pages, Netlify, Vercel, etc.). Requires HTTP server — not `file://` direct open, because JSON data file is loaded via fetch.

**Google Civic Information API:** Client-side call from browser. API key is hardcoded in a `<script>` config block at top of `index.html` — clearly labeled for easy replacement.

---

## Visual Design

### Color Palette
| Role | Hex | Usage |
|------|-----|-------|
| Amber (primary) | `#F59E0B` | Headings, buttons, accents |
| Forest green | `#2D6A4F` | Success states, solution section |
| Off-white | `#FFF9F0` | Page background |
| Deep teal | `#1B3A4B` | Hero + CTA section backgrounds |
| Dark slate | `#1F2937` | Body text |
| Light amber | `#FEF3C7` | Card backgrounds, highlights |

### Typography
- Font: [Inter](https://fonts.google.com/specimen/Inter) via Google Fonts
- Headlines: 700 weight, large (hero: ~56px desktop, ~36px mobile)
- Subheads: 600 weight
- Body: 400 weight, 18px, 1.7 line-height

### Design Language
- Generous white space; sections well separated
- Rounded card corners (`border-radius: 12px`)
- Subtle drop shadows on cards
- Feels like a smart magazine, not a government PDF
- Fully mobile-responsive (CSS Grid + Flexbox, no framework)

---

## Page Sections

### 1. Navigation
Sticky top nav. Logo/wordmark left: "BUILD Act." Links right: The Problem · What BUILD Does · FAQ · Take Action. Smooth-scroll to anchors.

### 2. Hero
**Background:** Deep teal (`#1B3A4B`)
**Left:** Main headline + subtext + two CTA buttons
**Right (floats):** Stat callout box — "Illinois needs 45,000 homes/year. We're building 19,000."

Copy:
- Headline: **"Let's Solve Illinois' Housing Crisis."**
- Sub: "Prices are up 37%. Inventory is down 64%. Families across Illinois can't find a home they can afford. The BUILD Act is common-sense reform to help fix that."
- CTA 1: "Learn What BUILD Does" → scrolls to solution section
- CTA 2: "Contact Your Legislator" → scrolls to CTA section

### 3. The Problem
**Background:** Off-white (`#FFF9F0`)
**Headline:** "Illinois Has a Housing Problem."

Four stat cards in a row:
| Stat | Label |
|------|-------|
| 142,000 | homes short right now |
| 37% | home price increase (5 yrs) |
| 64% | fewer listings than 5 years ago |
| 19,000/yr | homes built vs. 45,000 needed |

**Community Lookup Widget:**
- Subhead: "How does this affect your community?"
- Text input: "Search for your city or town..."
- Button: "Look Up"
- On result: show a card with:
  - Municipality name + county
  - IHDA affordability percentage (% of homes meeting affordable threshold)
  - Color indicator: green if ≥10% (IHDA exempt), red if <10% (non-exempt)
  - New homes built 2014–2024 (from BPS data)
  - Home value change 2014–2024 (from Zillow ZHVI; show "Data not available" if missing)
- Search is case-insensitive fuzzy match against municipality names
- If no match: "Try searching for a nearby larger city"

**Data JSON schema** (per municipality):
```json
{
  "name": "Naperville",
  "county": "DuPage",
  "affordability_pct": 12.4,
  "is_exempt": true,
  "units_built_2014_2024": 4821,
  "home_value_change_pct": 68.2
}
```

### 4. What BUILD Does
**Background:** Light green-tinted (`#F0FDF4`)
**Headline:** "What the BUILD Act Does"
**Subhead:** "Common-sense reforms to help more Illinoisans find a home they can afford."

Four equal cards (2×2 grid on mobile, 4-column on desktop):

| Card | Icon | Title | 2–3 sentence summary |
|------|------|-------|----------------------|
| 1 | 🏘️ | More Homes by Right | Allow 2–8 homes on residential lots currently zoned single-family. Tiered by lot size (2,500–5,000 sqft = 4 units; 5,000–7,500 = 6; 7,500+ = 8). Still requires permits and building inspections. |
| 2 | 🏡 | Backyard Cottages (ADUs) | Legalize accessory dwelling units — in-law suites, garage apartments, backyard cottages — on all residential properties. Creates naturally affordable rental options near existing services. |
| 3 | 📋 | Cut the Red Tape | Standardize statewide timelines for permit reviews. Allow third-party inspectors if municipalities miss deadlines. Eliminate parking minimums for missing middle housing. |
| 4 | 💰 | $250M Investment | $100M for site infrastructure (sewer, utilities); $100M for middle housing development via IHDA; $50M for first-time homebuyer assistance (Opening Doors + SmartBuy programs). |

### 5. Common Questions (FAQ / Mythbusting)
**Background:** Off-white
**Headline:** "Common Questions"
**Subhead:** "We've heard the concerns. Here are the facts."

Accordion-style. First item open by default. Five questions:

1. **"Won't this eliminate local control?"**
   BUILD doesn't rezone anything — it sets statewide minimums for what's allowed by right. Communities still control design standards, setbacks, landscaping requirements, and more. Local officials remain in charge of zoning classifications.

2. **"Will this just create luxury housing?"**
   Most new housing created under BUILD will be small-scale — duplexes, triplexes, backyard cottages. These are naturally more affordable than single-family homes. The $250M investment specifically targets affordable and workforce housing development.

3. **"What about strain on schools and utilities?"**
   BUILD allows gradual infill — a few units here and there — not large-scale development. The $100M in site infrastructure funding directly addresses utility capacity. Communities that already meet IHDA affordability thresholds are well-positioned to absorb modest growth.

4. **"Suburbs are already building — why force it?"**
   Illinois has been building 19,000 homes per year when it needs 45,000. Voluntary approaches haven't closed the gap. Statewide minimum standards — like those that exist for building codes, fire safety, and accessibility — are how we solve problems that cross municipal lines.

5. **"One size doesn't fit all communities."**
   BUILD uses a tiered lot-size system precisely to account for variation. Tiny lots get fewer units; larger lots can have more. Local communities retain design standards, historic district protections, and floodplain rules. What changes is the floor — the minimum that must be allowed.

### 6. Take Action (CTA)
**Background:** Deep teal (`#1B3A4B`)
**Headline:** "Tell Your Legislators: Support the BUILD Act."
**Subtext:** "Housing reform needs your voice. Find your state senator and representative and let them know you support common-sense housing solutions."

**Legislator Lookup:**
- Address/ZIP input + "Find My Reps" button
- Calls Google Civic Information API (`civicinfo.googleapis.com`) with `levels=administrativeArea1` and `roles=legislatorUpperBody,legislatorLowerBody`
- Filters results to Illinois state officials only
- On result: two cards side by side (Senator + Representative), each with:
  - Name, party, district
  - Phone number
  - Email address
  - "📞 Call" button (links to `tel:`)
  - "✉️ Email" button (opens mailto with pre-populated subject + message)

**Pre-populated email:**
- Subject: `I Support the BUILD Act — Please Vote Yes`
- Body: `Dear [Name], I'm a constituent in [district] writing to urge your support for the BUILD Act. Illinois is facing a housing crisis — we're 142,000 homes short and prices have risen 37% in five years. The BUILD Act is common-sense reform that will help more Illinoisans find a home they can afford. Please vote yes. Thank you, [Name]`

**Error states:**
- "Address not found" — prompt to try a more specific address
- "No Illinois legislators found" — suggest checking address
- API key missing — show fallback message with link to ILGA district finder (ilga.gov/house/rep/find.asp)

### 7. Footer
- Coalition supporters list: Housing Action Illinois, Impact for Equity, MPC, YIMBY Illinois, etc.
- Data sources: IHDA AHPAA 2023, Census Building Permits Survey 2014–2024, Zillow ZHVI
- Small print: "This site is maintained by [org]. BUILD Act information current as of February 2026."
- Share button (copies URL)

---

## Data Pipeline

### `build_data.py` steps:

1. **Load IHDA + BPS data** from `missing_middle.db`:
   ```sql
   SELECT m.name, m.county, i.affordability_pct, i.is_exempt,
          SUM(b.units_1unit + b.units_2unit + b.units_34unit + b.units_5plus) AS units_built
   FROM municipalities m
   JOIN ihda_affordability i ON m.fips_place = i.fips_place
   LEFT JOIN bps_permits b ON m.fips_place = b.fips_place
   GROUP BY m.fips_place
   ```

2. **Download Zillow ZHVI** city-level CSV (City_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv) filtered to Illinois:
   - URL: Zillow Research Data page (public download)
   - Filter: `State == 'IL'`
   - Find earliest available month ≥ Jan 2014 and most recent month ≤ Dec 2024
   - Compute `change_pct = (value_2024 / value_2014 - 1) * 100`

3. **Merge on municipality name** (normalized: lowercase, strip " village" / " city" / " town" suffixes for matching)

4. **Export to** `data/community-data.json`

---

## Files to Create

| File | Description |
|------|-------------|
| `index.html` | Full single-page site |
| `data/community-data.json` | Municipality lookup dataset |
| `build_data.py` | Python script to build the data file |
| `README.md` | Instructions: how to run build_data.py, how to deploy, where to set API key |

---

## Verification

1. Run `python build_data.py` — confirm `data/community-data.json` generates without errors, spot-check 5 municipalities
2. Open site on local HTTP server: `python -m http.server 8000` → `http://localhost:8000`
3. Test community lookup: search "Chicago," "Naperville," "Springfield" — verify cards show data
4. Test community lookup: search "nonexistent town" — verify graceful no-result state
5. Test legislator lookup: enter a Chicago ZIP (60601) — verify two legislators appear with working mailto/tel links
6. Test legislator lookup: enter an invalid ZIP — verify error message appears
7. Resize to mobile (375px) — verify all sections stack correctly, no horizontal overflow
8. Check color contrast (hero text on teal background, body text on off-white) meets WCAG AA
