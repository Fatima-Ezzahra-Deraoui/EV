import pandas as pd
import sys, os, random
from datetime import datetime

sys.path.insert(0, os.path.abspath("."))

from app import create_app, db
from app.models.borne import Borne
from app.models.session_recharge import SessionRecharge
from app.models.user import User

app = create_app()
random.seed(42)

with app.app_context():

    # ─── 1. Supprimer les anciennes sessions ──────────────────────────
    SessionRecharge.query.delete()
    db.session.commit()
    print("🗑️  Anciennes sessions supprimées.")

    # ─── 2. Récupérer les vrais user_ids en base ──────────────────────
    users_ids = [u.id for u in User.query.all()]
    if not users_ids:
        print("❌ Aucun utilisateur en base. Lance d'abord : python init_db.py")
        exit()
    print(f"👥 {len(users_ids)} utilisateur(s) trouvé(s) en base.")

    # ─── 3. Lire le dataset adapté ────────────────────────────────────
    csv_path = "ml/data/raw/sessions_maroc_adapte.csv"
    if not os.path.exists(csv_path):
        print(f"❌ Fichier introuvable : {csv_path}")
        print("   Lance d'abord : python ml/data/adapt_dataset.py")
        exit()

    df = pd.read_csv(csv_path)
    df_sample = df.sample(n=min(500, len(df)), random_state=42)
    print(f"📂 {len(df_sample)} sessions sélectionnées depuis le dataset.")

    # ─── 4. Importer les sessions ─────────────────────────────────────
    count      = 0
    skipped    = 0

    for _, row in df_sample.iterrows():
        # Chercher la borne correspondante
        borne = Borne.query.filter_by(nom=f"Borne {row['borne_id']}").first()
        if not borne:
            skipped += 1
            continue

        # Parser les dates
        try:
            debut = datetime.strptime(str(row["debut"]), "%Y-%m-%d %H:%M:%S")
            fin   = datetime.strptime(str(row["fin"]),   "%Y-%m-%d %H:%M:%S")
        except Exception:
            skipped += 1
            continue

        # Calculs financiers
        kwh        = round(float(row["kwh_total"]), 3)
        prix_kwh   = round(float(row["prix_kwh_mad"]), 2)
        cout_total = round(kwh * prix_kwh, 2)

        session = SessionRecharge(
            borne_id          = borne.id,
            user_id           = random.choice(users_ids),
            debut             = debut,
            fin               = fin,
            energie_kwh       = kwh,
            prix_kwh_applique = prix_kwh,
            cout_total        = cout_total,
            statut            = "terminee",
            methode_acces     = random.choice(["app_mobile", "carte_rfid", "qr_code"]),
        )
        db.session.add(session)
        count += 1

    db.session.commit()

    # ─── 5. Résumé ────────────────────────────────────────────────────
    total_revenu = db.session.execute(
        db.text("SELECT ROUND(SUM(cout_total)::numeric, 2) FROM sessions_recharge")
    ).scalar()
    total_kwh = db.session.execute(
        db.text("SELECT ROUND(SUM(energie_kwh)::numeric, 2) FROM sessions_recharge")
    ).scalar()

    print(f"✅ {count} sessions importées  |  ⏭️  {skipped} ignorées")
    print(f"💰 Revenu total  : {total_revenu} MAD")
    print(f"⚡ Énergie totale : {total_kwh} kWh")
    print(f"📊 Moyenne/session : {round(float(total_revenu)/count, 2)} MAD")