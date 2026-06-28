import os
import time
import asyncio
from dotenv import load_dotenv
from solders.keypair import Keypair
from pumpfun_sdk import PumpFunSDK

load_dotenv()

print("🤖 Starte Pump.fun Sniper Agent...")
print(f"🕒 Startzeit: {time.strftime('%Y-%m-%d %H:%M:%S')}")

# ==========================================
# 1. Solana Wallet laden
# ==========================================
# Du benötigst einen Solana-Private-Key (Base58) für deine Solana-Wallet
# Falls du noch keine hast: Erstelle eine auf phantom.app oder solflare.com
SOLANA_PRIVATE_KEY = os.getenv("SOLANA_PRIVATE_KEY")

if not SOLANA_PRIVATE_KEY:
    print("⚠️ Kein SOLANA_PRIVATE_KEY in .env gefunden!")
    print("📝 Erstelle eine Solana-Wallet (z.B. auf Phantom) und füge den Private Key in die .env ein.")
    exit(1)

try:
    # Private Key in Keypair umwandeln (Base58-Format)
    keypair = Keypair.from_base58_string(SOLANA_PRIVATE_KEY)
    wallet_address = str(keypair.pubkey())
    print(f"✅ Solana-Wallet verbunden: {wallet_address}")
except Exception as e:
    print(f"❌ Fehler beim Laden der Solana-Wallet: {e}")
    print("💡 Stelle sicher, dass der SOLANA_PRIVATE_KEY gültig ist.")
    exit(1)

# ==========================================
# 2. Pump.fun SDK initialisieren
# ==========================================
try:
    sdk = PumpFunSDK()
    print("✅ Pump.fun SDK initialisiert")
except Exception as e:
    print(f"❌ Fehler bei SDK-Initialisierung: {e}")
    exit(1)

# ==========================================
# 3. Token-Filter & Risikomanagement
# ==========================================
CONFIG = {
    "buy_amount_sol": 0.01,           # 0.01 SOL pro Kauf (~1-2 USD)
    "max_slippage": 0.10,             # 10% Slippage
    "take_profit_percent": 20,        # 20% Gewinn mitnehmen
    "stop_loss_percent": 10,          # 10% Verlust begrenzen
    "max_hold_time_minutes": 30,      # Max. 30 Minuten halten
    "min_liquidity_usd": 5000         # Mindestliquidität
}

# ==========================================
# 4. Handelsfunktionen
# ==========================================
def buy_token(mint_address, amount_sol):
    """Kauft einen Token auf Pump.fun."""
    print(f"🚀 Kaufe Token {mint_address} mit {amount_sol} SOL...")
    try:
        # Pump.fun SDK: buy_token(mint, amount_in_sol, slippage)
        tx_hash = sdk.buy_token(mint_address, amount_sol, CONFIG["max_slippage"])
        print(f"✅ Kauf erfolgreich! Tx: {tx_hash}")
        return tx_hash
    except Exception as e:
        print(f"❌ Fehler beim Kauf: {e}")
        return None

def sell_token(mint_address, amount_percent=100):
    """Verkauft einen Token auf Pump.fun."""
    print(f"📤 Verkaufe Token {mint_address} ({amount_percent}%)...")
    try:
        tx_hash = sdk.sell_token(mint_address, amount_percent)
        print(f"✅ Verkauf erfolgreich! Tx: {tx_hash}")
        return tx_hash
    except Exception as e:
        print(f"❌ Fehler beim Verkauf: {e}")
        return None

def get_token_info(mint_address):
    """Ruft Informationen zu einem Token ab."""
    try:
        info = sdk.get_token_info(mint_address)
        print(f"📊 Token: {info}")
        return info
    except Exception as e:
        print(f"❌ Fehler beim Abrufen der Token-Info: {e}")
        return None

# ==========================================
# 5. Hauptprogramm (Asynchron)
# ==========================================
async def main():
    print("\n" + "="*50)
    print("🚀 PUMP.FUN SNIPER AGENT")
    print("="*50)

    print("\n🔍 Warte auf neue Tokens...")
    print("💡 Der Agent überwacht kontinuierlich neue Pump.fun-Token.")
    print("   Drücke Strg+C zum Beenden.\n")

    try:
        # Pump.fun SDK: Neue Token überwachen
        async for token in sdk.watch_new_tokens():
            mint_address = token.get("mint")
            if not mint_address:
                continue

            print(f"\n🆕 Neuer Token entdeckt: {mint_address}")

            # 1. Token-Info abrufen
            info = get_token_info(mint_address)
            if not info:
                continue

            # 2. Liquidität prüfen
            liquidity = info.get("liquidity_usd", 0)
            if liquidity < CONFIG["min_liquidity_usd"]:
                print(f"⏳ Liquidität zu niedrig (${liquidity}). Überspringe.")
                continue

            # 3. Kaufsignal
            print(f"✅ Token erfüllt Kriterien! Kaufe...")
            tx_hash = buy_token(mint_address, CONFIG["buy_amount_sol"])

            if tx_hash:
                print(f"✅ Position eröffnet! Tx: {tx_hash}")
                # Hier könnte später eine Überwachung eingebaut werden
                # time.sleep(CONFIG["max_hold_time_minutes"] * 60)
                # sell_token(mint_address)

    except KeyboardInterrupt:
        print("\n🛑 Agent manuell gestoppt.")
    except Exception as e:
        print(f"❌ Fehler: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Agent beendet.")