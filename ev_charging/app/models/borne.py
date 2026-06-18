from app import db
from datetime import datetime


class Borne(db.Model):
    """
    Représente une borne de recharge pour véhicule électrique.
    Contient la localisation, le statut, et les caractéristiques techniques.
    """
    __tablename__ = "bornes"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    # Ex: "Borne A1 - Parking Centre Commercial"

    # ─── Localisation ─────────────────────────────────────────────────
    adresse = db.Column(db.String(255), nullable=True)
    ville = db.Column(db.String(100), nullable=True)
    code_postal = db.Column(db.String(10), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    # ─── Caractéristiques techniques ──────────────────────────────────
    puissance_kw = db.Column(db.Float, nullable=False, default=22.0)
    # Puissance en kilowatts (ex: 7.4, 22, 50, 150, 350)

    type_connecteur = db.Column(db.String(50), nullable=False, default="Type 2")
    # Valeurs possibles : "Type 1", "Type 2", "CHAdeMO", "CCS Combo", "Tesla"

    prix_kwh = db.Column(db.Float, nullable=False, default=0.30)
    # Prix en euros par kWh

    # ─── Statut ───────────────────────────────────────────────────────
    statut = db.Column(db.String(30), nullable=False, default="disponible")
    # Valeurs possibles : "disponible", "occupee", "en_panne", "maintenance"

    qr_code = db.Column(db.String(100), unique=True, nullable=True)
    # Identifiant unique pour accès QR ou RFID

    # ─── Métadonnées ──────────────────────────────────────────────────
    date_installation = db.Column(db.DateTime, default=datetime.utcnow)
    derniere_maintenance = db.Column(db.DateTime, nullable=True)
    date_mise_a_jour = db.Column(db.DateTime, onupdate=datetime.utcnow)

    actif = db.Column(db.Boolean, default=True, nullable=False)

    # ─── Relation : une borne peut avoir plusieurs sessions de recharge ─
    sessions_recharge = db.relationship(
        "SessionRecharge",
        back_populates="borne",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    def __repr__(self):
        return f"<Borne {self.nom} | statut={self.statut}>"

    # ─── Helpers ──────────────────────────────────────────────────────
    def est_disponible(self) -> bool:
        return self.statut == "disponible" and self.actif

    def est_en_panne(self) -> bool:
        return self.statut == "en_panne"

    def to_dict(self) -> dict:
        """Sérialise la borne pour l'API ou le dashboard."""
        return {
            "id": self.id,
            "nom": self.nom,
            "adresse": self.adresse,
            "ville": self.ville,
            "code_postal": self.code_postal,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "puissance_kw": self.puissance_kw,
            "type_connecteur": self.type_connecteur,
            "prix_kwh": self.prix_kwh,
            "statut": self.statut,
            "qr_code": self.qr_code,
            "date_installation": self.date_installation.isoformat() if self.date_installation else None,
            "derniere_maintenance": self.derniere_maintenance.isoformat() if self.derniere_maintenance else None,
            "actif": self.actif,
        }
