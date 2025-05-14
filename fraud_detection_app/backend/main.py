from fastapi import FastAPI, Depends, Request, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
import pandas as pd, os
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter
from pydantic import BaseModel, Field, conint, confloat
import requests
import json

MODEL_ENDPOINT = os.getenv("MODEL_ENDPOINT", "http://localhost:5001/invocations")
FRAUD_THRESHOLD = float(os.getenv("FRAUD_THRESHOLD", 0.8))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your_gemini_api_key")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_URL   = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)
# ─── Models ────────────────────────────────────────────────────────────────────

class InputForm(BaseModel):
    # numeric (floats)
    amt:          confloat(strict=True)          = Field(..., example=123.45)
    lat:          confloat(strict=True)
    long:         confloat(strict=True)
    merch_lat:    confloat(strict=True)
    merch_long:   confloat(strict=True)

    # numeric (ints)
    tx_hour:      conint(ge=0, le=23)
    tx_dayofweek: conint(ge=0, le=6)
    tx_month:     conint(ge=1, le=12)
    age:          conint(ge=0)

    # one-hot booleans --------------
    merchant_grouped_Cormier_LLC:  bool = False
    merchant_grouped_Kuhn_LLC:     bool = False
    merchant_grouped_Kilback_LLC:  bool = False
    merchant_grouped_Other:        bool = False
    merchant_grouped_Schumm_PLC:   bool = False

    category_food_dining:      bool = False
    category_gas_transport:    bool = False
    category_grocery_net:      bool = False
    category_grocery_pos:      bool = False
    category_health_fitness:   bool = False
    category_home:             bool = False
    category_kids_pets:        bool = False
    category_misc_net:         bool = False
    category_misc_pos:         bool = False
    category_personal_care:    bool = False
    category_shopping_net:     bool = False
    category_shopping_pos:     bool = False
    category_travel:           bool = False

    gender_M: bool = False

    job_grouped_Analyst:    bool = False
    job_grouped_Consultant: bool = False
    job_grouped_Creative:   bool = False
    job_grouped_Engineer:   bool = False
    job_grouped_Finance:    bool = False
    job_grouped_Healthcare: bool = False
    job_grouped_Legal:      bool = False
    job_grouped_Manager:    bool = False
    job_grouped_Officer:    bool = False
    job_grouped_Other:      bool = False
    job_grouped_Sales:      bool = False
    job_grouped_Scientist:  bool = False
    job_grouped_Teacher:    bool = False

    region_Northeast: bool = False
    region_South:     bool = False
    region_West:      bool = False


class Feedback(BaseModel):
    prediction: str       # "fraud" or "not_fraud"
    correct: bool

# ─── Load & App Setup ─────────────────────────────────────────────────────────

app = FastAPI(title="Fraud‑Detection API")
app.state.latest: dict[str, dict] = {}      # { user_id → {"features":…, "prediction":…, "proba":…} }
# Instrument before startup
Instrumentator().instrument(app).expose(app)

# Routers & CORS
from auth import router as auth_router, get_current_user
from clients import router_clients
app.include_router(auth_router, prefix="/auth")
app.include_router(router_clients)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Prometheus Counters ───────────────────────────────────────────────────────

# Total call counters
MODEL_PREDICT_TOTAL = Counter(
    "model_predict_total",
    "Number of model predict calls per client",
    ["client"]
)
MODEL_EXPLAIN_TOTAL = Counter(
    "model_explain_total",
    "Number of model explain calls per client",
    ["client"]
)

# Success vs failure counters for predict
MODEL_PREDICT_SUCCESS = Counter(
    "model_predict_success_total",
    "Number of successful model predict calls per client",
    ["client"]
)
MODEL_PREDICT_FAILURE = Counter(
    "model_predict_failure_total",
    "Number of failed model predict calls per client",
    ["client"]
)

# Success vs failure counters for explain
MODEL_EXPLAIN_SUCCESS = Counter(
    "model_explain_success_total",
    "Number of successful model explain calls per client",
    ["client"]
)
MODEL_EXPLAIN_FAILURE = Counter(
    "model_explain_failure_total",
    "Number of failed model explain calls per client",
    ["client"]
)

# True/False positives/negatives for predict
MODEL_PREDICT_TP = Counter(
    "model_predict_true_positive_total",
    "Number of true positives per client",
    ["client"]
)
MODEL_PREDICT_FP = Counter(
    "model_predict_false_positive_total",
    "Number of false positives per client",
    ["client"]
)
MODEL_PREDICT_TN = Counter(
    "model_predict_true_negative_total",
    "Number of true negatives per client",
    ["client"]
)
MODEL_PREDICT_FN = Counter(
    "model_predict_false_negative_total",
    "Number of false negatives per client",
    ["client"]
)

# ─── Middleware for call counting ──────────────────────────────────────────────

@app.middleware("http")
async def count_calls(request: Request, call_next):
    client = getattr(request.state, "user", "anon")
    route  = request.url.path

    if route == "/predict":
        MODEL_PREDICT_TOTAL.labels(client=client).inc()
    elif route == "/explain":
        MODEL_EXPLAIN_TOTAL.labels(client=client).inc()

    try:
        response = await call_next(request)
        status = response.status_code

        if route == "/predict":
            if 200 <= status < 300:
                MODEL_PREDICT_SUCCESS.labels(client=client).inc()
            else:
                MODEL_PREDICT_FAILURE.labels(client=client).inc()

        elif route == "/explain":
            if 200 <= status < 300:
                MODEL_EXPLAIN_SUCCESS.labels(client=client).inc()
            else:
                MODEL_EXPLAIN_FAILURE.labels(client=client).inc()

        return response

    except Exception:
        if route == "/predict":
            MODEL_PREDICT_FAILURE.labels(client=client).inc()
        elif route == "/explain":
            MODEL_EXPLAIN_FAILURE.labels(client=client).inc()
        raise

# ─── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/predict")
def predict(payload: InputForm, user=Depends(get_current_user)):
    features = payload.model_dump()             # → plain dict ready for JSON
    resp = requests.post(
        MODEL_ENDPOINT,
        json={"inputs": [features]},
        timeout=5,
    )
    resp.raise_for_status()
    proba = resp.json()["predictions"][0]
    prediction = "fraud" if proba >= FRAUD_THRESHOLD else "not_fraud"

    user_id = getattr(user, "email", "anon")
    app.state.latest[user_id] = {
        "features": features,
        "prediction": prediction,
        "proba": proba,
    }

    return {"fraud_probability": proba, "prediction": prediction}

@app.get("/explain/latest")
def explain_latest(user=Depends(get_current_user)):
    """Return the last input + prediction for this user (or empty {})."""
    return app.state.latest.get(getattr(user, "email", "anon"), {})

@app.get("/explain/prompt")
def get_prompt(user=Depends(get_current_user)):
    user_id = getattr(user, "email", "anon")
    payload = app.state.latest.get(user_id)
    if not payload:
        raise HTTPException(404, "No prompt available; please run /predict first")

    features = payload["features"]
    prediction = payload["prediction"]
    proba = payload["proba"]

    prompt = (
        "You are an explainable-AI assistant for a credit-card fraud-detection model.\n"
        "Given the JSON representation of the transaction features and the model’s output, "
        "explain—at a business-analyst level—*why* the model predicted it as "
        f"**{prediction.upper()}** (probability {proba:.2f}). "
        "Focus on the most influential features and avoid deep math jargon.\n\n"
        f"Transaction JSON:\n```json\n{json.dumps(features, indent=2)}\n```\n"
    )
    return {"prompt": prompt}


@app.post("/explain")
def explain(body: dict, user=Depends(get_current_user)):
    user_id = getattr(user, "email", "anon")

    # If the client sent us a raw prompt, use it directly
    if "prompt" in body:
        prompt = body["prompt"]
    else:
        # else fall back to old behavior: build prompt from stored payload
        payload = body or app.state.latest.get(user_id)
        if not payload:
            raise HTTPException(400, "No previous prediction found; please run /predict first")

        features = payload["features"]
        prediction = payload["prediction"]
        proba = payload["proba"]
        prompt = (
            "You are an explainable-AI assistant for a credit-card fraud-detection model.\n"
            "Given the JSON representation of the transaction features and the model’s output, "
            "explain—at a business-analyst level—*why* the model predicted it as "
            f"**{prediction.upper()}** (probability {proba:.2f}). "
            "Focus on the most influential features and avoid deep math jargon.\n\n"
            f"Transaction JSON:\n```json\n{json.dumps(features, indent=2)}\n```\n"
        )

    # Call Gemini
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        gresp = requests.post(GEMINI_URL, json=payload, timeout=15)
        gresp.raise_for_status()
        data = gresp.json()
        explanation = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as err:
        MODEL_EXPLAIN_FAILURE.labels(client=user_id).inc()
        raise HTTPException(500, f"Gemini error: {err}")

    return {"explanation": explanation}


@app.post("/feedback")
def feedback(
    payload: Feedback,
    request: Request,
    user=Depends(get_current_user),
):
    client = getattr(request.state, "user", "anon")
    pred, corr = payload.prediction, payload.correct

    if pred == "fraud" and corr:
        MODEL_PREDICT_TP.labels(client=client).inc()
    elif pred == "fraud" and not corr:
        MODEL_PREDICT_FP.labels(client=client).inc()
    elif pred == "not_fraud" and corr:
        MODEL_PREDICT_TN.labels(client=client).inc()
    elif pred == "not_fraud" and not corr:
        MODEL_PREDICT_FN.labels(client=client).inc()

    return {"status": "ok"}