from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
app.secret_key = 'development key'
socketio = SocketIO(app)

from app import views
