app = Bottle()

@app.route('/v1/name/cost/<name>')
def name_cost(name):
	return template('<p>Cost of {{name}} is {{cost}}</p>', name=name, cost=client.get_name_cost(str(name + '.blog')))