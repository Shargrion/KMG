"""Machine learning model trainer."""

from pathlib import Path

import joblib
import logging
from sklearn.ensemble import GradientBoostingClassifier

MODEL_PATH = Path(__file__).resolve().parents[2] / "project_metadata" / "MLModels" / "model_v1.pkl"


def train(features: list[list[float]], labels: list[int]) -> None:
    """Train a simple model and save to disk."""
    clf = GradientBoostingClassifier()
    clf.fit(features, labels)
    joblib.dump(clf, MODEL_PATH)


def update_model() -> None:
    """Retrain the model with recent data."""
    logging.info("Updating ML model")
    train([[0.0, 0.0], [1.0, 1.0]], [0, 1])
