import logging
import os
from logging.handlers import TimedRotatingFileHandler

if not os.path.exists("logs"):
    os.makedirs("logs")

logger = logging.getLogger("TradingBotLogger")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    file_handler = TimedRotatingFileHandler("logs/trading_bot.log", when="midnight", interval=1, backupCount=30, encoding="utf-8")
    file_handler.suffix = "%Y-%m-%d"
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

def log_trade(action: str, symbol: str, quantity: float, price: float, profit: float = None):
    msg = f"{action} | {symbol} | Quantità: {quantity} | Prezzo: {price}"
    if profit is not None:
        msg += f" | Profitto: {profit:.2f}%"
    logger.info(msg)

def log_order_status(order: dict):
    if order:
        status = order.get("status", "UNKNOWN")
        symbol = order.get("symbol", "N/A")
        side = order.get("side", "N/A")
        qty = order.get("executedQty", "0")
        price = order.get("fills", [{}])[0].get("price", "N/A")
        msg = f"Ordine {side} {symbol} | Status: {status} | Quantità: {qty} | Prezzo: {price}"
        logger.info(msg)
    else:
        logger.warning("Tentativo di log ordine vuoto!")

def log_trade_event(action: str, symbol: str, quantity: float, price: float, profit: float = None):
    msg = f"{action} | {symbol} | Quantità: {quantity} | Prezzo: {price}"
    if profit is not None:
        msg += f" | Profitto: {profit}%"
    logger.info(msg)

def log_order_event(order_type: str, symbol: str, quantity: float, price: float, status: str):
    logger.info(f"ORDINE: {order_type} | {symbol} | Quantità: {quantity} | Prezzo: {price} | Stato: {status}")

def log_websocket_event(event_message: str):
    logger.info(f"WEBSOCKET EVENT: {event_message}")

def log_error(error_message: str):
    logger.error(f"ERRORE: {error_message}")

def log_wallet_event(wallet_info: str):
    logger.info(f"WALLET | {wallet_info}")

def log_connection(status_message: str):
    logger.info(f"Connessione: {status_message}")

def log_debug(debug_message: str):
    logger.debug(f"DEBUG: {debug_message}")

def log_warning(warning_message: str):
    logger.warning(f"AVVISO: {warning_message}")

def log_critical(critical_message: str):
    logger.critical(f"CRITICO: {critical_message}")
