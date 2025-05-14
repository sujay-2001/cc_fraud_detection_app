export MLFLOW_TRACKING_URI=http://localhost:5001   # tracking server

mlflow models build-docker \
  -m models:/fraud_model/Production \
  -n sujays2001/fraud-detection-model:prod-v1 \
  --platform linux/arm64,linux/amd64 \
  --enable-mlserver

docker tag sujays2001/fraud-detection-model:prod-v1 sujays2001/fraud-detection-model:prod-v1

docker push sujays2001/fraud-detection-model:prod-v1