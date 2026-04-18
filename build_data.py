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
            ), 0)           AS units_built_2014_2024,
            AVG(NULLIF(b.population, 0)) AS avg_population
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


def load_zillow_illinois_data(url) -> pd.DataFrame:
    """Download Zillow ZHVI city CSV, return IL rows with pct_change and raw values."""
    print("Downloading Zillow ZHVI data...")
    if isinstance(url, Path):
        text = url.read_text(encoding="utf-8")
    else:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        text = resp.text

    df = pd.read_csv(io.StringIO(text))

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
    return il[["zillow_key", "zillow_city", "val_start", "val_end", "home_value_change_pct"]]


def merge_and_export(db_df: pd.DataFrame, zillow_df: pd.DataFrame, output_path: Path) -> None:
    """Merge DB and Zillow data, export to JSON for the website."""
    df = db_df.copy()
    df["db_key"] = df["raw_name"].apply(normalize_name)

    merged = df.merge(zillow_df, left_on="db_key", right_on="zillow_key", how="left")

    records = []
    for _, row in merged.iterrows():
        hvc = row["home_value_change_pct"]
        val_start = row["val_start"]
        val_end = row["val_end"]

        # avg_units_per_1000_per_year: (total units / avg_population / 10 years) * 1000
        avg_pop = row["avg_population"]
        units = int(row["units_built_2014_2024"])
        if pd.notna(avg_pop) and avg_pop > 0 and units > 0:
            avg_per_1000 = round((units / avg_pop / 10) * 1000, 1)
        else:
            avg_per_1000 = None

        records.append({
            "name": row["raw_name"],
            "county": row["county"] if pd.notna(row["county"]) else None,
            "affordability_pct": round(float(row["affordability_pct"]), 1),
            "is_exempt": bool(row["is_exempt"]),
            "units_built_2014_2024": units,
            "home_value_change_pct": round(float(hvc), 1) if pd.notna(hvc) else None,
            "home_value_start": int(round(float(val_start))) if pd.notna(val_start) else None,
            "home_value_end": int(round(float(val_end))) if pd.notna(val_end) else None,
            "avg_units_per_1000_per_year": avg_per_1000,
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


if __name__ == "__main__":
    print("Loading IHDA + BPS data from SQLite...")
    db_df = load_illinois_db_data(DB_PATH)
    print(f"  {len(db_df)} municipalities loaded")

    zillow_df = load_zillow_illinois_data(ZILLOW_URL)
    merge_and_export(db_df, zillow_df, OUTPUT_PATH)
