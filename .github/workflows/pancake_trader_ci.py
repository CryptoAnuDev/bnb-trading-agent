import os
import time
import requests
from dotenv import load_dotenv
from web3 import Web3
from bnbagent import EVMWalletProvider

load_dotenv()

# ==========================================
# 1. Wallet verbinden
# ==========================================
print("🤖 Starte PancakeSwap Trading Agent (GITHUB ACTIONS - 1 USDC TEST)...")
wallet = EVMWalletProvider(
    password=os.getenv("WALLET_PASSWORD"),
    private_key=os.getenv("PRIVATE_KEY")
)
print(f"✅ Agent-Wallet verbunden: {wallet.address}")

# ==========================================
# 2. PancakeSwap Router (MAINNET)
# ==========================================
BSC_MAINNET_RPC = "https://bsc-dataseed.binance.org/"
PANCAKE_ROUTER = "0x10ED43C718714eb63d5aA57B78B54704E256024E"
USDC = "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"
WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"

USDC_ABI = [
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]

def approve_usdc():
    print("🔑 Prüfe USDC-Freigabe...")
    w3 = Web3(Web3.HTTPProvider(BSC_MAINNET_RPC))
    private_key = os.getenv("PRIVATE_KEY")
    account = w3.eth.account.from_key(private_key)
    usdc_contract = w3.eth.contract(address=USDC, abi=USDC_ABI)
    
    current_allowance = usdc_contract.functions.allowance(account.address, PANCAKE_ROUTER).call()
    if current_allowance > 100 * 10**18:
        print("✅ USDC-Freigabe bereits vorhanden.")
        return True
    
    amount_to_approve = 100 * 10**18
    tx = usdc_contract.functions.approve(PANCAKE_ROUTER, amount_to_approve).build_transaction({
        'from': account.address,
        'gas': 200000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(account.address)
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    return receipt['status'] == 1

def get_fear_and_greed():
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

class RiskManager:
    def __init__(self, initial_balance_usd=100):
        self.initial_balance = initial_balance_usd
        self.daily_loss = 0
        self.trades_today = 0
        self.last_trade_day = None
        self.current_balance = initial_balance_usd

    def can_trade(self, amount_usd, current_day):
        print("🛡️ Führe Risikoprüfung durch...")
        loss_percent = (self.initial_balance - self.current_balance) / self.initial_balance
        if loss_percent > 0.30:
            print(f"❌ TRADE GESTOPPT: Max. Drawdown von 30% erreicht!")
            return False
        if amount_usd > self.initial_balance * 0.20:
            print(f"❌ TRADE ABGELEHNT: Betrag überschreitet Positionslimit (max. 20%)")
            return False
        if self.daily_loss > self.initial_balance * 0.10:
            print(f"❌ TRADE GESTOPPT: Tägliches Verlustlimit erreicht!")
            return False
        if current_day != self.last_trade_day:
            self.trades_today = 0
            self.last_trade_day = current_day
        if self.trades_today >= 5:
            print(f"❌ TRADE ABGELEHNT: Tägliches Trade-Limit erreicht.")
            return False
        print("✅ Risikoprüfung bestanden.")
        return True

    def record_trade(self, amount_usd, current_day):
        self.trades_today += 1
        print(f"💰 Trade aufgezeichnet: ${amount_usd}")

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
        "name": "swapExactTokensForTokens",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

def pancake_swap(action, amount_usd):
    print(f"🚀 Führe {action}-Trade auf PancakeSwap aus...")
    print(f"💰 Betrag: ${amount_usd} USDC")
    
    w3 = Web3(Web3.HTTPProvider(BSC_MAINNET_RPC))
    if not w3.is_connected():
        print("❌ Keine Verbindung zum BSC Mainnet")
        return None
    
    private_key = os.getenv("PRIVATE_KEY")
    account = w3.eth.account.from_key(private_key)
    
    router = w3.eth.contract(address=PANCAKE_ROUTER, abi=ROUTER_ABI)
    
    if action == "BUY":
        path = [USDC, WBNB]
        amount_in = int(amount_usd * 10**18)
        amount_out_min = 0
        tx = router.functions.swapExactTokensForTokens(
            amount_in,
            amount_out_min,
            path,
            account.address,
            int(time.time()) + 1200
        ).build_transaction({
            'from': account.address,
            'gas': 500000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address)
        })
    else:
        print("🔑 Verkaufe BNB über swapExactETHForTokens...")
        bnb_price_usd = 600
        bnb_amount = amount_usd / bnb_price_usd
        amount_in_wei = int(bnb_amount * 10**18)
        path = [WBNB, USDC]
        amount_out_min = 0
        tx = router.functions.swapExactETHForTokens(
            amount_out_min,
            path,
            account.address,
            int(time.time()) + 1200
        ).build_transaction({
            'from': account.address,
            'value': amount_in_wei,
            'gas': 500000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address)
        })
    
    print("📤 Sende Transaktion...")
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"✅ Transaktion gesendet! Hash: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    
    if receipt['status'] == 1:
        print(f"✅ SWAP erfolgreich! Tx: {tx_hash.hex()}")
        return tx_hash.hex()
    else:
        print("❌ SWAP fehlgeschlagen")
        return None

# ==========================================
# 5. Hauptprogramm (ONCE – für GitHub Actions)
# ==========================================
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 BNB HACK TRADING AGENT – GITHUB ACTIONS MODUS")
    print("="*50)
    
    # Approve einmalig prüfen
    if not approve_usdc():
        print("❌ Approve fehlgeschlagen. Agent beendet.")
        exit(1)
    
    risk_manager = RiskManager(initial_balance_usd=100)
    current_day = time.strftime("%Y-%m-%d")

    value, _ = get_fear_and_greed()
    if value is None:
        print("❌ Konnte Marktdaten nicht abrufen.")
        exit(1)

    if value <= 25:
        action = "BUY"
        reason = "Extreme Fear – Kaufsignal! (1 USDC Test)"
        trade_amount = 1
    elif value >= 75:
        action = "SELL"
        reason = "Extreme Greed – Verkaufssignal! (1 USDC Test)"
        trade_amount = 1
    else:
        action = "HOLD"
        reason = f"Neutral ({value}) – Abwarten."
        trade_amount = 0

    print(f"🧠 Entscheidung: {action} – {reason}")

    if action in ["BUY", "SELL"]:
        if risk_manager.can_trade(trade_amount, current_day):
            tx_hash = pancake_swap(action, trade_amount)
            if tx_hash:
                risk_manager.record_trade(trade_amount, current_day)
                print("✅ Trade erfolgreich!")
            else:
                print("❌ Trade fehlgeschlagen")
                exit(1)
        else:
            print("⛔ Handel blockiert.")
    else:
        print("⏳ Keine Aktion – kein Trade heute.")

    print("\n🏁 Analyse beendet.")