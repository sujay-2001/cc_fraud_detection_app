from airflow.operators.bash import BashOperator
from airflow.decorators import dag
from pendulum import datetime

@dag(start_date=datetime(2025, 4, 20), schedule="@daily", catchup=False)
def training():
    featurize = BashOperator(
        task_id="featurize",
        bash_command=(
            "python /opt/airflow/scripts/featurize.py "
            "/opt/airflow/data/raw/v1.csv "
            "/opt/airflow/data/processed/train.parquet"
        ),
        env={"PYTHONUNBUFFERED": "1"},
        append_env=True,
    )

    train = BashOperator(
        task_id="train_model",
        bash_command=(
            "python /opt/mlflow/train.py "
            "/opt/airflow/data/processed/train.parquet"
        ),
        env={"MLFLOW_TRACKING_URI": "http://mlflow:5000"},  # ← service name
        append_env=True,
    )

    featurize >> train

dag = training()
