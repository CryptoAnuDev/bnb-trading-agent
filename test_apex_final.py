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

# ApeX verwendet Millisekunden
timestamp = str(int(time.time() * 1000))
body = ""

# 1. Signatur: timestamp + method + path + body
signature_string = timestamp + "GET" + path + body
print(f"🔑 Signatur-String: {signature_string}")
signature = hmac.new(
    API_SECRET.encode('utf-8'),
    signature_string.encode('utf-8'),
    hashlib.sha256
).hexdigest()

# 2. Headers (ApeX erwartet vielleicht andere Header-Namen)
headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY,
    "X-Timestamp": timestamp,
    "X-Signature": signature,
    "X-Passphrase": PASSPHRASE
}
print(f"📋 Headers: {headers}")

# 3. Anfrage senden
try:
    response = requests.get(BASE_URL + path, headers=headers)
    print(f"📊 Status: {response.status_code}")
    print(f"📄 Response: {response.text}")
    
    if response.status_code == 200 and "err" not in response.text:
        print("✅ ApeX API funktioniert!")
    else:
        print("❌ Fehler: Prüfe API-Key-Berechtigungen.")
except Exception as e:
    print(f"❌ Fehler: {e}")