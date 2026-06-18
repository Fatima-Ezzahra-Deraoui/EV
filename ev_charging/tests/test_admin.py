"""
test_admin.py — Tests des routes d'administration.
Couvre : stats, liste utilisateurs, alertes, contrôle d'accès.
Format réel des réponses :
  - /admin/stats    → {"bornes": {...}, "utilisateurs": {...}, "sessions": {...}, "energie": {...}}
  - /admin/users    → [list of users]
  - /admin/alertes  → {"nombre_alertes": int, "bornes": [...]}
"""


class TestStatsAdmin:
    """Tests GET /admin/stats"""

    def test_stats_admin_acces(self, client, admin_token):
        """Un admin peut accéder aux statistiques globales."""
        r = client.get("/admin/stats", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert r.status_code == 200
        data = r.get_json()
        # Format réel : {"bornes": {}, "utilisateurs": {}, "sessions": {}, "energie": {}}
        assert "bornes" in data
        assert "utilisateurs" in data
        assert "sessions" in data
        assert "energie" in data

    def test_stats_user_interdit(self, client, user_token):
        """Un utilisateur standard ne peut pas accéder aux stats admin."""
        r = client.get("/admin/stats", headers={
            "Authorization": f"Bearer {user_token}"
        })
        assert r.status_code == 403

    def test_stats_sans_token(self, client):
        """Sans token, l'accès aux stats est refusé."""
        r = client.get("/admin/stats")
        assert r.status_code == 401

    def test_stats_bornes_coherentes(self, client, admin_token, borne_test):
        """Les stats bornes reflètent les données réelles en base."""
        r = client.get("/admin/stats", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        data = r.get_json()
        assert int(data["bornes"]["total"]) >= 1
        assert int(data["utilisateurs"]["total"]) >= 1

    def test_stats_contient_energie(self, client, admin_token):
        """Les stats incluent les données d'énergie et de revenu."""
        r = client.get("/admin/stats", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        data = r.get_json()
        assert "total_kwh" in data["energie"]
        assert "revenu_total_eur" in data["energie"]


class TestGestionUtilisateurs:
    """Tests GET /admin/users"""

    def test_liste_users_admin(self, client, admin_token, user_token):
        """Un admin peut lister tous les utilisateurs."""
        r = client.get("/admin/users", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert r.status_code == 200
        # Format réel : liste directe (pas de clé "users")
        users = r.get_json()
        assert isinstance(users, list)
        assert len(users) >= 1

    def test_liste_users_user_interdit(self, client, user_token):
        """Un utilisateur standard ne peut pas lister les utilisateurs."""
        r = client.get("/admin/users", headers={
            "Authorization": f"Bearer {user_token}"
        })
        assert r.status_code == 403

    def test_users_ne_retourne_pas_mdp(self, client, admin_token):
        """Les mots de passe ne doivent jamais être exposés dans la liste."""
        r = client.get("/admin/users", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        users = r.get_json()
        for user in users:
            assert "mot_de_passe" not in user
            assert "mot_de_passe_hash" not in user

    def test_users_contient_champs_requis(self, client, admin_token):
        """Chaque utilisateur retourné contient les champs essentiels."""
        r = client.get("/admin/users", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        users = r.get_json()
        assert len(users) > 0
        for u in users:
            assert "email" in u
            assert "role" in u


class TestAlertesAdmin:
    """Tests GET /admin/alertes"""

    def test_alertes_acces_admin(self, client, admin_token):
        """Un admin peut accéder aux alertes."""
        r = client.get("/admin/alertes", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert r.status_code == 200
        data = r.get_json()
        # Format réel : {"nombre_alertes": int, "bornes": [...]}
        assert "nombre_alertes" in data
        assert "bornes" in data

    def test_alertes_user_interdit(self, client, user_token):
        """Un utilisateur standard ne peut pas accéder aux alertes."""
        r = client.get("/admin/alertes", headers={
            "Authorization": f"Bearer {user_token}"
        })
        assert r.status_code == 403

    def test_alertes_sans_pannes(self, client, admin_token, borne_test):
        """Aucune alerte si toutes les bornes sont disponibles."""
        r = client.get("/admin/alertes", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        data = r.get_json()
        assert data["nombre_alertes"] == 0

    def test_alertes_borne_en_panne(self, client, admin_token, borne_test):
        """Une borne en panne apparaît dans les alertes."""
        # Mettre la borne en panne
        client.put(f"/api/bornes/{borne_test}", headers={
            "Authorization": f"Bearer {admin_token}"
        }, json={"statut": "en_panne"})

        r = client.get("/admin/alertes", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        data = r.get_json()
        assert data["nombre_alertes"] >= 1
        ids = [b["id"] for b in data["bornes"]]
        assert borne_test in ids


class TestModelesDonnees:
    """Tests unitaires sur les modèles SQLAlchemy directement."""

    def test_creation_user_model(self, client, app):
        """Le modèle User peut être créé et persisté."""
        from app import db, bcrypt
        from app.models.user import User
        with app.app_context():
            u = User(
                nom="ModelTest", prenom="User",
                email="modeltest@test.com",
                mot_de_passe_hash=bcrypt.generate_password_hash("test").decode(),
                role="user", actif=True
            )
            db.session.add(u)
            db.session.commit()
            assert u.id is not None

    def test_creation_borne_model(self, client, app):
        """Le modèle Borne peut être créé et persisté."""
        from app import db
        from app.models.borne import Borne
        with app.app_context():
            b = Borne(
                nom="Test Borne Model",
                adresse="Test Adresse",
                ville="Casablanca",
                code_postal="20000",
                puissance_kw=22.0,
                type_connecteur="Type2",
                prix_kwh=0.30,
                statut="disponible"
            )
            db.session.add(b)
            db.session.commit()
            assert b.id is not None
            assert b.est_disponible() is True

    def test_methode_est_disponible(self, client, app, borne_test):
        """est_disponible() retourne False pour une borne occupée."""
        from app import db
        from app.models.borne import Borne
        with app.app_context():
            b = Borne.query.get(borne_test)
            assert b.est_disponible() is True
            b.statut = "occupee"
            db.session.commit()
            assert b.est_disponible() is False
