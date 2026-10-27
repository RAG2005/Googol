import Pyro5.api

g = Pyro5.api.Proxy("PYRONAME:gateway")
g.add_url("https://excel.cloud.microsoft/")