"""
test_bornes.py — Tests des routes CRUD des bornes de recharge.
Couvre : lecture, création, modification, suppression.
"""


class TestListeBornes:
    """Tests GET /api/bornes/"""

    def test_liste_bornes_authentifie(self, client, admin_token, borne_test):
        """Un utilisateur authentifié peut lister les bornes."""
        r = client.get("/api/bornes/", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert r.status_code == 200
        data = r.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_liste_bornes_sans_token(self, client):
        """Sans token, la liste des bornes est refusée."""
        r = client.get("/api/bornes/")
        assert r.status_code == 401

    def test_borne_contient_champs_requis(self, client, admin_token, borne_test):
        """Chaque borne retournée contient les champs essentiels."""
        r = client.get("/api/bornes/", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        bornes = r.get_json()
        assert len(bornes) > 0
        borne = bornes[0]
        for champ in ["id", "nom", "statut", "puissance_kw", "prix_kwh"]:
            assert champ in borne, f"Champ manquant : {champ}"

    def test_borne_ne_retourne_pas_champs_sensibles(self, client, admin_token, borne_test):
        """La liste des bornes ne retourne pas de données sensibles."""
        r = client.get("/api/bornes/", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        bornes = r.get_json()
        for b in bornes:
            assert "mot_de_passe" not in b


class TestCreationBorne:
    """Tests POST /api/bornes/"""

    def test_creation_borne_admin(self, client, admin_token):
        """Un admin peut créer une nouvelle borne."""
        r = client.post("/api/bornes/", headers={
            "Authorization": f"Bearer {admin_token}"
        }, json={
            "nom": "Borne Gare - Quai Nord",
            "adresse": "Place de la Gare",
            "ville": "Casablanca",
            "code_postal": "20000",
            "latitude": 33.5898,
            "longitude": -7.6036,
            "puissance_kw": 50.0,
            "type_connecteur": "CCS",
            "prix_kwh": 0.35,
        })
        assert r.status_code == 201
        data = r.get_json()
        assert "borne" in data
        assert data["borne"]["nom"] == "Borne Gare - Quai Nord"

    def test_creation_borne_user_interdit(self, client, user_token):
        """Un utilisateur standard ne peut pas créer de borne."""
        r = client.post("/api/bornes/", headers={
            "Authorization": f"Bearer {user_token}"
        }, json={
            "nom": "Borne Interdite",
            "adresse": "Rue Inconnue",
            "ville": "Test",
            "puissance_kw": 22.0,
            "type_connecteur": "Type2",
            "prix_kwh": 0.30
        })
        assert r.status_code == 403

    def test_creation_borne_sans_nom_rejetee(self, client, admin_token):
        """La création sans nom est rejetée."""
        r = client.post("/api/bornes/", headers={
            "Authorization": f"Bearer {admin_token}"
        }, json={"puissance_kw": 22.0})
        assert r.status_code == 400


class TestModificationBorne:
    """Tests PUT /api/bornes/<id>"""

    def test_modifier_statut_borne(self, client, admin_token, borne_test):
        """Un admin peut changer le statut d'une borne."""
        r = client.put(f"/api/bornes/{borne_test}", headers={
            "Authorization": f"Bearer {admin_token}"
        }, json={"statut": "maintenance"})
        assert r.status_code == 200
        data = r.get_json()
        assert data["borne"]["statut"] == "maintenance"

    def test_modifier_prix_borne(self, client, admin_token, borne_test):
        """Un admin peut modifier le prix d'une borne."""
        r = client.put(f"/api/bornes/{borne_test}", headers={
            "Authorization": f"Bearer {admin_token}"
        }, json={"prix_kwh": 0.45})
        assert r.status_code == 200
        assert float(r.get_json()["borne"]["prix_kwh"]) == 0.45

    def test_modifier_borne_inexistante(self, client, admin_token):
        """Modifier une borne inexistante retourne 404."""
        r = client.put("/api/bornes/9999", headers={
            "Authorization": f"Bearer {admin_token}"
        }, json={"statut": "disponible"})
        assert r.status_code == 404

    def test_modifier_borne_user_interdit(self, client, user_token, borne_test):
        """Un utilisateur standard ne peut pas modifier une borne."""
        r = client.put(f"/api/bornes/{borne_test}", headers={
            "Authorization": f"Bearer {user_token}"
        }, json={"statut": "en_panne"})
        assert r.status_code == 403


class TestRecuperationBorne:
    """Tests GET /api/bornes/<id>"""

    def test_get_borne_existante(self, client, admin_token, borne_test):
        """Récupération d'une borne par son ID."""
        r = client.get(f"/api/bornes/{borne_test}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data["id"] == borne_test
        assert data["nom"] == "Borne Test - Centre Ville"

    def test_get_borne_inexistante(self, client, admin_token):
        """Récupérer une borne inexistante retourne 404."""
        r = client.get("/api/bornes/9999", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert r.status_code == 404
