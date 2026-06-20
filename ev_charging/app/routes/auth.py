from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
)
from datetime import datetime, timezone

from app import db
from app.models.user import User

auth_bp = Blueprint("auth", __name__)


# ─── Helpers ─────────────────────────────────────────────────────────────
def _tokens(user):
    """Génère access + refresh token pour un utilisateur."""
    identity = str(user.id)
    claims   = {"role": user.role}
    return (
        create_access_token(identity=identity,  additional_claims=claims),
        create_refresh_token(identity=identity, additional_claims=claims),
    )


def _validate_password(password: str):
    """
    Valide la robustesse du mot de passe.
    Retourne un message d'erreur ou None si valide.
    """
    if len(password) < 8:
        return "Le mot de passe doit contenir au moins 8 caractères."
    if not any(c.isupper() for c in password):
        return "Le mot de passe doit contenir au moins une majuscule."
    if not any(c.isdigit() for c in password):
        return "Le mot de passe doit contenir au moins un chiffre."
    return None


# ─── POST /api/auth/register ─────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    """Créer un nouveau compte utilisateur."""
    data = request.get_json(silent=True) or {}

    # Validation champs obligatoires
    champs_requis = ["nom", "email", "mot_de_passe"]
    for champ in champs_requis:
        if not data.get(champ, "").strip():
            return jsonify({"message": f"Le champ '{champ}' est requis."}), 400

    email    = data["email"].strip().lower()
    nom      = data["nom"].strip()
    prenom   = data.get("prenom", "").strip()
    password = data["mot_de_passe"]
    role     = data.get("role", "client")

    # Validation email basique
    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify({"message": "Adresse email invalide."}), 400

    # Validation rôle (on ne laisse pas créer un admin via register public)
    if role not in ("client", "user"):
        role = "client"

    # Validation mot de passe
    erreur_pwd = _validate_password(password)
    if erreur_pwd:
        return jsonify({"message": erreur_pwd}), 400

    # Unicité email
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Un compte existe déjà avec cet email."}), 409

    user = User(
        nom=nom,
        prenom=prenom if prenom else None,
        email=email,
        telephone=data.get("telephone"),
        role=role,
        actif=True,
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    access_token, refresh_token = _tokens(user)

    return jsonify({
        "message":       "Compte créé avec succès.",
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "user":          user.to_dict()
    }), 201


# ─── POST /api/auth/login ────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    """Connexion utilisateur — retourne access token et refresh token."""
    data = request.get_json(silent=True) or {}

    email    = (data.get("email") or "").strip().lower()
    password = data.get("mot_de_passe") or data.get("password") or ""

    if not email:
        return jsonify({"message": "L'adresse email est requise."}), 400
    if not password:
        return jsonify({"message": "Le mot de passe est requis."}), 400

    user = User.query.filter_by(email=email).first()

    # Message générique volontaire pour ne pas divulguer si l'email existe
    if not user or not user.check_password(password):
        return jsonify({"message": "Email ou mot de passe incorrect."}), 401

    if not user.actif:
        return jsonify({"message": "Compte désactivé. Contactez un administrateur."}), 403

    # Mise à jour dernière connexion (UTC aware)
    user.derniere_connexion = datetime.now(timezone.utc)
    db.session.commit()

    access_token, refresh_token = _tokens(user)

    return jsonify({
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "user":          user.to_dict()
    }), 200


# ─── POST /api/auth/refresh ──────────────────────────────────────────────
@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """Renouveler l'access token avec le refresh token."""
    identity = get_jwt_identity()
    claims   = get_jwt()
    role     = claims.get("role", "client")

    new_access = create_access_token(
        identity=identity,
        additional_claims={"role": role}
    )
    return jsonify({"access_token": new_access}), 200


# ─── POST /api/auth/logout ───────────────────────────────────────────────
@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """
    Déconnexion côté client.
    Le token reste techniquement valide jusqu'à expiration
    (implémentez une blocklist Redis pour invalidation stricte).
    """
    return jsonify({"message": "Déconnexion effectuée. Supprimez les tokens côté client."}), 200


# ─── GET /api/auth/me ────────────────────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """Retourne les infos de l'utilisateur connecté."""
    user_id = int(get_jwt_identity())
    user    = User.query.get_or_404(user_id)
    return jsonify(user.to_dict()), 200


# ─── PUT /api/auth/me ────────────────────────────────────────────────────
@auth_bp.route("/me", methods=["PUT"])
@jwt_required()
def update_me():
    """Modifier son propre profil (nom, prénom, téléphone)."""
    user_id = int(get_jwt_identity())
    user    = User.query.get_or_404(user_id)
    data    = request.get_json(silent=True) or {}

    if "nom" in data and data["nom"].strip():
        user.nom = data["nom"].strip()
    if "prenom" in data:
        user.prenom = data["prenom"].strip() or None
    if "telephone" in data:
        user.telephone = data["telephone"].strip() or None

    db.session.commit()
    return jsonify({"message": "Profil mis à jour.", "user": user.to_dict()}), 200


# ─── PUT /api/auth/me/password ───────────────────────────────────────────
@auth_bp.route("/me/password", methods=["PUT"])
@jwt_required()
def change_password():
    """Changer son propre mot de passe."""
    user_id      = int(get_jwt_identity())
    user         = User.query.get_or_404(user_id)
    data         = request.get_json(silent=True) or {}

    ancien       = data.get("ancien_mot_de_passe") or ""
    nouveau      = data.get("nouveau_mot_de_passe") or ""

    if not ancien:
        return jsonify({"message": "L'ancien mot de passe est requis."}), 400
    if not user.check_password(ancien):
        return jsonify({"message": "Ancien mot de passe incorrect."}), 401

    erreur_pwd = _validate_password(nouveau)
    if erreur_pwd:
        return jsonify({"message": erreur_pwd}), 400

    user.set_password(nouveau)
    db.session.commit()
    return jsonify({"message": "Mot de passe mis à jour avec succès."}), 200