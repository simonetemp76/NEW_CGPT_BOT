#!/usr/bin/env python3
"""
performance_monitor.py

Gestione delle performance:
- Aggiornamento e salvataggio dei log di performance.
- Generazione di report giornalieri e settimanali.
"""

import time
import schedule
import threading
import datetime
import json
import os
from telegram_notifications import send_telegram_message
from logging_system import log_trade_event, log_error
from config import TELEGRAM_BOT_TOKEN, API_KEY, API_SECRET, USE_TESTNET
from binance.client import Client

client = Client(API_KEY, API_SECRET, testnet=USE_TESTNET)

performance_data = {
    "total_trades": 0,
    "total_profit": 0.0,
    "total_profit_usdc": 0.0,
    "buy_trades": 0,
    "sell_trades": 0,
    "symbol_profit": {},
    "symbol_profit_usdc": {},
    "alerts": []
}

def save_performance_log(report_type, report_message, data, filename="performance_log.json"):
    entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "report_type": report_type,
        "report_message": report_message,
        "performance_data": data
    }
    try:
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                log_entries = json.load(f)
        else:
            log_entries = []
    except Exception:
        log_entries = []
    log_entries.append(entry)
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(log_entries, f, indent=4, ensure_ascii=False)
        print(f"[performance_monitor] Log salvato in {filename}.")
    except Exception as e:
        log_error(f"Errore salvataggio log: {e}")

def update_trade(trade_type, symbol, qty, profit):
    """
    Aggiorna le performance del bot.
    :param trade_type: "BUY" o "SELL"
    :param symbol: Simbolo di trading.
    :param qty: Quantità scambiata.
    :param profit: Profitto calcolato.
    """
    try:
        performance_data["total_trades"] += 1
        performance_data["total_profit"] += profit
        performance_data["total_profit_usdc"] += profit
        if trade_type.upper() == "BUY":
            performance_data["buy_trades"] += 1
        elif trade_type.upper() == "SELL":
            performance_data["sell_trades"] += 1
        if symbol not in performance_data["symbol_profit"]:
            performance_data["symbol_profit"][symbol] = 0.0
            performance_data["symbol_profit_usdc"][symbol] = 0.0
        performance_data["symbol_profit"][symbol] += profit
        performance_data["symbol_profit_usdc"][symbol] += profit
        log_trade_event(trade_type, symbol, qty, 0, profit)
    except Exception as e:
        log_error(f"Errore aggiornamento performance: {e}")

def reset_performance_data():
    performance_data["total_trades"] = 0
    performance_data["total_profit"] = 0.0
    performance_data["total_profit_usdc"] = 0.0
    performance_data["buy_trades"] = 0
    performance_data["sell_trades"] = 0
    performance_data["symbol_profit"] = {}
    performance_data["symbol_profit_usdc"] = {}

def generate_daily_report():
    try:
        report_message = "📈 **Report Performance Giornaliero** 📈\n"
        report_message += f"📅 Data: {time.strftime('%Y-%m-%d')}\n"
        report_message += "--------------------------------------\n"
        report_message += f"Totale operazioni: {performance_data['total_trades']}\n"
        report_message += f"BUY: {performance_data['buy_trades']}\n"
        report_message += f"SELL: {performance_data['sell_trades']}\n"
        report_message += f"Profitto Totale: {performance_data['total_profit']:.2f}% / {performance_data['total_profit_usdc']:.2f}\n"
        report_message += "Profitto per simbolo:\n"
        for sym, prof in performance_data["symbol_profit"].items():
            prof_usdc = performance_data["symbol_profit_usdc"].get(sym, 0.0)
            report_message += f"{sym}: {prof:.2f}% / {prof_usdc:.2f}\n"
        send_telegram_message(report_message)
        log_trade_event("DAILY_REPORT", "ALL", 0, 0, performance_data["total_profit"])
        save_performance_log("daily", report_message, performance_data)
        reset_performance_data()
    except Exception as e:
        log_error(f"Errore report giornaliero: {e}")

def generate_weekly_report():
    try:
        report_message = "📈 **Report Performance Settimanale** 📈\n"
        report_message += f"Settimana di: {time.strftime('%Y-%m-%d')}\n"
        report_message += "--------------------------------------\n"
        report_message += f"Totale operazioni: {performance_data['total_trades']}\n"
        report_message += f"BUY: {performance_data['buy_trades']}\n"
        report_message += f"SELL: {performance_data['sell_trades']}\n"
        report_message += f"Profitto Totale: {performance_data['total_profit']:.2f}% / {performance_data['total_profit_usdc']:.2f}\n"
        report_message += "Profitto per simbolo:\n"
        for sym, prof in performance_data["symbol_profit"].items():
            prof_usdc = performance_data["symbol_profit_usdc"].get(sym, 0.0)
            report_message += f"{sym}: {prof:.2f}% / {prof_usdc:.2f}\n"
        send_telegram_message(report_message)
        log_trade_event("WEEKLY_REPORT", "ALL", 0, 0, performance_data["total_profit"])
        save_performance_log("weekly", report_message, performance_data)
    except Exception as e:
        log_error(f"Errore report settimanale: {e}")

def schedule_performance_report():
    schedule.every().day.at("18:00").do(generate_daily_report)
    schedule.every().monday.at("10:00").do(generate_weekly_report)
    while True:
        schedule.run_pending()
        time.sleep(60)

async def get_performance_for_symbol(symbol: str) -> str:
    if symbol in performance_data["symbol_profit"]:
        profit = performance_data["symbol_profit"][symbol]
        profit_usdc = performance_data["symbol_profit_usdc"][symbol]
        return f"Profitto: {profit:.2f}% / {profit_usdc:.2f}"
    return "Nessuna performance registrata."

if __name__ == "__main__":
    threading.Thread(target=schedule_performance_report, daemon=True).start()
    while True:
        time.sleep(60)
