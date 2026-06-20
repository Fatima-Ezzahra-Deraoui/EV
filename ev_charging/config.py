import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()


class Config:
    # ─── Sécurité ────────────────────────────────────────────────────────
    SECRET_KEY                 = os.getenv("SECRET_KEY", "dev_secret_key_changez_moi")
    JWT_SECRET_KEY             = os.getenv("JWT_SECRET_KEY", "dev_jwt_secret_changez_moi")
    JWT_ACCESS_TOKEN_EXPIRES   = timedelta(hours=2)
    JWT_REFRESH_TOKEN_EXPIRES  = timedelta(days=30)
    JWT_ALGORITHM              = "HS256"
    JWT_TOKEN_LOCATION         = ["headers"]
    JWT_HEADER_NAME            = "Authorization"
    JWT_HEADER_TYPE            = "Bearer"

    # ─── Base de données ─────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = "postgresql+psycopg://postgres:motdepasse@localhost:5432/ev_charging_db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO                = False
    SQLALCHEMY_ENGINE_OPTIONS      = {
        "pool_pre_ping": True,        # Vérifie la connexion avant utilisation
        "pool_recycle":  300,         # Recycle les connexions toutes les 5 min
        "pool_size":     10,
        "max_overflow":  20,
    }

    # ─── Socket.IO ───────────────────────────────────────────────────────
    SOCKETIO_ASYNC_MODE = os.getenv("SOCKETIO_ASYNC_MODE", "eventlet")

    # ─── CORS ────────────────────────────────────────────────────────────
    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5000,http://127.0.0.1:5000"
    ).split(",")

    # ─── Upload fichiers (si nécessaire) ─────────────────────────────────
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024   # 16 Mo max

    # ─── Logs ────────────────────────────────────────────────────────────
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @staticmethod
    def validate():
        """
        Vérifie que les variables critiques ne sont pas
        les valeurs par défaut en production.
        """
        warnings = []
        if os.getenv("SECRET_KEY") is None:
            warnings.append("SECRET_KEY non définie — valeur par défaut utilisée.")
        if os.getenv("JWT_SECRET_KEY") is None:
            warnings.append("JWT_SECRET_KEY non définie — valeur par défaut utilisée.")
        if os.getenv("DATABASE_URL") is None:
            warnings.append("DATABASE_URL non définie — base locale utilisée.")
        return warnings


class DevelopmentConfig(Config):
    DEBUG          = True
    SQLALCHEMY_ECHO = True   # Affiche les requêtes SQL dans le terminal

    # Pool plus petit en dev
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle":  300,
        "pool_size":     5,
        "max_overflow":  10,
    }


class ProductionConfig(Config):
    DEBUG           = False
    SQLALCHEMY_ECHO = False

    # Tokens plus courts en production pour limiter l'exposition
    JWT_ACCESS_TOKEN_EXPIRES  = timedelta(minutes=30)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

    @classmethod
    def validate(cls):
        errors = super().validate()
        # En production, les clés par défaut sont inacceptables
        if os.getenv("SECRET_KEY") is None:
            raise RuntimeError("SECRET_KEY doit être définie en production.")
        if os.getenv("JWT_SECRET_KEY") is None:
            raise RuntimeError("JWT_SECRET_KEY doit être définie en production.")
        if os.getenv("DATABASE_URL") is None:
            raise RuntimeError("DATABASE_URL doit être définie en production.")
        return errors


class TestingConfig(Config):
    TESTING                        = True
    DEBUG                          = True
    SQLALCHEMY_DATABASE_URI        = "sqlite:///:memory:"
    SQLALCHEMY_ECHO                = False
    JWT_ACCESS_TOKEN_EXPIRES       = timedelta(minutes=5)
    JWT_REFRESH_TOKEN_EXPIRES      = timedelta(minutes=10)
    WTF_CSRF_ENABLED               = False

    # Désactiver le pool pour SQLite en mémoire
    SQLALCHEMY_ENGINE_OPTIONS      = {}


# ─── Mapping environnement → config ──────────────────────────────────────
config_map = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "testing":     TestingConfig,
}


def get_config():
    """
    Retourne la classe de configuration selon FLASK_ENV.
    Affiche les avertissements si des variables critiques manquent.
    """
    env    = os.getenv("FLASK_ENV", "development").lower()
    cfg    = config_map.get(env, DevelopmentConfig)

    # Afficher les warnings de configuration au démarrage
    warnings = cfg.validate()
    if warnings and env != "testing":
        for w in warnings:
            print(f"[CONFIG WARNING] {w}")

    return cfg