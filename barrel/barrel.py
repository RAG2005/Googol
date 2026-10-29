import sys
import Pyro5.api
import threading
import sqlite3
import stopwordsiso
STOP_WORDS = stopwordsiso.stopwords(["pt", "en"])
barrels = ["barrel1", "barrel2"]

@Pyro5.api.expose
class Barrel:
    def __init__(self, db_path="barrel.db"):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS pages (url TEXT PRIMARY KEY, title TEXT, snippet TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS words (word TEXT, url TEXT, PRIMARY KEY (word, url))")
        self.db.execute("CREATE TABLE IF NOT EXISTS backlinks (link TEXT, url TEXT, PRIMARY KEY (link, url))")
        self.db.execute("CREATE TABLE IF NOT EXISTS seen (url TEXT PRIMARY KEY)")
        self.db.execute("CREATE TABLE IF NOT EXISTS queue (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT UNIQUE)")
        self.db.commit()
        self.lock = threading.Lock()
        self.load_data()
        
    def load_data(self):
        self.index = {}
        self.pages = {}
        self.backlinks = {}
        self.por_visitar = []
        self.vistos = set()
        for url, title, snippet in self.db.execute("SELECT url, title, snippet FROM pages"):
            self.pages[url] = {"title": title, "snippet": snippet}
        for word, url in self.db.execute("SELECT word, url FROM words"):
            self.index.setdefault(word, set()).add(url)
        for link, url in self.db.execute("SELECT link, url FROM backlinks"):
            self.backlinks.setdefault(link, set()).add(url)
        for row in self.db.execute("SELECT url FROM seen"):
            self.vistos.add(row[0])
        for row in self.db.execute("SELECT url FROM queue ORDER BY id"):
            self.por_visitar.append(row[0])

    def add_page(self, url, title, snippet, words, links):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO pages VALUES (?, ?, ?)", (url, title, snippet))
            self.pages[url] = {"title": title, "snippet": snippet}
            for word in set(words):
                word = word.lower()
                if word in STOP_WORDS:
                    continue
                self.db.execute("INSERT OR IGNORE INTO words VALUES (?, ?)", (word, url))
                self.index.setdefault(word, set()).add(url)
            for link in set(links):
                self.db.execute("INSERT OR IGNORE INTO backlinks VALUES (?, ?)", (link, url))
                self.backlinks.setdefault(link, set()).add(url)
            self.db.commit()
            return True

    def search(self, terms, page=0):
        terms = [t.lower() for t in terms if t.lower() not in STOP_WORDS]
        if not terms:
            return []
        with self.lock:
            urls = None
            for term in terms:
                found = self.index.get(term.lower(), set())
                if urls is None:
                    urls = found
                else:
                    urls = urls & found
            ordered = sorted(urls, key=lambda u: len(self.backlinks.get(u, [])), reverse=True)
            start = page * 10
            results = []
            for url in ordered[start:start + 10]:
                results.append({"url": url, "title": self.pages[url]["title"], "snippet": self.pages[url]["snippet"], "backlinks": len(self.backlinks.get(url, []))})
            return results

    def get_backlinks(self, url):
        with self.lock:
            return list(self.backlinks.get(url, []))

    def add_url(self, url):
        with self.lock:
            if url in self.vistos:
                return True
            self.db.execute("INSERT INTO seen VALUES (?)", (url,))
            self.db.execute("INSERT INTO queue (url) VALUES (?)", (url,))
            self.db.commit()
            self.vistos.add(url)
            self.por_visitar.append(url)
            return True

    def get_url(self):
        with self.lock:
            if not self.por_visitar:
                return None
            url = self.por_visitar.pop(0)
            self.db.execute("DELETE FROM queue WHERE url = ?", (url,))
            self.db.commit()
            return url

    def remover_url(self, url):
        with self.lock:
            if url in self.por_visitar:
                self.por_visitar.remove(url)
                self.db.execute("DELETE FROM queue WHERE url = ?", (url,))
            if url not in self.vistos:
                self.vistos.add(url)
                self.db.execute("INSERT INTO seen VALUES (?)", (url,))
            self.db.commit()
            return True

    def get_estado(self):
        with self.lock:
            return {
                "pages": self.db.execute("SELECT url, title, snippet FROM pages").fetchall(),
                "words": self.db.execute("SELECT word, url FROM words").fetchall(),
                "backlinks": self.db.execute("SELECT link, url FROM backlinks").fetchall(),
                "seen": self.db.execute("SELECT url FROM seen").fetchall(),
                "queue": self.db.execute("SELECT url FROM queue ORDER BY id").fetchall(),
            }

    def sincronizar(self, outros):
        for nome in outros:
            try:
                with Pyro5.api.Proxy("PYRONAME:" + nome) as barrel:
                    estado = barrel.get_estado()
            except Exception:
                continue
            with self.lock:
                for linha in estado["pages"]:
                    self.db.execute("INSERT OR IGNORE INTO pages VALUES (?, ?, ?)", linha)
                for linha in estado["words"]:
                    self.db.execute("INSERT OR IGNORE INTO words VALUES (?, ?)", linha)
                for linha in estado["backlinks"]:
                    self.db.execute("INSERT OR IGNORE INTO backlinks VALUES (?, ?)", linha)
                self.db.commit()
            for linha in estado["queue"]:
                self.add_url(linha[0])
            with self.lock:
                for linha in estado["seen"]:
                    self.db.execute("INSERT OR IGNORE INTO seen VALUES (?)", linha)
                self.db.commit()
                self.load_data()
            print("sincronizado com", nome)

def main(name):
    barrel = Barrel(name + ".db")
    barrel.sincronizar([n for n in barrels if n != name])
    daemon = Pyro5.api.Daemon()
    uri = daemon.register(barrel)
    Pyro5.api.locate_ns().register(name, uri)
    print(name, "pronto")
    daemon.requestLoop()

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "barrel1")