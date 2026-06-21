"""
Route API pour la prédiction de disponibilité des bornes.
Charge le modèle ML entraîné et expose une API REST.

Endpoints :
  POST /api/predict/disponibilite      → prédit si une borne sera occupée
  GET  /api/predict/heatmap/<borne_id> → probabilités sur 24h pour une borne
  GET  /api/predict/recommander        → borne la plus disponible maintenant
"""

import pickle
import os
import pandas as pd
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

predict_bp = Blueprint("predict", __name__)

# ─── Chargement du modèle ─────────────────────────────────────────────────
MODEL_PATH  = os.path.join(os.path.dirname(__file__), "../../ml/model/model_disponibilite.pkl")
_model_data = None

HEURES_POINTE = [7, 8, 9, 17, 18, 19]


def charger_modele():
    """Charge le modèle depuis le fichier .pkl (une seule fois)."""
    global _model_data
    if _model_data is None:
        if not os.path.exists(MODEL_PATH):
            return None
        with open(MODEL_PATH, "rb") as f:
            _model_data = pickle.load(f)
    return _model_data


def _build_X(borne_id: int, heure: int, jour_semaine: int, mois: int) -> pd.DataFrame:
    """
    Construit le DataFrame d'entrée avec les 6 features attendues par le modèle.
    Identique à l'ordre de FEATURES dans train_model.py.
    """
    est_weekend     = 1 if jour_semaine >= 5 else 0
    est_heure_pointe = 1 if heure in HEURES_POINTE else 0

    return pd.DataFrame(
        [[borne_id, heure, jour_semaine, est_weekend, est_heure_pointe, mois]],
        columns=["borne_id", "heure", "jour_semaine", "est_weekend", "est_heure_pointe", "mois"]
    )


def _niveau_confiance(probabilite: float) -> str:
    if probabilite > 0.75 or probabilite < 0.25:
        return "haute"
    elif probabilite > 0.60 or probabilite < 0.40:
        return "moyenne"
    return "basse"


# ─── POST /api/predict/disponibilite ─────────────────────────────────────
@predict_bp.route("/disponibilite", methods=["POST"])
@jwt_required()
def predire_disponibilite():
    """
    Prédit si une borne sera occupée à un moment donné.

    Corps JSON attendu :
    {
        "borne_id":     1,
        "heure":        14,
        "jour_semaine": 1,   ← 0=lundi … 6=dimanche
        "mois":         6
    }
    """
    model_data = charger_modele()
    if model_data is None:
        return jsonify({
            "message": "Modèle ML non disponible. Exécutez : python ml/train_model.py"
        }), 503

    data = request.get_json()

    for champ in ["borne_id", "heure", "jour_semaine", "mois"]:
        if champ not in data:
            return jsonify({"message": f"Champ manquant : {champ}"}), 400

    borne_id     = int(data["borne_id"])
    heure        = int(data["heure"])
    jour_semaine = int(data["jour_semaine"])
    mois         = int(data["mois"])

    model = model_data["model"]
    X     = _build_X(borne_id, heure, jour_semaine, mois)

    prediction = model.predict(X)[0]
    probabilite = model.predict_proba(X)[0][1]

    return jsonify({
        "borne_id":                borne_id,
        "heure":                   heure,
        "jour_semaine":            jour_semaine,
        "mois":                    mois,
        "prediction":              "occupee" if prediction == 1 else "disponible",
        "probabilite_occupation":  round(float(probabilite), 3),
        "probabilite_disponible":  round(1 - float(probabilite), 3),
        "confiance":               _niveau_confiance(probabilite),
        "modele_version":          model_data.get("version", "1.0"),
        "modele_accuracy":         model_data.get("accuracy"),
    }), 200


# ─── GET /api/predict/heatmap/<borne_id> ─────────────────────────────────
@predict_bp.route("/heatmap/<int:borne_id>", methods=["GET"])
@jwt_required()
def heatmap_disponibilite(borne_id):
    """
    Retourne les probabilités d'occupation pour les 24h d'une journée.

    Query params optionnels :
      jour_semaine = 0-6 (défaut: 1 = mardi)
      mois         = 1-12 (défaut: mois actuel)
    """
    model_data = charger_modele()
    if model_data is None:
        return jsonify({"message": "Modèle ML non disponible."}), 503

    jour_semaine = int(request.args.get("jour_semaine", 1))
    mois         = int(request.args.get("mois", datetime.now().month))
    heures       = list(range(24))

    model = model_data["model"]

    X = pd.DataFrame(
        [
            [
                borne_id,
                h,
                jour_semaine,
                1 if jour_semaine >= 5 else 0,
                1 if h in HEURES_POINTE else 0,
                mois,
            ]
            for h in heures
        ],
        columns=["borne_id", "heure", "jour_semaine", "est_weekend", "est_heure_pointe", "mois"]
    )

    probas = model.predict_proba(X)[:, 1]

    return jsonify({
        "borne_id":                  borne_id,
        "jour_semaine":              jour_semaine,
        "mois":                      mois,
        "heures":                    heures,
        "probabilites_occupation":   [round(float(p), 3) for p in probas],
        "heure_recommandee":         int(heures[int(probas.argmin())]),
    }), 200


# ─── GET /api/predict/recommander ────────────────────────────────────────
@predict_bp.route("/recommander", methods=["GET"])
@jwt_required()
def recommander_borne():
    """
    Recommande la borne la plus susceptible d'être disponible maintenant.
    """
    model_data = charger_modele()
    if model_data is None:
        return jsonify({"message": "Modèle ML non disponible."}), 503

    maintenant   = datetime.now()
    heure        = maintenant.hour
    jour_semaine = maintenant.weekday()
    mois         = maintenant.month

    model      = model_data["model"]
    resultats  = []

    for borne_id in [1, 2, 3]:
        X = _build_X(borne_id, heure, jour_semaine, mois)
        proba_occupee = model.predict_proba(X)[0][1]
        resultats.append({
            "borne_id":               borne_id,
            "probabilite_disponible": round(1 - float(proba_occupee), 3),
            "probabilite_occupation": round(float(proba_occupee), 3),
            "confiance":              _niveau_confiance(proba_occupee),
        })

    resultats.sort(key=lambda x: -x["probabilite_disponible"])

    return jsonify({
        "heure_actuelle":    heure,
        "jour_semaine":      jour_semaine,
        "mois":              mois,
        "recommandations":   resultats,
        "meilleure_borne_id": resultats[0]["borne_id"],
    }), 200