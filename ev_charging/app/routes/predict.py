"""
Route API pour la prédiction de disponibilité des bornes.
Charge le modèle ML entraîné et expose une API REST.

Endpoints :
  POST /api/predict/disponibilite  → prédit si une borne sera occupée
  GET  /api/predict/heatmap/<id>   → probabilités sur 24h pour une borne
"""

import pickle
import os
import numpy as np
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

predict_bp = Blueprint("predict", __name__)

# ─── Chargement du modèle au démarrage du serveur ─────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(__file__), "../../ml/model/model_disponibilite.pkl")
_model_data = None


def charger_modele():
    """Charge le modèle depuis le fichier .pkl (une seule fois)."""
    global _model_data
    if _model_data is None:
        if not os.path.exists(MODEL_PATH):
            return None
        with open(MODEL_PATH, "rb") as f:
            _model_data = pickle.load(f)
    return _model_data


# ─── POST /api/predict/disponibilite ─────────────────────────────────────
@predict_bp.route("/disponibilite", methods=["POST"])
@jwt_required()
def predire_disponibilite():
    """
    Prédit si une borne sera occupée à un moment donné.

    Corps attendu :
    {
        "borne_id": 1,
        "heure": 14,
        "jour_semaine": 1,   ← 0=lundi, 6=dimanche
        "mois": 6
    }

    Réponse :
    {
        "borne_id": 1,
        "heure": 14,
        "prediction": "occupee" | "disponible",
        "probabilite_occupation": 0.73,
        "confiance": "haute" | "moyenne" | "basse"
    }
    """
    model_data = charger_modele()
    if model_data is None:
        return jsonify({
            "message": "Modèle ML non disponible. Exécutez d'abord : python ml/train_model.py"
        }), 503

    data = request.get_json()

    # Validation
    champs = ["borne_id", "heure", "jour_semaine", "mois"]
    for champ in champs:
        if champ not in data:
            return jsonify({"message": f"Champ manquant : {champ}"}), 400

    borne_id = int(data["borne_id"])
    heure = int(data["heure"])
    jour_semaine = int(data["jour_semaine"])
    mois = int(data["mois"])
    est_weekend = 1 if jour_semaine >= 5 else 0

    # Prédiction
    model = model_data["model"]
    X = np.array([[borne_id, heure, jour_semaine, est_weekend, mois]])
    prediction = model.predict(X)[0]
    probabilite = model.predict_proba(X)[0][1]  # proba d'être occupée

    # Niveau de confiance
    if probabilite > 0.75 or probabilite < 0.25:
        confiance = "haute"
    elif probabilite > 0.60 or probabilite < 0.40:
        confiance = "moyenne"
    else:
        confiance = "basse"

    return jsonify({
        "borne_id": borne_id,
        "heure": heure,
        "jour_semaine": jour_semaine,
        "mois": mois,
        "prediction": "occupee" if prediction == 1 else "disponible",
        "probabilite_occupation": round(float(probabilite), 3),
        "probabilite_disponible": round(1 - float(probabilite), 3),
        "confiance": confiance,
        "modele_version": model_data.get("version", "1.0"),
        "modele_accuracy": model_data.get("accuracy"),
    }), 200


# ─── GET /api/predict/heatmap/<borne_id> ─────────────────────────────────
@predict_bp.route("/heatmap/<int:borne_id>", methods=["GET"])
@jwt_required()
def heatmap_disponibilite(borne_id):
    """
    Retourne les probabilités d'occupation pour les 24h d'une journée.
    Utilisé pour afficher la heatmap dans le dashboard.

    Query params optionnels :
      jour_semaine = 0-6 (défaut: 1 = mardi, jour "type")
      mois = 1-12 (défaut: mois actuel)
    """
    model_data = charger_modele()
    if model_data is None:
        return jsonify({"message": "Modèle ML non disponible."}), 503

    from datetime import datetime
    jour_semaine = int(request.args.get("jour_semaine", 1))
    mois = int(request.args.get("mois", datetime.now().month))
    est_weekend = 1 if jour_semaine >= 5 else 0

    model = model_data["model"]
    heures = list(range(24))

    # Prédiction pour chaque heure
    X = np.array([
        [borne_id, h, jour_semaine, est_weekend, mois]
        for h in heures
    ])
    probas = model.predict_proba(X)[:, 1]

    return jsonify({
        "borne_id": borne_id,
        "jour_semaine": jour_semaine,
        "mois": mois,
        "heures": heures,
        "probabilites_occupation": [round(float(p), 3) for p in probas],
        "heure_recommandee": int(heures[int(np.argmin(probas))]),
        # ↑ L'heure où la borne a le plus de chances d'être libre
    }), 200


# ─── GET /api/predict/recommander ────────────────────────────────────────
@predict_bp.route("/recommander", methods=["GET"])
@jwt_required()
def recommander_borne():
    """
    Recommande la borne la plus susceptible d'être disponible
    à l'heure actuelle.
    """
    from datetime import datetime
    model_data = charger_modele()
    if model_data is None:
        return jsonify({"message": "Modèle ML non disponible."}), 503

    maintenant = datetime.now()
    heure = maintenant.hour
    jour_semaine = maintenant.weekday()
    mois = maintenant.month
    est_weekend = 1 if jour_semaine >= 5 else 0

    model = model_data["model"]
    resultats = []

    for borne_id in [1, 2, 3]:
        X = np.array([[borne_id, heure, jour_semaine, est_weekend, mois]])
        proba_occupee = model.predict_proba(X)[0][1]
        resultats.append({
            "borne_id": borne_id,
            "probabilite_disponible": round(1 - float(proba_occupee), 3),
            "probabilite_occupation": round(float(proba_occupee), 3),
        })

    # Trier par probabilité de disponibilité décroissante
    resultats.sort(key=lambda x: -x["probabilite_disponible"])

    return jsonify({
        "heure_actuelle": heure,
        "jour_semaine": jour_semaine,
        "recommandations": resultats,
        "meilleure_borne_id": resultats[0]["borne_id"],
    }), 200
