"""
conftest.py — Fixtures partagées pour tous les tests pytest.
Utilise SQLite en mémoire pour l'isolation totale.

FIX CLÉ : le test_config est passé directement à create_app()
AVANT que jwt.init_app(app) soit appelé, garantissant que
JWT_SECRET_KEY est correct dès le départ.
"""
import os
import pytest

# Forcer FLASK_ENV=testing AVANT tout import d'app
os.environ["FLASK_ENV"] = "testing"
os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_key_for_pytest_XXXXX_32chars"
os.environ["SECRET_KEY"] = "test_secret_key_for_pytest_YYYYYY_32chars"

# Config de test passée à create_app()
TEST_CONFIG = {
    "TESTING": True,
    "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    "JWT_SECRET_KEY": "test_jwt_secret_key_for_pytest_XXXXX_32chars",
    "SECRET_KEY": "test_secret_key_for_pytest_YYYYYY_32chars",
    "SOCKETIO_ASYNC_MODE": "threading",
    "JWT_ACCESS_TOKEN_EXPIRES": False,  # pas d'expiration en test
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    "WTF_CSRF_ENABLED": False,
}

from app import create_app, db as _db_ext


@pytest.fixture(scope="session")
def app():
    """Crée l'application Flask en mode test — une seule fois par session.
    Le test_config est passé à create_app() AVANT jwt.init_app()."""
    application = create_app(test_config=TEST_CONFIG)
    with application.app_context():
        _db_ext.create_all()
        yield application
        _db_ext.drop_all()


@pytest.fixture(scope="function")
def client(app):
    """
    Client de test Flask avec DB propre pour chaque test.
    Vide toutes les tables avant chaque test.
    """
    with app.app_context():
        for table in reversed(_db_ext.metadata.sorted_tables):
            _db_ext.session.execute(table.delete())
        _db_ext.session.commit()
    return app.test_client()


def _inserer_user(app, email, mot_de_passe, role="user", nom="Test", prenom="User"):
    """Insère un utilisateur directement en base via l'app context."""
    from app import bcrypt
    from app.models.user import User
    with app.app_context():
        u = User(
            nom=nom, prenom=prenom, email=email,
            mot_de_passe_hash=bcrypt.generate_password_hash(mot_de_passe).decode("utf-8"),
            role=role, actif=True
        )
        _db_ext.session.add(u)
        _db_ext.session.commit()


@pytest.fixture(scope="function")
def admin_token(app, client):
    """
    Crée un admin en DB et retourne son JWT via le client de test.
    Le token est signé avec la même JWT_SECRET_KEY que celle configurée
    dans l'app de test (passée via test_config à create_app).
    """
    _inserer_user(app, "admin@test.com", "Admin1234!", role="admin",
                  nom="Admin", prenom="Principal")
    r = client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "mot_de_passe": "Admin1234!"
    })
    assert r.status_code == 200, f"Login admin échoué : {r.get_json()}"
    return r.get_json()["access_token"]


@pytest.fixture(scope="function")
def user_token(app, client):
    """
    Crée un user standard en DB et retourne son JWT via le client de test.
    """
    _inserer_user(app, "jean@test.com", "User1234!", role="user",
                  nom="Dupont", prenom="Jean")
    r = client.post("/api/auth/login", json={
        "email": "jean@test.com",
        "mot_de_passe": "User1234!"
    })
    assert r.status_code == 200, f"Login user échoué : {r.get_json()}"
    return r.get_json()["access_token"]


@pytest.fixture(scope="function")
def borne_test(app, client):
    """Crée une borne disponible en DB et retourne son id."""
    from app.models.borne import Borne
    with app.app_context():
        b = Borne(
            nom="Borne Test - Centre Ville",
            adresse="1 rue de la Paix",
            ville="Casablanca",
            code_postal="20000",
            latitude=33.5731,
            longitude=-7.5898,
            puissance_kw=22.0,
            type_connecteur="Type2",
            prix_kwh=0.30,
            statut="disponible",
            actif=True
        )
        _db_ext.session.add(b)
        _db_ext.session.commit()
        return b.id
