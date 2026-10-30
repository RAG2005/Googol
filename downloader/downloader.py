import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urldefrag
import time
import Pyro5.api
import socket
import uuid

worker_id = f"{socket.gethostname()}-{uuid.uuid4()}"

def processar_pagina(url):
    print("A processar:", url)

    try:
        resposta = requests.get(
            url,
            timeout=(5, 10),
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        print("HTTP:", resposta.status_code)

    except requests.exceptions.Timeout as erro:
        print("TIMEOUT no download:", url, repr(erro))
        return None

    except requests.exceptions.RequestException as erro:
        print("ERRO HTTP:", url, repr(erro))
        return None

    except Exception as erro:
        print("ERRO inesperado no download:", url, repr(erro))
        
        return None

    if resposta.status_code != 200:
        print("HTTP diferente de 200:", resposta.status_code)
        return None

    content_type = resposta.headers.get("Content-Type", "")

    if "text/html" not in content_type.lower():
        print("Content-Type inválido:", content_type)
        return None

    try:
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
            link = urldefrag(
                urljoin(url, a["href"])
            )[0]

            if link.startswith("http"):
                links.add(link)

        print(
            "Página processada:",
            len(palavras),
            "palavras,",
            len(links),
            "links"
        )

        return titulo, citacao, palavras, list(links)

    except Exception as erro:
        print("ERRO ao processar HTML:", repr(erro))
        return None

barrels = ["barrel1", "barrel2"]
pendentes = []

def enviar(nome, url, titulo, citacao, palavras, links):
    try:
        print("A enviar para", nome, ":", url)

        with Pyro5.api.Proxy("PYRONAME:" + nome) as barrel:
            resultado = barrel.add_page(
                url,
                titulo,
                citacao,
                palavras,
                links
            )

        print("Resposta do", nome, ":", resultado)

        return resultado

    except Exception as erro:
        print(
            "ERRO ao enviar para",
            nome,
            ":",
            repr(erro)
        )

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
    print("\n==============================")
    print("A PROCESSAR:", url)
    print("==============================")

    resultado = processar_pagina(url)

    if resultado is None:
        print("FALHOU NO DOWNLOAD/PROCESSAMENTO")
        return False

    titulo, citacao, palavras, links = resultado

    print("A enviar página aos Barrels...")

    if not enviar_aos_barrels(
        url,
        titulo,
        citacao,
        palavras,
        links
    ):
        print("FALHOU NO ENVIO AOS BARRELS")
        return False

    print("Página guardada nos Barrels.")

    for link in links:
        try:
            gateway.add_url(link)
        except Exception as erro:
            print("Erro ao adicionar link:", link, repr(erro))

    print("TAREFA CONCLUÍDA:", url)

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
                    gateway.registar_erro()
                    print("Erro a processar", url, erro)

        except (Pyro5.errors.CommunicationError, Pyro5.errors.NamingError) as erro:
            gateway.registar_erro()
            print("Gateway indisponível:", erro)
            time.sleep(3)

        except Exception as erro:
            gateway.registar_erro()
            print("Erro inesperado:", erro)
            time.sleep(2)




if __name__ == "__main__":
    main()
