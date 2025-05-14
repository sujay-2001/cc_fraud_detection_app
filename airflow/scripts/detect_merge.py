import time
from pathlib import Path
import pandas as pd
from evidently.report import Report
from evidently.metrics import DatasetDriftMetric
import logging
import sys
SEED = 42

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
def _detect_version(seen_path, raw_dir) -> str:
    """Return newest version folder name (e.g. 'v3') if unseen."""
    with open(seen_path, "r") as f:
        seen = f.read().split(",")
    if not seen:
        seen = []
    versions = sorted(p.name for p in raw_dir.iterdir() if p.is_dir())
    unseen = [v for v in versions if v and v not in seen]
    if not unseen:
        raise ValueError("no-op – nothing new")
    new_v = unseen[-1]
    seen = ",".join(seen + [new_v])
    with open(seen_path, "w") as f:
        f.write(seen)
    return new_v

def _branch(raw_dir, version) -> str:
    """Return task-id to follow, with detailed logging."""
    logger.info(f"Starting drift check for version: {version}")
    base_path = raw_dir / "v1" / "baseline.csv"
    if version == "v1":
        logger.info("No new version detected; skipping drift check")
        return "no_drift"
    new_path  = raw_dir / version / "latest.csv"
    logger.info(f"Baseline file: {base_path}")
    logger.info(f"New file:      {new_path}")

    # 1) Read in CSVs
    t0 = time.time()
    base_df = pd.read_csv(base_path)
    logger.info(f"Loaded baseline.csv: {base_df.shape} in {time.time() - t0:.2f}s")
    t1 = time.time()
    new_df = pd.read_csv(new_path)
    logger.info(f"Loaded latest.csv:   {new_df.shape} in {time.time() - t1:.2f}s")
    base_df = base_df.sample(n=1000, random_state=SEED)
    new_df  = new_df.sample(n=1000, random_state=SEED)
    # 2) Build and run drift report
    report = Report(metrics=[DatasetDriftMetric()])

    logger.info("Running DataDriftTable report…")
    t2 = time.time()
    report.run(reference_data=base_df, current_data=new_df)
    t3 = time.time()
    logger.info(f"DataDriftTable computation took {t3 - t2:.2f}s")       
    result = report.as_dict()["metrics"][0]["result"]
    drift_detected = result["dataset_drift"]

    if drift_detected:
        logger.info(f"Drift detected; branching to merge_datasets")
        return "merge_datasets"
    else:
        logger.info(f"No Drift detected; branching to no_drift")
        return "no_drift"
    
def merge_datasets(raw_dir: str, new_version: str):
    baseline  = raw_dir / "v1" / "baseline.csv"
    new_csv   = raw_dir / new_version / "latest.csv"     # argv[1] = v2, v3 …
    df = pd.concat([pd.read_csv(baseline), pd.read_csv(new_csv)]).drop_duplicates()
    out = Path("/opt/airflow/data/merged/current.csv")
    out.parent.mkdir(exist_ok=True, parents=True)
    df.to_csv(out, index=False)

if __name__ == '__main__':
    seen_path = sys.argv[1]  # Path to seen.txt
    raw_dir = sys.argv[2]  # Path to raw data directory
    version = _detect_version(seen_path, raw_dir)
    res = _branch(raw_dir, version)
    if res == "merge_datasets":
        merge_datasets(raw_dir, version)
    else:
        logger.info("No drift detected; no action taken.")