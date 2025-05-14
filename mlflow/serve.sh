export MLFLOW_TRACKING_URI=http://localhost:5001   # tracking server
mlflow models serve \
      -m models:/fraud_model/Production \
      --env-manager=local \
      --host 0.0.0.0 --port 5002
