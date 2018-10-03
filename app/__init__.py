# activate eventlet
import eventlet
eventlet.monkey_patch(socket=True)

from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
app.secret_key = 'development key'
socketio = SocketIO(async_mode='eventlet', engineio_logger=False)
socketio.init_app(app)

from app import views
