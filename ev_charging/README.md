# ⚡ Plateforme de Gestion de Bornes de Recharge VE

Application web Flask pour la gestion de bornes de recharge pour véhicules électriques.

## Stack technique

| Composant | Technologie |
|---|---|
| Backend | Flask 3.0 + Python |
| Base de données | PostgreSQL + SQLAlchemy |
| Authentification | JWT (Flask-JWT-Extended) |
| Temps réel | Socket.IO (Flask-SocketIO) |
| Frontend | HTML/CSS + Chart.js |
| Migrations | Flask-Migrate (Alembic) |

## Structure du projet

```
ev_charging/
├── app/
│   ├── __init__.py          ← Factory Flask (create_app)
│   ├── models/
│   │   ├── user.py          ← Modèle User
│   │   ├── borne.py         ← Modèle Borne
│   │   └── session_recharge.py  ← Modèle SessionRecharge
│   ├── routes/
│   │   ├── auth.py          ← /api/auth/* (login, register, me)
│   │   ├── bornes.py        ← /api/bornes/* (CRUD)
│   │   ├── sessions.py      ← /api/sessions/* (démarrer, terminer)
│   │   ├── admin.py         ← /admin/* (stats, users, alertes)
│   │   └── dashboard.py     ← Pages HTML (templates)
│   ├── services/            ← Logique métier (Jour 2)
│   ├── utils/               ← Helpers partagés (Jour 2)
│   ├── templates/           ← HTML Jinja2 (Jour 2)
│   └── static/              ← CSS, JS, images (Jour 2)
├── migrations/              ← Généré par Flask-Migrate
├── tests/                   ← Tests pytest (Jour 3)
├── config.py                ← Configuration (dev/prod/test)
├── init_db.py               ← Script d'initialisation
├── run.py                   ← Point d'entrée (dev)
├── app.py                   ← Point d'entrée (prod/gunicorn)
├── requirements.txt
└── .env.example
```

## Installation rapide

```bash
# 1. Cloner et créer l'environnement
python -m venv venv
source venv/bin/activate       # Linux/Mac
venv\Scripts\activate          # Windows

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Configurer l'environnement
cp .env.example .env
# Éditer .env avec vos paramètres PostgreSQL

# 4. Créer la base de données PostgreSQL
psql -U postgres -c "CREATE DATABASE ev_charging_db;"

# 5. Initialiser les tables + données de test
python init_db.py

# 6. Lancer l'application
python run.py
```

## API Endpoints

### Authentification
| Méthode | URL | Description |
|---|---|---|
| POST | /api/auth/register | Créer un compte |
| POST | /api/auth/login | Se connecter |
| POST | /api/auth/refresh | Renouveler le token |
| GET | /api/auth/me | Profil connecté |

### Bornes
| Méthode | URL | Description |
|---|---|---|
| GET | /api/bornes/ | Lister les bornes |
| GET | /api/bornes/<id> | Détails d'une borne |
| POST | /api/bornes/ | Créer une borne (admin) |
| PUT | /api/bornes/<id> | Modifier une borne (admin) |
| PATCH | /api/bornes/<id>/statut | Changer le statut (admin) |
| DELETE | /api/bornes/<id> | Désactiver une borne (admin) |

### Sessions de recharge
| Méthode | URL | Description |
|---|---|---|
| POST | /api/sessions/demarrer | Démarrer une session |
| PATCH | /api/sessions/<id>/terminer | Terminer une session |
| GET | /api/sessions/mes-sessions | Mon historique |
| GET | /api/sessions/ | Toutes les sessions (admin) |

### Administration
| Méthode | URL | Description |
|---|---|---|
| GET | /admin/stats | Statistiques globales |
| GET | /admin/users | Liste des utilisateurs |
| PATCH | /admin/users/<id>/role | Changer le rôle |
| GET | /admin/alertes | Bornes en panne / maintenance |

## Compte admin par défaut (après init_db.py)

- Email : `admin@ev-charging.com`
- Mot de passe : `Admin1234!`
