from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_bcrypt import Bcrypt
from flask_cors import CORS

from config import get_config

# ─── Extensions (instanciées sans app, configurées dans create_app) ───
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
socketio = SocketIO()
bcrypt = Bcrypt()


def create_app(test_config=None):
    """
    Factory Flask : crée et configure l'application.
    Accepte un dict test_config optionnel pour les tests pytest.
    Le test_config est appliqué AVANT jwt.init_app() pour que
    JWT_SECRET_KEY soit correctement pris en compte.
    """
    app = Flask(__name__)
    app.config.from_object(get_config())

    # ─── Override de config pour les tests (AVANT init extensions) ────
    if test_config is not None:
        app.config.update(test_config)

    # ─── Initialisation des extensions ────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    CORS(app, origins=app.config.get("CORS_ORIGINS", "*"))
    socketio.init_app(
        app,
        async_mode=app.config.get("SOCKETIO_ASYNC_MODE", "threading"),
        cors_allowed_origins="*"
    )

    # ─── Importation des modèles (nécessaire pour Flask-Migrate) ──────
    from app.models import User, Borne, SessionRecharge  # noqa: F401

    # ─── Enregistrement des Blueprints (routes) ───────────────────────
    from app.routes.auth import auth_bp
    from app.routes.bornes import bornes_bp
    from app.routes.sessions import sessions_bp
    from app.routes.admin import admin_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.predict import predict_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(bornes_bp, url_prefix="/api/bornes")
    app.register_blueprint(sessions_bp, url_prefix="/api/sessions")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(dashboard_bp, url_prefix="/")
    app.register_blueprint(predict_bp, url_prefix="/api/predict")

    # ─── Gestion des erreurs JWT ───────────────────────────────────────
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {"message": "Token expiré, veuillez vous reconnecter."}, 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {"message": "Token invalide."}, 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {"message": "Token manquant. Authentification requise."}, 401

    return app
