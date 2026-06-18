from app import create_app, socketio

app = create_app()

if __name__ == "__main__":
    # Lance le serveur avec Socket.IO (pas flask run classique)
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
