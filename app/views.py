import json
from flask import render_template, request, Response
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


#NAME/Identity pages
@app.route('/name/details')
def details():
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


#NAMESPACE Lookup
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

