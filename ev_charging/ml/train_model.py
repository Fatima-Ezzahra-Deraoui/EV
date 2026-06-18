"""
Entraîne un modèle RandomForest pour prédire si une borne sera occupée
à une heure et un jour donnés.

Usage :
    python ml/train_model.py

Sortie :
    ml/model/model_disponibilite.pkl   ← modèle entraîné
    ml/model/rapport_evaluation.txt   ← métriques
"""

import pandas as pd
import numpy as np
import pickle
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    roc_auc_score
)
from sklearn.preprocessing import LabelEncoder

# ─── 1. Chargement des données ────────────────────────────────────────────
print("Chargement du dataset...")
df = pd.read_csv("ml/data/dataset_disponibilite.csv")
print(f"Dataset : {df.shape[0]} lignes × {df.shape[1]} colonnes")
print(f"Répartition target :\n{df['occupee'].value_counts()}\n")

# ─── 2. Features et target ────────────────────────────────────────────────
FEATURES = ["borne_id", "heure", "jour_semaine", "est_weekend", "mois"]
TARGET = "occupee"

X = df[FEATURES]
y = df[TARGET]

# ─── 3. Split train / test (80% / 20%) ───────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"Train : {len(X_train)} | Test : {len(X_test)}")

# ─── 4. Entraînement du modèle ────────────────────────────────────────────
print("\nEntraînement du RandomForestClassifier...")
model = RandomForestClassifier(
    n_estimators=100,       # 100 arbres
    max_depth=10,           # profondeur max pour éviter overfitting
    min_samples_split=5,
    class_weight="balanced",  # compense le déséquilibre occupé/libre
    random_state=42,
    n_jobs=-1               # utilise tous les cœurs CPU
)
model.fit(X_train, y_train)
print("✅ Modèle entraîné.")

# ─── 5. Évaluation ───────────────────────────────────────────────────────
print("\n=== ÉVALUATION ===")
y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
auc = roc_auc_score(y_test, y_proba)

print(f"Accuracy  : {accuracy:.4f} ({accuracy*100:.1f}%)")
print(f"AUC-ROC   : {auc:.4f}")
print("\nRapport de classification :")
print(classification_report(y_test, y_pred, target_names=["Disponible", "Occupée"]))

print("Matrice de confusion :")
print(confusion_matrix(y_test, y_pred))

# ─── 6. Importance des features ───────────────────────────────────────────
print("\nImportance des features :")
for feat, imp in sorted(zip(FEATURES, model.feature_importances_), key=lambda x: -x[1]):
    print(f"  {feat:15s} : {imp:.4f} ({imp*100:.1f}%)")

# ─── 7. Sauvegarde du modèle ─────────────────────────────────────────────
os.makedirs("ml/model", exist_ok=True)

model_data = {
    "model": model,
    "features": FEATURES,
    "version": "1.0",
    "accuracy": round(accuracy, 4),
    "auc": round(auc, 4),
}

with open("ml/model/model_disponibilite.pkl", "wb") as f:
    pickle.dump(model_data, f)

print("\n✅ Modèle sauvegardé → ml/model/model_disponibilite.pkl")

# ─── 8. Rapport texte ────────────────────────────────────────────────────
rapport = f"""
RAPPORT D'ÉVALUATION — Modèle de Prédiction de Disponibilité des Bornes
=========================================================================

Modèle       : RandomForestClassifier
Features     : {FEATURES}
Dataset      : {len(df)} lignes (90 jours × 3 bornes × 24h)
Train/Test   : 80% / 20%

MÉTRIQUES
---------
Accuracy     : {accuracy*100:.1f}%
AUC-ROC      : {auc:.4f}

INTERPRÉTATION
--------------
- Le modèle prédit si une borne sera occupée à une heure et un jour donnés.
- Une accuracy > 70% est suffisante pour un système d'aide à la décision.
- L'AUC-ROC mesure la capacité à discriminer disponible vs occupée.

IMPORTANCE DES FEATURES
-----------------------
"""
for feat, imp in sorted(zip(FEATURES, model.feature_importances_), key=lambda x: -x[1]):
    rapport += f"  {feat:15s} : {imp*100:.1f}%\n"

with open("ml/model/rapport_evaluation.txt", "w") as f:
    f.write(rapport)

print("✅ Rapport sauvegardé → ml/model/rapport_evaluation.txt")
print("\n Prochaine étape : python run.py pour lancer l'API de prédiction.")
