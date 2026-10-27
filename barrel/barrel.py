import sys
import Pyro5.api
import threading
import sqlite3

@Pyro5.api.expose
class Barrel:
    def __init__(self, db_path="barrel.db"):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS pages (
                url TEXT PRIMARY KEY,
                title TEXT,
                snippet TEXT
            );

            CREATE TABLE IF NOT EXISTS word_index (
                word TEXT,
                url TEXT,
                PRIMARY KEY (word, url)
            );

            CREATE TABLE IF NOT EXISTS backlinks (
                link TEXT,
                url TEXT,
                PRIMARY KEY (link, url)
            );

            CREATE TABLE IF NOT EXISTS seen (
                url TEXT PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS queue (
                url TEXT PRIMARY KEY,
                position INTEGER UNIQUE
            );
        """)
        self.db.commit()
        self.index = {}
        self.pages = {}
        self.backlinks = {}
        self.por_visitar = []
        self.vistos = set()
        self.lock = threading.Lock()
        self.load_data()
        
        
    def load_data(self):
        with self.lock:
            for url, title, snippet in self.db.execute("SELECT url, title, snippet FROM pages"):
                self.pages[url] = {
                    "title": title,
                    "snippet": snippet
                }
            
            for word, url in self.db.execute("SELECT word, url FROM word_index"):
                self.index.setdefault(word, set()).add(url)
                
            for link, url in self.db.execute("SELECT link, url FROM backlinks"):
                self.backlinks.setdefault(link, set()).add(url)
                
            self.vistos = {
                row[0] for row in self.db.execute("SELECT url FROM seen")
            }
            
            self.por_visitar = [
                row[0] for row in self.db.execute("SELECT url FROM queue ORDER BY position")
            ]
                

    def add_page(self, url, title, snippet, words, links):
        with self.lock:
            self.db.execute("""
                INSERT OR REPLACE INTO pages (url, title, snippet)
                VALUES (?, ?, ?)
            """, (url, title, snippet))

            for word in set(words):
                word = word.lower()
                self.db.execute("""
                    INSERT OR IGNORE INTO word_index (word, url)
                    VALUES (?, ?)
                """, (word, url))

                self.index.setdefault(word, set()).add(url)

            for link in set(links):
                self.db.execute("""
                    INSERT OR IGNORE INTO backlinks (link, url)
                    VALUES (?, ?)
                """, (link, url))

                self.backlinks.setdefault(link, set()).add(url)

            self.pages[url] = {
                "title": title,
                "snippet": snippet
            }

            self.db.commit()

    def search(self, terms, page=0):
        if not terms:
            return []
        urls = None
        for term in terms:
            found = self.index.get(term.lower(), set())
            if urls is None:
                urls = found
            else:
                urls = urls & found
        ordered = sorted(urls, key=lambda u: len(self.backlinks.get(u, [])), reverse = True)
        start = page * 10
        results = []
        for url in ordered[start:start + 10]:
            results.append({"url": url, "title": self.pages[url]["title"], "snippet": self.pages[url]["snippet"], "backlinks": len(self.backlinks.get(url, []))})
        return results

    def get_backlinks(self, url):
        return list(self.backlinks.get(url, []))

    def add_url(self, url):
        with self.lock:
            if url not in self.vistos:
                position = len(self.por_visitar)

                self.db.execute(
                    "INSERT OR IGNORE INTO seen (url) VALUES (?)",
                    (url,)
                )
                self.db.execute("""
                    INSERT OR IGNORE INTO queue (url, position)
                    VALUES (?, ?)
                """, (url, position))

                self.db.commit()

                self.vistos.add(url)
                self.por_visitar.append(url)

    def get_url(self):
        with self.lock:
            if not self.por_visitar:
                return None

            url = self.por_visitar.pop(0)

            self.db.execute(
                "DELETE FROM queue WHERE url = ?",
                (url,)
            )
            self.db.commit()

            return url
        
    def close(self):
        with self.lock:
            self.db.commit()
            self.db.close()


def main(name):
    barrel = Barrel()
    daemon = Pyro5.api.Daemon()
    uri = daemon.register(barrel)
    Pyro5.api.locate_ns().register(name, uri)
    print(name, "pronto")
    try:
        daemon.requestLoop()
    finally:
        barrel.close()
        daemon.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "barrel1")