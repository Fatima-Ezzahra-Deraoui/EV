"""
ml/prepare_dataset.py
Adapte station_data_dataverse.csv au format EVCharge.
Usage : python ml/prepare_dataset.py
"""

import os
import sys
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
log = logging.getLogger(__name__)

INPUT_PATH  = "ml/data/raw/station_data_dataverse.csv"
OUTPUT_PATH = "ml/data/dataset_disponibilite.csv"

WEEKDAY_MAP = {
    "Mon": 0, "Tues": 1, "Wed": 2,
    "Thurs": 3, "Fri": 4, "Sat": 5, "Sun": 6
}


def load_raw(path):
    if not os.path.exists(path):
        log.error("Fichier introuvable : %s", path)
        sys.exit(1)
    df = pd.read_csv(path)
    log.info("Dataset brut chargé : %d lignes × %d colonnes", *df.shape)
    return df


def transform(df):
    # ── 1. Supprimer les lignes avec valeurs critiques manquantes ─────────
    df = df.dropna(subset=["created", "startTime", "kwhTotal", "stationId"])
    log.info("Lignes après nettoyage : %d", len(df))

    # ── 2. Features temporelles ───────────────────────────────────────────
    df["heure"] = pd.to_numeric(df["startTime"], errors="coerce").fillna(0).astype(int)
    df["heure"] = df["heure"].clip(0, 23)  # sécuriser la plage 0-23

    # Jour de la semaine depuis la colonne 'weekday' (Mon, Tues, etc.)
    df["jour_semaine"] = df["weekday"].map(WEEKDAY_MAP)
    df = df.dropna(subset=["jour_semaine"])
    df["jour_semaine"] = df["jour_semaine"].astype(int)

    # Mois depuis 'created'
    df["created_dt"] = pd.to_datetime(df["created"], errors="coerce")
    df["mois"] = df["created_dt"].dt.month.fillna(6).astype(int)

    # Features dérivées
    df["est_weekend"]      = (df["jour_semaine"] >= 5).astype(int)
    df["est_heure_pointe"] = df["heure"].apply(
        lambda h: 1 if (7 <= h <= 9) or (17 <= h <= 20) else 0
    )

    # ── 3. Borne ID (numérique) ───────────────────────────────────────────
    borne_map = {v: i + 1 for i, v in enumerate(df["stationId"].unique())}
    df["borne_id"] = df["stationId"].map(borne_map)
    log.info("Bornes uniques : %d", len(borne_map))

    # ── 4. Énergie ────────────────────────────────────────────────────────
    df["energie_kwh"] = pd.to_numeric(df["kwhTotal"], errors="coerce").fillna(0)

    # ── 5. Target : occupee = 1 pour chaque session réelle ───────────────
    df["occupee"] = 1

    df_occupees = df[["borne_id", "heure", "jour_semaine", "est_weekend",
                       "est_heure_pointe", "mois", "energie_kwh", "occupee"]].copy()

    # ── 6. Générer les créneaux libres ────────────────────────────────────
    log.info("Génération des créneaux libres...")
    df_libre = _generate_free_slots(df_occupees)
    log.info("Créneaux libres générés : %d", len(df_libre))

    # ── 7. Assembler et mélanger ──────────────────────────────────────────
    df_final = pd.concat([df_occupees, df_libre], ignore_index=True)
    df_final = df_final.sample(frac=1, random_state=42).reset_index(drop=True)

    log.info("Dataset final : %d lignes | occupées: %d | libres: %d",
             len(df_final),
             df_final["occupee"].sum(),
             (df_final["occupee"] == 0).sum())
    return df_final


def _generate_free_slots(df_occ):
    """Crée les enregistrements 'borne libre' pour équilibrer le dataset."""
    records = []
    bornes = df_occ["borne_id"].unique()

    for borne_id in bornes:
        sessions = df_occ[df_occ["borne_id"] == borne_id]
        for jour in range(7):
            for mois in range(1, 13):
                heures_occ = sessions[
                    (sessions["jour_semaine"] == jour) &
                    (sessions["mois"] == mois)
                ]["heure"].values

                for heure in range(24):
                    if heure not in heures_occ:
                        records.append({
                            "borne_id":         borne_id,
                            "heure":            heure,
                            "jour_semaine":     jour,
                            "est_weekend":      1 if jour >= 5 else 0,
                            "est_heure_pointe": 1 if (7 <= heure <= 9) or (17 <= heure <= 20) else 0,
                            "mois":             mois,
                            "energie_kwh":      0.0,
                            "occupee":          0,
                        })
    return pd.DataFrame(records)


def save(df, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cols = ["borne_id", "heure", "jour_semaine", "est_weekend",
            "est_heure_pointe", "mois", "energie_kwh", "occupee"]
    df[cols].to_csv(path, index=False)
    log.info("Dataset sauvegardé → %s (%d lignes)", path, len(df))


def main():
    log.info("══ EVCharge — Préparation du dataset réel ══")
    df_raw   = load_raw(INPUT_PATH)
    df_final = transform(df_raw)
    save(df_final, OUTPUT_PATH)
    log.info("══ Terminé — Lance maintenant : python ml/train_model.py ══")


if __name__ == "__main__":
    main()