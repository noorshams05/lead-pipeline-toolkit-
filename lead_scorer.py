"""
Lead Scoring Tool
------------------
Scores and ranks prospect/lead lists for outbound sales and real estate
wholesaling pipelines. Takes a CSV of leads and outputs a ranked CSV
sorted by priority score (highest = call first).

Usage:
    python lead_scorer.py leads.csv ranked_output.csv

Input CSV columns (case-insensitive, order doesn't matter):
    name             - lead/contact name
    phone            - phone number (used to check completeness)
    email            - email address (used to check completeness)
    last_contact_days_ago  - integer, days since last touch (blank = never contacted)
    contact_attempts - integer, number of outreach attempts so far
    estimated_value  - numeric, deal/property/deal value estimate
    motivation_score - integer 1-10, how motivated/likely-to-convert (your own estimate)

Any missing columns are treated as 0 / blank and simply contribute less
to the score rather than crashing the script.
"""

import csv
import sys


# ---- Scoring weights (tune these to match how you actually prioritize) ----
WEIGHTS = {
    "completeness": 15,   # has both phone and email
    "freshness": 25,      # contacted recently = warmer lead
    "low_attempts": 15,   # fewer attempts so far = not yet burned out
    "value": 25,          # higher estimated deal value
    "motivation": 20,     # your own qualitative motivation score
}


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def score_lead(row, max_value):
    """Returns a 0-100 priority score for a single lead row."""
    score = 0.0

    # Completeness: do we have a phone and email to actually reach them?
    has_phone = bool(row.get("phone", "").strip())
    has_email = bool(row.get("email", "").strip())
    completeness_ratio = (has_phone + has_email) / 2
    score += completeness_ratio * WEIGHTS["completeness"]

    # Freshness: leads contacted recently (or never) score higher than
    # leads gone cold. Never-contacted = max freshness (untapped).
    days_ago = row.get("last_contact_days_ago", "").strip()
    if days_ago == "":
        freshness_ratio = 1.0
    else:
        days_ago = safe_float(days_ago)
        # Decays over 30 days; floors at 0
        freshness_ratio = max(0.0, 1 - (days_ago / 30))
    score += freshness_ratio * WEIGHTS["freshness"]

    # Low attempts: leads you haven't hammered yet get priority over
    # ones you've already called 8 times with no response.
    attempts = safe_int(row.get("contact_attempts", 0))
    low_attempts_ratio = max(0.0, 1 - (attempts / 8))
    score += low_attempts_ratio * WEIGHTS["low_attempts"]

    # Value: scaled against the highest value in the current batch so
    # it's always relative, not tied to a hardcoded dollar amount.
    value = safe_float(row.get("estimated_value", 0))
    value_ratio = (value / max_value) if max_value > 0 else 0
    score += value_ratio * WEIGHTS["value"]

    # Motivation: your own 1-10 gut/data score on how likely they convert
    motivation = safe_int(row.get("motivation_score", 0))
    motivation_ratio = min(1.0, motivation / 10)
    score += motivation_ratio * WEIGHTS["motivation"]

    return round(score, 1)


def load_leads(input_path):
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # normalize headers to lowercase so the script is forgiving
        normalized_rows = []
        for row in reader:
            normalized_rows.append({k.strip().lower(): v for k, v in row.items()})
        return normalized_rows


def main():
    if len(sys.argv) != 3:
        print("Usage: python lead_scorer.py <input_leads.csv> <output_ranked.csv>")
        sys.exit(1)

    input_path, output_path = sys.argv[1], sys.argv[2]

    rows = load_leads(input_path)
    if not rows:
        print("No rows found in input file.")
        sys.exit(1)

    max_value = max(safe_float(r.get("estimated_value", 0)) for r in rows) or 1

    for row in rows:
        row["priority_score"] = score_lead(row, max_value)

    ranked = sorted(rows, key=lambda r: r["priority_score"], reverse=True)

    fieldnames = list(ranked[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(ranked)

    print(f"Scored {len(ranked)} leads. Top 5 priority leads:")
    for row in ranked[:5]:
        name = row.get("name", "Unknown")
        print(f"  {row['priority_score']:>5} — {name}")
    print(f"\nFull ranked list written to: {output_path}")


if __name__ == "__main__":
    main()
