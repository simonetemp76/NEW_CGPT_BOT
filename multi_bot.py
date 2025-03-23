#!/usr/bin/env python3
"""
multi_bot.py

Gestisce l'avvio di più bot per coppie di trading.
Utilizza il bot_registry per registrare i bot e avvia thread separati.
"""

import threading
from binance.client import Client
from single_bot import SingleBot
from wallet import schedule_wallet_updates, send_wallet_update
import binance_websocket
from telegram_notifications import notify_trade, notify_startup
from config import USE_TESTNET, API_KEY, API_SECRET, BOT_SETTINGS, CYCLE_INTERVAL
import symbols_config
from performance_monitor import schedule_performance_report
from telegram_bot import main as run_telegram_bot
from config_manager import initialize_symbols_config
from bot_registry import register_bot, unregister_bot, active_bots
from error_handler import retry_on_failure
import time

report_thread = threading.Thread(target=schedule_performance_report, name="Performance_Report", daemon=True)
report_thread.start()
print("[multi_bot] Report thread avviato.")

def start_wallet_updates():
    send_wallet_update()
    schedule_wallet_updates()

def start_bot_for_pair(sym: str):
    from bot_registry import is_bot_registered
    if is_bot_registered(sym):
        print(f"[multi_bot] Bot per {sym} già in esecuzione.")
        return
    settings = BOT_SETTINGS.get(sym, {})
    timeframe = settings.get("timeframe", "4h")
    cycle_interval = settings.get("cycle_interval", CYCLE_INTERVAL)
    print(f"[multi_bot] Avvio bot per {sym}: timeframe={timeframe}, cycle_interval={cycle_interval}")
    bot = SingleBot(symbol=sym, interval=timeframe, cycle_interval=cycle_interval, use_testnet=USE_TESTNET, api_key=API_KEY, api_secret=API_SECRET)
    register_bot(sym, bot)
    t = threading.Thread(target=bot.run, name=f"Thread_{sym}", daemon=True)
    t.start()
    print(f"[multi_bot] Bot per {sym} avviato nel thread {t.name}.")

def stop_bot_for_pair(sym: str):
    from bot_registry import is_bot_registered
    if not is_bot_registered(sym):
        print(f"[multi_bot] Nessun bot attivo per {sym}.")
        return
    bot = active_bots.get(sym)
    print(f"[multi_bot] Fermo bot per {sym}...")
    bot.stop()
    if hasattr(bot, "terminate"):
        bot.terminate()
    unregister_bot(sym)
    print(f"[multi_bot] Bot per {sym} fermato.")

def main():
    initialize_symbols_config()
    import importlib
    importlib.reload(symbols_config)
    startup_symbols = symbols_config.SYMBOLS
    notify_startup(startup_symbols)
    print("[multi_bot] Avvio multi-bot con WebSocket condiviso...")
    wallet_thread = threading.Thread(target=start_wallet_updates, name="Wallet_Updates", daemon=True)
    wallet_thread.start()
    print("[multi_bot] Wallet update thread avviato.")
    websocket_thread = threading.Thread(target=binance_websocket.start_websocket, name="WebSocket", daemon=True)
    websocket_thread.start()
    print("[multi_bot] WebSocket thread avviato.")
    for sym in startup_symbols:
        print(f"[multi_bot] Avvio bot per {sym}...")
        start_bot_for_pair(sym)
    run_telegram_bot()

if __name__ == "__main__":
    main()
