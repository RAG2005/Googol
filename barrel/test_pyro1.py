import Pyro5.api

b = Pyro5.api.Proxy("PYRONAME:barrel2")
for i in range(25):
    b.add_page(f"http://p{i}", f"P{i}", f"texto {i}", ["python"], [])
print(len(b.search(["python"], 0)))
print(len(b.search(["python"], 1)))
print(len(b.search(["python"], 2)))
print(len(b.search(["python"], 3)))