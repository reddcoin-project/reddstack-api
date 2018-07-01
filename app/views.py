import json
from sqlite3 import dbapi2 as sqlite3
import requests
from flask import g, render_template, request, Response, redirect, url_for, session, flash, _app_ctx_stack
from werkzeug import check_password_hash, generate_password_hash
from time import sleep
from concurrent.futures import ThreadPoolExecutor
from app import app, socketio
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect
from .forms import LookupForm, PriceForm, LookupAllnamesForm, NamespaceLookupForm, NamespacePriceForm

from blockstore_client import config, client, schemas, parsing, user, storage, drivers
#from .config
#import client

#from blockstore_client import client, schemas, parsing, user
#from blockstore_client import storage, drivers
#networkfrom blockstore_client.utils import pretty_dump, print_result

executor = ThreadPoolExecutor(2)

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
print conf
proxy = client.session(conf, conf['server'], conf['port'])
#client = client.session(conf=conf, server_host=reddstack_server, server_port=reddstack_port, storage_drivers=reddstack_storage) 

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

print("Server: %s, Port: %s" % ( conf['server'], conf['port'] ))
def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    top = _app_ctx_stack.top
    if not hasattr(top, 'sqlite_db'):
        top.sqlite_db = sqlite3.connect(config.DATABASE)
        top.sqlite_db.row_factory = sqlite3.Row
    return top.sqlite_db

@app.teardown_appcontext
def close_database(exception):
    """Closes the database again at the end of the request."""
    top = _app_ctx_stack.top
    if hasattr(top, 'sqlite_db'):
        top.sqlite_db.close()

def init_db():
    """Initializes the database."""
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()

@app.cli.command('initdb')
def initdb_command():
    """Creates the database tables."""
    init_db()
    print('Initialized the database.')



def query_db(query, args=(), one=False):
    """Queries the database and returns a list of dictionaries."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv

def get_user_id(username):
    """Convenience method to look up the id for a username."""
    rv = query_db('select user_id from user where username = ?', [username], one=True)
    return rv[0] if rv else None

def get_blockchain_id(username):
    data = json.dumps(client.get_name_blockchain_record(str(username + '.tester')))
    data = json.loads(data)
    if 'name' in data:
        return (data['name'])
    return None


@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = query_db('select * from user where user_id = ?',
                          [session['user_id']], one=True)

@app.route('/test')
def test():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(conf['network'])

    return render_template("test.html", async_mode=socketio.async_mode, **resp)
    #BASE
@app.route('/')
def home():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(conf['network'])

    return render_template("index.html", **resp)

@app.route('/what_is_reddid')
def what_is():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(conf['network'])
    return render_template('what_is_reddid.html', **resp )

@app.route('/how_does_it_work')
def how_does_it_work():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(conf['network'])
    return render_template('how_does_it_work.html', **resp )

@app.route('/acknowledge')
def acknowledge():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(conf['network'])
    return render_template('acknowledge.html', **resp )

@app.route('/reward')
def reward():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(conf['network'])
    return render_template('reward.html', **resp )

@app.route('/promote')
def promote():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(conf['network'])
    return render_template('promote.html', **resp )


@app.route('/register', methods=['GET'])
def register():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(conf['network'])

    """Registers the user."""
    if g.user:
        return redirect(url_for('home'))
    error = None
    if request.method == 'POST':
        if not request.form['username']:
            error = 'You have to enter a username'
        elif get_blockchain_id(request.form['username']) is not None:
            error = 'The blockchain id is already taken'
        elif not request.form['email'] or \
                '@' not in request.form['email']:
            error = 'You have to enter a valid email address'
        elif not request.form['password']:
            error = 'You have to enter a password'
        elif request.form['password'] != request.form['password2']:
            error = 'The two passwords do not match'
        elif get_user_id(request.form['username']) is not None:
            error = 'The username is already taken'

        else:
            db = get_db()
            db.execute('''insert into user (
              username, email, pw_hash) values (?, ?, ?)''',
              [request.form['username'], request.form['email'],
               generate_password_hash(request.form['password'])])
            db.commit()

            # Do block chain registration
            #register_id(request.form['username']+'.test')

            
            
            resp['tx_hash'] = result['tx_hash']


            flash('You were successfully registered and can login now')
            return redirect(url_for('registration_status'))
    return render_template('register.html', error=error, **resp)

@app.route('/registration_status', methods=['GET', 'POST'])
def registration_status():
    resp = {}
    error = None
    resp['version'] = format(config.VERSION)
    resp['network'] = format(conf['network'])
    return render_template('registration_status.html', error=error, **resp)

@app.route('/login', methods=['GET', 'POST'])
def login():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(conf['network'])

    """Logs the user in."""
    if g.user:
        return redirect(url_for('details'))
    error = None
    if request.method == 'POST':
        user = query_db('''select * from user where
            username = ?''', [request.form['username']], one=True)
        if user is None:
            error = 'Invalid username'
        elif not check_password_hash(user['pw_hash'],
                                     request.form['password']):
            error = 'Invalid password'
        else:
            flash('You have logged in')
            session['user_id'] = user['user_id']
            return redirect(url_for('details'))
    return render_template('login.html', error=error, **resp)

@app.route('/logout')
def logout():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(conf['network'])
    session.pop('logged_in', None)
    session.pop('user_id', None)
    flash('You have logged out')
    return render_template('logout.html', **resp )

@app.route('/details')
def details():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(conf['network'])
    """Logs the user in."""
    if not g.user:
        return redirect(url_for('login'))
    return render_template('details.html', **resp )

#NAME/Identity pages
@app.route('/name/details')
def name_details():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(conf['network'])
    return render_template('name_details.html', **resp )




#NAME Lookup
@app.route('/name/lookup', methods=['GET', 'POST'])
def name_lookup():
    form = LookupForm()
    resp = {}
    resp['name'] = ''
    resp['status'] = ''
    resp['version'] = format(config.VERSION)
    resp['network'] = format(conf['network'])

    if request.method == 'POST':
        username = request.form['nameid']
        if username == '':
            return render_template('name_lookup.html', form=form, **resp )

        resp['name'] = username
        resp['status'] = client.get_name_blockchain_record(str(username + '.tester'))
    return render_template('name_lookup.html', form=form, **resp )
    
@app.route('/api/name/lookup/<name>')
def api_name_lookup(name):
    data = {}

    name = name + '.tester'

    data['blockchain_record'] = client.get_name_blockchain_record(str(name))
    try:
        data_id = data['blockchain_record']['value_hash']
        data['data_record'] = json.loads(client.get_immutable(str(name), data_id)['data'])
    except:
        data['data_record'] = None

    resp = Response(response=json.dumps(data),
    status=200, \
    mimetype="application/json")
    return (resp)

#NAME All names

@app.route('/name/allnames', methods=['GET', 'POST'])
def name_allnames():
    form = LookupAllnamesForm()
    resp = {}
    resp['namespace'] = ''
    resp['status'] = ''
    resp['version'] = format(config.VERSION)
    resp['network'] = format(conf['network'])
    if request.method == 'POST':
        namespace = request.form['namespace']
        if namespace == '':
            return render_template('name_allnames.html', form=form, **resp )
        resp['namespace'] = namespace
        resp['status'] = client.get_names_in_namespace(str(namespace))
    return render_template('name_allnames.html', form=form, **resp )

@app.route('/api/name/allnames/<namespace>')
def api_name_allnames(namespace):

    # Sanity checks
    if len(namespace) > LENGTHS['blockchain_id_namespace_id']:
        print "Blockchain Namespace ID too long"
        data = {}
        data['error'] = "Name too long"
        return json.dumps(data)

    data = json.dumps(client.get_names_in_namespace(str(namespace),None,None))
    data = json.loads(data)
    #data = json.dumps(data)
    print data
    if 'results' in data:
        data = data['results']
    elif 'error' in data:
        data = data
    else:
        data = {}

    resp = Response(response=json.dumps(data),
    status=200, \
    mimetype="application/json")
    return (resp) 


#NAME Price
@app.route('/name/price', methods=['GET', 'POST'])
def name_price():
    form  = PriceForm()
    resp = {}
    resp['price']=0
    resp['version'] = format(config.VERSION)
    resp['network'] = format(conf['network'])
    if request.method == 'POST':
        username = request.form['username']
        if username == '':
            return render_template('name_price.html', form=form, **resp)
        resp['name'] = username
        resp['price'] = client.get_name_cost(str(username + '.tester'))
    return render_template('name_price.html', form=form, **resp)

@app.route('/api/name/price/<name>')
def api_name_price(name):
    # Sanity checks
    if len(name) > LENGTHS['blockchain_id_name']:
        print "Blockchain ID too long"
        return {"error": "Name too long"}

    data = json.dumps(client.get_name_cost(str(name + '.tester')))
    resp = Response(response=data,
    status=200, \
    mimetype="application/json")
    return (resp)

#NAME register
@app.route('/name/register')
def name_register():
    return render_template('name_register.html')


#NAMESPACE 
#NAME register
@app.route('/namespace/details')
def namespace_details():
    return render_template('what_is_namespace.html')

#NAME Lookup
@app.route('/namespace/lookup', methods=['GET', 'POST'])
def namespace_lookup():
    form = NamespaceLookupForm()
    resp = {}
    resp['name'] = ''
    resp['status'] = ''
    resp['version'] = format(config.VERSION)
    resp['network'] = format(conf['network'])

    if request.method == 'POST':
        namespace = request.form['namespace']
        if namespace == '':
            return render_template('namespace_lookup.html', form=form, **resp )

        resp['name'] = namespace
        resp['status'] = client.get_namespace_blockchain_record(str(namespace))
    print resp

    return render_template('namespace_lookup.html', form=form, **resp )


@app.route('/api/namespace/lookup/<namespace>')
def api_namespace_lookup(namespace):
    # Sanity checks
    if len(namespace) > LENGTHS['blockchain_id_namespace_id']:
        print "Blockchain Namespace ID too long"
        return {"error": "Name too long"}

    data = json.dumps(client.get_namespace_blockchain_record(str(namespace)))
    print data
    resp = Response(response=data,
    status=200, \
    mimetype="application/json")
    return (resp)

#NAMESPACE price
@app.route('/namespace/price', methods=['GET', 'POST'])
def namespace_price():
    form = NamespacePriceForm()
    resp = {}
    resp['name'] = ''
    resp['status'] = ''
    resp['price'] = 0
    resp['version'] = format(config.VERSION)
    resp['network'] = format(conf['network'])

    if request.method == 'POST':
        namespace = request.form['namespace']
        if namespace == '':
            return render_template('namespace_price.html', form=form, **resp )

        resp['name'] = namespace

        resp['price'] = client.get_namespace_cost(str(namespace))

    print resp

    return render_template('namespace_price.html', form=form, **resp )


@app.route('/api/namespace/price/<namespace>')
def api_namespace_price(namespace):
    # Sanity checks
    if len(namespace) > LENGTHS['blockchain_id_namespace_id']:
        print "Blockchain Namespace ID too long"
        return {"error": "Name too long"}

    data = json.dumps(client.get_namespace_cost(str(namespace)))
    print data
    resp = Response(response=data,
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
def test_disconnect():
    print('Client disconnected', request.sid)

thread_blockheight = None
def background_thread_currentblock():
    """Example of how to send server generated events to clients."""
    blockheight = 0
    reply = {}
    payload = {}
    while True:
        socketio.sleep(10)
        data = client.getinfo() #json.dumps(client.getinfo())
        
        if 'bitcoind_blocks' in data:
            height = data['bitcoind_blocks']
            blockheight += 1
        else:
            height = 'Indexing'

        payload['height'] = height

        reply['type'] = 'height'
        reply['payload'] = payload

        socketio.emit('response', reply,
                      namespace='/account')
# Connect to server
@socketio.on('connect', namespace='/account') 
def test_connect():
    global thread
    global thread_blockheight
    if thread is None:
        thread = socketio.start_background_task(target=background_thread)
    if thread_blockheight is None:
        thread_blockheight = socketio.start_background_task(target=background_thread_currentblock)
    emit('my_response', {'data': 'Connected', 'count': 0})

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
def test_disconnect():
    print('Client disconnected', request.sid)

@socketio.on('register_', namespace='/account')
def acc_register_(message):
    error = None
    success = None
    namespace = 'test'

    print('Register User: %s' % str(message))

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
        print username

        preorder_result = json.dumps(client.preorder(username, config.PRIV_KEY))
        preorder_result = json.loads(preorder_result)
        preorder_result['operation'] = 'preorder'

        print('Blockchain result: %s' % str(preorder_result))

        if 'success' in preorder_result:
            db.commit()
            success = 'You successfully pre-ordered blockchain userid: ' + message['username']
            emit('preorder_tx', preorder_result)

            ## send a register request
            register_result = json.dumps(client.register(username, config.PRIV_KEY, preorder_result['register_address']))
            register_result = json.loads(register_result)
            register_result['operation'] = 'register'
            print ('Register Response = %s' % str(register_result))

            if 'success' in register_result:
                emit('register_tx', register_result)

        elif 'error' in preorder_result:
            ## need to do some conditional retries here eg indexing blockchain
            error = preorder_result['error']




    emit('my_response', {'data': 'Register a user', 'error': error, 'success': success})

@socketio.on('get_tx', namespace='/account')
def get_tx_hash(msg):
    print msg
    result = json.dumps(client.gettxinfo(msg['tx_hash']))
    result = json.loads(result)
    result['op'] = msg['op']
    result['tx_hash'] = msg['tx_hash']
    print result
    emit('send_tx', result)

@socketio.on('getcost', namespace='/account')
def get_cost(msg):
    print msg
    reply = {}
    result = json.dumps(client.get_name_cost(str(msg['data'] + '.tester')))
    result = json.loads(result)
    #result = json.dumps(client.gettxinfo(msg['tx_hash']))
    available = client.get_name_record(msg['data'] + '.tester')
    print available
    
    result['uid'] = msg['data']
    if 'error' in client.get_name_blockchain_record(msg['data'] + '.tester'):
        result['status'] = 'not found'
    else:
        result['status'] = 'found'

    print result
    reply['type'] = 'cost'
    reply['payload'] = result 
    emit('response',reply)
    return reply
    #emit('receivecost', result)

@socketio.on('preorder', namespace='/account')
def acc_preorder(msg):
    print msg
    error = None
    success = None
    reply = {}
    namespace = 'tester'
    uid = msg['uid']
    owningAddr = msg['owningAddr']
    publicKey = msg['publicKey']
    username = uid + '.' + namespace
    if get_blockchain_id(username) is not None:
        error = 'The blockchain id is already taken'

    print username
    print owningAddr
    print publicKey
    # preorder UID, paying privkey, [owning addr]

    #preorder_result = json.dumps(client.preorder(username, config.PRIV_KEY, owningAddr))
    preorder_result = json.dumps(client.preorder_unsigned(username, publicKey, owningAddr))
    preorder_result = json.loads(preorder_result)
    #preorder_result['operation'] = 'preorder'
    reply['type'] = 'preorder'
    reply['payload'] = preorder_result
    print('Blockchain result: %s' % str(reply))

    if not 'error' in preorder_result:
        print "Success in preorder "
        #emit('preorder', preorder_result)
        emit('response', reply)

    else:
        print "Error in preorder " + preorder_result['error']
        #emit('preorder', {'error': preorder_result['error']})
        emit('response', reply)
    #    return

    
@socketio.on('register', namespace='/account')
def acc_register(msg):
    print msg
    error = None
    success = None
    reply ={}
    namespace = 'tester'
    uid = msg['uid']
    owningAddr = msg['owningAddr']
    publicKey = msg['publicKey']
    username = uid + '.' + namespace

    ## send a register request
    #register_result = json.dumps(client.register(username, payingAddr, owningAddr))
    register_result = json.dumps(client.register_unsigned(username, publicKey, owningAddr))
    register_result = json.loads(register_result)
    #register_result['type'] = 'register'
    reply['type'] = 'register'
    reply['payload'] = register_result
    print ('Blockchain result: %s' % str(reply))

    if not 'error' in register_result:
        print "Success in register "
        #emit('register', register_result)
        emit('response', reply)

    else:
        print "Error in register " + register_result['error']
        #emit('register', {'error': register_result['error']})
        emit('response', reply)

@socketio.on('update', namespace='/account')
def acc_update(msg):
    error = None
    success = None
    reply ={}
    namespace = 'test'
    uid = msg['uid']
    owningAddr = msg['owningAddr']['priv']
    payload = json.dumps(msg['profile'])
    username = uid + '.' + namespace

    print "Payload = " + payload

    ## send a update request
    update_result = json.dumps(client.update(username, payload, owningAddr))
    update_result = json.loads(update_result)

    reply['type'] = 'update'
    reply['payload'] = update_result
    print ('Blockchain result: %s' % str(reply))

    if 'success' in update_result:
        print "Success in update "
        #emit('register', register_result)
        emit('response', reply)

    elif 'error' in update_result:
        print "Error in update " + update_result['error']
        #emit('register', {'error': register_result['error']})
        emit('response', reply)

@socketio.on('network', namespace='/account')
def acc_update(msg):
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
    response_result['address'] = getuseraddr(uid)
    response_result['success'] = True
    

    print ('network response: %s' % str(reply))

    emit('response', reply)

@socketio.on('tipurl', namespace='/account')
def acc_tipurl(msg):
    error = None
    success = None
    reply ={}

    reply['type'] = 'tipurl'
    reply['payload'] = msg

    print ('tipurl response: %s' % str(reply))

    emit('response', reply, broadcast=True)


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
            print ('Matched uid %s' % str(user['uid']))
            return user['address']

