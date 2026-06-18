from app import db, bcrypt
from datetime import datetime


class User(db.Model):
    """
    Représente un utilisateur de la plateforme.
    Peut être un simple utilisateur ou un administrateur.
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    mot_de_passe_hash = db.Column(db.String(256), nullable=False)
    telephone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), nullable=False, default="user")
    # Valeurs possibles : "user" ou "admin"

    actif = db.Column(db.Boolean, default=True, nullable=False)
    date_inscription = db.Column(db.DateTime, default=datetime.utcnow)
    derniere_connexion = db.Column(db.DateTime, nullable=True)

    # ─── Relation : un user peut avoir plusieurs sessions de recharge ──
    sessions_recharge = db.relationship(
        "SessionRecharge",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    def __repr__(self):
        return f"<User {self.email} | role={self.role}>"

    # ─── Mot de passe (hashé avec bcrypt) ─────────────────────────────
    def set_password(self, mot_de_passe: str):
        """Hash et stocke le mot de passe."""
        self.mot_de_passe_hash = bcrypt.generate_password_hash(mot_de_passe).decode("utf-8")

    def check_password(self, mot_de_passe: str) -> bool:
        """Vérifie si le mot de passe fourni correspond au hash stocké."""
        return bcrypt.check_password_hash(self.mot_de_passe_hash, mot_de_passe)

    # ─── Helpers ──────────────────────────────────────────────────────
    def is_admin(self) -> bool:
        return self.role == "admin"

    def to_dict(self) -> dict:
        """Sérialise l'utilisateur (sans le mot de passe !)."""
        return {
            "id": self.id,
            "nom": self.nom,
            "prenom": self.prenom,
            "email": self.email,
            "telephone": self.telephone,
            "role": self.role,
            "actif": self.actif,
            "date_inscription": self.date_inscription.isoformat() if self.date_inscription else None,
            "derniere_connexion": self.derniere_connexion.isoformat() if self.derniere_connexion else None,
        }
