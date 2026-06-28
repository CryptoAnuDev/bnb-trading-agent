import os
import time
import requests
import hashlib
import hmac
import json
from dotenv import load_dotenv

load_dotenv()

print("🤖 Starte ApeX Omni Perpetual Trading Agent (MAINNET) - REST API...")

# ==========================================
# 1. ApeX API Einstellungen
# ==========================================
API_KEY = os.getenv("APEX_API_KEY")
API_SECRET = os.getenv("APEX_API_SECRET")
PASSPHRASE = os.getenv("APEX_PASSPHRASE")

if not all([API_KEY, API_SECRET, PASSPHRASE]):
    print("⚠️ Bitte trage alle API-Keys in deine .env-Datei ein!")
    print("📝 Benötigt: APEX_API_KEY, APEX_API_SECRET, APEX_PASSPHRASE")
    exit(1)

BASE_URL = "https://omni.apex.exchange"

# ==========================================
# 2. ApeX API Helfer
# ==========================================
def apex_request(method, path, payload=None):
    timestamp = str(int(time.time() * 1000))
    body = json.dumps(payload) if payload else ""
    
    # Signatur: timestamp + method + path + body
    message = timestamp + method + path + body
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
    
    url = BASE_URL + path
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        else:
            response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Fehler: {response.status_code} - {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Fehler bei Anfrage: {e}")
        return None

# ==========================================
# 3. Fear & Greed Daten
# ==========================================
def get_fear_and_greed():
    print("📊 Frage Fear & Greed Index ab...")
    try:
        url = "https://api.alternative.me/fng/"
        response = requests.get(url, timeout=10)
        data = response.json()
        if data and "data" in data:
            latest = data["data"][0]
            value = int(latest["value"])
            classification = latest["value_classification"]
            print(f"📈 Fear & Greed: {value} – {classification}")
            return value, classification
    except Exception as e:
        print(f"⚠️ Fehler beim Abrufen der Daten: {e}")
    return None, None

# ==========================================
# 4. Risikomanager
# ==========================================
class PerpRiskManager:
    def __init__(self, max_leverage=2, max_position_usd=10):
        self.max_leverage = max_leverage
        self.max_position_usd = max_position_usd
        self.position = None

    def can_open_position(self, side, leverage, size_usd):
        print("🛡️ Führe Perp-Risikoprüfung durch...")
        if leverage > self.max_leverage:
            print(f"❌ Hebel {leverage}x überschreitet Limit von {self.max_leverage}x")
            return False
        if size_usd > self.max_position_usd:
            print(f"❌ Positionsgröße ${size_usd} überschreitet Limit von ${self.max_position_usd}")
            return False
        if self.position is not None:
            print("⚠️ Es ist bereits eine Position offen. Schließe diese zuerst.")
            return False
        print("✅ Perp-Risikoprüfung bestanden.")
        return True

    def close_position(self):
        if self.position is not None:
            print(f"🔒 Schließe {self.position['side']}-Position...")
            self.position = None
            return True
        else:
            print("ℹ️ Keine Position zum Schließen.")
            return False

# ==========================================
# 5. ApeX Trade ausführen
# ==========================================
def execute_apex_trade(side, leverage, size_usd):
    print(f"📤 Sende {side}-Order an ApeX Omni...")
    
    order_side = "BUY" if side == "LONG" else "SELL"
    symbol = "BNB-USDT"
    
    order_data = {
        "symbol": symbol,
        "side": order_side,
        "orderType": "MARKET",
        "quantity": str(size_usd),
        "leverage": str(leverage)
    }
    
    print(f"📋 Order-Daten: {order_data}")
    result = apex_request("POST", "/api/v3/order", order_data)
    
    if result and result.get("code") == 0:
        print(f"✅ Order erfolgreich: {result}")
        return result
    else:
        print(f"❌ Order fehlgeschlagen: {result}")
        return None

# ==========================================
# 6. Hauptprogramm
# ==========================================
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 BNB HACK APEX OMN I TRADING AGENT")
    print("="*50)

    risk_mgr = PerpRiskManager(max_leverage=2, max_position_usd=10)

    value, _ = get_fear_and_greed()
    if value is None:
        print("❌ Konnte Marktdaten nicht abrufen.")
        exit(1)

    if value <= 25:
        action = "LONG"
        reason = "Extreme Fear – Eröffne Long-Position!"
        trade_amount = 10
        leverage = 2
    elif value >= 75:
        action = "SHORT"
        reason = "Extreme Greed – Eröffne Short-Position!"
        trade_amount = 10
        leverage = 2
    else:
        action = "CLOSE"
        reason = f"Neutral ({value}) – Schließe Position (falls vorhanden)."
        trade_amount = 0
        leverage = 1

    print(f"🧠 Entscheidung: {action} – {reason}")

    if action in ["LONG", "SHORT"]:
        if risk_mgr.can_open_position(action, leverage, trade_amount):
            result = execute_apex_trade(action, leverage, trade_amount)
            if result:
                risk_mgr.position = {
                    "side": action,
                    "leverage": leverage,
                    "size_usd": trade_amount,
                    "entry_price": "MARKET"
                }
                print("✅ Perp-Trade erfolgreich ausgeführt!")
            else:
                print("❌ Perp-Trade fehlgeschlagen")
        else:
            print("⛔ Perp-Handel blockiert.")
    else:
        risk_mgr.close_position()
        print("⏳ Keine neue Position.")

    print("\n🏁 Analyse beendet.")