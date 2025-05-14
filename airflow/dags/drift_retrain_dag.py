# airflow/dags/retrain_dag.py  (Python 3.11, Airflow 2.8+)

from __future__ import annotations
from pathlib import Path
import json
import subprocess
import uuid

from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.decorators import dag
from pendulum import datetime

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator
from airflow.utils.trigger_rule import TriggerRule
from pendulum import datetime

import pandas as pd
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset
from evidently.metrics import DataDriftTable, DatasetDriftMetric
import logging
import time

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import pandas as pd


# Configure module‐level logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

RAW_BASE = Path("/opt/airflow/data/raw")          # v1/ v2/ vN/
PROCESSED = Path("/opt/airflow/data/processed")   # output parquet
MERGED    = Path("/opt/airflow/data/merged")
SEED = 42

@dag(
    schedule="@daily",          # or "@daily" – adjust to your cadence
    start_date=datetime(2025, 4, 1),
    catchup=False,
    tags=["retrain", "fraud"],
)
def retrain_on_drift():

    wait_for_new_data = EmptyOperator(task_id="new_data_arrived")

    # ------------------------------------------------------------------ #
    # Drift check                                                        #
    # ------------------------------------------------------------------ #
    @task(task_id="detect_new_version")
    def _detect_version() -> str:
        """Return newest version folder name (e.g. 'v3') if unseen."""
        seen: set[str] = Variable.get("seen_versions", default_var="").split(",")
        versions = sorted(p.name for p in RAW_BASE.iterdir() if p.is_dir())
        unseen = [v for v in versions if v and v not in seen]
        if not unseen:
            raise ValueError("no-op – nothing new")
        new_v = unseen[-1]
        Variable.set("seen_versions", ",".join(seen + [new_v]))
        return new_v

    @task.branch(task_id="branch_drift")
    def _branch(version: str) -> str:
        """Return task-id to follow, with detailed logging."""
        logger.info(f"Starting drift check for version: {version}")

        base_path = RAW_BASE / "v1" / "baseline.csv"
        if version == "v1":
            logger.info("No new version detected; skipping drift check")
            return "no_drift"
        new_path  = RAW_BASE / version / "latest.csv"
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
        
    def _push_pipeline_metrics(**context):
        # 1) grab DAG run timestamps
        dr = context["dag_run"]
        start_ts = dr.start_date.timestamp()
        end_ts   = time.time()
        duration = end_ts - start_ts

        # 2) compute rows processed (read the parquet you just wrote)
        #    adjust path if you have multiple outputs or different filenames
        df = pd.read_parquet(PROCESSED / "train.parquet")
        rows = len(df)
        throughput = rows / duration if duration > 0 else 0

        # 3) push to Pushgateway
        registry = CollectorRegistry()
        Gauge("pipeline_run_duration_seconds",
            "Total DAG run duration in seconds",
            registry=registry).set(duration)
        Gauge("pipeline_processed_rows_total",
            "Total rows processed by the DAG",
            registry=registry).set(rows)
        Gauge("pipeline_throughput_rows_per_second",
            "Rows processed per second",
            registry=registry).set(throughput)

        push_to_gateway(
            "pushgateway:9091",
            job=context["dag"].dag_id,
            registry=registry,
        )

    no_drift = EmptyOperator(task_id="no_drift")

    # ------------------------------------------------------------------ #
    #  Retrain path                                                      #
    # ------------------------------------------------------------------ #
    merge = BashMerge = BashOperator(
        task_id="merge_datasets",
        bash_command=(
            "python /opt/airflow/scripts/merge_versions.py "
            "{{ ti.xcom_pull(task_ids='detect_new_version') }}"
        )
        # → writes /data/merged/current.csv
    )

    featurize = BashOperator(
        task_id="featurize",
        bash_command=(
            "python /opt/airflow/scripts/featurize.py "
            f"{MERGED}/current.csv {PROCESSED}/train.parquet"
        ),
    )

    train = BashOperator(
        task_id="train_log_mlflow",
        env={"MLFLOW_TRACKING_URI": "http://mlflow:5000"},
        bash_command=(
            "python /opt/mlflow/train.py "
            f"{PROCESSED}/train.parquet "
            "{{ ti.xcom_pull(task_ids='detect_new_version') }}"
        ),
    )

    push_metrics = PythonOperator(
    task_id="push_pipeline_metrics",
    python_callable=_push_pipeline_metrics,
    provide_context=True,
    )

    # ------------------------------------------------------------------ #
    #  Wiring                                                             #
    # ------------------------------------------------------------------ #
    detect_version = _detect_version()      # task object
    branch = _branch(detect_version)        # pass XCom to the branch fn

    wait_for_new_data >> detect_version >> branch
    branch >> no_drift                     # skip path
    branch >> merge >> featurize >> train >>push_metrics   # drift-positive path

retrain_on_drift()
