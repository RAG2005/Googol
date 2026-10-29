import os
from barrel import Barrel

def barrel_novo(ficheiro):
    if os.path.exists(ficheiro):
        os.remove(ficheiro)
    return Barrel(ficheiro)

def test_persistencia():
    b = barrel_novo("teste1.db")
    b.add_page("http://exemplo.pt", "Teste", "citacao", ["python", "sqlite"], ["http://outro.pt"])
    b.add_url("http://fila.pt")

    b2 = Barrel("teste1.db")
    assert b2.pages["http://exemplo.pt"]["title"] == "Teste"
    assert "http://exemplo.pt" in b2.index["python"]
    assert "http://exemplo.pt" in b2.backlinks["http://outro.pt"]
    assert "http://fila.pt" in b2.vistos
    assert b2.por_visitar == ["http://fila.pt"]

def test_fila_apos_get_url():
    b = barrel_novo("teste2.db")
    b.add_url("A")
    b.add_url("B")
    assert b.get_url() == "A"
    b.add_url("C")

    b2 = Barrel("teste2.db")
    assert b2.por_visitar == ["B", "C"]

def test_stop_words():
    b = barrel_novo("teste3.db")
    b.add_page("http://a", "A", "citacao", ["o", "python", "the"], [])
    assert "o" not in b.index
    assert "the" not in b.index
    assert len(b.search(["o", "python"])) == 1
    assert b.search(["o"]) == []

if __name__ == "__main__":
    test_persistencia()
    test_fila_apos_get_url()
    test_stop_words()
    print("SUCESSO")