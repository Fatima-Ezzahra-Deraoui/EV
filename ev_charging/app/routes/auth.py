from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
)
from datetime import datetime

from app import db
from app.models.user import User

auth_bp = Blueprint("auth", __name__)


# ─── POST /api/auth/register ──────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    """Créer un nouveau compte utilisateur."""
    data = request.get_json()

    # Validation des champs obligatoires
    champs_requis = ["nom", "prenom", "email", "mot_de_passe"]
    for champ in champs_requis:
        if champ not in data or not data[champ]:
            return jsonify({"message": f"Le champ '{champ}' est requis."}), 400

    # Vérifier si l'email existe déjà
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"message": "Un compte existe déjà avec cet email."}), 409

    # Créer l'utilisateur
    user = User(
        nom=data["nom"],
        prenom=data["prenom"],
        email=data["email"],
        telephone=data.get("telephone"),
        role=data.get("role", "user"),
    )
    user.set_password(data["mot_de_passe"])

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "message": "Compte créé avec succès.",
        "user": user.to_dict()
    }), 201


# ─── POST /api/auth/login ─────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    """Connexion utilisateur — retourne un access token et un refresh token."""
    data = request.get_json()

    if not data.get("email") or not data.get("mot_de_passe"):
        return jsonify({"message": "Email et mot de passe requis."}), 400

    user = User.query.filter_by(email=data["email"]).first()

    if not user or not user.check_password(data["mot_de_passe"]):
        return jsonify({"message": "Email ou mot de passe incorrect."}), 401

    if not user.actif:
        return jsonify({"message": "Compte désactivé. Contactez un administrateur."}), 403

    # Mettre à jour la dernière connexion
    user.derniere_connexion = datetime.utcnow()
    db.session.commit()

    # identity = string (user_id), role stocké dans additional_claims
    # Flask-JWT-Extended 4.6+ exige que identity soit un string/int, pas un dict
    identity = str(user.id)
    additional_claims = {"role": user.role}

    access_token = create_access_token(
        identity=identity,
        additional_claims=additional_claims
    )
    refresh_token = create_refresh_token(
        identity=identity,
        additional_claims=additional_claims
    )

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict()
    }), 200


# ─── POST /api/auth/refresh ───────────────────────────────────────────────
@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """Renouveler l'access token avec le refresh token."""
    identity = get_jwt_identity()
    claims = get_jwt()
    additional_claims = {"role": claims.get("role", "user")}
    new_access_token = create_access_token(
        identity=identity,
        additional_claims=additional_claims
    )
    return jsonify({"access_token": new_access_token}), 200


# ─── GET /api/auth/me ─────────────────────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """Retourne les infos de l'utilisateur connecté."""
    user_id = get_jwt_identity()  # string
    user = User.query.get_or_404(int(user_id))
    return jsonify(user.to_dict()), 200
