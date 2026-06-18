from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime

from app import db, socketio
from app.models.session_recharge import SessionRecharge
from app.models.borne import Borne

sessions_bp = Blueprint("sessions", __name__)


# ─── POST /api/sessions/demarrer ─────────────────────────────────────────
@sessions_bp.route("/demarrer", methods=["POST"])
@jwt_required()
def demarrer_session():
    """
    Démarre une session de recharge.
    Corps attendu : { "borne_id": int, "methode_acces": "app"|"qr_code"|"rfid" }
    """
    user_id = int(get_jwt_identity())  # identity = string → int
    data = request.get_json()

    borne_id = data.get("borne_id")
    if not borne_id:
        return jsonify({"message": "L'identifiant de la borne est requis."}), 400

    borne = Borne.query.get_or_404(borne_id)

    if not borne.est_disponible():
        return jsonify({
            "message": f"La borne '{borne.nom}' n'est pas disponible (statut: {borne.statut})."
        }), 409

    # Vérifier que l'utilisateur n'a pas déjà une session en cours
    session_en_cours = SessionRecharge.query.filter_by(
        user_id=user_id,
        statut="en_cours"
    ).first()
    if session_en_cours:
        return jsonify({
            "message": "Vous avez déjà une session de recharge en cours.",
            "session_id": session_en_cours.id
        }), 409

    # Créer la session et occuper la borne
    session = SessionRecharge(
        user_id=user_id,
        borne_id=borne_id,
        debut=datetime.utcnow(),
        prix_kwh_applique=borne.prix_kwh,
        methode_acces=data.get("methode_acces", "app"),
        statut="en_cours"
    )
    borne.statut = "occupee"

    db.session.add(session)
    db.session.commit()

    socketio.emit("session_demarree", {
        "session_id": session.id,
        "borne_id": borne_id,
        "user_id": user_id
    })

    return jsonify({
        "message": "Session de recharge démarrée.",
        "session": session.to_dict()
    }), 201


# ─── PATCH /api/sessions/<id>/terminer ───────────────────────────────────
@sessions_bp.route("/<int:session_id>/terminer", methods=["PATCH"])
@jwt_required()
def terminer_session(session_id):
    """
    Termine une session de recharge.
    Corps attendu : { "energie_kwh": float }
    """
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    data = request.get_json()

    session = SessionRecharge.query.get_or_404(session_id)

    # Sécurité : seul le propriétaire ou un admin peut terminer
    if session.user_id != user_id and claims.get("role") != "admin":
        return jsonify({"message": "Accès refusé."}), 403

    if session.statut != "en_cours":
        return jsonify({"message": "Cette session n'est pas en cours."}), 400

    energie_kwh = data.get("energie_kwh", 0.0)
    session.terminer(energie_kwh)
    db.session.commit()

    socketio.emit("session_terminee", {
        "session_id": session.id,
        "borne_id": session.borne_id,
        "cout_total": session.cout_total
    })

    return jsonify({
        "message": "Session terminée.",
        "session": session.to_dict()
    }), 200


# ─── GET /api/sessions/mes-sessions ──────────────────────────────────────
@sessions_bp.route("/mes-sessions", methods=["GET"])
@jwt_required()
def mes_sessions():
    """Historique des sessions de recharge de l'utilisateur connecté."""
    user_id = int(get_jwt_identity())
    sessions = SessionRecharge.query.filter_by(
        user_id=user_id
    ).order_by(SessionRecharge.debut.desc()).all()

    return jsonify([s.to_dict() for s in sessions]), 200


# ─── GET /api/sessions/ (admin) ───────────────────────────────────────────
@sessions_bp.route("/", methods=["GET"])
@jwt_required()
def toutes_sessions():
    """Toutes les sessions (admin uniquement)."""
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"message": "Accès réservé aux administrateurs."}), 403

    sessions = SessionRecharge.query.order_by(
        SessionRecharge.debut.desc()
    ).limit(200).all()

    return jsonify([s.to_dict() for s in sessions]), 200


# ─── GET /api/sessions/historique (admin) ─────────────────────────────────
@sessions_bp.route("/historique", methods=["GET"])
@jwt_required()
def historique_sessions():
    """Historique enrichi des sessions (avec email user et nom borne)."""
    from app.models.user import User
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"message": "Accès réservé aux administrateurs."}), 403

    sessions = SessionRecharge.query.order_by(
        SessionRecharge.debut.desc()
    ).limit(500).all()

    result = []
    for s in sessions:
        d = s.to_dict()
        user = User.query.get(s.user_id)
        d["user_email"] = user.email if user else "—"
        borne = Borne.query.get(s.borne_id)
        d["borne_nom"] = borne.nom if borne else f"Borne #{s.borne_id}"
        result.append(d)

    return jsonify(result), 200
