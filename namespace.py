
app = Bottle()

#NAMESPACE
@app.route('/v1/namespace/cost/<namespace>')
def namespace_cost(namespace):
	return template('<p>Cost of {{name}} is {{cost}}</p>', name=namespace, cost=client.get_namespace_cost(str(namespace),proxy))
