
import Pyro5.api
import time
import os
import queue
import threading
import Pyro5.errors


def pesquisar():
    terms = input("Termos: ").split()
    page = 0
    while True:
        resultados = chamar_gateway("search", terms, page)
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
        


def estatisticas():
    callback = StatsCallback()

    daemon = Pyro5.api.Daemon(host="localhost")
    callback_uri = daemon.register(callback)

    thread = threading.Thread(
        target=daemon.requestLoop,
        daemon=True
    )
    thread.start()

    ligado = False

    try:
        while True:

            # Registar ou voltar a registar o callback
            if not ligado:
                try:
                    with Pyro5.api.Proxy("PYRONAME:gateway") as gateway:
                        gateway._pyroTimeout = 5
                        gateway.registar_callback(str(callback_uri))

                    ligado = True
                    print("Ligação ao Gateway estabelecida.")

                except (
                    Pyro5.errors.CommunicationError,
                    Pyro5.errors.NamingError,
                    TimeoutError
                ) as erro:
                    print("Gateway indisponível:", erro)
                    print("Nova tentativa em 3 segundos...")
                    time.sleep(3)
                    continue

            try:
                stats = callback.fila.get(timeout=3)

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

            except queue.Empty:
                # Verificar se o Gateway continua ligado
                try:
                    with Pyro5.api.Proxy("PYRONAME:gateway") as gateway:
                        gateway._pyroTimeout = 5
                        gateway.ping()

                except (
                    Pyro5.errors.CommunicationError,
                    Pyro5.errors.NamingError,
                    TimeoutError
                ):
                    print("\nGateway desligado! A tentar restabelecer ligação...")
                    ligado = False

    except KeyboardInterrupt:
        print("\nA voltar ao menu...")

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

def indexar_url():
    url = input("URL: ")
    chamar_gateway("add_url", url)
    print("URL enviado")
    

def chamar_gateway(metodo, *args):
    while True:
        try:
            with Pyro5.api.Proxy("PYRONAME:gateway") as gateway:
                gateway._pyroTimeout = 5
                return getattr(gateway, metodo)(*args)

        except (
            Pyro5.errors.CommunicationError,
            Pyro5.errors.NamingError,
            TimeoutError
        ) as erro:
            print("\nGateway indisponível:", erro)
            print("Nova tentativa em 3 segundos...")
            time.sleep(3)



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
        if opcao == "1":
            pesquisar()

        elif opcao == "2":
            backlinks()

        elif opcao == "3":
            indexar_url()

        elif opcao == "4":
            estatisticas()

    except KeyboardInterrupt:
        print("\nOperação cancelada.")

    except Exception as e:
        print("ERRO:", e)



