from app import db
from datetime import datetime


class SessionRecharge(db.Model):
    """
    Représente une session de recharge : quand un utilisateur
    branche son véhicule sur une borne.
    Contient l'énergie consommée et le coût facturé.
    """
    __tablename__ = "sessions_recharge"

    id = db.Column(db.Integer, primary_key=True)

    # ─── Relations (clés étrangères) ──────────────────────────────────
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    borne_id = db.Column(db.Integer, db.ForeignKey("bornes.id"), nullable=False, index=True)

    user = db.relationship("User", back_populates="sessions_recharge")
    borne = db.relationship("Borne", back_populates="sessions_recharge")

    # ─── Temps ────────────────────────────────────────────────────────
    debut = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fin = db.Column(db.DateTime, nullable=True)
    # fin=None signifie que la session est en cours

    # ─── Énergie et facturation ───────────────────────────────────────
    energie_kwh = db.Column(db.Float, nullable=True, default=0.0)
    # Énergie consommée en kWh (calculée à la fin de la session)

    cout_total = db.Column(db.Float, nullable=True, default=0.0)
    # Coût en euros (calculé à la fin de la session)

    prix_kwh_applique = db.Column(db.Float, nullable=True)
    # Prix au kWh au moment de la session (peut changer)

    # ─── Statut de la session ─────────────────────────────────────────
    statut = db.Column(db.String(20), nullable=False, default="en_cours")
    # Valeurs : "en_cours", "terminee", "annulee", "erreur"

    # ─── Accès ────────────────────────────────────────────────────────
    methode_acces = db.Column(db.String(20), nullable=True, default="app")
    # Valeurs : "app", "qr_code", "rfid", "admin"

    def __repr__(self):
        return f"<Session #{self.id} | user={self.user_id} | borne={self.borne_id} | statut={self.statut}>"

    # ─── Calculs automatiques ─────────────────────────────────────────
    def duree_minutes(self) -> float | None:
        """Retourne la durée de la session en minutes."""
        if self.debut and self.fin:
            delta = self.fin - self.debut
            return round(delta.total_seconds() / 60, 2)
        return None

    def calculer_cout(self) -> float:
        """
        Calcule le coût total à partir de l'énergie consommée
        et du prix appliqué. Doit être appelé à la fin de la session.
        """
        if self.energie_kwh and self.prix_kwh_applique:
            self.cout_total = round(self.energie_kwh * self.prix_kwh_applique, 2)
            return self.cout_total
        return 0.0

    def terminer(self, energie_kwh: float):
        """
        Termine la session : enregistre l'énergie, calcule le coût,
        met à jour le statut et l'heure de fin.
        """
        self.fin = datetime.utcnow()
        self.energie_kwh = energie_kwh
        self.prix_kwh_applique = self.borne.prix_kwh if self.borne else 0.0
        self.calculer_cout()
        self.statut = "terminee"

        # Libérer la borne
        if self.borne:
            self.borne.statut = "disponible"

    def to_dict(self) -> dict:
        """Sérialise la session pour l'API ou le dashboard."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "borne_id": self.borne_id,
            "borne_nom": self.borne.nom if self.borne else None,
            "debut": self.debut.isoformat() if self.debut else None,
            "fin": self.fin.isoformat() if self.fin else None,
            "duree_minutes": self.duree_minutes(),
            "energie_kwh": self.energie_kwh,
            "cout_total": self.cout_total,
            "prix_kwh_applique": self.prix_kwh_applique,
            "statut": self.statut,
            "methode_acces": self.methode_acces,
        }
