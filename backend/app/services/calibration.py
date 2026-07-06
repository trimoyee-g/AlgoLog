"""
Lightweight ML model (not an LLM) that learns YOUR personal difficulty-rating
pattern from your own attempt history, and predicts how you'll likely rate a
new problem before you solve it. Retrains on demand via /api/calibration/train.

Uses scikit-learn GradientBoostingRegressor - simple, no native-dependency
headaches (unlike xgboost), plenty for a few hundred rows of personal data.
"""
import os
import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sqlalchemy.orm import Session

from app.models import Attempt, Problem

_MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
MIN_SAMPLES_TO_TRAIN = 10


def _model_path(user_id: str) -> str:
    # One model per user, keyed by their id (already safe chars: a UUID).
    return os.path.join(_MODEL_DIR, f"calibration_model_{user_id}.joblib")


def _load_dataframe(db: Session, user_id: str) -> pd.DataFrame:
    rows = (
        db.query(
            Attempt.rating,
            Attempt.time_taken_minutes,
            Problem.platform,
            Problem.official_difficulty,
            Problem.tags,
        )
        .join(Problem, Attempt.problem_id == Problem.id)
        .filter(Attempt.user_id == user_id)
        .all()
    )
    df = pd.DataFrame(rows, columns=["rating", "time_taken_minutes", "platform", "official_difficulty", "tags"])
    df["platform"] = df["platform"].astype(str)
    df["official_difficulty"] = df["official_difficulty"].fillna("unknown").astype(str)
    df["tags"] = df["tags"].fillna("unknown").astype(str)
    df["time_taken_minutes"] = df["time_taken_minutes"].fillna(df["time_taken_minutes"].median() if len(df) else 30)
    return df


def train(db: Session, user_id: str) -> dict:
    df = _load_dataframe(db, user_id)
    if len(df) < MIN_SAMPLES_TO_TRAIN:
        return {"trained": False, "reason": f"Need at least {MIN_SAMPLES_TO_TRAIN} attempts, have {len(df)}."}

    X = df[["platform", "official_difficulty", "tags", "time_taken_minutes"]]
    y = df["rating"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), ["platform", "official_difficulty", "tags"]),
        ],
        remainder="passthrough",
    )
    pipeline = Pipeline(steps=[
        ("preprocess", preprocessor),
        ("model", GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=42)),
    ])
    pipeline.fit(X, y)
    joblib.dump(pipeline, _model_path(user_id))
    return {"trained": True, "samples_used": len(df)}


def predict(platform: str, official_difficulty: str | None, tags: str | None, time_taken_minutes: int | None, db: Session, user_id: str) -> tuple[float, str]:
    model_path = _model_path(user_id)
    if not os.path.exists(model_path):
        df = _load_dataframe(db, user_id)
        if len(df) == 0:
            return 3.0, "No history yet - defaulting to a neutral 3/5. Log a few attempts first."
        return float(df["rating"].mean()), "Model not trained yet - using your average rating so far. Call /api/calibration/train once you have 10+ attempts."

    pipeline = joblib.load(model_path)
    row = pd.DataFrame([{
        "platform": platform,
        "official_difficulty": official_difficulty or "unknown",
        "tags": tags or "unknown",
        "time_taken_minutes": time_taken_minutes or 30,
    }])
    pred = float(pipeline.predict(row)[0])
    pred = max(1.0, min(5.0, pred))
    return pred, "Predicted from your personal attempt history via a trained model."
