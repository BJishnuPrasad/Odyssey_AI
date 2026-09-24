"""
src/models/train.py
-------------------
Trains a Random Forest classifier on the feature table at
    data/processed/features/site_features.csv

Saves model artefact + evaluation report to outputs/.

Run
---
    python -m src.models.train
"""

from __future__ import annotations

import json
import pathlib
import pickle

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler

from src.utils.config import cfg
from src.utils.logger import get_logger

log = get_logger(__name__)

FEATURE_COLS = ["elevation", "slope", "dist_water", "dist_road", "dist_building", "landuse_code"]
TARGET_COL   = "label"

OUT_MODELS  = pathlib.Path(cfg.paths.outputs.models)
OUT_REPORTS = pathlib.Path(cfg.paths.outputs.reports)
OUT_MODELS.mkdir(parents=True, exist_ok=True)
OUT_REPORTS.mkdir(parents=True, exist_ok=True)


def load_data() -> tuple[np.ndarray, np.ndarray]:
    df = pd.read_csv(cfg.files.site_features)
    # Only rows with a real label
    df = df[df[TARGET_COL].isin([0, 1])].dropna(subset=FEATURE_COLS)
    X = df[FEATURE_COLS].values
    y = df[TARGET_COL].values.astype(int)
    log.info("Dataset: %d samples, %d positive sites", len(y), y.sum())
    return X, y


def train() -> None:
    X, y = load_data()

    # ── Train / test split ────────────────────────────────────────────────────
    mc = cfg.model
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=mc.test_size, random_state=mc.random_state, stratify=y
    )

    # Scale features (RF doesn't need it, but kept for future model swaps)
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test  = scaler.transform(X_test)

    # ── Train ─────────────────────────────────────────────────────────────────
    log.info("Training %s …", mc.type)
    clf = RandomForestClassifier(
        n_estimators=mc.n_estimators,
        max_depth=mc.max_depth if mc.max_depth != "null" else None,
        random_state=mc.random_state,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    # ── Evaluate ──────────────────────────────────────────────────────────────
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]
    auc    = roc_auc_score(y_test, y_prob)

    report = classification_report(y_test, y_pred, output_dict=True)
    cm     = confusion_matrix(y_test, y_pred).tolist()

    log.info("AUC-ROC: %.4f", auc)
    log.info("\n%s", classification_report(y_test, y_pred))

    # Cross-validation
    cv = StratifiedKFold(n_splits=mc.cross_validation_folds, shuffle=True, random_state=mc.random_state)
    cv_scores = cross_val_score(clf, np.vstack([X_train, X_test]),
                                np.hstack([y_train, y_test]), cv=cv, scoring="roc_auc")
    log.info("CV AUC: %.4f ± %.4f", cv_scores.mean(), cv_scores.std())

    # ── Save artefacts ────────────────────────────────────────────────────────
    model_path  = OUT_MODELS / "random_forest.pkl"
    scaler_path = OUT_MODELS / "scaler.pkl"
    report_path = OUT_REPORTS / "eval_report.json"

    with open(model_path,  "wb") as f: pickle.dump(clf,    f)
    with open(scaler_path, "wb") as f: pickle.dump(scaler, f)

    eval_results = {
        "auc_roc":        auc,
        "cv_auc_mean":    float(cv_scores.mean()),
        "cv_auc_std":     float(cv_scores.std()),
        "classification_report": report,
        "confusion_matrix": cm,
        "feature_importance": dict(zip(FEATURE_COLS, clf.feature_importances_.tolist())),
    }
    with open(report_path, "w") as f:
        json.dump(eval_results, f, indent=2)

    log.info("Model saved → %s", model_path)
    log.info("Report saved → %s", report_path)


if __name__ == "__main__":
    train()
