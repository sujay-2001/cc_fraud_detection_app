# airflow/Dockerfile
ARG AIRFLOW_VERSION=2.10.4
FROM apache/airflow:${AIRFLOW_VERSION}-python3.11

USER root
# ------- OS deps -------                                    ▼ add libgomp1
RUN apt-get update && apt-get install -y --no-install-recommends git libgomp1 \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

USER airflow
# ------- Python deps -------
RUN pip install --no-cache-dir \
        mlflow==2.10.2 \
        lightgbm \
        scikit-learn pandas dvc[s3] evidently==0.4.19


