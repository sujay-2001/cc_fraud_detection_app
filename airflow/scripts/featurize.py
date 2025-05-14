#!/usr/bin/env python3
"""
featurize.py – shrink high-cardinality ‘merchant’ & ‘job’, map state→region,
and save a training-ready Parquet file.

Usage
-----
python featurize.py raw.csv processed.parquet \
    [--top-merchants 50]
"""
import argparse, re
import pandas as pd
from pathlib import Path

TOP_MERCHANTS = 5
# ---------------------------------------------------------------------------
# 1. • low-cardinality region • (unchanged)
# ---------------------------------------------------------------------------
REGION_MAP = {
    **dict.fromkeys(
        ["CT","ME","MA","NH","RI","VT","NJ","NY","PA"], "Northeast"),
    **dict.fromkeys(
        ["IL","IN","MI","OH","WI","IA","KS","MN","MO","NE","ND","SD"],
        "Midwest"),
    **dict.fromkeys(
        ["DE","FL","GA","MD","NC","SC","VA","DC","WV","AL","KY","MS","TN",
         "AR","LA","OK","TX"],
        "South"),
    **dict.fromkeys(
        ["AZ","CO","ID","MT","NV","NM","UT","WY","AK","CA","HI","OR","WA"],
        "West"),
}

# ---------------------------------------------------------------------------
# 2. • broad job families •  (order matters – first match wins)
# ---------------------------------------------------------------------------
JOB_KEYWORD_MAP = {
    "engineer":          "Engineer",
    "developer":         "Engineer",
    "architect":         "Engineer",
    "scientist":         "Scientist",
    "research":          "Scientist",
    "analyst":           "Analyst",
    "data":              "Analyst",
    "teacher":           "Teacher",
    "professor":         "Teacher",
    "lecturer":          "Teacher",
    "nurse":             "Healthcare",
    "doctor":            "Healthcare",
    "physician":         "Healthcare",
    "psycholog":         "Healthcare",
    "therapist":         "Healthcare",
    "surgeon":           "Healthcare",
    "manager":           "Manager",
    "director":          "Manager",
    "officer":           "Officer",
    "administrator":     "Admin",
    "consultant":        "Consultant",
    "lawyer":            "Legal",
    "solicitor":         "Legal",
    "attorney":          "Legal",
    "accountant":        "Finance",
    "trader":            "Finance",
    "banker":            "Finance",
    "finance":           "Finance",
    "artist":            "Creative",
    "designer":          "Creative",
    "editor":            "Creative",
    "writer":            "Creative",
    "sales":             "Sales",
    "marketing":         "Sales",
}

JOB_DEFAULT = "Other"
MERCHANT_PREFIX = "fraud_"

# ---------------------------------------------------------------------------
def collapse_job(title: str) -> str:
    """Map verbose job titles to a broad family."""
    low = title.lower()
    for kw, fam in JOB_KEYWORD_MAP.items():
        if kw in low:
            return fam
    return JOB_DEFAULT


def build_merchant_map(series: pd.Series, top_n: int):
    """Return a dict: raw → cleaned/Other, keeping only top-n merchants."""
    cleaned = series.str.replace(f"^{MERCHANT_PREFIX}", "", regex=True)
    top_merchants = set(cleaned.value_counts().nlargest(top_n).index)
    return {raw: (name if (name := raw[len(MERCHANT_PREFIX):]) in top_merchants
                  else "Other")
            for raw in series.unique()}


def featurize(raw_csv: Path, out_parquet: Path, top_merchants: int = 50):
    df = pd.read_csv(
        raw_csv,
        parse_dates=["trans_date_trans_time", "dob"],
        dayfirst=False,
    )

    # ── Temporal & age features ───────────────────────────────────────────
    df["tx_hour"]       = df["trans_date_trans_time"].dt.hour
    df["tx_dayofweek"]  = df["trans_date_trans_time"].dt.dayofweek
    df["tx_month"]      = df["trans_date_trans_time"].dt.month
    df["age"] = ((df["trans_date_trans_time"] - df["dob"]).dt.days // 365)

    # ── Region (state → US Census region) ────────────────────────────────
    if "state" in df.columns:
        df["region"] = df["state"].map(REGION_MAP).fillna("Other")

    # ── Merchant collapse ────────────────────────────────────────────────
    if "merchant" in df.columns:
        m_map = build_merchant_map(df["merchant"], top_merchants)
        df["merchant_grouped"] = df["merchant"].map(m_map)

    # ── Job collapse ─────────────────────────────────────────────────────
    if "job" in df.columns:
        df["job_grouped"] = df["job"].apply(collapse_job)

    # ── Raw/PII drops ────────────────────────────────────────────────────
    drop_cols = [
        "Unnamed: 0","trans_date_trans_time","dob","first","last","street",
        "city","state","zip","trans_num","unix_time","cc_num","city_pop",
        "is_fraud","merchant","job"
    ]
    df["label"] = df["is_fraud"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns])

    # ── One-hot encode remaining categoricals ────────────────────────────
    cat_cols = [c for c in
                ["merchant_grouped","category","gender","job_grouped",
                 "region"]
                if c in df.columns]
    if cat_cols:
        df = pd.get_dummies(df, columns=cat_cols, drop_first=True)

    # ── Save ──────────────────────────────────────────────────────────────
    out_parquet.parent.mkdir(exist_ok=True, parents=True)
    df.to_parquet(out_parquet, index=False)
    print(
        f"Featurization complete: {df.shape[0]:,} rows, "
        f"{len(df.columns):,} columns – saved → {out_parquet}"
    )


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Clean & encode raw transactions for fraud-model training"
    )
    ap.add_argument("input_csv",  type=Path,
                    help="Raw CSV path (e.g. data/raw/latest.csv)")
    ap.add_argument("output_parquet", type=Path,
                    help="Destination Parquet path")
    args = ap.parse_args()
    featurize(args.input_csv, args.output_parquet, TOP_MERCHANTS)
