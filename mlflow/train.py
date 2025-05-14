#!/usr/bin/env python
# mlflow/train.py
# ---------------------------------------------------------------
import argparse, json, os, re, sys, tempfile
from pathlib import Path
from prometheus_client import CollectorRegistry, Gauge, pushadd_to_gateway
from mlflow import lightgbm as mlflow_lgb 
import lightgbm as lgb
import mlflow
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient
from sklearn.metrics import (
    roc_auc_score,
    accuracy_score,
    f1_score,
    log_loss,
)
from sklearn.model_selection import train_test_split

from evidently.metrics import DatasetDriftMetric
from evidently.report import Report

# ---------------------------------------------------------------
EXPERIMENT = "Fraud detection model training"
PARAMS_PATH = Path(__file__).with_name("params.json")
BASELINE_CSV = Path("/opt/airflow/data/raw/v1/baseline.csv")  
SEED = 42

mlflow.set_experiment(EXPERIMENT)
mlflow.lightgbm.autolog(log_models=False)  # we'll log the model manually

# ---------------------------------------------------------------
def sanitize(df: pd.DataFrame) -> pd.DataFrame:
    """LightGBM forbids some chars in column names; replace them once."""
    df = df.copy()
    df.columns = [re.sub(r"[^\w]", "_", c) for c in df.columns]
    return df


def load_params() -> dict:
    with PARAMS_PATH.open() as f:
        return json.load(f)


def evaluate(model, X_test, y_test) -> dict[str, float]:
    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)
    return {
        "auc": roc_auc_score(y_test, proba),
        "log_loss": log_loss(y_test, proba),
        "accuracy": accuracy_score(y_test, pred),
        "f1": f1_score(y_test, pred),
    }


def compute_drift(ref: pd.DataFrame, cur: pd.DataFrame) -> tuple[float, str]:
    """Return (result, html_report_path)."""
    report = Report(metrics=[DatasetDriftMetric()])
    report.run(reference_data=ref, current_data=cur)
    result = report.as_dict()["metrics"][0]["result"]

    html_path = tempfile.mktemp(suffix=".html")
    report.save_html(html_path)
    return result, html_path

# ---------------------------------------------------------------
def main(data_path: str, baseline_path: str, new_version: str):
    df_full = sanitize(pd.read_parquet(data_path))
    X = df_full.drop(columns="label")
    y = df_full["label"]

    X_train, X_tmp, y_train, y_tmp = train_test_split(
        X, y, test_size=0.30, random_state=SEED, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_tmp, y_tmp, test_size=0.50, random_state=SEED, stratify=y_tmp
    )

    params = load_params()

    with mlflow.start_run() as run:
        # ---------------- train -----------------
        model = lgb.LGBMClassifier(**params)
        model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            eval_metric="auc",
            callbacks=[lgb.log_evaluation(period=50)],
        )

        # -------------- metrics -----------------
        mlflow.log_metric("train_rows", len(X_train))
        mlflow.log_metric("val_rows", len(X_val))
        mlflow.log_metric("test_rows", len(X_test))

        for k, v in evaluate(model, X_test, y_test).items():
            mlflow.log_metric(k, v)
        registry = CollectorRegistry()
        for k, v in evaluate(model, X_test, y_test).items():
            Gauge(f"fraud_{k}", f"{k} on test split", registry=registry).set(v)


        # -------------- drift -------------------
        
        if new_version != "v1":
            # new version: compute drift
            ref_df = pd.read_csv(baseline_path)
            cur_df = pd.read_csv(f'/opt/airflow/data/raw/{new_version}/latest.csv')
            ref_df = ref_df.sample(n=1000, random_state=SEED)
            cur_df = cur_df.sample(n=1000, random_state=SEED)
            result, html = compute_drift(ref_df, cur_df)
            mlflow.log_metric("drift_share", result["drift_share"])
            mlflow.log_metric("share_of_drifted_columns", result["share_of_drifted_columns"])
            mlflow.log_metric("dataset_drift", result["dataset_drift"])
            mlflow.log_artifact(html, artifact_path="drift_report")
            Gauge("share_of_drifted_columns", "Share of drifted cols", registry=registry).set(result["share_of_drifted_columns"])
            Gauge("drift_share", "Drift share", registry=registry).set(result["drift_share"])
            Gauge("dataset_drift", "Dataset drift", registry=registry).set(result["dataset_drift"])
            
        pushadd_to_gateway("pushgateway:9091", job="fraud_train", registry=registry)
        # -------------- model -------------------
        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            input_example=X_test.head(1),
            registered_model_name="fraud_model",
            signature=mlflow.models.infer_signature(X_test, model.predict_proba(X_test)),
            pip_requirements=[
            "scikit-learn==1.4.1.post1",
            "lightgbm==4.3.0"
            ],            
        )

        # auto-promote newest version
        client = MlflowClient()
        latest = client.get_latest_versions("fraud_model", stages=["None"])[0]
        client.transition_model_version_stage(
            "fraud_model",
            latest.version,
            stage="Production",
            archive_existing_versions=True,
        )
        print(f"🚀 Promoted fraud_model v{latest.version} to Production")


# ---------------------------------------------------------------
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("data_path", help="processed parquet with label column")
    p.add_argument("new_version", help="version folder name (e.g. v2, v3, …)")
    args = p.parse_args()
    main(args.data_path, str(BASELINE_CSV), args.new_version)
