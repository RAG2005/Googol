import random
import Pyro5.api


@Pyro5.api.expose
class Gateway:
    def __init__(self):
        self.barrel_names = ["barrel1", "barrel2"]

    def chamar_barrel(self, metodo, *args):
        nomes = self.barrel_names[:]
        random.shuffle(nomes)
        for nome in nomes:
            try:
                with Pyro5.api.Proxy("PYRONAME:" + nome) as barrel:
                    return getattr(barrel, metodo)(*args)
            except (Pyro5.errors.CommunicationError, Pyro5.errors.NamingError):
                print(nome, "falhou")
        raise Exception("Nenhum SB disponível")

    def search(self, terms, page=0):
        return self.chamar_barrel("search", terms, page)

    def get_backlinks(self, url):
        return self.chamar_barrel("get_backlinks", url)

    def chamar_primario(self, metodo, *args):
        for nome in self.barrel_names:
            try:
                with Pyro5.api.Proxy("PYRONAME:" + nome) as barrel:
                    return getattr(barrel, metodo)(*args)
            except (Pyro5.errors.CommunicationError, Pyro5.errors.NamingError):
                print(nome, "falhou")
        raise Exception("Nenhum barrel disponivel")

    def add_url(self, url):
        return self.chamar_primario("add_url", url)

    def get_url(self):
        return self.chamar_primario("get_url")

def main():
    daemon = Pyro5.api.Daemon()
    uri = daemon.register(Gateway())
    Pyro5.api.locate_ns().register("gateway", uri)
    print("gateway pronto")
    daemon.requestLoop()


if __name__ == "__main__":
    main()