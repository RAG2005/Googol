import sys
import Pyro5.api
import threading

@Pyro5.api.expose
class Barrel:
    def __init__(self):
        self.index = {}
        self.pages = {}
        self.backlinks = {}
        self.por_visitar = []
        self.vistos = set()
        self.lock = threading.Lock()

    def add_page(self, url, title, snippet, words, links):
        self.pages[url] = {"title": title, "snippet": snippet}
        for word in words:
            word = word.lower()
            if word not in self.index:
                self.index[word] = set()
            self.index[word].add(url)
        for link in links:
            if link not in self.backlinks:
                self.backlinks[link] = set()
            self.backlinks[link].add(url)

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
                self.vistos.add(url)
                self.por_visitar.append(url)

    def get_url(self):
        with self.lock:
            if not self.por_visitar:
                return None
            return self.por_visitar.pop(0)


def main(name):
    daemon = Pyro5.api.Daemon()
    uri = daemon.register(Barrel())
    Pyro5.api.locate_ns().register(name, uri)
    print(name, "pronto")
    daemon.requestLoop()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "barrel1")