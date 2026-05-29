# BUILD Act Website Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-page HTML advocacy website for the Illinois BUILD Act with a community housing data lookup and a legislator contact feature.

**Architecture:** Static `index.html` + `data/community-data.json` served from any HTTP host. A Python script `build_data.py` builds the JSON by merging IHDA/BPS data from an existing SQLite DB with downloaded Zillow ZHVI home value data. The legislator lookup calls the Google Civic Information API client-side.

**Tech Stack:** Python 3 + pandas + sqlite3 (data pipeline); vanilla HTML/CSS/JS, Inter (Google Fonts), Google Civic Information API v2 (website)

**Working directory for all steps:** `C:\Users\bpi\Documents\Claude Code\BUILD\website\`

**Security note:** All dynamic content inserted into innerHTML uses an `esc()` helper to prevent XSS. API responses and lookup results are HTML-escaped before rendering.

---

### Task 1: Project scaffold + README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README**

Write `README.md` with these contents (plain text, no code blocks that confuse the hook):

```
# Illinois BUILD Act — Advocacy Website

Single-page advocacy site for the Illinois BUILD Act.

## Setup

### 1. Build the community data file

Requires Python 3 with pandas and requests:

    pip install pandas requests

Then run:

    python build_data.py

This generates data/community-data.json from:
- C:\Users\bpi\Documents\Claude Code\Missing Middle\missing_middle.db (IHDA + BPS data)
- Zillow ZHVI city-level home value index (downloaded automatically)

### 2. Set your Google Civic Information API key

Open index.html and find the CONFIG block near the top of the script section:

    const CONFIG = { CIVIC_API_KEY: 'YOUR_API_KEY_HERE' };

Replace YOUR_API_KEY_HERE with your key from Google Cloud Console
(enable the "Google Civic Information API").

### 3. Serve locally

    python -m http.server 8000

Open http://localhost:8000

### 4. Deploy

Upload index.html and the data/ directory to any static host
(GitHub Pages, Netlify, Vercel). Must be served over HTTP — the
community lookup uses fetch() to load data/community-data.json.

## Data sources

- IHDA Affordable Housing Planning and Appeal Act (AHPAA) 2023
- Census Building Permits Survey 2014-2024
- Zillow Home Value Index (ZHVI) - city level, all homes, mid-tier
```

- [ ] **Step 2: Create data directory**

```bash
mkdir -p data
```

- [ ] **Step 3: Commit**

```bash
cd "C:/Users/bpi/Documents/Claude Code/BUILD/website"
git init
git add README.md
git commit -m "chore: project scaffold"
```

---

### Task 2: Data pipeline — extract IHDA + BPS from SQLite

**Files:**
- Create: `build_data.py`

The DB is at `C:\Users\bpi\Documents\Claude Code\Missing Middle\missing_middle.db`.

Tables:
- `municipalities(fips_place, name, county, county_fips)`
- `bps_permits(id, fips_place, year, population, footnote, units_1unit, units_2unit, units_34unit, units_5plus)`
- `ihda_affordability(id, year, municipality_name, county, total_housing_units, affordable_units, affordability_pct, is_exempt, fips_place, match_confidence)`

- [ ] **Step 1: Create build_data.py with SQLite extraction**

```python
import sqlite3
import pandas as pd
import requests
import io
import json
import re
from pathlib import Path

DB_PATH = Path(r"C:\Users\bpi\Documents\Claude Code\Missing Middle\missing_middle.db")
OUTPUT_PATH = Path("data/community-data.json")

ZILLOW_URL = (
    "https://files.zillowstatic.com/research/public_csvs/zhvi/"
    "City_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
)


def load_illinois_db_data(db_path: Path) -> pd.DataFrame:
    """Load IHDA affordability + BPS permit totals from missing_middle.db."""
    conn = sqlite3.connect(db_path)
    query = """
        SELECT
            m.fips_place,
            m.name        AS raw_name,
            m.county,
            i.affordability_pct,
            i.is_exempt,
            COALESCE(SUM(
                b.units_1unit + b.units_2unit + b.units_34unit + b.units_5plus
            ), 0)           AS units_built_2014_2024
        FROM municipalities m
        JOIN ihda_affordability i ON m.fips_place = i.fips_place
        LEFT JOIN bps_permits b ON m.fips_place = b.fips_place
        GROUP BY m.fips_place
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def normalize_name(name: str) -> str:
    """Strip common suffixes and lowercase for fuzzy matching."""
    name = name.lower().strip()
    for suffix in [" village", " city", " town", " township", " cdp"]:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name.strip()


if __name__ == "__main__":
    print("Loading IHDA + BPS data from SQLite...")
    db_df = load_illinois_db_data(DB_PATH)
    print(f"  {len(db_df)} municipalities loaded")
    print(db_df.head(3).to_string())
```

- [ ] **Step 2: Run and verify extraction works**

```bash
cd "C:/Users/bpi/Documents/Claude Code/BUILD/website"
python build_data.py
```

Expected output:
```
Loading IHDA + BPS data from SQLite...
  1298 municipalities loaded
  fips_place  raw_name county  affordability_pct  is_exempt  units_built_2014_2024
0    1700113  Abingdon   None               85.0          1                      0
...
```

If you get an import error, run `pip install pandas requests`.

- [ ] **Step 3: Commit**

```bash
git add build_data.py
git commit -m "feat: data pipeline - SQLite extraction"
```

---

### Task 3: Data pipeline — download and process Zillow ZHVI

**Files:**
- Modify: `build_data.py` (add `load_zillow_illinois_data` function + update `__main__`)

The Zillow ZHVI CSV has one row per city with monthly columns like `2014-01-31`, `2024-12-31`. Compute % change between earliest 2014 month and latest 2024 month.

- [ ] **Step 1: Add Zillow download + processing function**

Add this function after `normalize_name` in `build_data.py`:

```python
def load_zillow_illinois_data(url: str) -> pd.DataFrame:
    """Download Zillow ZHVI city CSV, return IL rows with pct_change_2014_2024."""
    print("Downloading Zillow ZHVI data...")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()

    df = pd.read_csv(io.StringIO(resp.text))

    # Filter to Illinois
    il = df[df["State"] == "IL"].copy()
    print(f"  {len(il)} Illinois cities in Zillow data")

    # Find date columns (format: YYYY-MM-DD)
    date_cols = [c for c in il.columns if re.match(r"^\d{4}-\d{2}-\d{2}$", c)]
    date_cols_2014 = sorted([c for c in date_cols if c.startswith("2014")])
    date_cols_2024 = sorted([c for c in date_cols if c.startswith("2024")])

    if not date_cols_2014 or not date_cols_2024:
        raise ValueError(
            f"Expected 2014/2024 columns. Found date cols sample: {date_cols[:5]}"
        )

    col_start = date_cols_2014[0]   # earliest 2014 month
    col_end = date_cols_2024[-1]    # latest 2024 month
    print(f"  Using {col_start} -> {col_end}")

    il = il[["RegionName", col_start, col_end]].copy()
    il.columns = ["zillow_city", "val_start", "val_end"]

    # Compute % change; NaN if either value missing
    il["home_value_change_pct"] = (
        (il["val_end"] - il["val_start"]) / il["val_start"] * 100
    ).round(1)

    il["zillow_key"] = il["zillow_city"].apply(normalize_name)
    return il[["zillow_key", "zillow_city", "home_value_change_pct"]]
```

- [ ] **Step 2: Update `__main__` to call the new function**

Replace the `if __name__ == "__main__":` block with:

```python
if __name__ == "__main__":
    print("Loading IHDA + BPS data from SQLite...")
    db_df = load_illinois_db_data(DB_PATH)
    print(f"  {len(db_df)} municipalities loaded")

    zillow_df = load_zillow_illinois_data(ZILLOW_URL)
    print(f"  {len(zillow_df)} IL Zillow rows with price change data")
    print(zillow_df.head(3).to_string())
```

- [ ] **Step 3: Run and verify Zillow download works**

```bash
python build_data.py
```

Expected output:
```
Loading IHDA + BPS data from SQLite...
  1298 municipalities loaded
Downloading Zillow ZHVI data...
  ~420 Illinois cities in Zillow data
  Using 2014-01-31 -> 2024-12-31
  zillow_key zillow_city  home_value_change_pct
0    addison     Addison                   62.3
...
```

If the download fails (403/404), the URL may have changed. Visit zillow.com/research/data, find "ZHVI All Homes (SFR, Condo/Co-op) Time Series, Smoothed, Seasonally Adjusted" -> "City", download the CSV manually to `data/zhvi_city.csv`, then in `build_data.py` change:
- `ZILLOW_URL` to `Path("data/zhvi_city.csv")`
- In `load_zillow_illinois_data`: replace `requests.get(url, timeout=60).text` with `url.read_text(encoding='utf-8')`

- [ ] **Step 4: Commit**

```bash
git add build_data.py
git commit -m "feat: data pipeline - Zillow ZHVI download and processing"
```

---

### Task 4: Data pipeline — merge + export JSON

**Files:**
- Modify: `build_data.py` (add merge + export function, finalize `__main__`)

- [ ] **Step 1: Add merge + export function**

Add after `load_zillow_illinois_data` in `build_data.py`:

```python
def merge_and_export(db_df: pd.DataFrame, zillow_df: pd.DataFrame, output_path: Path) -> None:
    """Merge DB and Zillow data, export to JSON for the website."""
    df = db_df.copy()
    df["db_key"] = df["raw_name"].apply(normalize_name)

    merged = df.merge(zillow_df, left_on="db_key", right_on="zillow_key", how="left")

    records = []
    for _, row in merged.iterrows():
        hvc = row["home_value_change_pct"]
        records.append({
            "name": row["raw_name"],
            "county": row["county"] if pd.notna(row["county"]) else None,
            "affordability_pct": round(float(row["affordability_pct"]), 1),
            "is_exempt": bool(row["is_exempt"]),
            "units_built_2014_2024": int(row["units_built_2014_2024"]),
            "home_value_change_pct": round(float(hvc), 1) if pd.notna(hvc) else None,
        })

    # Sort alphabetically for consistent output
    records.sort(key=lambda r: r["name"].lower())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    matched = sum(1 for r in records if r["home_value_change_pct"] is not None)
    print(f"\nExported {len(records)} municipalities to {output_path}")
    print(f"  {matched} with Zillow price change data, {len(records)-matched} without")

    examples = [r for r in records if r["name"].lower().startswith("naper")][:2]
    if examples:
        print(f"  Spot check Naperville: {examples}")
```

- [ ] **Step 2: Update `__main__` to call merge and export**

Replace the `if __name__ == "__main__":` block:

```python
if __name__ == "__main__":
    print("Loading IHDA + BPS data from SQLite...")
    db_df = load_illinois_db_data(DB_PATH)
    print(f"  {len(db_df)} municipalities loaded")

    zillow_df = load_zillow_illinois_data(ZILLOW_URL)
    merge_and_export(db_df, zillow_df, OUTPUT_PATH)
```

- [ ] **Step 3: Run the full pipeline**

```bash
python build_data.py
```

Expected output:
```
Loading IHDA + BPS data from SQLite...
  1298 municipalities loaded
Downloading Zillow ZHVI data...
  ~420 Illinois cities in Zillow data
  Using 2014-01-31 -> 2024-12-31

Exported 1298 municipalities to data/community-data.json
  ~400 with Zillow price change data, ~900 without
  Spot check Naperville: [{'name': 'Naperville', ...}]
```

- [ ] **Step 4: Spot-check the JSON**

```bash
python -c "
import json
data = json.load(open('data/community-data.json'))
with_price = [r for r in data if r['home_value_change_pct'] is not None]
for r in with_price[:3]:
    print(r)
print(f'Total: {len(data)}, with price change: {len(with_price)}')
"
```

Verify: names are alphabetical, `affordability_pct` values are 0-100, `is_exempt` is boolean.

- [ ] **Step 5: Commit**

```bash
git add build_data.py data/community-data.json
git commit -m "feat: data pipeline - merge and export community-data.json"
```

---

### Task 5: HTML shell + design system

**Files:**
- Create: `index.html`

- [ ] **Step 1: Create the HTML shell with design tokens**

Create `index.html` with this content. Sections will be filled in by later tasks — placeholders are HTML comments.

The `esc()` function at the top of the script block HTML-escapes all dynamic content before it touches `innerHTML`, preventing XSS from API responses.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Support the BUILD Act — Illinois Housing Reform</title>
  <meta name="description" content="Illinois is 142,000 homes short. The BUILD Act is common-sense reform to help fix that.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --amber:       #F59E0B;
      --amber-dark:  #D97706;
      --amber-light: #FEF3C7;
      --green:       #2D6A4F;
      --green-light: #F0FDF4;
      --teal:        #1B3A4B;
      --teal-dark:   #122839;
      --off-white:   #FFF9F0;
      --slate:       #1F2937;
      --slate-mid:   #4B5563;
      --slate-light: #9CA3AF;
      --white:       #FFFFFF;
      --red:         #DC2626;
      --radius:      12px;
      --radius-sm:   8px;
      --shadow:      0 2px 12px rgba(0,0,0,0.08);
      --shadow-lg:   0 4px 24px rgba(0,0,0,0.12);
      --font:        'Inter', system-ui, -apple-system, sans-serif;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html { scroll-behavior: smooth; }
    body {
      font-family: var(--font);
      color: var(--slate);
      background: var(--off-white);
      line-height: 1.6;
      font-size: 18px;
      overflow-x: hidden;
    }
    a { color: inherit; }
    .container { max-width: 1100px; margin: 0 auto; padding: 0 24px; }
    .section { padding: 80px 0; }
    .section-label {
      font-size: 13px; font-weight: 600; letter-spacing: 0.1em;
      text-transform: uppercase; color: var(--amber); margin-bottom: 12px;
    }
    h1 { font-size: clamp(36px, 5vw, 60px); font-weight: 800; line-height: 1.1; }
    h2 { font-size: clamp(28px, 4vw, 44px); font-weight: 700; line-height: 1.2; }
    h3 { font-size: 20px; font-weight: 700; }
    .lead { font-size: 20px; line-height: 1.7; color: var(--slate-mid); }
    .btn {
      display: inline-flex; align-items: center; gap: 8px;
      padding: 14px 28px; border-radius: var(--radius-sm);
      font-size: 16px; font-weight: 600; text-decoration: none;
      cursor: pointer; border: none; transition: background 0.15s, transform 0.1s;
      font-family: var(--font);
    }
    .btn:active { transform: translateY(1px); }
    .btn-primary { background: var(--amber); color: var(--slate); }
    .btn-primary:hover { background: var(--amber-dark); }
    .btn-outline {
      background: transparent; color: var(--white);
      border: 2px solid rgba(255,255,255,0.5);
    }
    .btn-outline:hover { border-color: var(--white); background: rgba(255,255,255,0.1); }
    .btn-ghost {
      background: transparent; color: var(--amber);
      border: 2px solid var(--amber);
    }
    .btn-ghost:hover { background: var(--amber); color: var(--slate); }
    .input-row { display: flex; gap: 10px; flex-wrap: wrap; }
    .input-row input {
      flex: 1; min-width: 220px; padding: 14px 18px;
      border-radius: var(--radius-sm); border: 2px solid #E5E7EB;
      font-family: var(--font); font-size: 16px; color: var(--slate);
      background: var(--white); transition: border-color 0.15s;
    }
    .input-row input:focus { outline: none; border-color: var(--amber); }
    .input-row input::placeholder { color: var(--slate-light); }
    :focus-visible { outline: 3px solid var(--amber); outline-offset: 2px; }
    button:focus:not(:focus-visible), a:focus:not(:focus-visible) { outline: none; }
    @media (max-width: 640px) { .section { padding: 56px 0; } }
  </style>
</head>
<body>
  <!-- NAV -->
  <!-- HERO -->
  <!-- PROBLEM -->
  <!-- SOLUTION -->
  <!-- FAQ -->
  <!-- ACTION -->
  <!-- FOOTER -->

  <script>
    const CONFIG = { CIVIC_API_KEY: 'YOUR_API_KEY_HERE' };

    /** Escape a value for safe insertion into innerHTML. */
    function esc(val) {
      if (val === null || val === undefined) return '';
      return String(val)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }
  </script>
</body>
</html>
```

- [ ] **Step 2: Verify the shell loads without errors**

```bash
python -m http.server 8000
```

Open http://localhost:8000. Expect: blank off-white page, no console errors. Stop server with Ctrl+C.

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: HTML shell + design system tokens"
```

---

### Task 6: Navigation + Hero section

**Files:**
- Modify: `index.html` (replace `<!-- NAV -->` and `<!-- HERO -->`)

- [ ] **Step 1: Replace `<!-- NAV -->` comment**

```html
  <!-- NAV -->
  <nav id="nav">
    <div class="container" style="display:flex;align-items:center;justify-content:space-between;height:64px;">
      <a href="#" style="font-size:18px;font-weight:800;color:var(--amber);text-decoration:none;letter-spacing:-0.02em;">BUILD Act</a>
      <div style="display:flex;gap:28px;align-items:center;" class="nav-links">
        <a href="#problem" class="nav-link">The Problem</a>
        <a href="#solution" class="nav-link">What BUILD Does</a>
        <a href="#faq" class="nav-link">FAQ</a>
        <a href="#action" class="btn btn-primary" style="padding:8px 18px;font-size:15px;">Take Action</a>
      </div>
    </div>
  </nav>
```

Add to `<style>` (before the closing `</style>`):

```css
    #nav { position:sticky; top:0; z-index:100; background:var(--teal-dark); border-bottom:1px solid rgba(255,255,255,0.08); }
    .nav-link { color:rgba(255,255,255,0.75); text-decoration:none; font-size:15px; font-weight:500; transition:color 0.15s; }
    .nav-link:hover { color:var(--white); }
    @media (max-width:640px) { .nav-links { display:none !important; } }
```

- [ ] **Step 2: Replace `<!-- HERO -->` comment**

```html
  <!-- HERO -->
  <section id="hero" style="background:var(--teal);padding:80px 0 72px;">
    <div class="container">
      <div class="hero-grid">
        <div>
          <p class="section-label">Illinois Housing Reform</p>
          <h1 style="color:var(--white);margin-bottom:24px;">Let's Solve Illinois'<br>Housing Crisis.</h1>
          <p style="font-size:20px;color:rgba(255,255,255,0.8);line-height:1.7;max-width:520px;margin-bottom:36px;">
            Prices are up 37%. Inventory is down 64%. Families across Illinois can't find a home they can afford. The BUILD Act is common-sense reform to help fix that.
          </p>
          <div style="display:flex;gap:14px;flex-wrap:wrap;">
            <a href="#solution" class="btn btn-primary">Learn What BUILD Does</a>
            <a href="#action" class="btn btn-outline">Contact Your Legislator</a>
          </div>
        </div>
        <div class="hero-stat-box">
          <p style="font-size:13px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:var(--amber);margin-bottom:10px;">The Gap</p>
          <p style="font-size:48px;font-weight:800;color:var(--white);line-height:1;">45,000</p>
          <p style="color:rgba(255,255,255,0.7);font-size:16px;margin-bottom:20px;">homes needed per year</p>
          <div style="width:100%;height:2px;background:rgba(255,255,255,0.15);margin-bottom:20px;position:relative;">
            <div style="position:absolute;left:0;top:0;height:100%;width:42%;background:var(--amber);"></div>
          </div>
          <p style="font-size:48px;font-weight:800;color:var(--amber);line-height:1;">19,000</p>
          <p style="color:rgba(255,255,255,0.7);font-size:16px;">actually being built</p>
        </div>
      </div>
    </div>
  </section>
```

Add to `<style>`:

```css
    .hero-grid { display:grid; grid-template-columns:1fr 280px; gap:48px; align-items:center; }
    .hero-stat-box { background:rgba(255,255,255,0.07); border:1px solid rgba(255,255,255,0.15); border-radius:var(--radius); padding:28px; }
    @media (max-width:800px) { .hero-grid { grid-template-columns:1fr; } .hero-stat-box { max-width:320px; } }
```

- [ ] **Step 3: Verify in browser**

```bash
python -m http.server 8000
```

Open http://localhost:8000. Verify:
- Sticky dark nav with amber "BUILD Act" wordmark
- Deep teal hero with white headline, amber stat box showing 45k/19k gap
- Both CTA buttons visible; resize to 375px — nav links hidden, hero stacks

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: navigation and hero section"
```

---

### Task 7: Problem section + community lookup

**Files:**
- Modify: `index.html` (replace `<!-- PROBLEM -->`, add JS to `<script>`)

The community lookup fetches `data/community-data.json` and does a client-side fuzzy name match. All dynamic values go through `esc()` before touching `innerHTML`.

- [ ] **Step 1: Replace `<!-- PROBLEM -->` comment**

```html
  <!-- PROBLEM -->
  <section id="problem" class="section" style="background:var(--off-white);border-top:4px solid var(--amber);">
    <div class="container">
      <p class="section-label">The Housing Crisis</p>
      <h2 style="margin-bottom:16px;">Illinois Has a Housing Problem.</h2>
      <p class="lead" style="max-width:600px;margin-bottom:56px;">The shortage is real, it's statewide, and voluntary approaches haven't worked.</p>

      <div class="stat-grid">
        <div class="stat-card"><div class="stat-number">142,000</div><div class="stat-label">homes short<br>right now</div></div>
        <div class="stat-card"><div class="stat-number">+37%</div><div class="stat-label">home prices<br>in 5 years</div></div>
        <div class="stat-card"><div class="stat-number">64%</div><div class="stat-label">fewer listings<br>than 5 years ago</div></div>
        <div class="stat-card"><div class="stat-number">19k</div><div class="stat-label">homes built/year<br>vs. 45k needed</div></div>
      </div>

      <div style="margin-top:64px;padding-top:48px;border-top:2px solid #E5E7EB;">
        <h3 style="margin-bottom:8px;">How does this affect your community?</h3>
        <p style="color:var(--slate-mid);margin-bottom:20px;">Enter your city or town to see local housing data.</p>
        <div class="input-row" style="max-width:540px;">
          <input type="text" id="community-input" placeholder="e.g. Naperville, Springfield, Evanston" autocomplete="off">
          <button class="btn btn-primary" onclick="lookupCommunity()">Look Up</button>
        </div>
        <div id="community-result" style="margin-top:20px;max-width:540px;"></div>
      </div>
    </div>
  </section>
```

Add to `<style>`:

```css
    .stat-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:20px; }
    .stat-card { background:var(--white); border-radius:var(--radius); padding:28px 20px; box-shadow:var(--shadow); text-align:center; }
    .stat-number { font-size:40px; font-weight:800; color:var(--amber-dark); line-height:1; margin-bottom:8px; }
    .stat-label { font-size:14px; color:var(--slate-mid); line-height:1.4; }
    @media (max-width:800px) { .stat-grid { grid-template-columns:repeat(2,1fr); } }
    @media (max-width:480px) { .stat-grid { grid-template-columns:1fr; } .stat-number { font-size:32px; } }
```

- [ ] **Step 2: Add community lookup JS to the `<script>` block (after the `esc` function)**

```js
    let COMMUNITY_DATA = null;

    async function loadCommunityData() {
      if (COMMUNITY_DATA) return COMMUNITY_DATA;
      const resp = await fetch('data/community-data.json');
      if (!resp.ok) throw new Error('Failed to load community data');
      COMMUNITY_DATA = await resp.json();
      return COMMUNITY_DATA;
    }

    function lookupCommunity() {
      const query = document.getElementById('community-input').value.trim();
      if (!query) return;
      const resultEl = document.getElementById('community-result');
      resultEl.innerHTML = '<p style="color:var(--slate-mid);">Loading\u2026</p>';

      loadCommunityData().then(data => {
        const q = query.toLowerCase();
        const match =
          data.find(r => r.name.toLowerCase() === q) ||
          data.find(r => r.name.toLowerCase().startsWith(q)) ||
          data.find(r => r.name.toLowerCase().includes(q));

        if (!match) {
          resultEl.innerHTML =
            '<div style="background:var(--white);border-radius:var(--radius);padding:24px;box-shadow:var(--shadow);border-left:4px solid var(--slate-light);">' +
            '<p style="font-weight:600;">No results for \u201c' + esc(query) + '\u201d</p>' +
            '<p style="color:var(--slate-mid);font-size:15px;margin-top:6px;">Try a nearby larger city, or check spelling. Data covers Illinois municipalities.</p>' +
            '</div>';
          return;
        }

        const exempt = match.is_exempt;
        const accentColor = exempt ? 'var(--green)' : 'var(--red)';
        const affordLabel = exempt
          ? esc(match.affordability_pct) + '% affordable \u2014 meets state threshold \u2713'
          : esc(match.affordability_pct) + '% affordable \u2014 below state 10% threshold';
        const countyStr = match.county ? ', ' + esc(match.county) + ' County' : '';
        const priceStr = match.home_value_change_pct !== null
          ? '+' + esc(match.home_value_change_pct.toFixed(1)) + '% (2014\u20132024)'
          : 'Data not available for this community';
        const unitsStr = esc(match.units_built_2014_2024.toLocaleString());

        resultEl.innerHTML =
          '<div style="background:var(--white);border-radius:var(--radius);padding:28px;box-shadow:var(--shadow);border-left:4px solid ' + accentColor + ';">' +
          '<p style="font-size:13px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:var(--slate-mid);margin-bottom:16px;">' +
          esc(match.name) + countyStr + '</p>' +
          '<div style="display:grid;gap:14px;">' +
          '<div><span style="font-size:13px;color:var(--slate-mid);display:block;margin-bottom:2px;">IHDA Affordability</span>' +
          '<span style="font-weight:600;color:' + accentColor + ';">' + affordLabel + '</span></div>' +
          '<div><span style="font-size:13px;color:var(--slate-mid);display:block;margin-bottom:2px;">New Homes Built (2014\u20132024)</span>' +
          '<span style="font-weight:600;">' + unitsStr + ' units</span></div>' +
          '<div><span style="font-size:13px;color:var(--slate-mid);display:block;margin-bottom:2px;">Home Value Change</span>' +
          '<span style="font-weight:600;">' + priceStr + '</span></div>' +
          '</div></div>';
      }).catch(err => {
        resultEl.innerHTML = '<p style="color:var(--red);">Could not load community data. ' + esc(err.message) + '</p>';
      });
    }

    document.getElementById('community-input').addEventListener('keydown', function(e) {
      if (e.key === 'Enter') lookupCommunity();
    });
```

- [ ] **Step 3: Verify in browser**

```bash
python -m http.server 8000
```

Open http://localhost:8000. Scroll to "The Problem". Verify:
- Four stat cards display; resize to 480px — 2-column; to 375px — single column
- Search "Naperville" — result card appears with affordability, units, price change
- Search "Chicago" — result card appears
- Search "zzzzz" — "No results" card appears with escaped query text
- Press Enter in the input — triggers lookup

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: problem section and community lookup widget"
```

---

### Task 8: Solution section

**Files:**
- Modify: `index.html` (replace `<!-- SOLUTION -->`)

- [ ] **Step 1: Replace `<!-- SOLUTION -->` comment**

```html
  <!-- SOLUTION -->
  <section id="solution" class="section" style="background:var(--green-light);border-top:4px solid var(--green);">
    <div class="container">
      <p class="section-label" style="color:var(--green);">The Solution</p>
      <h2 style="margin-bottom:16px;">What the BUILD Act Does</h2>
      <p class="lead" style="max-width:620px;margin-bottom:56px;">Common-sense reforms to help more Illinoisans find a home they can afford. Not radical — reasonable.</p>

      <div class="pillar-grid">
        <div class="pillar-card">
          <div class="pillar-icon">&#x1F3D8;&#xFE0F;</div>
          <h3>More Homes by Right</h3>
          <p style="margin:10px 0 12px;">Allow 2&#x2013;8 homes on residential lots currently zoned single-family, based on lot size:</p>
          <ul style="padding-left:18px;font-size:15px;color:var(--slate-mid);line-height:1.8;">
            <li>2,500&#x2013;5,000 sq ft lot &#x2192; up to 4 units</li>
            <li>5,000&#x2013;7,500 sq ft lot &#x2192; up to 6 units</li>
            <li>7,500+ sq ft lot &#x2192; up to 8 units</li>
          </ul>
          <p style="margin-top:12px;font-size:15px;color:var(--slate-mid);">Permits and building inspections still required. Local design standards preserved.</p>
        </div>

        <div class="pillar-card">
          <div class="pillar-icon">&#x1F3E1;</div>
          <h3>Backyard Cottages (ADUs)</h3>
          <p style="margin:10px 0 12px;">Legalize accessory dwelling units on all residential properties statewide &#x2014; in-law suites, garage apartments, and backyard cottages.</p>
          <p style="font-size:15px;color:var(--slate-mid);">Creates naturally affordable rental options near existing jobs, transit, and services. Helps homeowners build equity while adding housing.</p>
        </div>

        <div class="pillar-card">
          <div class="pillar-icon">&#x1F4CB;</div>
          <h3>Cut the Red Tape</h3>
          <p style="margin:10px 0 12px;">Reduce unnecessary delays that make housing more expensive to build:</p>
          <ul style="padding-left:18px;font-size:15px;color:var(--slate-mid);line-height:1.8;">
            <li>Statewide timelines for permit reviews</li>
            <li>Third-party inspectors if deadlines are missed</li>
            <li>No parking minimums for missing middle housing</li>
            <li>Standardized impact fee practices</li>
          </ul>
        </div>

        <div class="pillar-card">
          <div class="pillar-icon">&#x1F4B0;</div>
          <h3>$250 Million Investment</h3>
          <p style="margin:10px 0 12px;">Targeted funding to make housing affordable, not just possible:</p>
          <ul style="padding-left:18px;font-size:15px;color:var(--slate-mid);line-height:1.8;">
            <li><strong>$100M</strong> &#x2014; site infrastructure (sewer, utilities)</li>
            <li><strong>$100M</strong> &#x2014; middle housing via IHDA</li>
            <li><strong>$50M</strong> &#x2014; first-time homebuyer assistance</li>
          </ul>
          <p style="margin-top:12px;font-size:15px;color:var(--slate-mid);">Builds on Opening Doors (12,000 served since 2020) and SmartBuy programs.</p>
        </div>
      </div>
    </div>
  </section>
```

Add to `<style>`:

```css
    .pillar-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:24px; }
    .pillar-card { background:var(--white); border-radius:var(--radius); padding:32px; box-shadow:var(--shadow); }
    .pillar-icon { font-size:36px; margin-bottom:14px; }
    @media (max-width:700px) { .pillar-grid { grid-template-columns:1fr; } }
```

- [ ] **Step 2: Verify in browser**

Open http://localhost:8000. Scroll to "What the BUILD Act Does". Verify:
- Four cards in 2-column grid with icons and body text
- Green-tinted section background
- Mobile: stacks to single column

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: solution section with 4 BUILD pillars"
```

---

### Task 9: FAQ accordion

**Files:**
- Modify: `index.html` (replace `<!-- FAQ -->`, add JS to `<script>`)

- [ ] **Step 1: Replace `<!-- FAQ -->` comment**

```html
  <!-- FAQ -->
  <section id="faq" class="section" style="background:var(--off-white);">
    <div class="container" style="max-width:780px;">
      <p class="section-label">Common Questions</p>
      <h2 style="margin-bottom:16px;">We've Heard the Concerns.</h2>
      <p class="lead" style="margin-bottom:48px;">Here are the facts.</p>

      <div class="faq-list">
        <div class="faq-item open">
          <button class="faq-q" onclick="toggleFaq(this)">
            <span>&#x201C;Won't this eliminate local control?&#x201D;</span>
            <span class="faq-icon" aria-hidden="true">&#x25B2;</span>
          </button>
          <div class="faq-a">
            <p>No. BUILD doesn&#x2019;t rezone anything &#x2014; it sets statewide <em>minimums</em> for what&#x2019;s allowed by right. Communities still control design standards, setbacks, landscaping requirements, historic district protections, and floodplain rules. Local officials remain in charge of zoning classifications. What changes is the floor, not the ceiling.</p>
            <p style="margin-top:12px;">Illinois already sets statewide minimums for building codes, fire safety, and accessibility. Housing is no different.</p>
          </div>
        </div>

        <div class="faq-item">
          <button class="faq-q" onclick="toggleFaq(this)">
            <span>&#x201C;Will this just create luxury housing?&#x201D;</span>
            <span class="faq-icon" aria-hidden="true">&#x25BC;</span>
          </button>
          <div class="faq-a">
            <p>Most new housing created under BUILD will be small-scale &#x2014; duplexes, triplexes, backyard cottages. These are naturally more affordable than single-family homes because they share land and infrastructure costs.</p>
            <p style="margin-top:12px;">The $250M investment specifically targets affordable and workforce housing development through IHDA. First-time homebuyer programs have already served over 13,000 Illinoisans since 2020.</p>
          </div>
        </div>

        <div class="faq-item">
          <button class="faq-q" onclick="toggleFaq(this)">
            <span>&#x201C;What about strain on schools and utilities?&#x201D;</span>
            <span class="faq-icon" aria-hidden="true">&#x25BC;</span>
          </button>
          <div class="faq-a">
            <p>BUILD allows gradual infill &#x2014; a few units here and there across neighborhoods &#x2014; not large-scale development. The impact on any single school or utility district is modest.</p>
            <p style="margin-top:12px;">The $100M in site infrastructure funding directly addresses utility capacity. Communities that already meet IHDA affordability thresholds are well-positioned to absorb modest growth.</p>
          </div>
        </div>

        <div class="faq-item">
          <button class="faq-q" onclick="toggleFaq(this)">
            <span>&#x201C;Suburbs are already building &#x2014; why force it?&#x201D;</span>
            <span class="faq-icon" aria-hidden="true">&#x25BC;</span>
          </button>
          <div class="faq-a">
            <p>Some are &#x2014; but statewide, Illinois has been building 19,000 homes per year when it needs 45,000. The gap isn&#x2019;t closing, and it&#x2019;s been widening for years.</p>
            <p style="margin-top:12px;">Voluntary, community-by-community approaches haven&#x2019;t worked at scale. Statewide minimum standards are how we solve problems that cross municipal lines &#x2014; the same way we handle clean water, fire safety, and accessible design.</p>
          </div>
        </div>

        <div class="faq-item">
          <button class="faq-q" onclick="toggleFaq(this)">
            <span>&#x201C;One size doesn't fit all communities.&#x201D;</span>
            <span class="faq-icon" aria-hidden="true">&#x25BC;</span>
          </button>
          <div class="faq-a">
            <p>BUILD uses a tiered lot-size system precisely to account for variation. Tiny lots get fewer units; larger lots can have more. Local communities retain design standards, historic district protections, and floodplain rules.</p>
            <p style="margin-top:12px;">What BUILD does is prevent any community from entirely banning modest increases in housing supply &#x2014; because when every suburb says no, the housing crisis is everyone&#x2019;s problem.</p>
          </div>
        </div>
      </div>
    </div>
  </section>
```

Add to `<style>`:

```css
    .faq-list { display:flex; flex-direction:column; gap:12px; }
    .faq-item { background:var(--white); border-radius:var(--radius-sm); box-shadow:var(--shadow); overflow:hidden; }
    .faq-q {
      width:100%; display:flex; justify-content:space-between; align-items:center;
      padding:20px 24px; background:none; border:none; cursor:pointer;
      font-family:var(--font); font-size:17px; font-weight:600; color:var(--slate); text-align:left; gap:16px;
    }
    .faq-q:hover { background:var(--amber-light); }
    .faq-icon { font-size:12px; flex-shrink:0; color:var(--amber-dark); }
    .faq-a { display:none; padding:0 24px 24px; font-size:16px; line-height:1.7; color:var(--slate-mid); border-top:1px solid #F3F4F6; }
    .faq-item.open .faq-a { display:block; }
```

- [ ] **Step 2: Add FAQ accordion JS to `<script>` block (after community lookup code)**

```js
    function toggleFaq(btn) {
      var item = btn.closest('.faq-item');
      var isOpen = item.classList.contains('open');
      item.classList.toggle('open');
      btn.querySelector('.faq-icon').innerHTML = isOpen ? '&#x25BC;' : '&#x25B2;';
    }
```

- [ ] **Step 3: Verify in browser**

Open http://localhost:8000. Scroll to "Common Questions". Verify:
- First question is open by default; others collapsed
- Clicking any question expands it and updates the arrow
- Clicking again collapses it
- Text wraps cleanly on mobile

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: FAQ accordion with 5 mythbusting items"
```

---

### Task 10: CTA section + legislator lookup

**Files:**
- Modify: `index.html` (replace `<!-- ACTION -->`, add JS to `<script>`)

The legislator lookup calls the Google Civic Information API. All fields from the API response (`official.name`, `official.party`, `office.name`, `phone`, `email`) are passed through `esc()` before being inserted into the DOM.

- [ ] **Step 1: Replace `<!-- ACTION -->` comment**

```html
  <!-- ACTION -->
  <section id="action" style="background:var(--teal);padding:80px 0;">
    <div class="container">
      <p class="section-label" style="color:var(--amber);">Take Action</p>
      <h2 style="color:var(--white);margin-bottom:16px;">Tell Your Legislators:<br>Support the BUILD Act.</h2>
      <p style="color:rgba(255,255,255,0.75);font-size:18px;max-width:560px;margin-bottom:40px;line-height:1.7;">
        Housing reform needs your voice. Find your state senator and representative and let them know you support common-sense housing solutions.
      </p>

      <div class="input-row" style="max-width:560px;margin-bottom:8px;">
        <input type="text" id="address-input"
          placeholder="Enter your address or ZIP code"
          style="background:rgba(255,255,255,0.1);border-color:rgba(255,255,255,0.25);color:var(--white);"
          autocomplete="off">
        <button class="btn btn-primary" onclick="lookupLegislators()">Find My Reps</button>
      </div>
      <p id="civic-status" style="font-size:14px;color:rgba(255,255,255,0.5);min-height:20px;margin-bottom:24px;"></p>
      <div id="legislator-result"></div>
    </div>
  </section>
```

- [ ] **Step 2: Add legislator lookup JS to `<script>` block (after FAQ code)**

```js
    function lookupLegislators() {
      var address = document.getElementById('address-input').value.trim();
      if (!address) return;
      var statusEl = document.getElementById('civic-status');
      var resultEl = document.getElementById('legislator-result');
      statusEl.textContent = 'Looking up your legislators\u2026';
      resultEl.innerHTML = '';

      if (!CONFIG.CIVIC_API_KEY || CONFIG.CIVIC_API_KEY === 'YOUR_API_KEY_HERE') {
        statusEl.textContent = '';
        resultEl.innerHTML =
          '<div style="max-width:560px;background:rgba(255,255,255,0.1);border-radius:var(--radius);padding:24px;">' +
          '<p style="color:rgba(255,255,255,0.85);font-weight:600;margin-bottom:8px;">API key not configured</p>' +
          '<p style="color:rgba(255,255,255,0.7);font-size:15px;margin-bottom:14px;">Use the Illinois General Assembly\'s district finder:</p>' +
          '<div style="display:flex;gap:16px;flex-wrap:wrap;">' +
          '<a href="https://www.ilga.gov/house/rep/find.asp" target="_blank" rel="noopener noreferrer" style="color:var(--amber);font-weight:600;font-size:15px;">Find My IL House Rep &#x2192;</a>' +
          '<a href="https://www.ilga.gov/senate/senator/find.asp" target="_blank" rel="noopener noreferrer" style="color:var(--amber);font-weight:600;font-size:15px;">Find My IL Senator &#x2192;</a>' +
          '</div></div>';
        return;
      }

      var url = 'https://www.googleapis.com/civicinfo/v2/representatives' +
        '?address=' + encodeURIComponent(address) +
        '&levels=administrativeArea1' +
        '&roles=legislatorUpperBody&roles=legislatorLowerBody' +
        '&key=' + encodeURIComponent(CONFIG.CIVIC_API_KEY);

      fetch(url)
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (data.error) {
            statusEl.textContent = data.error.message || 'Address not found. Try a more specific address.';
            return;
          }
          statusEl.textContent = '';

          var ilOffices = (data.offices || []).filter(function(o) {
            return (o.levels || []).includes('administrativeArea1') &&
              (o.roles || []).some(function(r) {
                return r === 'legislatorUpperBody' || r === 'legislatorLowerBody';
              });
          });

          if (ilOffices.length === 0) {
            resultEl.innerHTML =
              '<p style="color:rgba(255,255,255,0.75);max-width:560px;">No Illinois state legislators found for that address. Try including your full city and state (e.g. "123 Main St, Chicago IL").</p>';
            return;
          }

          var grid = document.createElement('div');
          grid.style.cssText = 'display:grid;grid-template-columns:' +
            (window.innerWidth < 600 ? '1fr' : '1fr 1fr') +
            ';gap:20px;max-width:700px;';

          ilOffices.forEach(function(office) {
            (office.officialIndices || []).forEach(function(idx) {
              var official = data.officials[idx];
              if (!official) return;

              var phone = (official.phones || [])[0] || null;
              var email = (official.emails || [])[0] || null;

              var subject = encodeURIComponent('I Support the BUILD Act \u2014 Please Vote Yes');
              var bodyText = 'Dear ' + (official.name || 'Representative') + ',\n\n' +
                'I am a constituent writing to urge your support for the BUILD Act.\n\n' +
                'Illinois is facing a housing crisis \u2014 we are 142,000 homes short and prices have risen 37% in five years. ' +
                'The BUILD Act is common-sense reform that will help more Illinoisans find a home they can afford.\n\n' +
                'Please vote yes on the BUILD Act.\n\nThank you,\n[Your name]';
              var bodyParam = encodeURIComponent(bodyText);

              var card = document.createElement('div');
              card.style.cssText = 'background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.15);border-radius:var(--radius);padding:24px;';

              var officeName = document.createElement('p');
              officeName.style.cssText = 'font-size:12px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:var(--amber);margin-bottom:6px;';
              officeName.textContent = office.name || '';

              var nameEl = document.createElement('p');
              nameEl.style.cssText = 'font-size:20px;font-weight:700;color:var(--white);margin-bottom:4px;';
              nameEl.textContent = official.name || '';

              var partyEl = document.createElement('p');
              partyEl.style.cssText = 'font-size:14px;color:rgba(255,255,255,0.6);margin-bottom:16px;';
              partyEl.textContent = official.party || '';

              var btnRow = document.createElement('div');
              btnRow.style.cssText = 'display:flex;gap:10px;flex-wrap:wrap;';

              if (phone) {
                var callBtn = document.createElement('a');
                callBtn.className = 'btn btn-ghost';
                callBtn.style.cssText = 'font-size:14px;padding:10px 16px;';
                callBtn.href = 'tel:' + phone;
                callBtn.textContent = '\uD83D\uDCDE ' + phone;
                btnRow.appendChild(callBtn);
              }

              if (email) {
                var emailBtn = document.createElement('a');
                emailBtn.className = 'btn btn-ghost';
                emailBtn.style.cssText = 'font-size:14px;padding:10px 16px;';
                emailBtn.href = 'mailto:' + email + '?subject=' + subject + '&body=' + bodyParam;
                emailBtn.textContent = '\u2709 Email';
                btnRow.appendChild(emailBtn);
              }

              card.appendChild(officeName);
              card.appendChild(nameEl);
              card.appendChild(partyEl);
              card.appendChild(btnRow);
              grid.appendChild(card);
            });
          });

          resultEl.appendChild(grid);
        })
        .catch(function() {
          statusEl.textContent = 'Network error. Please try again.';
        });
    }

    document.getElementById('address-input').addEventListener('keydown', function(e) {
      if (e.key === 'Enter') lookupLegislators();
    });

    window.addEventListener('resize', function() {
      var grid = document.querySelector('#legislator-result > div');
      if (grid) grid.style.gridTemplateColumns = window.innerWidth < 600 ? '1fr' : '1fr 1fr';
    });
```

- [ ] **Step 3: Verify in browser**

Open http://localhost:8000. Scroll to "Take Action". Verify:
- Input has light text on dark background (readable)
- Without API key: entering any address shows ILGA fallback links
- Pressing Enter triggers lookup
- (With real API key) entering a Chicago address returns two legislator cards; call + email buttons work

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: CTA section and Google Civic API legislator lookup"
```

---

### Task 11: Footer + final verification

**Files:**
- Modify: `index.html` (replace `<!-- FOOTER -->`)

- [ ] **Step 1: Replace `<!-- FOOTER -->` comment**

```html
  <!-- FOOTER -->
  <footer style="background:var(--teal-dark);padding:48px 0 32px;border-top:1px solid rgba(255,255,255,0.08);">
    <div class="container">
      <div class="footer-grid">
        <div>
          <p style="font-size:18px;font-weight:800;color:var(--amber);margin-bottom:12px;">BUILD Act Coalition</p>
          <p style="color:rgba(255,255,255,0.6);font-size:15px;line-height:1.7;max-width:360px;">
            A coalition of housing organizations committed to solving Illinois&#x2019; housing crisis through the BUILD Act.
          </p>
        </div>
        <div>
          <p style="font-size:13px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:rgba(255,255,255,0.4);margin-bottom:12px;">Coalition Members</p>
          <ul style="list-style:none;color:rgba(255,255,255,0.65);font-size:15px;line-height:2;">
            <li>Abundant Housing Illinois</li>
            <li>Elevated Chicago</li>
            <li>Housing Action Illinois</li>
            <li>Illinois Housing Council</li>
            <li>Impact for Equity</li>
            <li>Metropolitan Planning Council</li>
            <li>YIMBY Illinois</li>
          </ul>
        </div>
      </div>
      <div style="border-top:1px solid rgba(255,255,255,0.1);padding-top:24px;margin-top:40px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
        <p style="color:rgba(255,255,255,0.35);font-size:13px;">
          Data: IHDA AHPAA 2023 &#x00B7; Census Building Permits Survey 2014&#x2013;2024 &#x00B7; Zillow ZHVI &#x00B7; BUILD Act information current as of February 2026.
        </p>
        <button onclick="navigator.clipboard.writeText(location.href).then(function(){this.textContent='Copied \u2713';}.bind(this))"
          style="background:none;border:1px solid rgba(255,255,255,0.2);color:rgba(255,255,255,0.6);padding:6px 14px;border-radius:6px;cursor:pointer;font-size:13px;font-family:var(--font);">
          Share this page
        </button>
      </div>
    </div>
  </footer>
```

Add to `<style>`:

```css
    .footer-grid { display:grid; grid-template-columns:1fr 1fr; gap:40px; margin-bottom:0; }
    @media (max-width:600px) { .footer-grid { grid-template-columns:1fr; } }
```

- [ ] **Step 2: Full end-to-end verification checklist**

```bash
python -m http.server 8000
```

Open http://localhost:8000 and confirm each item:

Layout:
- [ ] Sticky nav stays at top while scrolling; links smooth-scroll to sections
- [ ] Hero: teal background, white headline, amber stat box
- [ ] Problem: 4 stat cards, amber top border
- [ ] Solution: green-tinted background, 4 pillar cards
- [ ] FAQ: accordion, first item open
- [ ] CTA: teal background, address input
- [ ] Footer: coalition list, data sources, share button

Community lookup:
- [ ] "Chicago" returns a result card
- [ ] "Naperville" returns a result card with price change data
- [ ] "xyz123" returns "No results" message (with escaped text)
- [ ] Enter key triggers lookup

FAQ accordion:
- [ ] All 5 items expand and collapse correctly
- [ ] Arrow icon updates on toggle

CTA:
- [ ] Without API key: ILGA fallback links appear after any address entry
- [ ] Share button copies URL and changes text to "Copied"

Mobile (resize browser to 375px):
- [ ] Nav links hidden; hero, stats, pillars stack to single column
- [ ] No horizontal overflow anywhere

- [ ] **Step 3: Final commit**

```bash
git add index.html
git commit -m "feat: footer and BUILD Act website complete"
```

---

## Summary

After all tasks complete:
1. `python build_data.py` generates `data/community-data.json` with ~1300 IL municipalities
2. `python -m http.server 8000` serves the site at http://localhost:8000
3. Community lookup returns IHDA affordability + permit + Zillow price data
4. Legislator lookup shows ILGA fallback links without API key; real legislator cards with a configured key
5. Site is fully responsive at 375px mobile width
6. All 5 FAQ items expand/collapse correctly
