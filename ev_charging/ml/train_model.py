"""
Entraîne un modèle RandomForest pour prédire si une borne sera occupée
à une heure et un jour donnés.

Usage :
    python ml/train_model.py

Sortie :
    ml/model/model_disponibilite.pkl
    ml/model/rapport_evaluation.txt
"""

import os
import sys
import pickle
import logging
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
)

# ─── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── Constantes ───────────────────────────────────────────────────────────
DATA_PATH     = "ml/data/dataset_disponibilite.csv"
MODEL_DIR     = "ml/model"
MODEL_PATH    = os.path.join(MODEL_DIR, "model_disponibilite.pkl")
REPORT_PATH   = os.path.join(MODEL_DIR, "rapport_evaluation.txt")
MODEL_VERSION = "2.0"

FEATURES = ["borne_id", "heure", "jour_semaine", "est_weekend", "est_heure_pointe", "mois"]
TARGET   = "occupee"

HEURES_POINTE = [7, 8, 9, 17, 18, 19]

RF_PARAMS = {
    "n_estimators":      100,
    "max_depth":         10,
    "min_samples_split": 5,
    "min_samples_leaf":  2,
    "class_weight":      "balanced",
    "random_state":      42,
    "n_jobs":            -1,
}


# ─── 1. Chargement & validation ───────────────────────────────────────────
def load_data(path: str) -> pd.DataFrame:
    log.info("Chargement du dataset : %s", path)

    if not os.path.exists(path):
        log.error("Fichier introuvable : %s", path)
        log.error("Générez d'abord le dataset avec : python ml/generate_dataset.py")
        sys.exit(1)

    df = pd.read_csv(path)
    log.info("Dataset chargé : %d lignes × %d colonnes", *df.shape)

    # Générer les features calculées si absentes
    if "est_weekend" not in df.columns:
        df["est_weekend"] = (df["jour_semaine"] >= 5).astype(int)
        log.info("Colonne 'est_weekend' générée automatiquement.")

    if "est_heure_pointe" not in df.columns:
        df["est_heure_pointe"] = df["heure"].isin(HEURES_POINTE).astype(int)
        log.info("Colonne 'est_heure_pointe' générée automatiquement.")

    manquantes = [c for c in FEATURES + [TARGET] if c not in df.columns]
    if manquantes:
        log.error("Colonnes manquantes dans le CSV : %s", manquantes)
        sys.exit(1)

    nulls = df[FEATURES + [TARGET]].isnull().sum()
    if nulls.any():
        log.warning("Valeurs nulles détectées :\n%s", nulls[nulls > 0])
        df = df.dropna(subset=FEATURES + [TARGET])
        log.info("Lignes conservées après nettoyage : %d", len(df))

    log.info("Répartition target :\n%s", df[TARGET].value_counts().to_string())
    return df


# ─── 2. Entraînement ──────────────────────────────────────────────────────
def train(X_train, y_train) -> RandomForestClassifier:
    log.info("Entraînement RandomForestClassifier — paramètres : %s", RF_PARAMS)
    model = RandomForestClassifier(**RF_PARAMS)
    model.fit(X_train, y_train)
    log.info("Modèle entraîné avec succès.")
    return model


# ─── 3. Évaluation ────────────────────────────────────────────────────────
def evaluate(model, X_train, X_test, y_train, y_test) -> dict:
    y_pred  = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    accuracy  = accuracy_score(y_test, y_pred)
    auc       = roc_auc_score(y_test, y_proba)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall    = recall_score(y_test, y_pred, zero_division=0)
    f1        = f1_score(y_test, y_pred, zero_division=0)

    cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring="accuracy", n_jobs=-1)

    log.info("─── Métriques ──────────────────────────────────")
    log.info("Accuracy   : %.4f  (%.1f%%)", accuracy, accuracy * 100)
    log.info("AUC-ROC    : %.4f", auc)
    log.info("Precision  : %.4f", precision)
    log.info("Recall     : %.4f", recall)
    log.info("F1-Score   : %.4f", f1)
    log.info("CV 5-fold  : %.4f ± %.4f", cv_scores.mean(), cv_scores.std())
    log.info("────────────────────────────────────────────────")

    log.info("Rapport de classification :\n%s",
             classification_report(y_test, y_pred, target_names=["Disponible", "Occupée"]))
    log.info("Matrice de confusion :\n%s", confusion_matrix(y_test, y_pred))

    return {
        "accuracy":  round(accuracy,  4),
        "auc":       round(auc,       4),
        "precision": round(precision, 4),
        "recall":    round(recall,    4),
        "f1":        round(f1,        4),
        "cv_mean":   round(float(cv_scores.mean()), 4),
        "cv_std":    round(float(cv_scores.std()),  4),
    }


# ─── 4. Importance des features ───────────────────────────────────────────
def feature_importance(model) -> list:
    pairs = sorted(
        zip(FEATURES, model.feature_importances_),
        key=lambda x: -x[1]
    )
    log.info("Importance des features :")
    for feat, imp in pairs:
        bar = "█" * int(imp * 40)
        log.info("  %-18s : %5.1f%%  %s", feat, imp * 100, bar)
    return pairs


# ─── 5. Sauvegarde du modèle ──────────────────────────────────────────────
def save_model(model, metrics: dict, importances: list):
    os.makedirs(MODEL_DIR, exist_ok=True)

    model_data = {
        "model":       model,
        "features":    FEATURES,
        "version":     MODEL_VERSION,
        "trained_at":  datetime.now().isoformat(),
        "params":      RF_PARAMS,
        "metrics":     metrics,
        "accuracy":    metrics["accuracy"],   # accès rapide depuis predict.py
        "importances": {f: round(i, 4) for f, i in importances},
        "heures_pointe": HEURES_POINTE,
    }

    with open(MODEL_PATH, "wb") as fh:
        pickle.dump(model_data, fh, protocol=pickle.HIGHEST_PROTOCOL)

    log.info("Modèle sauvegardé → %s", MODEL_PATH)


# ─── 6. Rapport texte ─────────────────────────────────────────────────────
def save_report(metrics: dict, importances: list, n_total: int):
    sep = "=" * 70
    lines = [
        sep,
        "RAPPORT D'ÉVALUATION — Prédiction Disponibilité des Bornes EVCharge",
        sep,
        f"  Version modèle   : {MODEL_VERSION}",
        f"  Date             : {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"  Algorithme       : RandomForestClassifier",
        f"  Paramètres       : {RF_PARAMS}",
        f"  Dataset          : {n_total} lignes",
        f"  Features ({len(FEATURES)})    : {FEATURES}",
        f"  Split            : 80% train / 20% test",
        "",
        "MÉTRIQUES",
        "-" * 40,
        f"  Accuracy         : {metrics['accuracy']*100:.1f}%",
        f"  AUC-ROC          : {metrics['auc']:.4f}",
        f"  Precision        : {metrics['precision']:.4f}",
        f"  Recall           : {metrics['recall']:.4f}",
        f"  F1-Score         : {metrics['f1']:.4f}",
        f"  CV 5-fold        : {metrics['cv_mean']*100:.1f}% ± {metrics['cv_std']*100:.1f}%",
        "",
        "IMPORTANCE DES FEATURES",
        "-" * 40,
    ]

    for feat, imp in importances:
        bar = "█" * int(imp * 40)
        lines.append(f"  {feat:<18} : {imp*100:5.1f}%  {bar}")

    lines += [
        "",
        "INTERPRÉTATION",
        "-" * 40,
        "  L'heure est la variable dominante — les bornes suivent",
        "  des patterns journaliers clairs (pic matin 8h, pic soir 18h).",
        "  Une accuracy > 70% est suffisante pour un système d'aide à la décision.",
        "  L'AUC-ROC > 0.75 confirme une bonne discrimination disponible/occupée.",
        "",
        sep,
        "  Prochaine étape : python run.py pour démarrer l'API Flask.",
        sep,
    ]

    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    log.info("Rapport sauvegardé → %s", REPORT_PATH)


# ─── Main ──────────────────────────────────────────────────────────────────
def main():
    log.info("══ EVCharge — Entraînement du modèle IA ══")

    df = load_data(DATA_PATH)
    X  = df[FEATURES]
    y  = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    log.info("Split : %d train / %d test", len(X_train), len(X_test))

    model       = train(X_train, y_train)
    metrics     = evaluate(model, X_train, X_test, y_train, y_test)
    importances = feature_importance(model)

    save_model(model, metrics, importances)
    save_report(metrics, importances, n_total=len(df))

    log.info("══ Entraînement terminé avec succès ══")


if __name__ == "__main__":
    main()