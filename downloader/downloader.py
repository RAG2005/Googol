import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urldefrag
import time
import Pyro5.api
import socket
import uuid

worker_id = f"{socket.gethostname()}-{uuid.uuid4()}"
barrels = ["barrel1", "barrel2"]
pendentes = []

def processar_pagina(url):
    try:
        resposta = requests.get(url, timeout=10)
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
    except Exception:
        return None

def enviar(nome, url, titulo, citacao, palavras, links):
    try:
        with Pyro5.api.Proxy("PYRONAME:" + nome) as barrel:
            return barrel.add_page(url, titulo, citacao, palavras, links)
    except Exception:
        return False

def enviar_aos_barrels(url, titulo, citacao, palavras, links):
    confirmados = 0
    for nome in barrels:
        if enviar(nome, url, titulo, citacao, palavras, links):
            confirmados += 1
        else:
            print(nome, "sem ACK, fica pendente")
            pendentes.append((nome, url, titulo, citacao, palavras, links))
    return confirmados > 0

def reenviar_pendentes():
    for item in pendentes[:]:
        nome, url, titulo, citacao, palavras, links = item
        if enviar(nome, url, titulo, citacao, palavras, links):
            pendentes.remove(item)
            print("reenviado a", nome)

def tratar_url(gateway, url):
    resultado = processar_pagina(url)
    if resultado is None:
        print("Falhou:", url)
        return False
    titulo, citacao, palavras, links = resultado
    if not enviar_aos_barrels(url, titulo, citacao, palavras, links):
        print("Nenhum barrel confirmou:", url)
        return False
    for link in links:
        gateway.add_url(link)
    return True

def um_ciclo():
    with Pyro5.api.Proxy("PYRONAME:gateway") as gateway:
        url = gateway.get_url(worker_id)
        if url is None:
            time.sleep(1)
        elif tratar_url(gateway, url):
            gateway.ack_url(url, worker_id)
            print("Concluido:", url)

def main():
    while True:
        reenviar_pendentes()
        try:
            um_ciclo()
        except Exception as erro:
            print("Erro:", erro)
            time.sleep(2)
            
if __name__ == "__main__":
    main()