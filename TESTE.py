
import Pyro5.api

gateway = Pyro5.api.Proxy("PYRONAME:gateway")

url = "https://example.com/?teste=2"
gateway.add_url(url)
print("URL enviada para a fila:", url)
import Pyro5.api

urls = [
    "https://example.com/?worker=1",
    "https://example.com/?worker=2",
    "https://example.com/?worker=3",
    "https://example.com/?worker=4",
]

with Pyro5.api.Proxy("PYRONAME:gateway") as gateway:
    for url in urls:
        gateway.add_url(url)
        print("Adicionada:", url)