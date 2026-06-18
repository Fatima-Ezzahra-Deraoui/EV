from flask import Blueprint, render_template

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    """Page de connexion (point d'entrée)."""
    return render_template("auth/login.html")


@dashboard_bp.route("/admin/dashboard")
def admin_dashboard():
    """Dashboard administrateur principal."""
    return render_template("admin/dashboard.html")


@dashboard_bp.route("/user/dashboard")
def user_dashboard():
    """Dashboard utilisateur."""
    return render_template("user/dashboard.html")


@dashboard_bp.route("/bornes")
def bornes_page():
    """Page gestion des bornes."""
    return render_template("admin/bornes.html")


@dashboard_bp.route("/sessions")
def sessions_page():
    """Page historique des sessions."""
    return render_template("admin/sessions.html")


@dashboard_bp.route("/admin/users")
def users_page():
    """Page gestion des utilisateurs."""
    return render_template("admin/utilisateurs.html")


@dashboard_bp.route("/admin/alertes")
def alertes_page():
    """Page alertes réseau."""
    return render_template("admin/alertes.html")


@dashboard_bp.route("/admin/ml")
def ml_page():
    """Page prédiction IA."""
    return render_template("admin/ml.html")
