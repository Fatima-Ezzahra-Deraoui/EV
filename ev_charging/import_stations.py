import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath("."))

from app import create_app, db
from app.models.borne import Borne

app = create_app()

with app.app_context():
    df = pd.read_csv("ml/data/raw/sessions_maroc_adapte.csv")

    # Stations uniques avec toutes leurs infos
    stations = df[[
        "borne_id", "site_id", "type_site",
        "ville", "code_postal", "latitude", "longitude"
    ]].drop_duplicates(subset=["borne_id"])

    count = 0
    for _, row in stations.iterrows():
        existe = Borne.query.filter_by(nom=f"Borne {row['borne_id']}").first()
        if not existe:
            borne = Borne(
                nom=f"Borne {row['borne_id']}",
                adresse=f"{row['type_site']} — Site {row['site_id']}",
                ville=str(row["ville"]),
                code_postal=str(row["code_postal"]),
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                puissance_kw=22.0,
                type_connecteur="Type 2",
                prix_kwh=float(row["prix_kwh_mad"]),
                statut="disponible",
                actif=True,
            )
            db.session.add(borne)
            count += 1

    db.session.commit()
    print(f" {count} bornes importées avec succès.")
    print(f"Total bornes en base : {Borne.query.count()}")