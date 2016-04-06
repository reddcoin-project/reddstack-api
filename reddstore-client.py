import argparse
import sys
import json
import traceback
import os
import pybitcoin
import logging

# Hack around absolute paths
current_dir = os.path.abspath(os.path.dirname(__file__))
parent_dir = os.path.abspath(current_dir + "/../")

sys.path.insert(0, parent_dir)

import config
import client
#from blockstore_client import config, client, schemas, parsing, user
#from blockstore_client import storage, drivers
#from blockstore_client.utils import pretty_dump, print_result


log = config.log
log.setLevel(logging.DEBUG)
log.debug('Start')

from bottle import Bottle, run, template, get, post, request

app = Bottle()

conf = config.get_config()

if conf is None:
    log.error("Failed to load config")
    sys.exit(1)

blockstore_server = conf['server']
blockstore_port = conf['port']

log.debug('did somethign')
log.info('start session')

proxy = client.session(conf=conf, server_host=blockstore_server, server_port=blockstore_port)

#USER
@app.route('/')
def home():
	return "<p>Welcome to ReddID, Please see ___ for details</p>"

@app.route('/v1/version')
def version():
    return template('<p>System Version: {{version}}.</p>', version=format(config.VERSION))

@app.route('/v1/name/cost/<name>')
def name_cost(name):
	return template('<p>Cost of {{name}} is {{cost}}</p>', name=name, cost=client.get_name_cost(str(name + '.blog')))

#NAMESPACE
@app.route('/v1/namespace/cost/<namespace>')
def namespace_cost(namespace):
	return template('<p>Cost of {{name}} is {{cost}}</p>', name=namespace, cost=client.get_namespace_cost(str(namespace),proxy))

@app.route('/login') # or @route('/login')
def login():
    return '''
        <form action="/login" method="post">
            Username: <input name="username" type="text" />
            Password: <input name="password" type="password" />
            <input value="Login" type="submit" />
        </form>
    '''
@app.route('/login', method="POST") # or @route('/login', method='POST')
def do_login():
    username = request.forms.get('username')
    password = request.forms.get('password')
    if check_login(username, password):
        return "<p>Your login information was correct.</p>"
    else:
        return "<p>Login failed.</p>"


run(app, host='192.168.1.130', port=8080, debug=True)