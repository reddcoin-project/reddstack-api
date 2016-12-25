import json
from sqlite3 import dbapi2 as sqlite3
import requests
from flask import g, render_template, request, Response, redirect, url_for, session, flash, _app_ctx_stack
from werkzeug import check_password_hash, generate_password_hash
from app import app
from .forms import LookupForm, PriceForm, LookupAllnamesForm, NamespaceLookupForm, NamespacePriceForm

import config
import client

conf = config.get_config()

if conf is None:
    print("Failed to load config")
    sys.exit(1)

reddstack_server = conf['server']
reddstack_port = conf['port']

proxy = client.session(conf=conf, server_host=reddstack_server, server_port=reddstack_port) 

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
    data = json.dumps(client.get_name_blockchain_record(str(username + '.test')))
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

    #BASE
@app.route('/')
def home():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(config.NETWORK)

    return render_template("index.html", **resp)

@app.route('/what_is_reddid')
def what_is():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(config.NETWORK)
    return render_template('what_is_reddid.html', **resp )

@app.route('/how_does_it_work')
def how_does_it_work():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(config.NETWORK)
    return render_template('how_does_it_work.html', **resp )

@app.route('/acknowledge')
def acknowledge():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(config.NETWORK)
    return render_template('acknowledge.html', **resp )

@app.route('/reward')
def reward():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(config.NETWORK)
    return render_template('reward.html', **resp )

@app.route('/promote')
def promote():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(config.NETWORK)
    return render_template('promote.html', **resp )

@app.route('/register', methods=['GET', 'POST'])
def register():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(config.NETWORK)

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


            flash('You were successfully registered and can login now')
            return redirect(url_for('login'))
    return render_template('register.html', error=error, **resp)

@app.route('/login', methods=['GET', 'POST'])
def login():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(config.NETWORK)

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
    resp['network'] = format(config.NETWORK)
    session.pop('logged_in', None)
    session.pop('user_id', None)
    flash('You have logged out')
    return render_template('logout.html', **resp )

@app.route('/details')
def details():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(config.NETWORK)
    """Logs the user in."""
    if not g.user:
        return redirect(url_for('login'))
    return render_template('details.html', **resp )

#NAME/Identity pages
@app.route('/name/details')
def name_details():
    resp = {}
    resp['version'] = format(config.VERSION)
    resp['network'] = format(config.NETWORK)
    return render_template('name_details.html', **resp )




#NAME Lookup
@app.route('/name/lookup', methods=['GET', 'POST'])
def name_lookup():
    form = LookupForm()
    resp = {}
    resp['name'] = ''
    resp['status'] = ''
    resp['version'] = format(config.VERSION)
    resp['network'] = format(config.NETWORK)

    if request.method == 'POST':
        username = request.form['nameid']
        if username == '':
            return render_template('name_lookup.html', form=form, **resp )

        resp['name'] = username
        resp['status'] = client.get_name_blockchain_record(str(username + '.test'))
    return render_template('name_lookup.html', form=form, **resp )
    
@app.route('/api/name/lookup/<name>')
def api_name_lookup(name):
    data = json.dumps(client.get_name_blockchain_record(str(name + '.test')))
    resp = Response(response=data,
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
    resp['network'] = format(config.NETWORK)
    if request.method == 'POST':
        namespace = request.form['namespace']
        if namespace == '':
            return render_template('name_allnames.html', form=form, **resp )
        resp['namespace'] = namespace
        resp['status'] = client.get_names_in_namespace(str(namespace))
    return render_template('name_allnames.html', form=form, **resp )

@app.route('/api/name/allnames/<namespace>')
def api_name_allnames(namespace):
    data = json.dumps(client.get_names_in_namespace(str(namespace),None,None))
    data = json.loads(data)
    resp = Response(response=json.dumps(data['results']),
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
    resp['network'] = format(config.NETWORK)
    if request.method == 'POST':
        username = request.form['username']
        if username == '':
            return render_template('name_price.html', form=form, **resp)
        resp['name'] = username
        resp['price'] = client.get_name_cost(str(username + '.test'))
    return render_template('name_price.html', form=form, **resp)

@app.route('/api/name/price/<name>')
def api_name_price(name):
    data = json.dumps(client.get_name_cost(str(name + '.test')))
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
    resp['network'] = format(config.NETWORK)

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
    resp['network'] = format(config.NETWORK)

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

    data = json.dumps(client.get_namespace_cost(str(namespace)))
    print data
    resp = Response(response=data,
    status=200, \
    mimetype="application/json")
    return (resp)

