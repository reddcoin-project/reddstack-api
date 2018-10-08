#!venv/bin/python
from app import app, socketio

socketio.run(app, host='0.0.0.0', port=5000, debug=False, max_size=4096)
#app.run(host='0.0.0.0', port=8082, debug=True)
