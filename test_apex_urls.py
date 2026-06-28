import requests

urls = [
    "https://api.apex.exchange/",
    "https://api.apex.exchange/v1/account",
    "https://api.apex.exchange/v1/market/ticker",
    "https://api.apex.exchange/v1/order",
    "https://api.apex.exchange/api/account",
    "https://api.apex.exchange/api/order",
    "https://api.apex.exchange/order",
    "https://api.apex.exchange/account"
]

for url in urls:
    try:
        r = requests.get(url, timeout=5)
        print(f"{url} → Status: {r.status_code}")
    except Exception as e:
        print(f"{url} → Fehler: {e}")