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

from bottle import Bottle, run, template, get, post, request, response, static_file, url, debug

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

# Static Routes

@app.get('/<filename:re:.*\.js>')
def javascripts(filename):
    return static_file(filename, root='static/js')

@app.get('/<filename:re:.*\.css>')
def stylesheets(filename):
    return static_file(filename, root='static/css')

@app.get('/<filename:re:.*\.(jpg|png|gif|ico)>')
def images(filename):
    return static_file(filename, root='static/images')

@app.get('/<filename:re:.*\.(eot|ttf|woff|svg)>')
def fonts(filename):
    return static_file(filename, root='static/fonts')

#BASE
@app.route('/')
def home():
    my_dict = {}
    my_dict['version'] = format(config.VERSION)
    my_dict['network'] = format(config.NETWORK)

    return template("index.html", **my_dict)
    #return "<p>Welcome to ReddID, Please see ___ for details</p>"

@app.route('/v1/version', name='version')
def version():
    return template('<p>System Version: {{version}}.</p>', version=format(config.VERSION))

@app.route('/status')
def status():
    #return template('<p>System Status: {{status}}.</p>', status=json.dumps(client.getinfo(), sort_keys=True, indent=4, separators=(',',': ')))
    status = client.getinfo()
    return template('status.html', **status)
    #return template('status.html', status=json.dumps(client.getinfo(), sort_keys=True, indent=4, separators=(',',': ')))

@app.route('/api/status')
def status():
    status = client.getinfo()
    return status

##WEBSITE
@app.route('/what_is_reddid')
def status():
    return template('what_is_reddid')


#NAME
@app.get('/name/details')
def name_cost():
    return template('name_details')


#NAME Lookup
@app.route('/name/lookup', method='GET')
def name_lookup():
    resp = {}
    resp['name'] = ''
    return template('name_lookup', **resp)

@app.route('/name/lookup', method='POST')
def name_lookup():
    resp = {}
    username = request.forms.get('username')
    resp['name'] = username
    resp['status'] = client.get_name_blockchain_record(str(username + '.test'))
    print repr(resp)
    return template('name_lookup', **resp)

@app.route('/api/name/lookup/<name>')
def name_lookup(name):
    response.content_type = 'application/json'
    return client.get_name_blockchain_record(str(name + '.test'))
    #return template('<p>Lookup of {{name}} is {{status}}</p>', name=name, status=client.get_name_blockchain_record(str(name + '.test')))   

#NAME all_names
@app.route('/name/allnames', method='GET')
def name_allnames():
    resp = {}
    resp['name'] = ''
    return template('name_allnames', **resp)

@app.route('/name/allnames', method='POST')
def name_allnames():
    resp = {}
    namespace = request.forms.get('namespace')
    resp['namespace'] = namespace
    resp['status'] = client.get_names_in_namespace(str(namespace))
    print repr(resp)
    return template('name_allnames', **resp)

@app.route('/api/name/allnames/<namespace>')
def name_allnames(namespace):
    result = json.dumps(client.get_names_in_namespace(str(namespace),None,None))   
    #print result 
    resp = json.loads(result) 
    #print resp
    response.content_type = 'application/json'
    return json.dumps(resp['results'])
    #return template('{{result}}', **result) 

#NAME Price
@app.route('/name/price', method='GET')
def name_price():
    resp = {}
    resp['price']=0
    return template('name_price', **resp)

@app.route('/name/price', method='POST')
def name_price():
    resp = {}
    username = request.forms.get('username')
    resp['name'] = username
    resp['price'] = client.get_name_cost(str(username + '.test'))
    return template('name_price', **resp)

@app.route('/api/name/price/<name>')
def name_price(name):
    return template('<p>Price of {{name}} is {{price}}</p>', name=name, price=client.get_name_cost(str(name + '.test')))

#NAME
@app.get('/name/register')
def name_register():
    return template('name_register')

#NAME order
@app.route('/v1/name/preorder/<name>/<privaddress>/<address>')
def name_preorder(name, privaddress, address):
    return template('<p>Preorder of {{name}} is {{status}}</p>', name=name, status=client.preorder(str(name + '.test'), str(privaddress), str('tx_only=True')))

#NAMESPACE Price
@app.route('/namespace/price', method='GET')
def namespace_price():
    resp = {}
    resp['price']=0
    return template('namespace_price', **resp)

@app.route('/namespace/price', method='POST')
def namespace_price():
    resp = {}
    namespace = request.forms.get('namespace')
    resp['name'] = namespace
    resp['price'] = client.get_namespace_cost(str(namespace),proxy)
    return template('namespace_price', **resp)

@app.route('/api/namespace/price/<namespace>')
def namespace_price(namespace):
    return template('<p>Price of {{name}} is {{price}}</p>', name=namespace, price=client.get_namespace_cost(str(namespace),proxy))

#NAMESPACE Lookup
@app.route('/namespace/lookup', method='GET')
def namespace_lookup():
    resp = {}
    resp['name'] = ''
    return template('namespace_lookup', **resp)

@app.route('/namespace/lookup', method='POST')
def namespace_lookup():
    resp = {}
    namespace = request.forms.get('namespace')
    resp['name'] = namespace
    resp['status'] = client.get_namespace_blockchain_record(str(namespace))
    return template('namespace_lookup', **resp)

@app.route('/api/namespace/lookup/<name>')
def name_lookup(namespace):
    return template('<p>Lookup of {{name}} is {{status}}</p>', name=namespace, status=client.get_namespace_blockchain_record(str(namespace)))

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

debug(True)
run(app, host='0.0.0.0', port=8080, debug=False, reloader=True)