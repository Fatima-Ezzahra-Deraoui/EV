# Importation de tous les modèles pour que SQLAlchemy les détecte
# lors de db.create_all() ou des migrations Flask-Migrate

from app.models.user import User
from app.models.borne import Borne
from app.models.session_recharge import SessionRecharge

__all__ = ["User", "Borne", "SessionRecharge"]
