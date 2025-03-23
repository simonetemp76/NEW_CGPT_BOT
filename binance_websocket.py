#!/usr/bin/env python3
"""
binance_websocket.py

Gestisce la connessione WebSocket a Binance per dati di mercato e ordini.
"""

import asyncio
import json
import ssl
import certifi
import websockets
import logging
from config import API_KEY, API_SECRET, USE_TESTNET
from binance.client import Client
from telegram_notifications import send_telegram_message
import symbols_config
from logging_system import log_order_event, log_websocket_event, log_error

telegram_message_sent = False
client = Client(API_KEY, API_SECRET, testnet=USE_TESTNET)
latest_prices = {}
current_symbols = symbols_config.SYMBOLS.copy()
logging.basicConfig(level=logging.INFO)

def get_latest_price(symbol):
    return latest_prices.get(symbol.upper(), None)

async def process_websocket_data(data):
    if "s" in data and "c" in data:
        symbol = data["s"]
        import importlib
        importlib.reload(symbols_config)
        if symbol not in symbols_config.SYMBOLS:
            return
        price = float(data["c"])
        if latest_prices.get(symbol) == price:
            return
        latest_prices[symbol] = price
        log_websocket_event(f"[{symbol}] Prezzo aggiornato: {price}")

async def process_data_with_retry(data, max_retries=3, delay=2):
    for attempt in range(1, max_retries + 1):
        try:
            await process_websocket_data(data)
            return
        except Exception as e:
            log_error(f"Errore nel processamento (tentativo {attempt}/{max_retries}): {e}")
            if attempt == max_retries:
                send_telegram_message(f"Errore nel recupero del prezzo dopo {max_retries} tentativi.")
            await asyncio.sleep(delay)

async def subscribe_new_symbols(websocket, new_symbols):
    subscribe_message = {
        "method": "SUBSCRIBE",
        "params": [f"{symbol.lower()}@ticker" for symbol in new_symbols],
        "id": 100
    }
    await websocket.send(json.dumps(subscribe_message))
    log_websocket_event(f"Sottoscrizione aggiuntiva per: {new_symbols}")

async def unsubscribe_symbols(websocket, symbols_to_unsubscribe):
    unsubscribe_message = {
        "method": "UNSUBSCRIBE",
        "params": [f"{symbol.lower()}@ticker" for symbol in symbols_to_unsubscribe],
        "id": 200
    }
    await websocket.send(json.dumps(unsubscribe_message))
    log_websocket_event(f"Richiesta UNSUBSCRIBE per: {symbols_to_unsubscribe}")

async def connect_to_binance():
    global current_symbols, telegram_message_sent
    uri = "wss://stream.binance.com:9443/ws"
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.load_verify_locations(certifi.where())
    while True:
        try:
            import importlib
            importlib.reload(symbols_config)
            current_symbols = symbols_config.SYMBOLS.copy()
            streams = "/".join([f"{symbol.lower()}@ticker" for symbol in current_symbols])
            full_uri = f"{uri}/{streams}"
            async with websockets.connect(full_uri, ssl=ssl_context) as websocket:
                log_websocket_event("Connessione WebSocket Binance stabilita.")
                subscribe_message = {
                    "method": "SUBSCRIBE",
                    "params": [f"{symbol.lower()}@ticker" for symbol in current_symbols],
                    "id": 1
                }
                await websocket.send(json.dumps(subscribe_message))
                log_websocket_event("Sottoscrizione ai dati di mercato inviata.")
                if not telegram_message_sent:
                    send_telegram_message("WebSocket Binance avviato. Monitoraggio in corso...")
                    telegram_message_sent = True
                while True:
                    import importlib
                    importlib.reload(symbols_config)
                    new_symbols_list = symbols_config.SYMBOLS.copy()
                    new_set = set(new_symbols_list)
                    current_set = set(current_symbols)
                    new_symbols = list(new_set - current_set)
                    if new_symbols:
                        await subscribe_new_symbols(websocket, new_symbols)
                    removed_symbols = list(current_set - new_set)
                    if removed_symbols:
                        await unsubscribe_symbols(websocket, removed_symbols)
                    current_symbols = new_symbols_list
                    response = await websocket.recv()
                    data = json.loads(response)
                    await process_data_with_retry(data)
        except websockets.exceptions.ConnectionClosed:
            log_error("Connessione WebSocket chiusa. Riconnessione...")
        except Exception as e:
            log_error(f"Errore WebSocket: {e}")
        await asyncio.sleep(5)

async def listen_to_orders():
    listen_key = client.stream_get_listen_key()
    uri = f"wss://stream.binance.com:9443/ws/{listen_key}"
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.load_verify_locations(certifi.where())
    while True:
        try:
            async with websockets.connect(uri, ssl=ssl_context) as websocket:
                log_websocket_event("Connessione WebSocket per ordini stabilita.")
                while True:
                    response = await websocket.recv()
                    data = json.loads(response)
                    if data.get("e") == "executionReport":
                        symbol = data["s"]
                        side = data["S"]
                        status = data["X"]
                        quantity = data["q"]
                        price = data["p"]
                        if status == "FILLED":
                            message = f"{side} {symbol} COMPLETATO! Quantità: {quantity}, Prezzo: {price}"
                            send_telegram_message(message)
                            log_order_event(side, symbol, quantity, price, status)
        except websockets.exceptions.ConnectionClosed:
            log_error("WebSocket ordini chiuso. Riconnessione...")
        except Exception as e:
            log_error(f"Errore WebSocket ordini: {e}")
        await asyncio.sleep(5)

def start_websocket():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    asyncio.gather(connect_to_binance(), listen_to_orders())
    loop.run_forever()

if __name__ == "__main__":
    start_websocket()
