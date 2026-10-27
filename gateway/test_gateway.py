import Pyro5.api

g = Pyro5.api.Proxy("PYRONAME:gateway")
print(g.search(["python"]))
print(g.get_backlinks("http://b"))