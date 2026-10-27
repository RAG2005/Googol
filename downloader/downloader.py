import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urldefrag


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