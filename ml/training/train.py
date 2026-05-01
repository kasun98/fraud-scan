import json
import warnings
from pathlib import Path

import mlflow
import mlflow.xgboost
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.preprocessing import LabelEncoder

from features import (
    ALL_FEATURES,
    CATEGORICAL_FEATURES,
    CATEGORY_MAPS,
    NUMERIC_FEATURES,
    TARGET,
)

warnings.filterwarnings("ignore")

DATA_PATH    = Path("ml/data/transactions_100k.csv")
MLFLOW_URI   = "http://localhost:5001"
EXPERIMENT   = "fraud-detection-baseline"


def load_and_prepare(path: Path) -> tuple[pd.DataFrame, pd.Series]:
    print("Loading data...")
    df = pd.read_csv(path)
    print(f"  Shape: {df.shape}")
    print(f"  Fraud rate: {df[TARGET].mean()*100:.2f}%")

    # Encode categoricals using shared map
    for col, mapping in CATEGORY_MAPS.items():
        df[col] = df[col].map(mapping).fillna(0).astype(int)

    # Fill missing numerics
    df["hours_since_last_txn"] = df["hours_since_last_txn"].replace(-1, df["hours_since_last_txn"].median())
    df[NUMERIC_FEATURES]       = df[NUMERIC_FEATURES].fillna(0)

    X = df[ALL_FEATURES]
    y = df[TARGET].astype(int)
    return X, y


def train():
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT)

    X, y = load_and_prepare(DATA_PATH)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train, y_train, test_size=0.15, stratify=y_train, random_state=42
    )

    print(f"Train: {len(X_train):,} | Val: {len(X_val):,} | Test: {len(X_test):,}")

    # Class imbalance — scale_pos_weight balances fraud vs non-fraud
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    print(f"scale_pos_weight: {scale_pos_weight:.1f}")

    params = {
        "n_estimators":       500,
        "max_depth":          6,
        "learning_rate":      0.05,
        "subsample":          0.8,
        "colsample_bytree":   0.8,
        "min_child_weight":   5,
        "gamma":              0.1,
        "reg_alpha":          0.1,
        "reg_lambda":         1.0,
        "scale_pos_weight":   scale_pos_weight,
        "tree_method":        "hist",      # fast CPU training
        "eval_metric":        "aucpr",     # area under PR curve — best for imbalanced
        "early_stopping_rounds": 30,
        "random_state":       42,
        "n_jobs":             -1,
    }

    with mlflow.start_run(run_name="xgboost-baseline") as run:
        print(f"\nMLflow run: {run.info.run_id}")
        mlflow.log_params(params)
        mlflow.log_param("train_size",     len(X_train))
        mlflow.log_param("test_size",      len(X_test))
        mlflow.log_param("fraud_rate_pct", round(y.mean() * 100, 2))
        mlflow.log_param("features",       ALL_FEATURES)

        model = xgb.XGBClassifier(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=50,
        )

        # Evaluate on test set
        y_prob = model.predict_proba(X_test)[:, 1]
        y_pred = (y_prob >= 0.5).astype(int)

        metrics = {
            "test_roc_auc":          round(roc_auc_score(y_test, y_prob), 4),
            "test_avg_precision":    round(average_precision_score(y_test, y_prob), 4),
            "test_f1":               round(f1_score(y_test, y_pred), 4),
            "test_precision":        round(precision_score(y_test, y_pred, zero_division=0), 4),
            "test_recall":           round(recall_score(y_test, y_pred), 4),
            "best_iteration":        model.best_iteration,
        }

        mlflow.log_metrics(metrics)

        print("\n=== Test Set Metrics ===")
        for k, v in metrics.items():
            print(f"  {k}: {v}")

        print("\n=== Classification Report ===")
        print(classification_report(y_test, y_pred, target_names=["legitimate", "fraud"]))

        print("\n=== Confusion Matrix ===")
        cm = confusion_matrix(y_test, y_pred)
        print(f"  TN={cm[0,0]}  FP={cm[0,1]}")
        print(f"  FN={cm[1,0]}  TP={cm[1,1]}")

        # Feature importance
        importance = dict(zip(ALL_FEATURES, model.feature_importances_))
        importance_sorted = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
        print("\n=== Feature Importance ===")
        for feat, score in importance_sorted.items():
            print(f"  {feat}: {score:.4f}")

        mlflow.log_dict(importance_sorted, "feature_importance.json")

        # Log and register model
        mlflow.xgboost.log_model(
            model,
            artifact_path="model",
            registered_model_name="fraud-detector",
            input_example=X_test.iloc[:1],
        )

        # Save feature metadata alongside model
        feature_meta = {
            "all_features":         ALL_FEATURES,
            "numeric_features":     NUMERIC_FEATURES,
            "categorical_features": CATEGORICAL_FEATURES,
            "category_maps":        CATEGORY_MAPS,
            "threshold":            0.5,
        }
        mlflow.log_dict(feature_meta, "feature_meta.json")

        print(f"\nModel registered as 'fraud-detector'")
        print(f"Run ID: {run.info.run_id}")
        print(f"View at: {MLFLOW_URI}/#/experiments")

        # Save model directly to disk for runtime use (no MLflow server needed)
        model_dir = Path("services/ml-scoring/model")
        model_dir.mkdir(parents=True, exist_ok=True)

        model.save_model(str(model_dir / "model.ubj"))   # XGBoost native binary format

        # Save feature metadata alongside model
        with open(model_dir / "feature_meta.json", "w") as f:
            json.dump(feature_meta, f, indent=2)

        print(f"Model saved to {model_dir}/model.ubj")

        return run.info.run_id


if __name__ == "__main__":
    train()