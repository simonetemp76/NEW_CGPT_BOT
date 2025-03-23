# bot_registry.py

from threading import Lock

active_bots = {}
active_bots_lock = Lock()

def register_bot(symbol: str, bot_instance):
    with active_bots_lock:
        if symbol in active_bots:
            print(f"[BotRegistry] Attenzione: bot per {symbol} già registrato.")
        active_bots[symbol] = bot_instance
        print(f"[BotRegistry] Bot per {symbol} registrato.")

def unregister_bot(symbol: str):
    with active_bots_lock:
        if symbol in active_bots:
            del active_bots[symbol]
            print(f"[BotRegistry] Bot per {symbol} rimosso.")
        else:
            print(f"[BotRegistry] Nessun bot per {symbol} da rimuovere.")

def get_bot(symbol: str):
    with active_bots_lock:
        return active_bots.get(symbol)

def is_bot_registered(symbol: str):
    with active_bots_lock:
        return symbol in active_bots

def list_registered_bots():
    with active_bots_lock:
        return list(active_bots.keys())
