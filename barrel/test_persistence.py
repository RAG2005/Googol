
import os
import tempfile

from barrel import Barrel


def test_persistence():
    # Criar uma base de dados temporária
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_path = temp.name
    temp.close()

    try:
        # 1. Criar o Barrel e guardar dados
        barrel = Barrel(db_path)

        barrel.add_page(
            "https://exemplo.pt",
            "Página de teste",
            "Um exemplo de persistência",
            ["python", "sqlite", "teste"],
            ["https://outro.pt"]
        )

        barrel.add_url("https://fila.pt")

        # Confirmar que os dados existem em memória
        assert "https://exemplo.pt" in barrel.pages
        assert "python" in barrel.index
        assert "https://fila.pt" in barrel.vistos

        # Fechar a primeira instância
        barrel.close()

        # 2. Criar uma nova instância com a mesma base de dados
        barrel2 = Barrel(db_path)

        # 3. Confirmar que os dados foram recuperados
        assert "https://exemplo.pt" in barrel2.pages
        assert barrel2.pages["https://exemplo.pt"]["title"] == "Página de teste"

        assert "https://exemplo.pt" in barrel2.index["python"]
        assert "https://exemplo.pt" in barrel2.backlinks["https://outro.pt"]

        assert "https://fila.pt" in barrel2.vistos
        assert "https://fila.pt" in barrel2.por_visitar

        print("SUCESSO: a persistência funciona!")

        barrel2.close()

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

        if os.path.exists(db_path + "-wal"):
            os.remove(db_path + "-wal")

        if os.path.exists(db_path + "-shm"):
            os.remove(db_path + "-shm")


if __name__ == "__main__":
    test_persistence()
