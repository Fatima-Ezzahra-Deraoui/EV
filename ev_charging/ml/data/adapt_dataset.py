import pandas as pd
import numpy as np
import random

random.seed(42)
np.random.seed(42)

df = pd.read_csv("ml/data/raw/station_data_dataverse.csv")

# ─── 1. Renommer les colonnes ─────────────────────────────────────────
df = df.rename(columns={
    "sessionId":      "session_id",
    "kwhTotal":       "kwh_total",
    "dollars":        "prix_dollars",   # sera converti en MAD
    "created":        "debut",
    "ended":          "fin",
    "startTime":      "heure_debut",
    "endTime":        "heure_fin",
    "chargeTimeHrs":  "duree_heures",
    "weekday":        "jour_semaine",
    "platform":       "plateforme",
    "distance":       "distance_km",
    "userId":         "utilisateur_id",
    "stationId":      "borne_id",
    "locationId":     "site_id",
    "managerVehicle": "vehicule_gestionnaire",
    "facilityType":   "type_site",
    "reportedZip":    "code_postal_us",    # sera remplacé
})

# ─── 2. Convertir dollars → MAD (1 USD ≈ 10.1 MAD) ───────────────────
# ─── Ajouter prix en MAD ──────────────────────────────────────────────
df["prix_kwh_mad"] = df["kwh_total"].apply(
    lambda x: round(random.uniform(1.5, 3.5), 2)
)

# Prix total de la session en MAD = kwh * prix_kwh
df["prix_total_mad"] = (df["kwh_total"] * df["prix_kwh_mad"]).round(2)

# ─── Supprimer SEULEMENT la colonne dollars (inutile) ─────────────────
df = df.drop(columns=["prix_dollars"])

# ✅ Garder kwh_total — utilisé par le ML et les sessions

# ─── 3. Remplacer facilityType numérique → labels français ───────────
facility_map = {
    1: "Université / Campus",
    2: "Bureau / Entreprise",
    3: "Parking public",
    4: "Centre commercial",
    5: "Hôpital",
}
df["type_site"] = df["type_site"].map(facility_map).fillna("Autre")

# ─── 4. Remplacer les zip codes US → villes marocaines ───────────────
villes_maroc = [
    {"ville": "Casablanca",  "code_postal": "20000", "lat": 33.5731, "lon": -7.5898},
    {"ville": "Rabat",       "code_postal": "10000", "lat": 34.0209, "lon": -6.8416},
    {"ville": "Marrakech",   "code_postal": "40000", "lat": 31.6295, "lon": -7.9811},
    {"ville": "Fès",         "code_postal": "30000", "lat": 34.0331, "lon": -5.0003},
    {"ville": "Tanger",      "code_postal": "90000", "lat": 35.7595, "lon": -5.8340},
    {"ville": "Agadir",      "code_postal": "80000", "lat": 30.4278, "lon": -9.5981},
    {"ville": "Meknès",      "code_postal": "50000", "lat": 33.8935, "lon": -5.5473},
    {"ville": "Oujda",       "code_postal": "60000", "lat": 34.6867, "lon": -1.9114},
]

# Assigner une ville marocaine fixe à chaque borne_id unique
bornes_uniques = df["borne_id"].unique()
borne_ville_map = {
    borne_id: random.choice(villes_maroc)
    for borne_id in bornes_uniques
}

df["ville"]       = df["borne_id"].map(lambda b: borne_ville_map[b]["ville"])
df["code_postal"] = df["borne_id"].map(lambda b: borne_ville_map[b]["code_postal"])
df["latitude"]    = df["borne_id"].map(lambda b: borne_ville_map[b]["lat"] + np.random.uniform(-0.03, 0.03))
df["longitude"]   = df["borne_id"].map(lambda b: borne_ville_map[b]["lon"] + np.random.uniform(-0.03, 0.03))
df = df.drop(columns=["code_postal_us"])

# ─── 5. Traduire les jours en français ───────────────────────────────
jours_map = {
    "Mon": "Lundi", "Tue": "Mardi",  "Wed": "Mercredi",
    "Thu": "Jeudi", "Fri": "Vendredi", "Sat": "Samedi", "Sun": "Dimanche"
}
df["jour_semaine"] = df["jour_semaine"].map(jours_map).fillna(df["jour_semaine"])

# ─── 6. Supprimer colonnes inutiles ──────────────────────────────────
df = df.drop(columns=["Mon", "Tues", "Wed", "Thurs", "Fri", "Sat", "Sun", "vehicule_gestionnaire"])

# ─── 7. Sauvegarder ──────────────────────────────────────────────────
output_path = "ml/data/raw/sessions_maroc_adapte.csv"
df.to_csv(output_path, index=False)

print(f"✅ Dataset adapté sauvegardé : {output_path}")
print(f"📊 {len(df)} sessions | {df['borne_id'].nunique()} bornes | {df['ville'].nunique()} villes")
print(f"\nColonnes finales :\n{list(df.columns)}")
print(f"\nAperçu :\n{df.head(3).to_string()}")