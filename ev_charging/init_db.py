"""
Script à exécuter UNE SEULE FOIS pour :
1. Créer toutes les tables dans PostgreSQL
2. Créer un compte admin par défaut
3. Insérer quelques bornes de test

Usage :
    python init_db.py
"""

from app import create_app, db
from app.models.user import User
from app.models.borne import Borne
from app.models.session_recharge import SessionRecharge  # noqa: F401


def initialiser_base():
    app = create_app()

    with app.app_context():
        print("⚡ Création des tables...")
        db.create_all()
        print("✅ Tables créées.")

        # ─── Admin par défaut ──────────────────────────────────────────
        if not User.query.filter_by(email="admin@ev-charging.com").first():
            admin = User(
                nom="Admin",
                prenom="Principal",
                email="admin@ev-charging.com",
                role="admin",
                actif=True
            )
            admin.set_password("Admin1234!")
            db.session.add(admin)
            print("✅ Compte admin créé : admin@ev-charging.com / Admin1234!")
        else:
            print("ℹ️  Admin déjà existant.")

        # ─── Bornes de test ────────────────────────────────────────────
        if Borne.query.count() == 0:
            bornes_test = [
                Borne(
                    nom="Borne A1 - Centre Commercial",
                    adresse="12 Avenue de la Gare",
                    ville="Casablanca",
                    code_postal="20000",
                    latitude=33.5731,
                    longitude=-7.5898,
                    puissance_kw=22.0,
                    type_connecteur="Type 2",
                    prix_kwh=0.30,
                    statut="disponible",
                    qr_code="QR-A1-001"
                ),
                Borne(
                    nom="Borne B2 - Parking Université",
                    adresse="45 Boulevard Hassan II",
                    ville="Casablanca",
                    code_postal="20100",
                    latitude=33.5850,
                    longitude=-7.6350,
                    puissance_kw=50.0,
                    type_connecteur="CCS Combo",
                    prix_kwh=0.45,
                    statut="disponible",
                    qr_code="QR-B2-002"
                ),
                Borne(
                    nom="Borne C3 - Parking Aéroport",
                    adresse="Route de l'Aéroport",
                    ville="Casablanca",
                    code_postal="20800",
                    latitude=33.3675,
                    longitude=-7.5898,
                    puissance_kw=150.0,
                    type_connecteur="CCS Combo",
                    prix_kwh=0.60,
                    statut="en_panne",
                    qr_code="QR-C3-003"
                ),
            ]

            db.session.add_all(bornes_test)
            print(f"✅ {len(bornes_test)} bornes de test créées.")
        else:
            print(f"ℹ️  {Borne.query.count()} bornes déjà présentes.")

        db.session.commit()
        print("\n🚀 Base de données prête ! Lance l'app avec : python run.py")


if __name__ == "__main__":
    initialiser_base()
