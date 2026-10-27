import Pyro5.api

g = Pyro5.api.Proxy("PYRONAME:gateway")
g.add_url("http://a")
g.add_url("http://b")
g.add_url("http://a")
print(g.get_url())
print(g.get_url())
print(g.get_url())