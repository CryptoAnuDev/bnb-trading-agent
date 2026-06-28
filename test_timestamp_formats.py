import os
import time
import requests
import hashlib
import hmac
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("APEX_API_KEY")
API_SECRET = os.getenv("APEX_API_SECRET")
PASSPHRASE = os.getenv("APEX_PASSPHRASE")

BASE_URL = "https://omni.apex.exchange"
path = "/api/v3/account"

# Verschiedene Timestamp-Formate testen
formats = [
    ("Sekunden (Unix)", str(int(time.time()))),
    ("Millisekunden (Unix)", str(int(time.time() * 1000))),
    ("ISO-8601", datetime.utcnow().isoformat() + "Z"),
    ("ISO-8601 ohne Z", datetime.utcnow().isoformat())
]

for name, timestamp in formats:
    print(f"\n🔍 Teste: {name} -> {timestamp}")
    
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
    
    try:
        response = requests.get(BASE_URL + path, headers=headers, timeout=5)
        print(f"✅ Status: {response.status_code}")
        print(f"📄 Response: {response.text[:200]}")
        if response.status_code == 200 and "err" not in response.text:
            print("🎉 ERFOLG! Dieses Timestamp-Format funktioniert!")
            break
    except Exception as e:
        print(f"❌ Fehler: {e}")