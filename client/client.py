import Pyro5.api

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
    print("4 - Sair")
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
    except Exception as e:
        print("ERRO: ", e)


