import requests

r = requests.get("https://www.brickeconomy.com/", timeout=5)
print(r.status_code)
print(r.headers.get("Content-Type"))