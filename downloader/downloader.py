<<<<<<< Updated upstream
=======
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urldefrag
import time
import Pyro5.api
import socket
import uuid

worker_id = f"{socket.gethostname()}-{uuid.uuid4()}"

def processar_pagina(url):
    try:
        resposta = requests.get(url, timeout=5)
    except Exception:
        return None
    if resposta.status_code != 200:
        return None
    if "text/html" not in resposta.headers.get("Content-Type", ""):
        return None

    soup = BeautifulSoup(resposta.text, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()

    if soup.title and soup.title.string:
        titulo = soup.title.string.strip()
    else:
        titulo = url

    texto = soup.get_text(" ")
    palavras = []
    for p in texto.split():
        p = p.lower().strip(".,;:!?()\"'")
        if p:
            palavras.append(p)

    citacao = " ".join(texto.split())[:150]

    links = set()
    for a in soup.find_all("a", href=True):
        link = urldefrag(urljoin(url, a["href"]))[0]
        if link.startswith("http"):
            links.add(link)

    return titulo, citacao, palavras, list(links)

barrels = ["barrel1", "barrel2"]
pendentes = []

def enviar(nome, url, titulo, citacao, palavras, links):
    try:
        with Pyro5.api.Proxy("PYRONAME:" + nome) as barrel:
            return barrel.add_page(url, titulo, citacao, palavras, links)
    except Exception:
        return False

def enviar_aos_barrels(url, titulo, citacao, palavras, links):
    sucesso = True
    for nome in barrels:
        if not enviar(nome, url, titulo, citacao, palavras, links):
            print(nome, "sem ACK, fica pendente")
            pendentes.append((nome, url, titulo, citacao, palavras, links))
            sucesso = False
    
    return sucesso

def reenviar_pendentes():
    for item in pendentes[:]:
        nome, url, titulo, citacao, palavras, links = item
        if enviar(nome, url, titulo, citacao, palavras, links):
            pendentes.remove(item)
            print("reenviado a", nome)

def tratar_url(gateway, url):
    resultado = processar_pagina(url)
    if resultado is None:
        return False
    titulo, citacao, palavras, links = resultado
    if not enviar_aos_barrels(url, titulo, citacao, palavras, links):
        return False
    for link in links:
        gateway.add_url(link)
    print(url)
    return True


def main():
    while True:
        try:
            with Pyro5.api.Proxy("PYRONAME:gateway") as gateway:
                url = gateway.get_url(worker_id)

                if url is None:
                    time.sleep(1)
                    continue

                try:
                    concluido = tratar_url(gateway, url)

                    if concluido:
                        confirmado = gateway.ack_url(
                            url, worker_id
                        )

                        if confirmado:
                            print("Concluído:", url)
                        else:
                            print(
                                "Tarefa já não pertence a este worker:",
                                url
                            )

                    else:
                        print(
                            "Tarefa será recuperada após o timeout:",
                            url
                        )

                except Exception as erro:
                    print("Erro a processar", url, erro)

        except (Pyro5.errors.CommunicationError,
                Pyro5.errors.NamingError) as erro:
            print("Gateway indisponível:", erro)
            time.sleep(3)

        except Exception as erro:
            print("Erro inesperado:", erro)
            time.sleep(2)




if __name__ == "__main__":
    main()
>>>>>>> Stashed changes
