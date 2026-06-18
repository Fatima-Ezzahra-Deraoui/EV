"""
test_auth.py — Tests des routes d'authentification.
Couvre : inscription, connexion, accès profil, token invalide.
"""


class TestInscription:
    """Tests POST /api/auth/register"""

    def test_inscription_succes(self, client):
        """Un nouvel utilisateur peut s'inscrire avec des données valides."""
        r = client.post("/api/auth/register", json={
            "nom": "Martin",
            "prenom": "Sophie",
            "email": "sophie@test.com",
            "mot_de_passe": "Sophie1234!",
            "telephone": "0612345678"
        })
        assert r.status_code == 201
        data = r.get_json()
        # L'API register retourne message + user (pas de token direct — c'est normal)
        assert "user" in data
        assert data["user"]["email"] == "sophie@test.com"
        assert data["user"]["role"] == "user"

    def test_inscription_email_duplique(self, client):
        """Deux inscriptions avec le même email sont refusées."""
        payload = {
            "nom": "Durand",
            "prenom": "Paul",
            "email": "paul@test.com",
            "mot_de_passe": "Paul1234!"
        }
        client.post("/api/auth/register", json=payload)
        r = client.post("/api/auth/register", json=payload)
        assert r.status_code == 409

    def test_inscription_champs_manquants(self, client):
        """Une inscription sans email ou mot de passe est rejetée."""
        r = client.post("/api/auth/register", json={"nom": "Sans", "prenom": "Email"})
        assert r.status_code == 400

    def test_inscription_retourne_user_sans_mdp(self, client):
        """L'inscription ne doit jamais exposer le hash du mot de passe."""
        r = client.post("/api/auth/register", json={
            "nom": "Secure",
            "prenom": "Test",
            "email": "secure@test.com",
            "mot_de_passe": "Secure1234!"
        })
        data = r.get_json()
        assert "mot_de_passe" not in data.get("user", {})
        assert "mot_de_passe_hash" not in data.get("user", {})


class TestConnexion:
    """Tests POST /api/auth/login"""

    def test_login_succes_admin(self, client, admin_token):
        """L'admin peut se connecter et reçoit un token JWT valide."""
        assert admin_token != ""
        assert len(admin_token) > 20

    def test_login_succes_user(self, client, user_token):
        """Un utilisateur standard peut se connecter."""
        assert user_token != ""

    def test_login_retourne_token_et_user(self, client):
        """Le login retourne access_token, refresh_token et user."""
        from app import db, bcrypt
        from app.models.user import User
        with client.application.app_context():
            u = User(
                nom="Login", prenom="Test", email="logintest@test.com",
                mot_de_passe_hash=bcrypt.generate_password_hash("Test1234!").decode(),
                role="user", actif=True
            )
            db.session.add(u)
            db.session.commit()

        r = client.post("/api/auth/login", json={
            "email": "logintest@test.com",
            "mot_de_passe": "Test1234!"
        })
        assert r.status_code == 200
        data = r.get_json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data

    def test_login_mauvais_mot_de_passe(self, client, admin_token):
        """Un mauvais mot de passe retourne 401."""
        r = client.post("/api/auth/login", json={
            "email": "admin@test.com",
            "mot_de_passe": "mauvais_mdp"
        })
        assert r.status_code == 401

    def test_login_email_inexistant(self, client):
        """Un email inconnu retourne 401."""
        r = client.post("/api/auth/login", json={
            "email": "inconnu@test.com",
            "mot_de_passe": "Test1234!"
        })
        assert r.status_code == 401

    def test_login_corps_vide(self, client):
        """Une requête sans corps retourne 400."""
        r = client.post("/api/auth/login", json={})
        assert r.status_code == 400


class TestProfilUtilisateur:
    """Tests GET /api/auth/me"""

    def test_profil_avec_token_valide(self, client, user_token):
        """Un utilisateur authentifié peut accéder à son profil."""
        r = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {user_token}"
        })
        assert r.status_code == 200
        data = r.get_json()
        assert "email" in data
        assert data["email"] == "jean@test.com"

    def test_profil_sans_token(self, client):
        """Sans token, l'accès au profil est refusé."""
        r = client.get("/api/auth/me")
        assert r.status_code == 401

    def test_profil_token_invalide(self, client):
        """Un token falsifié est rejeté."""
        r = client.get("/api/auth/me", headers={
            "Authorization": "Bearer token.faux.invalide"
        })
        assert r.status_code == 401

    def test_profil_ne_retourne_pas_mdp(self, client, user_token):
        """Le profil ne doit jamais exposer le hash du mot de passe."""
        r = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {user_token}"
        })
        data = r.get_json()
        assert "mot_de_passe_hash" not in data
        assert "mot_de_passe" not in data
