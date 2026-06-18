"""
Génère des données historiques réalistes de sessions de recharge.
Simule 3 bornes sur 90 jours avec des patterns réels :
- Heures de pointe : 8h-9h, 12h-14h, 17h-19h
- Week-ends moins chargés
- Borne C3 souvent en panne
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

random.seed(42)
np.random.seed(42)

BORNES = [
    {"id": 1, "nom": "Borne A1 - Centre Commercial", "puissance_kw": 22.0, "prix_kwh": 0.30},
    {"id": 2, "nom": "Borne B2 - Parking Université", "puissance_kw": 50.0, "prix_kwh": 0.45},
    {"id": 3, "nom": "Borne C3 - Parking Aéroport",  "puissance_kw": 150.0, "prix_kwh": 0.60},
]

# Probabilité d'occupation par heure (0-23) — simule les heures de pointe
PROB_PAR_HEURE = [
    0.02, 0.01, 0.01, 0.01, 0.02, 0.05,  # 0h-5h
    0.10, 0.30, 0.55, 0.45, 0.35, 0.40,  # 6h-11h
    0.60, 0.65, 0.50, 0.40, 0.35, 0.55,  # 12h-17h
    0.70, 0.65, 0.45, 0.30, 0.15, 0.05,  # 18h-23h
]

def generer_sessions(nb_jours=90):
    debut_periode = datetime.now() - timedelta(days=nb_jours)
    sessions = []
    session_id = 1

    for borne in BORNES:
        for jour_offset in range(nb_jours):
            date_jour = debut_periode + timedelta(days=jour_offset)
            est_weekend = date_jour.weekday() >= 5  # samedi=5, dimanche=6

            # Borne C3 (aéroport) a 20% de chances d'être en panne chaque jour
            if borne["id"] == 3 and random.random() < 0.20:
                continue

            for heure in range(24):
                prob = PROB_PAR_HEURE[heure]
                if est_weekend:
                    prob *= 0.6  # moins d'utilisation le week-end

                # Nombre de sessions dans cette heure
                nb_sessions = np.random.poisson(prob * 1.5)

                for _ in range(nb_sessions):
                    minute_debut = random.randint(0, 59)
                    debut = date_jour.replace(hour=heure, minute=minute_debut, second=0)

                    # Durée entre 15 min et 2h (en minutes)
                    duree_min = random.randint(15, 120)
                    fin = debut + timedelta(minutes=duree_min)

                    # Énergie consommée = puissance × durée en heures (avec un facteur aléatoire)
                    energie = round(borne["puissance_kw"] * (duree_min / 60) * random.uniform(0.6, 1.0), 2)
                    cout = round(energie * borne["prix_kwh"], 2)

                    sessions.append({
                        "session_id": session_id,
                        "borne_id": borne["id"],
                        "borne_nom": borne["nom"],
                        "user_id": random.randint(1, 50),
                        "debut": debut,
                        "fin": fin,
                        "duree_minutes": duree_min,
                        "energie_kwh": energie,
                        "cout_total": cout,
                        "heure": heure,
                        "jour_semaine": date_jour.weekday(),  # 0=lundi, 6=dimanche
                        "est_weekend": int(est_weekend),
                        "mois": date_jour.month,
                        "statut": "terminee"
                    })
                    session_id += 1

    df = pd.DataFrame(sessions)
    df = df.sort_values("debut").reset_index(drop=True)
    return df


def generer_dataset_disponibilite(df):
    """
    Crée le dataset pour le modèle ML.
    Pour chaque heure de chaque borne, on indique si elle était occupée (1) ou libre (0).
    Features : borne_id, heure, jour_semaine, est_weekend, mois
    Target : occupee (1) ou disponible (0)
    """
    # Créer toutes les combinaisons borne × heure × jour
    bornes_ids = [1, 2, 3]
    debut_periode = df["debut"].min().date()
    fin_periode = df["debut"].max().date()

    rows = []
    current = datetime.combine(debut_periode, datetime.min.time())
    end = datetime.combine(fin_periode, datetime.min.time())

    while current <= end:
        for borne_id in bornes_ids:
            # Compter les sessions actives à cette heure pour cette borne
            nb_sessions = len(df[
                (df["borne_id"] == borne_id) &
                (df["debut"].dt.date == current.date()) &
                (df["heure"] == current.hour)
            ])
            occupee = 1 if nb_sessions > 0 else 0

            rows.append({
                "borne_id": borne_id,
                "heure": current.hour,
                "jour_semaine": current.weekday(),
                "est_weekend": int(current.weekday() >= 5),
                "mois": current.month,
                "occupee": occupee
            })
        current += timedelta(hours=1)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    os.makedirs("ml/data", exist_ok=True)

    print("Génération des sessions...")
    df_sessions = generer_sessions(nb_jours=90)
    df_sessions.to_csv("ml/data/sessions_historiques.csv", index=False)
    print(f"✅ {len(df_sessions)} sessions générées → ml/data/sessions_historiques.csv")

    print("Création du dataset ML...")
    df_ml = generer_dataset_disponibilite(df_sessions)
    df_ml.to_csv("ml/data/dataset_disponibilite.csv", index=False)
    print(f"✅ {len(df_ml)} lignes → ml/data/dataset_disponibilite.csv")
    print(f"\nRépartition : {df_ml['occupee'].value_counts().to_dict()}")
