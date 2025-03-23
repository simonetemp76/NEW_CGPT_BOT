import requests
import logging
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS, TELEGRAM_BOT_NAME

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_telegram_message(message: str, parse_mode: str = "Markdown"):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chat_id in TELEGRAM_CHAT_IDS:
        payload = {"chat_id": chat_id, "text": message, "parse_mode": parse_mode}
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code != 200:
                logger.error(f"Errore invio a {chat_id}: {response.json()}")
            else:
                logger.info(f"Messaggio inviato a {chat_id}.")
        except Exception as e:
            logger.error(f"Errore invio a {chat_id}: {e}")

def notify_trade(action: str, symbol: str, quantity: float, price: float, profit=None):
    message = (
        f"📢 *Trade Eseguito da {TELEGRAM_BOT_NAME}*\n"
        f"🔹 Azione: {action}\n"
        f"🔹 Coppia: {symbol}\n"
        f"🔹 Quantità: {quantity}\n"
        f"🔹 Prezzo: {price:.2f} USDC\n"
    )
    if profit is not None:
        try:
            profit_value = float(profit)
            message += f"💰 Profitto: {profit_value:.2f}%\n"
        except ValueError:
            message += f"💰 Profitto: {profit}\n"
    send_telegram_message(message)

def notify_startup(symbols: list):
    message = f"🚀 *{TELEGRAM_BOT_NAME} Avviato!*\nCoppie monitorate:\n" + "\n".join(f"🔹 {s}" for s in symbols)
    send_telegram_message(message)

def notify_error(error_message: str):
    message = f"❌ *Errore Critico in {TELEGRAM_BOT_NAME}*\n{error_message}"
    send_telegram_message(message)

def notify_warning(warning_message: str):
    message = f"⚠️ *Avviso in {TELEGRAM_BOT_NAME}*\n{warning_message}"
    send_telegram_message(message)

def notify_info(info_message: str):
    message = f"ℹ️ *Info da {TELEGRAM_BOT_NAME}*\n{info_message}"
    send_telegram_message(message)

def notify_cycle_start(symbol: str):
    message = f"🔄 *{TELEGRAM_BOT_NAME}*\nCoppia: {symbol}\nAnalisi in corso..."
    send_telegram_message(message)

def notify_cycle_end(symbol: str, result: str):
    message = f"✅ *{TELEGRAM_BOT_NAME}*\nCoppia: {symbol}\nRisultato: {result}"
    send_telegram_message(message)
