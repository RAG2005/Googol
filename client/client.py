<<<<<<< Updated upstream
=======
import Pyro5.api
import time
import os

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
        
def estatisticas(gateway):
    while True:
        try:
            stats = gateway.get_stats()

            os.system("cls" if os.name == "nt" else "clear")

            print("========== ESTATÍSTICAS ==========")
            print()
            print("URLs submetidos: ", stats["urls_submetidos"])
            print("URLs na fila:    ", stats["urls_na_fila"])
            print("Pesquisas:       ", stats["pesquisas"])
            print("Downloads:       ", stats["downloads"])
            print("Erros:            ", stats["erros"])
            print("Barrels ativos:  ", stats["barrels_ativos"])
            print()
            print("Atualização automática a cada 1 segundo.")
            print("Prima CTRL+C para voltar ao menu.")

            time.sleep(1)

        except KeyboardInterrupt:
            print()
            return

        except Exception as e:
            print("Erro ao obter estatísticas:", e)
            return
        




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
    if opcao == "4":
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



>>>>>>> Stashed changes
