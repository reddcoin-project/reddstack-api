import json
import os
import logging
from logging.handlers import RotatingFileHandler
from pymongo import MongoClient
from packaging import version
from bson.json_util import loads, dumps
import requests
from flask import g, render_template, request, Response, redirect, url_for, session, flash, _app_ctx_stack
from werkzeug import check_password_hash, generate_password_hash
from time import sleep
from concurrent.futures import ThreadPoolExecutor
from reddstackapi import app, socketio
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect

from blockstore_client import config, client, schemas, parsing, user, storage, drivers

from reddstackapi import config as rsaconfig

connected_users = []
max_online = 0
connUid = 0

log = config.log
#Remove all logging handlers and pipe everything to file

for handler in log.handlers[:]:
    log.removeHandler(handler)


DEBUG = True
logPath = "../logs"
if not os.path.isdir(logPath):
    os.makedirs(logPath)
logFileHandler = RotatingFileHandler(logPath + "/reddstack-api.log", maxBytes=50000000, backupCount=99)
log_format = ('[%(asctime)s] [%(levelname)s] [%(module)s:%(lineno)d] (' + str(os.getpid()) + ') %(message)s' if DEBUG else '%(message)s')
logfile_formatter = logging.Formatter(log_format)
logFileHandler.setFormatter(logfile_formatter)
log.addHandler(logFileHandler)


executor = ThreadPoolExecutor(2)

# Database Connections
clientDB = MongoClient('localhost', 27017)
db = clientDB['socialAccounts']
# collections

networkColls = db.networks

#conf = config.get_config()

#if conf is None:
#    print("Failed to load config")
#    sys.exit(1)

#reddstack_server = conf['server']
#reddstack_port = conf['port']
#reddstack_storage = conf['storage_drivers']

#log = config.log
from ConfigParser import SafeConfigParser
conf = config.get_config()
conf["network"] = "mainnet"

proxy = client.session(conf, conf['server'], conf['port'])
#client = client.session(conf=conf, server_host=reddstack_server, server_port=reddstack_port, storage_drivers=reddstack_storage)
DEFAULT_NAMESPACE = 'tester'

# borrowed from Blockstore
# these never change, so it's fine to duplicate them here
# op-return formats
LENGTHS = {
    'magic_bytes': 2,
    'opcode': 1,
    'preorder_name_hash': 20,
    'consensus_hash': 16,
    'namelen': 1,
    'name_min': 1,
    'name_max': 34,
    'name_hash': 16,
    'update_hash': 20,
    'data_hash': 20,
    'blockchain_id_name': 37,
    'blockchain_id_namespace_life': 4,
    'blockchain_id_namespace_coeff': 1,
    'blockchain_id_namespace_base': 1,
    'blockchain_id_namespace_buckets': 8,
    'blockchain_id_namespace_discounts': 1,
    'blockchain_id_namespace_version': 2,
    'blockchain_id_namespace_id': 19,
    'announce': 20,
    'max_op_length': 40
}
log.info("\n\n****************************\n Starting API server v{0}\n****************************\n\n".format(rsaconfig.VERSION))
log.info("Server: %s, Port: %s" % ( conf['server'], conf['port'] ))
log.info(conf)

def checkLength (data, operation):
    if len(data) > LENGTHS[operation]:
        return False
    return True


def get_blockchain_id(name):
    name = name + '.' + DEFAULT_NAMESPACE
    data = json.dumps(client.get_name_blockchain_record(str(name)))
    data = json.loads(data)
    if 'name' in data:
        return (data['name'])
    return None

def handle_exception(e):
    log.debug("Exception Occurred")
    log.debug(e)

@app.route('/api/connected')
def api_connected_clients():
    data = {
    'online': len(connected_users),
    'max_online': max_online
    }
    resp = Response(response=json.dumps(data),
    status=200, \
    mimetype="application/json")
    return (resp)


@app.route('/api/consensus')
def api_consensus():

    data = client.getinfo()
    height = data['last_block']
    return redirect(url_for('api_consensus_height', height=height))


@app.route('/api/consensus/<height>')
def api_consensus_height(height):
    data = {}
    data['height'] = height
    data['consensus_hash'] = client.get_consensus_at(height)
    resp = Response(response=json.dumps(data),
    status=200, \
    mimetype="application/json")
    return (resp)


@app.route('/api/name/lookup/<name>')
def api_name_lookup(name):

    data = {}

    # Sanity checks
    if checkLength(name,'blockchain_id_name'):

        name = name + '.' + DEFAULT_NAMESPACE

        data['blockchain_record'] = client.get_name_blockchain_record(str(name))
        try:
            data_id = data['blockchain_record']['value_hash']
            data['data_record'] = json.loads(client.get_immutable(str(name), data_id)['data'])
        except Exception as e:
            handle_exception(e)
            data['error'] = 'Cannot connect to server'
    else:
        data['error'] = 'input data not valid'

    resp = Response(response=json.dumps(data),
    status=200, \
    mimetype="application/json")
    return (resp)


#NAME All names
@app.route('/api/name/allnames/<namespace>')
def api_name_allnames(namespace):
    data = {}
    # Sanity checks
    if checkLength(namespace, 'blockchain_id_namespace_id'):

        try:
            data = client.get_names_in_namespace(str(namespace),None,None)
        except Exception as e:
            handle_exception(e)
            data['error'] = 'Cannot connect to server'
    else:
        data['error'] = 'input data not valid'

    resp = Response(response=json.dumps(data),
    status=200, \
    mimetype="application/json")
    return (resp)

#NAME Price
@app.route('/api/name/price/<name>')
def api_name_price(name):
    data = {}
    # Sanity checks
    if checkLength(name,'blockchain_id_name'):

        name = name + '.' + DEFAULT_NAMESPACE

        try:
            data = client.get_name_cost(str(name))
        except Exception as e:
            handle_exception(e)
            data['error'] = 'Cannot connect to server'
    else:
        data['error'] = 'input data not valid'

    resp = Response(response=json.dumps(data),
    status=200, \
    mimetype="application/json")
    return (resp)


#NAMESPACE
@app.route('/api/namespace/lookup/<namespace>')
def api_namespace_lookup(namespace):
    data = {}
    # Sanity checks
    if checkLength(namespace,'blockchain_id_namespace_id'):
        try:
            data = client.get_namespace_blockchain_record(str(namespace))
        except Exception as e:
            handle_exception(e)
            data['error'] = 'Cannot connect to server'
    else:
        data['error'] = 'input data not valid'

    resp = Response(response=json.dumps(data),
    status=200, \
    mimetype="application/json")
    return (resp)


#NAMESPACE price
@app.route('/api/namespace/price/<namespace>')
def api_namespace_price(namespace):
    data = {}
    # Sanity checks
    if checkLength(namespace,'blockchain_id_namespace_id'):
        try:
            data = client.get_namespace_cost(str(namespace))
        except Exception as e:
            handle_exception(e)
            data['error'] = 'Cannot connect to server'
    else:
        data['error'] = 'input data not valid'

    resp = Response(response=json.dumps(data),
    status=200, \
    mimetype="application/json")
    return (resp)


thread = None
def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        socketio.sleep(10)
        count += 1
        socketio.emit('my_response',
                      {'data': 'Server generated event', 'count': count},
                      namespace='/test')

@socketio.on('monitor', namespace='/test')
def test_message(message):
    session['monitor'] = session.get('monitor', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']})

@socketio.on('my_event', namespace='/test')
def test_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']})


@socketio.on('my_broadcast_event', namespace='/test')
def test_broadcast_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']},
         broadcast=True)


@socketio.on('join', namespace='/test')
def join(message):
    join_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})


@socketio.on('leave', namespace='/test')
def leave(message):
    leave_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})


@socketio.on('close_room', namespace='/test')
def close(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response', {'data': 'Room ' + message['room'] + ' is closing.',
                         'count': session['receive_count']},
         room=message['room'])
    close_room(message['room'])


@socketio.on('my_room_event', namespace='/test')
def send_room_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']},
         room=message['room'])


@socketio.on('disconnect_request', namespace='/test')
def disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()


@socketio.on('my_ping', namespace='/test')
def ping_pong():
    emit('my_pong')


@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    if thread is None:
        thread = socketio.start_background_task(target=background_thread)
    emit('my_response', {'data': 'Connected', 'count': 0})


@socketio.on('disconnect', namespace='/test')
def test_disconnect(sid):
    log.info('Client disconnected', sid)

thread_blockheight = None
def background_thread_currentblock():
    """Example of how to send server generated events to clients."""
    currentheight = 0
    height = 0
    reply = {}
    payload = {}
    while True:
        data = client.getinfo() #json.dumps(client.getinfo())
        log.info(data)
        if 'bitcoind_blocks' in data:
            height = data['bitcoind_blocks']
        else:
            height = 'Indexing'

        payload['height'] = height

        reply['type'] = 'getinfo'
        data['api_version'] = rsaconfig.VERSION
        reply['payload'] = data
        reply['connections'] = {
            'online': len(connected_users),
            'max_online': max_online
        }
        #only send if we need to
        if height > currentheight:
            log.info('Sending %s' % (reply))
            socketio.emit('response', reply, 
                      namespace='/account')
            currentheight = height
        
        socketio.sleep(20)
# Connect to server
@socketio.on('connect', namespace='/account')
def acc_connect():
    global thread_blockheight
    global connUid
    global max_online

    if thread_blockheight is None:
        thread_blockheight = 'pending'
        thread_blockheight = socketio.start_background_task(target=background_thread_currentblock)

    connected_users.append({
        'id': connUid,
        'sid': str(request.sid)
        })
    if len(connected_users) > max_online:
        max_online = len(connected_users)

    log.info('Client connected %s, %s users connected, %s peak connections' % (str(request.sid), len(connected_users), str(max_online)))
    connUid += 1
    emit('response', {'data': 'Connected', 'count': len(connected_users)})

# Disconnect from server
@socketio.on('disconnect_request', namespace='/account')
def disconnect_request():
    emit('my_response',
         {'data': 'Disconnected!'})
    disconnect()

# Ping message for timing
@socketio.on('my_ping', namespace='/account')
def ping_pong():
    emit('my_pong')

@socketio.on('disconnect', namespace='/account')
def acc_disconnect():
    client = (item for item in connected_users if item['sid'] == request.sid).next()

    if client:
        client_id = client['id']
        connected_users.remove(client)

    log.info('Client disconnected %s, %s users connected, %s peak connections' % (str(request.sid), len(connected_users), str(max_online)))

@socketio.on('register_', namespace='/account')
def acc_register_(message):
    error = None
    success = None
    namespace = 'test'

    log.info('Register User: %s' % str(message))

    if not message['username']:
        error = 'You have to enter a blockchain id'
    elif get_blockchain_id(message['username']) is not None:
        error = 'The blockchain id is already taken'
    elif not message['email'] or \
            '@' not in message['email']:
        error = 'You have to enter a valid email address'
    elif not message['pwd1']:
        error = 'You have to enter a password'
    elif message['pwd1'] != message['pwd2']:
        error = 'The two passwords do not match'
    elif get_user_id(message['username']) is not None:
        error = 'The username is already taken'

    else:
        db = get_db()
        db.execute('''insert into user (
          username, email, pw_hash) values (?, ?, ?)''',
          [message['username'], message['email'],
           generate_password_hash(message['pwd1'])])


        username = message['username'] + '.' + namespace
        log.info(username)

        preorder_result = json.dumps(client.preorder(username, config.PRIV_KEY))
        preorder_result = json.loads(preorder_result)
        preorder_result['operation'] = 'preorder'

        log.info('Blockchain result: %s' % str(preorder_result))

        if 'success' in preorder_result:
            db.commit()
            success = 'You successfully pre-ordered blockchain userid: ' + message['username']
            emit('preorder_tx', preorder_result)

            ## send a register request
            register_result = json.dumps(client.register(username, config.PRIV_KEY, preorder_result['register_address']))
            register_result = json.loads(register_result)
            register_result['operation'] = 'register'
            log.info ('Register Response = %s' % str(register_result))

            if 'success' in register_result:
                emit('register_tx', register_result)

        elif 'error' in preorder_result:
            ## need to do some conditional retries here eg indexing blockchain
            error = preorder_result['error']




    emit('my_response', {'data': 'Register a user', 'error': error, 'success': success})

@socketio.on('get_tx', namespace='/account')
def get_tx_hash(msg):
    log.info(msg)
    result = json.dumps(client.gettxinfo(msg['tx_hash']))
    result = json.loads(result)
    result['op'] = msg['op']
    result['tx_hash'] = msg['tx_hash']
    log.info(result)
    emit('send_tx', result)

@socketio.on('getcost', namespace='/account')
def get_cost(msg):
    log.info(msg)
    name = msg['data']
    name = name + '.' + DEFAULT_NAMESPACE
    reply = {}
    result = json.dumps(client.get_name_cost(name))
    result = json.loads(result)
    #result = json.dumps(client.gettxinfo(msg['tx_hash']))
    available = client.get_name_record(name)
    log.info(available)

    result['uid'] = msg['data']
    if 'error' in client.get_name_blockchain_record(name):
        result['status'] = 'not found'
    else:
        result['status'] = 'found'

    log.info(result)
    reply['type'] = 'cost'
    reply['payload'] = result
    emit('response',reply)
    return reply
    #emit('receivecost', result)

@socketio.on('lookup', namespace='/account')
def lookup(msg):
    log.info(msg)
    name = msg['user']
    name = name + '.' + DEFAULT_NAMESPACE
    reply = {}
    result = {}
    try:
        result = client.get_name_blockchain_record(name)
    except Exception as e:
        handle_exception(e)
        result['error'] = 'Cannot connect to server'

    # print result
    reply['type'] = 'lookup'
    reply['payload'] = json.dumps(result)
    emit('response',reply)

@socketio.on('getimmutable', namespace='/account')
def getimmutable(msg):
    log.info(msg)
    name = msg['uid']
    name = name + '.' + DEFAULT_NAMESPACE
    value_hash = msg['value_hash']
    reply = {}      
    result = {}
    try:
        result = client.get_immutable(name, value_hash)
    except Exception as e:
        handle_exception(e)
        result['error'] = 'Cannot connect to server'

    # print result
    reply['type'] = 'getimmutable'
    reply['payload'] = json.dumps(result)
    emit('response',reply)

@socketio.on('preorder', namespace='/account')
def acc_preorder(msg):
    log.info(msg)
    error = None
    success = None
    reply = {}
    name = msg['uid']
    name = name + '.' + DEFAULT_NAMESPACE
    owningAddr = msg['owningAddr']
    publicKey = msg['publicKey']

    if get_blockchain_id(name) is not None:
        error = 'The blockchain id is already taken'

    # preorder UID, paying privkey, [owning addr]

    #preorder_result = json.dumps(client.preorder(username, config.PRIV_KEY, owningAddr))
    preorder_result = json.dumps(client.preorder_unsigned(name, publicKey, owningAddr))
    preorder_result = json.loads(preorder_result)
    #preorder_result['operation'] = 'preorder'
    reply['type'] = 'preorder'
    reply['payload'] = preorder_result
    log.info('Blockchain result: %s' % str(reply))

    if not 'error' in preorder_result:
        log.info("Success in preorder ")
        #emit('preorder', preorder_result)
        emit('response', reply)

    else:
        log.info("Error in preorder " + preorder_result['error'])
        #emit('preorder', {'error': preorder_result['error']})
        emit('response', reply)
    #    return

    
@socketio.on('register', namespace='/account')
def acc_register(msg):
    log.info(msg)
    error = None
    success = None
    reply ={}
    name = msg['uid']
    name = name + '.' + DEFAULT_NAMESPACE
    owningAddr = msg['owningAddr']
    publicKey = msg['publicKey']

    ## send a register request
    #register_result = json.dumps(client.register(username, payingAddr, owningAddr))
    register_result = json.dumps(client.register_unsigned(name, publicKey, owningAddr))
    register_result = json.loads(register_result)
    #register_result['type'] = 'register'
    reply['type'] = 'register'
    reply['payload'] = register_result
    log.info ('Blockchain result: %s' % str(reply))

    if not 'error' in register_result:
        log.info ("Success in register ")
        #emit('register', register_result)
        emit('response', reply)

    else:
        log.info ("Error in register " + register_result['error'])
        #emit('register', {'error': register_result['error']})
        emit('response', reply)

@socketio.on('update', namespace='/account')
def acc_update(msg):
    log.info( "Updating: " + str(msg))
    error = None
    success = None
    reply ={}
    name = msg['user']
    name = name + '.' + DEFAULT_NAMESPACE
    payload = json.dumps(msg['profile'])
    publicKey = msg['publicKey']

    if 'tx_hash' in msg:
        # sending the confirmation command
        tx_hash = msg['tx_hash']
        log.info ("Sending Update")
        update_result = client.update(name, payload, publicKey, tx_hash)
    else:
        # generating out update transaction only. Will call the above again soon
        log.info ("Getting Transaction")
        update_result = client.update_unsigned(name, payload, publicKey)

    #update_result = json.loads(update_result)

    reply['type'] = 'update'
    reply['payload'] = update_result
    log.info ('Blockchain result: %s' % str(reply))

    if not 'error' in update_result:
        log.info ("Success in update ")
        #emit('register', register_result)
        emit('response', reply)

    else:
        log.info ("Error in update " + update_result['error'])
        #emit('register', {'error': register_result['error']})
        emit('response', reply)

@socketio.on('getProfile', namespace='/account')
def acc_getProfile(msg):
    log.debug(msg)
    reply = {}
    name = msg['name'] + '.' + DEFAULT_NAMESPACE
    data = msg['hash']

    profile_result = client.get_immutable(str(name), str(data))
    profile_result['uid'] = name
    reply['type'] = 'getProfile'
    reply['payload'] = profile_result
    emit('response', reply)

@socketio.on('getNamesOwnedByAddress', namespace='/account')
def acc_getNamesOwnedByAddress(msg):
    log.debug(msg)
    address = msg['address']
    reply = {}

    names_result = client.get_names_owned_by_address(address)
    reply['type'] = 'getNamesOwnedByAddress'
    reply['payload'] = names_result

    emit('response', reply)

@socketio.on('getreddidcontacts', namespace='/account')
def acc_getreddidcontacts(msg):
    log.debug(msg)
    log.debug("Get Reddid Contacts")
    reply = {}
    data = {}

    try:
        data = client.get_names_in_namespace(DEFAULT_NAMESPACE,None,None)
    except Exception as e:
        handle_exception(e)

    names = json.dumps(data)

    reply['type'] = 'getreddidcontacts'
    reply['payload'] = names
    emit('response', reply)

@socketio.on('getreddidcontactaddress', namespace='/account')
def acc_getreddidcontactaddres(msg):
    log.info(msg)
    name = msg['name']
    reply = {}
    result = {}
    try:
        result = client.get_name_blockchain_record(name)
    except Exception as e:
        handle_exception(e)
        result['error'] = 'Cannot connect to server'

    # print result
    reply['type'] = 'getreddidcontactaddress'
    reply['payload'] = json.dumps(result)
    emit('response',reply)

@socketio.on('network', namespace='/account')
def acc_network(msg):
    error = None
    success = None
    reply ={}
    response_result = {}
    namespace = 'test'
    network = msg['network']
    uid = msg['uid']

    reply['type'] = 'network'
    reply['payload'] = response_result
    response_result['network'] = network
    response_result['user'] = uid

    queryNetwork = networkColls.find_one({network + ".username": uid})
    if queryNetwork is not None:
        log.debug(queryNetwork[network])
        if "username" in queryNetwork[network]:
            log.debug(dumps(queryNetwork[network]))
            if queryNetwork[network]['address'] != '':
                response_result['address'] = queryNetwork[network]['address']
                response_result['success'] = True
            else:
                response_result['address'] = ''
                response_result['success'] = False

            response_result['valid'] = queryNetwork[network].get('valid', False)

    else:
    #no results
        response_result['address'] = ''
        response_result['success'] = False

    log.debug('network response: %s' % str(reply))

    emit('response', reply)

@socketio.on('tipurl', namespace='/account')
def acc_tipurl(msg):
    error = None
    success = None
    reply ={}

    reply['type'] = 'tipurl'
    reply['payload'] = msg

    log.debug('tipurl response: %s' % str(reply))

    emit('response', reply, broadcast=True)

@socketio.on('client_version', namespace='/account')
def acc_clientVersion(msg):
    response = {}
    reply = {}
    if version.parse(msg['data']) == version.parse(rsaconfig.CLIENTLATEST):
        log.info('Client version {0} ok'.format(msg['data']))
        response['status'] = 'ok'
    elif version.parse(msg['data']) < version.parse(rsaconfig.CLIENTLATEST):
        log.info('Client version {0} old'.format(msg['data']))
        response['status'] = 'check'
    elif version.parse(msg['data']) > version.parse(rsaconfig.CLIENTLATEST):
        log.info('Client version {0} new'.format(msg['data']))
        response['status'] = 'check'

    response['version'] = rsaconfig.CLIENTLATEST
    reply['type'] = 'version'
    reply['payload'] = response
    emit('response', reply)

@socketio.on('my_event', namespace='/account')
def test_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response', {'data': message['data'], 'count': session['receive_count']})


def getuseraddr(uid):
    users = [
        {"uid":"reddCoin", "address":"maazGQc5AKDNt782Q7poWx2dSbdFohcrGasN"},
        {"uid":"cryptognasher", "address":"maczGQc5AKDNt782Q7poWx2dSbdFohcrGasN"},
        {"uid":"underwaterjungle", "address":"maezGQc5AKDNt782Q7poWx2dSbdFohcrGasN"},
        {"uid":"DrTad", "address":"mafzGQc5AKDNt782Q7poWx2dSbdFohcrGasN"},
        {"uid":"Teodor87", "address":"magzGQc5AKDNt782Q7poWx2dSbdFohcrGasN"},
        {"uid":"bigbearxxx", "address":"maizGQc5AKDNt782Q7poWx2dSbdFohcrGasN"},
        {"uid":"Ragnar84", "address":"majzGQc5AKDNt782Q7poWx2dSbdFohcrGasN"},
        {"uid":"ssaxamaphone", "address":"makzGQc5AKDNt782Q7poWx2dSbdFohcrGasN"},
        {"uid":"Meow3r", "address":"malzGQc5AKDNt782Q7poWx2dSbdFohcrGasN"},
        {"uid":"henryyoung42", "address":"mamzGQc5AKDNt782Q7poWx2dSbdFohcrGasN"},
    ]

    for user in users:
        if uid == user['uid']:
            log.debug('Matched uid %s' % str(user['uid']))
            return user['address']

