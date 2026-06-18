# Point d'entrée principal - utilisé par gunicorn en production
# En développement, utilise run.py à la place

from app import create_app, socketio

application = create_app()
