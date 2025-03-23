#!/usr/bin/env python3
"""
wallet.py

Modulo per il recupero e l'aggiornamento del saldo del wallet Binance.
"""
import time
import schedule
from binance.client import Client
from config import API_KEY, API_SECRET, USE_TESTNET, INTERVAL, CYCLE_INTERVAL, BOT_SETTINGS
from telegram_notifications import send_telegram_message
import logging_system
import importlib
import symbols_config
from symbols_config import SYMBOLS
from performance_monitor import update_trade
from money_management import get_base_asset, get_quote_asset

client = Client(API_KEY, API_SECRET, testnet=USE_TESTNET)

def get_wallet_balance():
    try:
        print("🔍 Recupero bilancio del wallet da Binance...")
        account = client.get_account()
        balances = account["balances"]
        importlib.reload(symbols_config)
        current_symbols = symbols_config.SYMBOLS
        wallet_info = "📊 **Situazione Wallet Binance** 📊\n"
        wallet_info += "----------------------------------\n"
        assets_to_monitor = {"BTC", "USDC"}
        for sym in current_symbols:
            base_asset = get_base_asset(sym)
            quote_asset = get_quote_asset(sym)
            assets_to_monitor.add(base_asset)
            assets_to_monitor.add(quote_asset)
        has_assets = False
        for balance in balances:
            asset = balance["asset"]
            free = float(balance["free"])
            locked = float(balance["locked"])
            if asset in assets_to_monitor and (free > 0 or locked > 0):
                wallet_info += f"🔹 {asset}: Free = {free}, Locked = {locked}\n"
                has_assets = True
        if not has_assets:
            wallet_info += "🚨 Nessun asset disponibile nel wallet!\n"
        wallet_info += "----------------------------------"
        print(wallet_info)
        return wallet_info
    except Exception as e:
        error_message = f"❌ Errore nel recupero del wallet: {e}"
        print(error_message)
        logging_system.log_wallet_event(error_message)
        return error_message

def display_wallet():
    wallet_info = get_wallet_balance()
    print(wallet_info)
    logging_system.log_wallet_event(wallet_info)

def send_wallet_update():
    print("📢 Inviando aggiornamento wallet...")
    wallet_info = get_wallet_balance()
    logging_system.log_wallet_event(wallet_info)
    send_telegram_message(wallet_info)
    print("✅ Wallet aggiornato e inviato su Telegram.")

def update_wallet_after_trade(trade_type, profit, symbol, qty):
    print(f"🔄 Controllo saldo wallet dopo {trade_type} trade...")
    send_wallet_update()
    update_trade(trade_type, symbol, qty, profit)

def schedule_wallet_updates():
    print("⏳ Pianificazione aggiornamenti wallet alle 08:00 e 22:00...")
    schedule.every().day.at("08:00").do(send_wallet_update)
    schedule.every().day.at("22:00").do(send_wallet_update)
    while True:
        schedule.run_pending()
        print(f"Prossimo aggiornamento wallet: {schedule.next_run()}")
        time.sleep(60)

if __name__ == "__main__":
    schedule_wallet_updates()
