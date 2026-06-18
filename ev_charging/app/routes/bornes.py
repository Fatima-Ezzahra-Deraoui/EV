from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import db, socketio
from app.models.borne import Borne

bornes_bp = Blueprint("bornes", __name__)


def require_admin():
    """Helper : vérifie que l'utilisateur connecté est admin (via claims JWT)."""
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"message": "Accès réservé aux administrateurs."}), 403
    return None


# ─── GET /api/bornes/ ─────────────────────────────────────────────────────
@bornes_bp.route("/", methods=["GET"])
@jwt_required()
def lister_bornes():
    """Lister toutes les bornes actives. Filtres optionnels : statut, ville."""
    statut = request.args.get("statut")
    ville = request.args.get("ville")

    query = Borne.query.filter_by(actif=True)
    if statut:
        query = query.filter_by(statut=statut)
    if ville:
        query = query.filter(Borne.ville.ilike(f"%{ville}%"))

    bornes = query.all()
    return jsonify([b.to_dict() for b in bornes]), 200


# ─── GET /api/bornes/<id> ─────────────────────────────────────────────────
@bornes_bp.route("/<int:borne_id>", methods=["GET"])
@jwt_required()
def obtenir_borne(borne_id):
    """Détails d'une borne spécifique."""
    borne = Borne.query.get_or_404(borne_id)
    return jsonify(borne.to_dict()), 200


# ─── POST /api/bornes/ ────────────────────────────────────────────────────
@bornes_bp.route("/", methods=["POST"])
@jwt_required()
def creer_borne():
    """Créer une nouvelle borne (admin uniquement)."""
    erreur = require_admin()
    if erreur:
        return erreur

    data = request.get_json()
    if not data.get("nom"):
        return jsonify({"message": "Le nom de la borne est requis."}), 400

    borne = Borne(
        nom=data["nom"],
        adresse=data.get("adresse"),
        ville=data.get("ville"),
        code_postal=data.get("code_postal"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        puissance_kw=data.get("puissance_kw", 22.0),
        type_connecteur=data.get("type_connecteur", "Type 2"),
        prix_kwh=data.get("prix_kwh", 0.30),
        qr_code=data.get("qr_code"),
    )

    db.session.add(borne)
    db.session.commit()

    socketio.emit("borne_ajoutee", borne.to_dict())

    return jsonify({"message": "Borne créée.", "borne": borne.to_dict()}), 201


# ─── PUT /api/bornes/<id> ─────────────────────────────────────────────────
@bornes_bp.route("/<int:borne_id>", methods=["PUT"])
@jwt_required()
def modifier_borne(borne_id):
    """Modifier une borne existante (admin uniquement)."""
    erreur = require_admin()
    if erreur:
        return erreur

    borne = Borne.query.get_or_404(borne_id)
    data = request.get_json()

    champs_modifiables = [
        "nom", "adresse", "ville", "code_postal",
        "latitude", "longitude", "puissance_kw",
        "type_connecteur", "prix_kwh", "statut", "qr_code", "actif"
    ]

    for champ in champs_modifiables:
        if champ in data:
            setattr(borne, champ, data[champ])

    db.session.commit()

    socketio.emit("borne_mise_a_jour", borne.to_dict())

    return jsonify({"message": "Borne modifiée.", "borne": borne.to_dict()}), 200


# ─── PATCH /api/bornes/<id>/statut ───────────────────────────────────────
@bornes_bp.route("/<int:borne_id>/statut", methods=["PATCH"])
@jwt_required()
def changer_statut(borne_id):
    """Changer uniquement le statut d'une borne (admin uniquement)."""
    erreur = require_admin()
    if erreur:
        return erreur

    borne = Borne.query.get_or_404(borne_id)
    data = request.get_json()
    statuts_valides = ["disponible", "occupee", "en_panne", "maintenance"]

    nouveau_statut = data.get("statut")
    if nouveau_statut not in statuts_valides:
        return jsonify({"message": f"Statut invalide. Valeurs possibles : {statuts_valides}"}), 400

    borne.statut = nouveau_statut
    db.session.commit()

    socketio.emit("statut_borne", {"borne_id": borne_id, "statut": nouveau_statut})

    return jsonify({"message": f"Statut mis à jour : {nouveau_statut}"}), 200


# ─── DELETE /api/bornes/<id> ──────────────────────────────────────────────
@bornes_bp.route("/<int:borne_id>", methods=["DELETE"])
@jwt_required()
def supprimer_borne(borne_id):
    """Désactiver une borne (soft delete — admin uniquement)."""
    erreur = require_admin()
    if erreur:
        return erreur

    borne = Borne.query.get_or_404(borne_id)
    borne.actif = False
    db.session.commit()

    socketio.emit("borne_supprimee", {"borne_id": borne_id})

    return jsonify({"message": "Borne désactivée."}), 200
