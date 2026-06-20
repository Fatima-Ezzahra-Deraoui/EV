from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func
from datetime import date, datetime
from functools import wraps

from app import db
from app.models.user import User
from app.models.borne import Borne
from app.models.session_recharge import SessionRecharge

admin_bp = Blueprint("admin", __name__)


# ─── Décorateur admin ────────────────────────────────────────────────────
def admin_required(f):
    """Décorateur : vérifie le rôle admin via les claims JWT."""
    @wraps(f)
    def decorated(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"message": "Accès réservé aux administrateurs."}), 403
        return f(*args, **kwargs)
    return decorated


# ─── GET /admin/stats ────────────────────────────────────────────────────
@admin_bp.route("/stats", methods=["GET"])
@jwt_required()
@admin_required
def statistiques():
    """
    Statistiques globales pour le dashboard admin :
    - Bornes (total, par statut)
    - Utilisateurs
    - Sessions (total, aujourd'hui)
    - Énergie totale (kWh) et revenu total (€)
    - Évolution sessions sur les 7 derniers jours
    """
    # ── Bornes ───────────────────────────────────────────────────────────
    total_bornes      = Borne.query.filter_by(actif=True).count()
    bornes_dispo      = Borne.query.filter_by(statut="disponible",   actif=True).count()
    bornes_occupees   = Borne.query.filter_by(statut="occupee",      actif=True).count()
    bornes_panne      = Borne.query.filter_by(statut="en_panne",     actif=True).count()
    bornes_mainteance = Borne.query.filter_by(statut="maintenance",  actif=True).count()

    # ── Utilisateurs ─────────────────────────────────────────────────────
    total_users  = User.query.filter_by(actif=True).count()
    total_admins = User.query.filter_by(role="admin", actif=True).count()

    # ── Sessions ─────────────────────────────────────────────────────────
    total_sessions = SessionRecharge.query.filter_by(statut="terminee").count()
    sessions_en_cours = SessionRecharge.query.filter_by(statut="en_cours").count()

    debut_jour = datetime.combine(date.today(), datetime.min.time())
    sessions_aujourd_hui = SessionRecharge.query.filter(
        SessionRecharge.debut >= debut_jour
    ).count()

    # ── Énergie & revenus ────────────────────────────────────────────────
    energie_totale = db.session.query(
        func.sum(SessionRecharge.energie_kwh)
    ).filter_by(statut="terminee").scalar() or 0.0

    revenu_total = db.session.query(
        func.sum(SessionRecharge.cout_total)
    ).filter_by(statut="terminee").scalar() or 0.0

    # ── Évolution 7 jours ────────────────────────────────────────────────
    evolution_7j = []
    for i in range(6, -1, -1):
        from datetime import timedelta
        jour = date.today() - timedelta(days=i)
        debut = datetime.combine(jour, datetime.min.time())
        fin   = datetime.combine(jour, datetime.max.time())
        nb = SessionRecharge.query.filter(
            SessionRecharge.debut >= debut,
            SessionRecharge.debut <= fin
        ).count()
        evolution_7j.append({
            "date":     jour.strftime("%d/%m"),
            "sessions": nb
        })

    return jsonify({
        "bornes": {
            "total":       total_bornes,
            "disponibles": bornes_dispo,
            "occupees":    bornes_occupees,
            "en_panne":    bornes_panne,
            "maintenance": bornes_mainteance
        },
        "utilisateurs": {
            "total":  total_users,
            "admins": total_admins
        },
        "sessions": {
            "total_terminees":  total_sessions,
            "en_cours":         sessions_en_cours,
            "aujourd_hui":      sessions_aujourd_hui
        },
        "energie": {
            "total_kwh":       round(energie_totale, 2),
            "revenu_total_eur": round(revenu_total, 2)
        },
        "evolution_7j": evolution_7j
    }), 200


# ─── GET /admin/users ────────────────────────────────────────────────────
@admin_bp.route("/users", methods=["GET"])
@jwt_required()
@admin_required
def lister_users():
    """Liste tous les utilisateurs avec filtres optionnels."""
    role   = request.args.get("role")
    search = request.args.get("q", "").strip()

    query = User.query

    if role in ("admin", "user", "client"):
        query = query.filter_by(role=role)

    if search:
        query = query.filter(
            db.or_(
                User.nom.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )

    users = query.order_by(User.date_inscription.desc()).all()
    return jsonify([u.to_dict() for u in users]), 200


# ─── POST /admin/users ───────────────────────────────────────────────────
@admin_bp.route("/users", methods=["POST"])
@jwt_required()
@admin_required
def creer_user():
    """Créer un nouvel utilisateur depuis l'interface admin."""
    data = request.get_json(silent=True) or {}

    nom      = (data.get("nom") or "").strip()
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password", "")
    role     = data.get("role", "client")

    if not nom:
        return jsonify({"message": "Le nom est requis."}), 400
    if not email:
        return jsonify({"message": "L'adresse email est requise."}), 400
    if len(password) < 8:
        return jsonify({"message": "Le mot de passe doit contenir au moins 8 caractères."}), 400
    if role not in ("admin", "client", "user"):
        return jsonify({"message": "Rôle invalide."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Cette adresse email est déjà utilisée."}), 409

    user = User(nom=nom, email=email, role=role, actif=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Utilisateur créé.", "user": user.to_dict()}), 201


# ─── GET /admin/users/<id> ───────────────────────────────────────────────
@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@jwt_required()
@admin_required
def get_user(user_id):
    """Détail d'un utilisateur."""
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict()), 200


# ─── PUT /admin/users/<id> ───────────────────────────────────────────────
@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@jwt_required()
@admin_required
def modifier_user(user_id):
    """Modifier les informations d'un utilisateur."""
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}

    nom   = (data.get("nom") or "").strip()
    email = (data.get("email") or "").strip().lower()
    role  = data.get("role")

    if not nom:
        return jsonify({"message": "Le nom est requis."}), 400
    if not email:
        return jsonify({"message": "L'adresse email est requise."}), 400
    if role and role not in ("admin", "client", "user"):
        return jsonify({"message": "Rôle invalide."}), 400

    # Vérifier unicité email si changé
    existing = User.query.filter_by(email=email).first()
    if existing and existing.id != user_id:
        return jsonify({"message": "Cette adresse email est déjà utilisée."}), 409

    user.nom   = nom
    user.email = email
    if role:
        user.role = role

    db.session.commit()
    return jsonify({"message": "Utilisateur mis à jour.", "user": user.to_dict()}), 200


# ─── DELETE /admin/users/<id> ────────────────────────────────────────────
@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def supprimer_user(user_id):
    """Suppression douce (soft delete) d'un utilisateur."""
    user = User.query.get_or_404(user_id)

    # Empêcher la suppression de son propre compte
    from flask_jwt_extended import get_jwt_identity
    if get_jwt_identity() == user_id:
        return jsonify({"message": "Vous ne pouvez pas supprimer votre propre compte."}), 400

    user.actif = False
    db.session.commit()
    return jsonify({"message": "Compte désactivé avec succès."}), 200


# ─── PATCH /admin/users/<id>/role ────────────────────────────────────────
@admin_bp.route("/users/<int:user_id>/role", methods=["PATCH"])
@jwt_required()
@admin_required
def changer_role(user_id):
    """Promouvoir / rétrograder un utilisateur."""
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}
    nouveau_role = data.get("role")

    if nouveau_role not in ("user", "admin", "client"):
        return jsonify({"message": "Rôle invalide. Valeurs : 'user', 'client' ou 'admin'."}), 400

    user.role = nouveau_role
    db.session.commit()
    return jsonify({"message": f"Rôle mis à jour : {nouveau_role}", "user": user.to_dict()}), 200


# ─── GET /admin/alertes ──────────────────────────────────────────────────
@admin_bp.route("/alertes", methods=["GET"])
@jwt_required()
@admin_required
def alertes_maintenance():
    """Retourne les bornes en panne ou en maintenance."""
    bornes_alertes = Borne.query.filter(
        Borne.statut.in_(["en_panne", "maintenance"]),
        Borne.actif == True
    ).order_by(Borne.statut).all()

    return jsonify({
        "nombre_alertes": len(bornes_alertes),
        "pannes":         sum(1 for b in bornes_alertes if b.statut == "en_panne"),
        "maintenances":   sum(1 for b in bornes_alertes if b.statut == "maintenance"),
        "bornes":         [b.to_dict() for b in bornes_alertes]
    }), 200