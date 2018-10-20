#!venv/bin/python
from reddstackapi import app, socketio, views, config

def run_reddstackapid():
	"""
	Run the Reddstack API server
	"""
	print ("\nStarting API Server v{0}\n".format(config.VERSION))
	socketio.run(app, host='0.0.0.0', port=5000, debug=False, max_size=4096)

