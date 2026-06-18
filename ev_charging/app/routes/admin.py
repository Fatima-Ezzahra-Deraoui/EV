from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func

from app import db
from app.models.user import User
from app.models.borne import Borne
from app.models.session_recharge import SessionRecharge

admin_bp = Blueprint("admin", __name__)


def admin_required():
    """Helper : vérifie le rôle admin via les claims JWT."""
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"message": "Accès réservé aux administrateurs."}), 403
    return None


# ─── GET /admin/stats ──────────────────────────────────────────────────────
@admin_bp.route("/stats", methods=["GET"])
@jwt_required()
def statistiques():
    """
    Statistiques globales pour le dashboard admin :
    - Nombre total de bornes (et par statut)
    - Nombre d'utilisateurs
    - Énergie totale distribuée (kWh)
    - Revenu total (€)
    - Sessions aujourd'hui
    """
    erreur = admin_required()
    if erreur:
        return erreur

    from datetime import date, datetime

    # Stats bornes
    total_bornes = Borne.query.filter_by(actif=True).count()
    bornes_disponibles = Borne.query.filter_by(statut="disponible", actif=True).count()
    bornes_occupees = Borne.query.filter_by(statut="occupee", actif=True).count()
    bornes_en_panne = Borne.query.filter_by(statut="en_panne", actif=True).count()

    # Stats utilisateurs
    total_users = User.query.filter_by(actif=True).count()

    # Stats sessions
    total_sessions = SessionRecharge.query.filter_by(statut="terminee").count()
    energie_totale = db.session.query(
        func.sum(SessionRecharge.energie_kwh)
    ).filter_by(statut="terminee").scalar() or 0.0

    revenu_total = db.session.query(
        func.sum(SessionRecharge.cout_total)
    ).filter_by(statut="terminee").scalar() or 0.0

    # Sessions aujourd'hui
    debut_jour = datetime.combine(date.today(), datetime.min.time())
    sessions_aujourd_hui = SessionRecharge.query.filter(
        SessionRecharge.debut >= debut_jour
    ).count()

    return jsonify({
        "bornes": {
            "total": total_bornes,
            "disponibles": bornes_disponibles,
            "occupees": bornes_occupees,
            "en_panne": bornes_en_panne,
            "maintenance": total_bornes - bornes_disponibles - bornes_occupees - bornes_en_panne
        },
        "utilisateurs": {"total": total_users},
        "sessions": {
            "total_terminées": total_sessions,
            "aujourd_hui": sessions_aujourd_hui,
        },
        "energie": {
            "total_kwh": round(energie_totale, 2),
            "revenu_total_eur": round(revenu_total, 2)
        }
    }), 200


# ─── GET /admin/users ─────────────────────────────────────────────────────
@admin_bp.route("/users", methods=["GET"])
@jwt_required()
def lister_users():
    """Liste tous les utilisateurs (admin)."""
    erreur = admin_required()
    if erreur:
        return erreur

    users = User.query.all()
    return jsonify([u.to_dict() for u in users]), 200


# ─── PATCH /admin/users/<id>/role ─────────────────────────────────────────
@admin_bp.route("/users/<int:user_id>/role", methods=["PATCH"])
@jwt_required()
def changer_role(user_id):
    """Promouvoir/rétrograder un utilisateur (admin)."""
    erreur = admin_required()
    if erreur:
        return erreur

    user = User.query.get_or_404(user_id)
    data = request.get_json()
    nouveau_role = data.get("role")

    if nouveau_role not in ["user", "admin"]:
        return jsonify({"message": "Rôle invalide. Valeurs : 'user' ou 'admin'."}), 400

    user.role = nouveau_role
    db.session.commit()

    return jsonify({"message": f"Rôle mis à jour : {nouveau_role}", "user": user.to_dict()}), 200


# ─── GET /admin/alertes ───────────────────────────────────────────────────
@admin_bp.route("/alertes", methods=["GET"])
@jwt_required()
def alertes_maintenance():
    """Retourne les bornes en panne ou en maintenance (alertes)."""
    erreur = admin_required()
    if erreur:
        return erreur

    bornes_alertes = Borne.query.filter(
        Borne.statut.in_(["en_panne", "maintenance"]),
        Borne.actif == True
    ).all()

    return jsonify({
        "nombre_alertes": len(bornes_alertes),
        "bornes": [b.to_dict() for b in bornes_alertes]
    }), 200
