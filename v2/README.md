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
(GitHub Pages, Netlify, Vercel). Must be served over HTTP -- the
community lookup uses fetch() to load data/community-data.json.

## Data sources

- IHDA Affordable Housing Planning and Appeal Act (AHPAA) 2023
- Census Building Permits Survey 2014-2024
- Zillow Home Value Index (ZHVI) - city level, all homes, mid-tier
