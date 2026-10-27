import Pyro5.api

b = Pyro5.api.Proxy("PYRONAME:barrel1")
'''
for i in range(25):
    b.add_page(f"http://p{i}", f"P{i}", f"texto {i}", ["python"], [])
print(len(b.search(["python"], 0)))
print(len(b.search(["python"], 1)))
print(len(b.search(["python"], 2)))
print(len(b.search(["python"], 3)))
'''
b.add_page("http://a", "A", "texto a", ["python", "redes"], ["http://b"])
b.add_page("http://b", "B", "texto b", ["python"], ["http://c"])
b.add_page("http://c", "C", "texto c", ["python", "redes"], ["http://b"])
print(b.search(["python"]))
print(b.search(["python", "redes"]))
print(b.search(["xyz"]))
print(b.search([]))
print(b.search(["Python"]))
print(b.search(["python"], 1))

'''
b.add_page("http://a", "A", "texto a", ["python", "redes"], ["http://b"])
b.add_page("http://b", "B", "texto b", ["python"], ["http://c"])
b.add_page("http://c", "C", "texto c", ["python", "redes"], ["http://b"])
print(b.search(["python"]))
print(b.search(["python", "redes"]))
print(b.get_backlinks("http://b"))
'''