"""
test_ml.py — Tests des endpoints de prédiction IA.
Couvre : disponibilité, recommandation, heatmap, fichiers modèle.
"""
import os
import pytest


class TestPredictionDisponibilite:
    """Tests POST /api/predict/disponibilite"""

    def test_prediction_retourne_resultat(self, client, admin_token, borne_test):
        """La prédiction retourne un résultat structuré (200) ou signale modèle absent (503)."""
        r = client.post("/api/predict/disponibilite", headers={
            "Authorization": f"Bearer {admin_token}"
        }, json={
            "borne_id": borne_test,
            "heure": 14,
            "jour_semaine": 1,
            "mois": 6
        })
        assert r.status_code in (200, 503)
        if r.status_code == 200:
            data = r.get_json()
            assert "prediction" in data
            assert data["prediction"] in ("disponible", "occupee")
            assert "probabilite_occupation" in data
            assert 0.0 <= float(data["probabilite_occupation"]) <= 1.0

    def test_prediction_heure_pic(self, client, admin_token, borne_test):
        """Prédiction à 18h (heure de pointe) — doit retourner un résultat valide."""
        r = client.post("/api/predict/disponibilite", headers={
            "Authorization": f"Bearer {admin_token}"
        }, json={
            "borne_id": borne_test,
            "heure": 18,
            "jour_semaine": 0,
            "mois": 6
        })
        assert r.status_code in (200, 503)

    def test_prediction_champs_manquants(self, client, admin_token, borne_test):
        """Une requête sans les champs requis retourne 400."""
        r = client.post("/api/predict/disponibilite", headers={
            "Authorization": f"Bearer {admin_token}"
        }, json={"borne_id": borne_test})
        assert r.status_code == 400

    def test_prediction_sans_token(self, client, borne_test):
        """Sans authentification, la prédiction est refusée."""
        r = client.post("/api/predict/disponibilite", json={
            "borne_id": borne_test,
            "heure": 10,
            "jour_semaine": 2,
            "mois": 6
        })
        assert r.status_code == 401

    def test_prediction_toutes_heures(self, client, admin_token, borne_test):
        """La prédiction fonctionne pour chaque heure de la journée."""
        for heure in [0, 6, 12, 18, 23]:
            r = client.post("/api/predict/disponibilite", headers={
                "Authorization": f"Bearer {admin_token}"
            }, json={
                "borne_id": borne_test,
                "heure": heure,
                "jour_semaine": 1,
                "mois": 6
            })
            assert r.status_code in (200, 503), f"Erreur pour heure={heure}"


class TestRecommandation:
    """Tests GET /api/predict/recommander"""

    def test_recommander_authentifie(self, client, admin_token, borne_test):
        """L'endpoint recommandation nécessite une authentification."""
        r = client.get("/api/predict/recommander", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert r.status_code in (200, 503)

    def test_recommander_sans_token(self, client):
        """Sans token, la recommandation est refusée."""
        r = client.get("/api/predict/recommander")
        assert r.status_code == 401


class TestHeatmap:
    """Tests GET /api/predict/heatmap/<borne_id>"""

    def test_heatmap_borne_existante(self, client, admin_token, borne_test):
        """La heatmap retourne les données d'occupation pour une borne."""
        r = client.get(f"/api/predict/heatmap/{borne_test}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert r.status_code in (200, 503)

    def test_heatmap_sans_token(self, client, borne_test):
        """Sans token, la heatmap est refusée."""
        r = client.get(f"/api/predict/heatmap/{borne_test}")
        assert r.status_code == 401


class TestModeleML:
    """Tests unitaires sur les artefacts ML directement."""

    def test_modele_pkl_existe(self):
        """Le fichier modèle .pkl doit exister après train_model.py."""
        model_path = os.path.join(
            os.path.dirname(__file__), "..", "ml", "model", "model_disponibilite.pkl"
        )
        assert os.path.exists(model_path), \
            "Modèle introuvable — lancez : python ml/train_model.py"

    def test_donnees_csv_existent(self):
        """Les fichiers CSV générés doivent exister."""
        data_dir = os.path.join(os.path.dirname(__file__), "..", "ml", "data")
        assert os.path.exists(os.path.join(data_dir, "sessions_historiques.csv")), \
            "Données manquantes — lancez : python ml/generate_data.py"
        assert os.path.exists(os.path.join(data_dir, "dataset_disponibilite.csv")), \
            "Dataset ML manquant — lancez : python ml/generate_data.py"

    def test_modele_chargeable_et_predictif(self):
        """Le modèle peut être rechargé et produit des prédictions valides."""
        import pickle
        import numpy as np
        model_path = os.path.join(
            os.path.dirname(__file__), "..", "ml", "model", "model_disponibilite.pkl"
        )
        if not os.path.exists(model_path):
            pytest.skip("Modèle non entraîné — ignoré")

        with open(model_path, "rb") as f:
            artefacts = pickle.load(f)

        assert "model" in artefacts
        model = artefacts["model"]

        # Test de prédiction : [borne_id, heure, jour_semaine, est_weekend, mois]
        X = np.array([[1, 14, 1, 0, 6]])
        pred = model.predict(X)
        assert pred[0] in (0, 1), "La prédiction doit être 0 (disponible) ou 1 (occupée)"

        proba = model.predict_proba(X)
        assert proba.shape[1] == 2
        assert abs(proba[0].sum() - 1.0) < 1e-6, "Les probabilités doivent sommer à 1"

    def test_accuracy_minimale(self):
        """L'accuracy du modèle doit dépasser 60%."""
        import pickle
        model_path = os.path.join(
            os.path.dirname(__file__), "..", "ml", "model", "model_disponibilite.pkl"
        )
        if not os.path.exists(model_path):
            pytest.skip("Modèle non entraîné — ignoré")

        with open(model_path, "rb") as f:
            artefacts = pickle.load(f)

        accuracy = artefacts.get("accuracy", 0)
        assert accuracy >= 0.60, \
            f"Accuracy trop faible : {accuracy:.2%} (minimum : 60%)"
