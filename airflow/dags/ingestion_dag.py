from airflow.decorators import dag, task
from pendulum import datetime
import pandas as pd, requests, os

RAW = "/opt/airflow/data/raw"          # mounted volume
URL = 'os.environ["DATA_URL"]'

@dag(schedule="0 */6 * * *", start_date=datetime(2025,4,20), catchup=False, tags=["ingest"])
def ingestion():
    @task
    def download():
        df = pd.read_csv(URL)
        path = f"{RAW}/transactions_{pd.Timestamp.now().date()}.csv"
        df.to_csv(path, index=False)
        return path
    download()

dag = ingestion()
