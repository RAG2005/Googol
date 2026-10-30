import random
import Pyro5.api
import threading
import sqlite3
import time
import os

@Pyro5.api.expose
class Gateway:
    def __init__(self):
        self.barrel_names = ["barrel1", "barrel2"]
        
        self.urls_submetidos = 0
        self.pesquisas = 0
        self.downloads = 0
        self.erros = 0
        self.urls_na_fila = 0
        
        self.stats_lock = threading.Lock()
        self.db_lock = threading.Lock()
        self.db=sqlite3.connect("gateway.db", check_same_thread=False, timeout=10)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS tasks (url TEXT PRIMARY KEY, status TEXT NOT NULL DEFAULT 'pending', claimed_at REAL, worker_id TEXT, attempts INTEGER NOT NULL DEFAULT 0)")
        self.db.commit()
        
        
        

    def chamar_barrel(self, metodo, *args):
        nomes = self.barrel_names[:]
        random.shuffle(nomes)
        for nome in nomes:
            try:
                with Pyro5.api.Proxy("PYRONAME:" + nome) as barrel:
                    return getattr(barrel, metodo)(*args)
            except (Pyro5.errors.CommunicationError, Pyro5.errors.NamingError):
                print(nome, "falhou")
        raise Exception("Nenhum SB disponível")

    def search(self, terms, page=0):
        with self.stats_lock:
            self.pesquisas += 1
        return self.chamar_barrel("search", terms, page)

    def get_backlinks(self, url):
        return self.chamar_barrel("get_backlinks", url)

    def chamar_primario(self, metodo, *args):
        for nome in self.barrel_names:
            try:
                with Pyro5.api.Proxy("PYRONAME:" + nome) as barrel:
                    return getattr(barrel, metodo)(*args)
            except (Pyro5.errors.CommunicationError, Pyro5.errors.NamingError):
                print(nome, "falhou")
        raise Exception("Nenhum barrel disponivel")


    def add_url(self, url):
        with self.db_lock:
            cursor = self.db.execute("""
                INSERT OR IGNORE INTO tasks (url, status)
                VALUES (?, 'pending')
            """, (url,))
            self.db.commit()

            added = cursor.rowcount > 0

        if added:
            with self.stats_lock:
                self.urls_submetidos += 1
                self.urls_na_fila += 1

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

            confirmado = cursor.rowcount == 1

        if confirmado:
            with self.stats_lock:
                self.downloads += 1

        return confirmado

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
    
    def get_stats(self):
        with self.db_lock:
            pendentes = self.db.execute("""
                SELECT COUNT(*)
                FROM tasks
                WHERE status = 'pending'
            """).fetchone()[0]

            processing = self.db.execute("""
                SELECT COUNT(*)
                FROM tasks
                WHERE status = 'processing'
            """).fetchone()[0]

            concluidas = self.db.execute("""
                SELECT COUNT(*)
                FROM tasks
                WHERE status = 'done'
            """).fetchone()[0]

        with self.stats_lock:
            stats = {
                "urls_submetidos": self.urls_submetidos,
                "urls_na_fila": pendentes,
                "urls_em_processamento": processing,
                "urls_concluidas": concluidas,
                "pesquisas": self.pesquisas,
                "downloads": self.downloads,
                "erros": self.erros
            }

        ativos = 0

        for nome in self.barrel_names:
            try:
                with Pyro5.api.Proxy("PYRONAME:" + nome) as barrel:
                    barrel._pyroBind()
                    ativos += 1
            except Exception:
                pass

        stats["barrels_ativos"] = ativos

        return stats
        

def main():
    daemon = Pyro5.api.Daemon()
    uri = daemon.register(Gateway())
    Pyro5.api.locate_ns().register("gateway", uri)
    print("gateway pronto")
    daemon.requestLoop()


if __name__ == "__main__":
    main()