
import Pyro5.api
import time
import os
import queue
import threading
def pesquisar(gateway):
    terms = input("Termos: ").split()
    page = 0
    while True:
        resultados = gateway.search(terms, page)
        if not resultados:
            print("Sem resultados")
            return
        for resultado in resultados:
            print(resultado["title"])
            print(resultado["url"])
            print(resultado["snippet"])
            print("backlinks: ", resultado["backlinks"])
            print()
        if input("[n] página seguinte [ENTER] voltar: ") != "n":
            return
        page +=1


@Pyro5.api.expose
class StatsCallback:
    def __init__(self):
        self.fila = queue.Queue()

    def update_stats(self, stats):
        self.fila.put(stats)
        

def estatisticas(gateway):
    callback = StatsCallback()

    daemon = Pyro5.api.Daemon(host="localhost")
    callback_uri = daemon.register(callback)

    thread = threading.Thread(
        target=daemon.requestLoop,
        daemon=True
    )
    thread.start()

    try:
        gateway._pyroTimeout = 5
        gateway.registar_callback(str(callback_uri))

        while True:
            try:
                stats = callback.fila.get(timeout=1)
            except queue.Empty:
                continue

            os.system("cls" if os.name == "nt" else "clear")

            print("========== ESTATÍSTICAS ==========")
            for nome, valor in stats.items():
                if nome == "barrels":
                    print("\nBarrels:")
                    for barrel in valor:
                        print("-", barrel)

                elif nome == "ultimas_pesquisas":
                    print("\nÚltimas 10 pesquisas:")
                    if valor:
                        for i, pesquisa in enumerate(valor, 1):
                            print(f"{i}. {pesquisa}")
                    else:
                        print("Ainda não foram efetuadas pesquisas.")

                else:
                    print(f"{nome}: {valor}")

            print("\nPrima CTRL+C para voltar ao menu.")

    except KeyboardInterrupt:
        print("\nA voltar ao menu...")

    except Exception as e:
        print("ERRO NAS ESTATÍSTICAS:", repr(e))

    finally:
        daemon.shutdown()
        daemon.close()

    

def registar_erro(self):
    with self.stats_lock:
        self.erros += 1

    self.atualizar_stats()

    print("Erro registado nas estatísticas.")


def backlinks(gateway):
    url =input("URL: ")
    for u in gateway.get_backlinks(url):
        print(u)

def indexar_url(gateway):
    url = input("URL: ")
    gateway.add_url(url)
    print("URL enviado")

while True:
    print("1 - Pesquisar")
    print("2 - Backlinks")
    print("3 - Indexar URL")
    print("4 - Estatísticas")
    print("5 - Sair")
    opcao = input("> ")
    if opcao == "5":
        break
    try:
        gateway = Pyro5.api.Proxy("PYRONAME:gateway")
        if opcao == "1":
            pesquisar(gateway)
        elif opcao == "2":
            backlinks(gateway)
        elif opcao == "3":
            indexar_url(gateway)
        elif opcao == "4":
            estatisticas(gateway)
        
    except Exception as e:
        print("ERRO: ", e)


