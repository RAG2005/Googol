import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urldefrag
import time
import Pyro5.api

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

def enviar_aos_barrels(url, titulo, citacao, palavras, links):
    for nome in barrels:
        try:
            with Pyro5.api.Proxy("PYRONAME:" + nome) as barrel:
                barrel.add_page(url, titulo, citacao, palavras, links)
        except Exception:
            print(nome, "falhou")

def tratar_url(gateway, url):
    resultado = processar_pagina(url)
    if resultado is None:
        return
    titulo, citacao, palavras, links = resultado
    enviar_aos_barrels(url, titulo, citacao, palavras, links)
    for link in links:
        gateway.add_url(link)
    print(url)

def main():
    gateway = Pyro5.api.Proxy("PYRONAME:gateway")
    for i in range(20):
        url = gateway.get_url()
        if url is None:
            time.sleep(1)
        else:
            tratar_url(gateway, url)


if __name__ == "__main__":
    main()