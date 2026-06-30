import os
import time
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from web3 import Web3
from bnbagent import EVMWalletProvider

load_dotenv()

# ==========================================
# 1. Konfiguration & Wallet
# ==========================================
print("🤖 Starte Meme-Coin Sniper Agent (1 USD Trades)...")
print(f"🕒 Startzeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Wallet laden
wallet = EVMWalletProvider(
    password=os.getenv("WALLET_PASSWORD"),
    private_key=os.getenv("PRIVATE_KEY")
)
print(f"✅ Agent-Wallet verbunden: {wallet.address}")

# ==========================================
# 2. Token-Discovery mit DexScreener API (kostenlos)
# ==========================================
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex"

def get_new_bsc_tokens():
    """Ruft die neuesten Tokens auf BSC über DexScreener ab."""
    try:
        url = f"{DEXSCREENER_API}/search?q=BSC"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get("pairs"):
            bsc_pairs = [p for p in data["pairs"] if p.get("chainId") == "bsc"]
            return bsc_pairs
        return []
    except Exception as e:
        print(f"❌ Fehler beim Abrufen neuer Tokens: {e}")
        return []

# ==========================================
# 3. PancakeSwap Router (MAINNET)
# ==========================================
BSC_MAINNET_RPC = "https://bsc-dataseed.binance.org/"
PANCAKE_ROUTER = "0x10ED43C718714eb63d5aA57B78B54704E256024E"
WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"

ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactETHForTokens",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForETH",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# ==========================================
# 4. Token-Filter & Risikomanagement
# ==========================================
CONFIG = {
    "min_liquidity_usd": 10000,
    "max_pool_age_hours": 6,
    "max_slippage": 0.10,
    "buy_amount_bnb": 0.0017,  # ~1 USD
    "min_tx_count": 10,
    "take_profit_percent": 30,   # 30% Gewinn mitnehmen
    "stop_loss_percent": 15,     # 15% Verlust begrenzen
    "max_hold_time_minutes": 0   # 0 = deaktiviert
}

def is_token_attractive(token):
    """Prüft, ob ein Token die Kriterien erfüllt."""
    try:
        liq_usd = float(token.get("liquidity", {}).get("usd", 0))
        if liq_usd < CONFIG["min_liquidity_usd"]:
            return False
        
        creation_time = token.get("pairCreatedAt")
        if creation_time:
            age_hours = (time.time() - (creation_time / 1000)) / 3600
            if age_hours > CONFIG["max_pool_age_hours"]:
                return False
        
        tx_count_24h = token.get("txns", {}).get("h24", {}).get("buys", 0) + token.get("txns", {}).get("h24", {}).get("sells", 0)
        if tx_count_24h < CONFIG["min_tx_count"]:
            return False
        
        symbol = token.get("baseToken", {}).get("symbol", "").upper()
        if not symbol:
            return False
        
        known_scams = ["RUG", "SCAM", "HONEYPOT", "TEST"]
        for scam in known_scams:
            if scam in symbol:
                return False
        
        print(f"✅ Token {symbol} ist attraktiv!")
        print(f"   💧 Liquidität: ${liq_usd:.2f}")
        print(f"   🔄 Transaktionen (24h): {tx_count_24h}")
        return True
    except Exception as e:
        print(f"⚠️ Fehler beim Prüfen von Token: {e}")
        return False

# ==========================================
# 5. Trading-Funktionen
# ==========================================
def buy_token_with_bnb(token_address, amount_bnb):
    """Kauft einen Token mit BNB über PancakeSwap."""
    print(f"🚀 Kaufe Token {token_address} mit {amount_bnb} BNB (~1 USD)...")
    
    w3 = Web3(Web3.HTTPProvider(BSC_MAINNET_RPC))
    if not w3.is_connected():
        print("❌ Keine Verbindung zum BSC Mainnet")
        return None
    
    private_key = os.getenv("PRIVATE_KEY")
    account = w3.eth.account.from_key(private_key)
    
    router = w3.eth.contract(address=PANCAKE_ROUTER, abi=ROUTER_ABI)
    amount_in_wei = int(amount_bnb * 10**18)
    
    tx = router.functions.swapExactETHForTokens(
        0,
        [WBNB, token_address],
        account.address,
        int(time.time()) + 1200
    ).build_transaction({
        'from': account.address,
        'value': amount_in_wei,
        'gas': 500000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(account.address)
    })
    
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"✅ Kauf-Transaktion gesendet: {tx_hash.hex()}")
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    if receipt['status'] == 1:
        print(f"✅ Kauf erfolgreich! Tx: {tx_hash.hex()}")
        return tx_hash.hex()
    else:
        print("❌ Kauf fehlgeschlagen")
        return None

def sell_token(token_address, amount_percent=100):
    """Verkauft einen Token über PancakeSwap."""
    print(f"📤 Verkaufe Token {token_address} ({amount_percent}%)...")
    
    w3 = Web3(Web3.HTTPProvider(BSC_MAINNET_RPC))
    if not w3.is_connected():
        print("❌ Keine Verbindung zum BSC Mainnet")
        return None
    
    private_key = os.getenv("PRIVATE_KEY")
    account = w3.eth.account.from_key(private_key)
    
    router = w3.eth.contract(address=PANCAKE_ROUTER, abi=ROUTER_ABI)
    
    # Token-Balance abrufen
    token_contract = w3.eth.contract(
        address=token_address,
        abi=[{"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"}]
    )
    balance = token_contract.functions.balanceOf(account.address).call()
    
    if balance == 0:
        print("❌ Kein Token-Bestand zum Verkaufen")
        return None
    
    amount_to_sell = int(balance * amount_percent / 100)
    
    tx = router.functions.swapExactTokensForETH(
        amount_to_sell,
        0,
        [token_address, WBNB],
        account.address,
        int(time.time()) + 1200
    ).build_transaction({
        'from': account.address,
        'gas': 500000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(account.address)
    })
    
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"✅ Verkauf-Transaktion gesendet: {tx_hash.hex()}")
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    if receipt['status'] == 1:
        print(f"✅ Verkauf erfolgreich! Tx: {tx_hash.hex()}")
        return tx_hash.hex()
    else:
        print("❌ Verkauf fehlgeschlagen")
        return None

def monitor_position(token_address, entry_price_bnb):
    """Überwacht die Position und verkauft bei TP oder SL."""
    print(f"📊 Überwache Position: {token_address}")
    print(f"   Einstiegspreis: {entry_price_bnb:.6f} BNB")
    print(f"   📈 Take-Profit: +{CONFIG['take_profit_percent']}%")
    print(f"   📉 Stop-Loss: -{CONFIG['stop_loss_percent']}%")
    
    w3 = Web3(Web3.HTTPProvider(BSC_MAINNET_RPC))
    private_key = os.getenv("PRIVATE_KEY")
    account = w3.eth.account.from_key(private_key)
    
    # Token-Contract für Balance
    token_contract = w3.eth.contract(
        address=token_address,
        abi=[{"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"}]
    )
    
    while True:
        try:
            # Aktuellen Token-Preis abrufen (über PancakeSwap)
            # Vereinfacht: Wir holen den Preis über DexScreener
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get("pairs"):
                pair = data["pairs"][0]
                price_usd = float(pair.get("priceUsd", 0))
                price_bnb = price_usd / 600  # Ungefährer BNB-Preis
                
                # Gewinn/Verlust berechnen
                price_change = ((price_bnb - entry_price_bnb) / entry_price_bnb) * 100
                print(f"📊 Aktueller Preis: ${price_usd:.4f} | Veränderung: {price_change:.2f}%")
                
                # Take-Profit prüfen
                if price_change >= CONFIG["take_profit_percent"]:
                    print(f"✅ Take-Profit erreicht! ({price_change:.2f}%)")
                    sell_token(token_address)
                    return True
                
                # Stop-Loss prüfen
                if price_change <= -CONFIG["stop_loss_percent"]:
                    print(f"❌ Stop-Loss ausgelöst! ({price_change:.2f}%)")
                    sell_token(token_address)
                    return True
            
            time.sleep(30)  # Alle 30 Sekunden prüfen
            
        except KeyboardInterrupt:
            print("\n🛑 Überwachung manuell gestoppt.")
            break
        except Exception as e:
            print(f"⚠️ Fehler bei Überwachung: {e}")
            time.sleep(60)
    
    return False

# ==========================================
# 6. Hauptprogramm
# ==========================================
def main():
    print("\n" + "="*50)
    print("🚀 MEME-COIN SNIPER AGENT (1 USD TRADES)")
    print("="*50)
    
    # 1. Neue Tokens abrufen
    print("🔍 Suche nach neuen BSC-Tokens...")
    tokens = get_new_bsc_tokens()
    if not tokens:
        print("❌ Keine Tokens gefunden.")
        return
    
    print(f"📊 Gefundene BSC-Tokens: {len(tokens)}")
    
    # 2. Tokens filtern
    attractive_tokens = []
    for token in tokens:
        if is_token_attractive(token):
            attractive_tokens.append(token)
    
    if not attractive_tokens:
        print("❌ Kein attraktiver Token gefunden.")
        return
    
    print(f"✅ {len(attractive_tokens)} attraktive Token gefunden!")
    
    # 3. Besten Token auswählen
    best_token = max(attractive_tokens, key=lambda x: float(x.get("liquidity", {}).get("usd", 0)))
    token_address = best_token.get("baseToken", {}).get("address")
    token_symbol = best_token.get("baseToken", {}).get("symbol", "UNKNOWN")
    token_liq = float(best_token.get("liquidity", {}).get("usd", 0))
    entry_price_bnb = 0.0017  # Ungefährer Einstiegspreis
    
    print(f"\n🎯 Beste Token: {token_symbol}")
    print(f"   Adresse: {token_address}")
    print(f"   Liquidität: ${token_liq:.2f}")
    
    # 4. Kauf ausführen
    buy_amount_bnb = CONFIG["buy_amount_bnb"]
    print(f"\n💰 Kaufe Token mit {buy_amount_bnb} BNB (~1 USD)...")
    
    tx_hash = buy_token_with_bnb(token_address, buy_amount_bnb)
    if tx_hash:
        print(f"✅ Position für {token_symbol} eröffnet!")
        print(f"📊 Tx Hash: {tx_hash}")
        
        # 5. Position überwachen (TP/SL)
        print("\n🔍 Starte Positionsüberwachung...")
        monitor_position(token_address, entry_price_bnb)
    else:
        print("❌ Kauf fehlgeschlagen.")
    
    print("\n🏁 Analyse beendet.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Agent manuell gestoppt.")
    except Exception as e:
        print(f"❌ Fehler: {e}")