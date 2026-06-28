import os
import time
import requests
import hashlib
import hmac
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("APEX_API_KEY")
API_SECRET = os.getenv("APEX_API_SECRET")
PASSPHRASE = os.getenv("APEX_PASSPHRASE")

BASE_URL = "https://omni.apex.exchange"
path = "/api/v3/account"

# Timestamp in Sekunden (nicht Millisekunden)
timestamp = str(int(time.time()))
body = ""
message = timestamp + "GET" + path + body
signature = hmac.new(
    API_SECRET.encode('utf-8'),
    message.encode('utf-8'),
    hashlib.sha256
).hexdigest()

headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY,
    "X-Signature": signature,
    "X-Timestamp": timestamp,
    "X-Passphrase": PASSPHRASE
}

response = requests.get(BASE_URL + path, headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:500]}")