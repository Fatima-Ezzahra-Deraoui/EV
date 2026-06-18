"""
test_sessions.py — Tests des sessions de recharge.
Couvre : démarrer, terminer, historique, règles métier.
"""


def _login(client, email, mot_de_passe):
    """Helper : login et retourne le token."""
    r = client.post("/api/auth/login", json={
        "email": email, "mot_de_passe": mot_de_passe
    })
    return r.get_json().get("access_token", "")


def _creer_session(client, token, borne_id):
    """Helper : démarre une session et retourne son id."""
    r = client.post("/api/sessions/demarrer", headers={
        "Authorization": f"Bearer {token}"
    }, json={"borne_id": borne_id})
    data = r.get_json()
    # La route retourne {"message": ..., "session": {...}}
    return r.status_code, data.get("session", {}).get("id")


class TestDemarrerSession:
    """Tests POST /api/sessions/demarrer"""

    def test_demarrer_session_succes(self, client, user_token, borne_test):
        """Un utilisateur peut démarrer une session sur une borne disponible."""
        r = client.post("/api/sessions/demarrer", headers={
            "Authorization": f"Bearer {user_token}"
        }, json={"borne_id": borne_test})
        assert r.status_code == 201
        data = r.get_json()
        assert "session" in data
        assert data["session"]["statut"] == "en_cours"
        assert data["session"]["borne_id"] == borne_test

    def test_demarrer_session_borne_occupee(self, client, app, user_token, borne_test):
        """Impossible de démarrer une session sur une borne déjà occupée."""
        # Première session par user1
        client.post("/api/sessions/demarrer", headers={
            "Authorization": f"Bearer {user_token}"
        }, json={"borne_id": borne_test})

        # Créer un second utilisateur
        from app import db, bcrypt
        from app.models.user import User
        with app.app_context():
            u2 = User(
                nom="Second", prenom="User", email="second@test.com",
                mot_de_passe_hash=bcrypt.generate_password_hash("Second1234!").decode(),
                role="user", actif=True
            )
            db.session.add(u2)
            db.session.commit()

        token2 = _login(client, "second@test.com", "Second1234!")

        # Deuxième tentative sur la même borne
        r = client.post("/api/sessions/demarrer", headers={
            "Authorization": f"Bearer {token2}"
        }, json={"borne_id": borne_test})
        assert r.status_code == 409

    def test_demarrer_deux_sessions_simultanees(self, client, user_token, borne_test):
        """Un utilisateur ne peut pas avoir deux sessions en cours."""
        # Première session
        client.post("/api/sessions/demarrer", headers={
            "Authorization": f"Bearer {user_token}"
        }, json={"borne_id": borne_test})
        # Deuxième tentative
        r = client.post("/api/sessions/demarrer", headers={
            "Authorization": f"Bearer {user_token}"
        }, json={"borne_id": borne_test})
        assert r.status_code == 409

    def test_demarrer_session_sans_token(self, client, borne_test):
        """Sans authentification, impossible de démarrer une session."""
        r = client.post("/api/sessions/demarrer", json={"borne_id": borne_test})
        assert r.status_code == 401

    def test_demarrer_session_borne_inexistante(self, client, user_token):
        """Démarrer une session sur une borne inexistante retourne 404."""
        r = client.post("/api/sessions/demarrer", headers={
            "Authorization": f"Bearer {user_token}"
        }, json={"borne_id": 9999})
        assert r.status_code == 404


class TestTerminerSession:
    """Tests PATCH /api/sessions/<id>/terminer"""

    def test_terminer_session_succes(self, client, user_token, borne_test):
        """L'utilisateur peut terminer sa propre session."""
        status, session_id = _creer_session(client, user_token, borne_test)
        assert status == 201

        r = client.patch(f"/api/sessions/{session_id}/terminer", headers={
            "Authorization": f"Bearer {user_token}"
        }, json={"energie_kwh": 10.5})
        assert r.status_code == 200
        data = r.get_json()
        assert data["session"]["statut"] == "terminee"
        assert float(data["session"]["energie_kwh"]) == 10.5

    def test_montant_calcule_correctement(self, client, user_token, borne_test):
        """Le montant est calculé : énergie × prix/kWh (0.30 €/kWh)."""
        _, session_id = _creer_session(client, user_token, borne_test)
        r = client.patch(f"/api/sessions/{session_id}/terminer", headers={
            "Authorization": f"Bearer {user_token}"
        }, json={"energie_kwh": 10.0})
        assert r.status_code == 200
        data = r.get_json()
        # prix_kwh=0.30 × energie=10.0 → 3.00 €
        montant = float(data["session"].get("cout_total") or 0)
        assert abs(montant - 3.00) < 0.05

    def test_terminer_session_admin(self, client, app, user_token, admin_token, borne_test):
        """Un admin peut terminer la session d'un autre utilisateur."""
        _, session_id = _creer_session(client, user_token, borne_test)
        r = client.patch(f"/api/sessions/{session_id}/terminer", headers={
            "Authorization": f"Bearer {admin_token}"
        }, json={"energie_kwh": 5.0})
        assert r.status_code == 200

    def test_terminer_session_deja_terminee(self, client, user_token, borne_test):
        """Terminer une session déjà terminée retourne 400."""
        _, session_id = _creer_session(client, user_token, borne_test)
        # Première terminaison
        client.patch(f"/api/sessions/{session_id}/terminer", headers={
            "Authorization": f"Bearer {user_token}"
        }, json={"energie_kwh": 5.0})
        # Deuxième tentative
        r = client.patch(f"/api/sessions/{session_id}/terminer", headers={
            "Authorization": f"Bearer {user_token}"
        }, json={"energie_kwh": 5.0})
        assert r.status_code == 400


class TestHistoriqueSessions:
    """Tests GET /api/sessions/mes-sessions et /api/sessions/historique"""

    def test_mes_sessions_vide(self, client, user_token):
        """L'historique personnel est vide pour un nouvel utilisateur."""
        r = client.get("/api/sessions/mes-sessions", headers={
            "Authorization": f"Bearer {user_token}"
        })
        assert r.status_code == 200
        assert r.get_json() == []

    def test_mes_sessions_apres_recharge(self, client, user_token, borne_test):
        """L'historique personnel contient la session terminée."""
        _, session_id = _creer_session(client, user_token, borne_test)
        client.patch(f"/api/sessions/{session_id}/terminer", headers={
            "Authorization": f"Bearer {user_token}"
        }, json={"energie_kwh": 8.0})

        r = client.get("/api/sessions/mes-sessions", headers={
            "Authorization": f"Bearer {user_token}"
        })
        assert r.status_code == 200
        sessions = r.get_json()
        assert len(sessions) == 1
        assert sessions[0]["statut"] == "terminee"

    def test_historique_complet_admin_uniquement(self, client, user_token, admin_token):
        """L'historique complet est réservé aux admins."""
        r_user = client.get("/api/sessions/historique", headers={
            "Authorization": f"Bearer {user_token}"
        })
        assert r_user.status_code == 403

        r_admin = client.get("/api/sessions/historique", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert r_admin.status_code == 200
        assert isinstance(r_admin.get_json(), list)
