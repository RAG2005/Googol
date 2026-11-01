import random
import Pyro5.api
import threading
import sqlite3
import time
import os
from collections import OrderedDict

@Pyro5.api.expose
class Gateway:
    def __init__(self):
        self.barrel_names = ["barrel1", "barrel2"]
        self.contagem = {}
        self.tempos = {}
        self.stats_callbacks = []
        self.ultimas_stats = {}
        self.stats_lock = threading.Lock()
        self.mudou = threading.Event()
        self.db_lock = threading.Lock()
        self.db=sqlite3.connect("gateway.db", check_same_thread=False, timeout=10)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS tasks (url TEXT PRIMARY KEY, status TEXT NOT NULL DEFAULT 'pending', claimed_at REAL, worker_id TEXT, attempts INTEGER NOT NULL DEFAULT 0)")
        with self.db_lock:
            self.db.execute("DELETE FROM tasks WHERE TRIM(url) = ''")
            self.db.commit()

    def chamar_barrel(self, metodo, *args):
        nomes = self.barrel_names[:]
        random.shuffle(nomes)
        for nome in nomes:
            try:
                with Pyro5.api.Proxy("PYRONAME:" + nome) as barrel:
                    inicio = time.time()
                    resultado = getattr(barrel, metodo)(*args)
                if metodo == "search":
                    self.registar_tempo(nome, (time.time() - inicio) * 10)
                return resultado
            except (Pyro5.errors.CommunicationError, Pyro5.errors.NamingError):
                print(nome, "falhou")
        raise Exception("Nenhum SB disponível")

    def registar_tempo(self, nome, decimas):
        with self.stats_lock:
            total, n = self.tempos.get(nome, (0, 0))
            self.tempos[nome] = (total + decimas, n + 1)

    def search(self, terms, page=0):
        if page == 0 and terms:
            pesquisa = " ".join(terms).lower()
            with self.stats_lock:
                self.contagem[pesquisa] = self.contagem.get(pesquisa, 0) + 1
        resultados = self.chamar_barrel("search", terms, page)
        self.mudou.set()
        return resultados

    def get_backlinks(self, url):
        return self.chamar_barrel("get_backlinks", url)

    def add_url(self, url):
        with self.db_lock:
            self.db.execute("INSERT OR IGNORE INTO tasks (url, status) VALUES (?, 'pending')", (url,))
            self.db.commit()
        return True

    def ack_url(self, url, worker_id):
        with self.db_lock:
            cursor = self.db.execute("""
                UPDATE tasks
                SET status = 'done',
                    claimed_at = NULL,
                    worker_id = NULL
                WHERE url = ?
                AND status = 'processing'
                AND worker_id = ?
            """, (url, worker_id))
            self.db.commit()
            return cursor.rowcount == 1

    def get_url(self, worker_id):
        now = time.time()
        lease_seconds = 30
        with self.db_lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                self.db.execute("""
                    UPDATE tasks
                    SET status = 'pending',
                        claimed_at = NULL,
                        worker_id = NULL
                    WHERE status = 'processing'
                    AND claimed_at < ?
                """, (now - lease_seconds,))
                row = self.db.execute("""
                    SELECT url
                    FROM tasks
                    WHERE status = 'pending'
                    ORDER BY attempts, url
                    LIMIT 1
                """).fetchone()
                if row is None:
                    self.db.commit()
                    return None
                url = row[0]
                cursor = self.db.execute("""
                    UPDATE tasks
                    SET status = 'processing',
                        claimed_at = ?,
                        worker_id = ?,
                        attempts = attempts + 1
                    WHERE url = ?
                    AND status = 'pending'
                """, (now, worker_id, url))
                if cursor.rowcount != 1:
                    self.db.rollback()
                    return None
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
        return url

    def estado_barrels(self):
        estado = {}
        for nome in self.barrel_names:
            try:
                with Pyro5.api.Proxy("PYRONAME:" + nome) as barrel:
                    barrel._pyroTimeout = 2
                    estado[nome] = barrel.get_stats()
            except Exception:
                pass
        return estado

    def montar_stats(self):
        estado = self.estado_barrels()
        with self.stats_lock:
            top = sorted(self.contagem.items(), key=lambda x: x[1], reverse=True)[:10]
            tempos = dict(self.tempos)
        barrels = []
        for nome, dados in estado.items():
            media = None
            if nome in tempos:
                total, n = tempos[nome]
                media = round(total / n, 1)
            barrels.append({
                "nome": nome,
                "paginas": dados["paginas"],
                "palavras": dados["palavras"],
                "tempo_medio": media,
            })
        return {"top_pesquisas": top, "barrels": barrels}
    
    def atualizar_stats(self):
        stats = self.montar_stats()
        if stats == self.ultimas_stats:
            return
        self.ultimas_stats = stats
        with self.stats_lock:
            callbacks = self.stats_callbacks[:]
        falhados = []
        for uri in callbacks:
            try:
                with Pyro5.api.Proxy(uri) as callback:
                    callback._pyroTimeout = 2
                    callback.update_stats(stats)
            except Exception:
                falhados.append(uri)
        with self.stats_lock:
            self.stats_callbacks = [u for u in self.stats_callbacks if u not in falhados]

    def monitor(self):
        while True:
            self.mudou.wait(2)
            self.mudou.clear()
            try:
                self.atualizar_stats()
            except Exception as erro:
                print("Erro nas estatisticas:", erro)
    
    def registar_callback(self, callback_uri):
        with self.stats_lock:
            if callback_uri not in self.stats_callbacks:
                self.stats_callbacks.append(callback_uri)
        with Pyro5.api.Proxy(callback_uri) as callback:
            callback._pyroTimeout = 5
            callback.update_stats(self.montar_stats())
        print("Novo cliente registado para estatísticas")

    def ping(self):
        return True
    
def main():
    gateway = Gateway()
    threading.Thread(target=gateway.monitor, daemon=True).start()
    daemon = Pyro5.api.Daemon()
    uri = daemon.register(gateway)
    Pyro5.api.locate_ns().register("gateway", uri)
    print("Gateway pronto")
    daemon.requestLoop()

if __name__ == "__main__":
    main()