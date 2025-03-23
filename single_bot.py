#!/usr/bin/env python3
"""
single_bot.py

Modulo che definisce la classe SingleBot.
- Recupera dati storici e calcola indicatori tramite data_utils.
- Esegue backtesting (se disponibile).
- Gestisce trading, aggiornamento wallet e notifiche Telegram.
- Integra il plugin ML per migliorare l’analisi dei segnali.
"""

import re
import time
import pandas as pd
import numpy as np
from binance.client import Client
from config import API_KEY, API_SECRET, USE_TESTNET, INTERVAL, CYCLE_INTERVAL, BOT_SETTINGS
from money_management import calculate_trade_quantity, get_quote_asset, get_base_asset, round_step_size, format_quantity
from wallet import display_wallet
from telegram_notifications import notify_trade
from binance_websocket import get_latest_price
from logging_system import log_trade_event, log_error
from error_handler import retry_on_failure
from ml_strategy import MLStrategy
import symbols_config  # Deve contenere SYMBOLS = ["BTCUSDT", "ETHUSDT", ...]
from decimal import Decimal, ROUND_DOWN
from config_manager import load_config_for_pair
from data_utils import get_historical_data, compute_indicators
from bot_registry import register_bot

def clean_symbol(symbol: str) -> str:
    return re.sub(r'[^A-Z0-9-_.]', '', symbol.upper())

def indicator_signal(data, position_open):
    """
    Restituisce "buy", "sell" o "hold" basato sui crossover tra indicatori.
    """
    if len(data) < 2:
        return "hold"
    i = len(data) - 1
    if not position_open:
        entry_condition = (
            data["RSI"].iloc[i-1] < data["RSI_MA"].iloc[i-1] and
            data["RSI"].iloc[i] >= data["RSI_MA"].iloc[i] and
            (not np.isnan(data["lowerBand"].iloc[i-1])) and 
            data["OBV"].iloc[i-1] < data["lowerBand"].iloc[i-1] and 
            data["OBV"].iloc[i] >= data["lowerBand"].iloc[i]
        )
        return "buy" if entry_condition else "hold"
    else:
        exit_condition = (
            data["Close"].iloc[i] < data["lcMa1"].iloc[i] or 
            ((not np.isnan(data["upperBand"].iloc[i-1])) and 
             data["OBV"].iloc[i-1] > data["upperBand"].iloc[i-1] and 
             data["OBV"].iloc[i] <= data["upperBand"].iloc[i])
        )
        return "sell" if exit_condition else "hold"

# Inizializza plugin ML
try:
    ml_plugin = MLStrategy()
except Exception as e:
    ml_plugin = None
    print(f"[single_bot] ⚠️ Plugin ML non disponibile: {e}")

# Backtesting (se disponibile)
try:
    from backtesting_engine import run_backtest
    print("[single_bot] ✅ Backtesting caricato con successo.")
except Exception as e:
    print(f"[single_bot] ⚠️ Backtesting non disponibile: {e}")
    run_backtest = None

class SingleBot:
    def __init__(self, symbol=None, interval=INTERVAL, cycle_interval=CYCLE_INTERVAL,
                 use_testnet=True, api_key=API_KEY, api_secret=API_SECRET):
        self.symbol = clean_symbol(symbol if symbol is not None else symbols_config.SYMBOLS[0])
        self.interval = interval
        self.cycle_interval = cycle_interval
        self.use_testnet = use_testnet
        self.api_key = api_key
        self.api_secret = api_secret
        self.ml_plugin = ml_plugin
        self.buy_price = None
        self.qty = None
        self.active = True
        self.running = True
        self.start_time = time.time()
        self.client = Client(api_key, api_secret, testnet=use_testnet)
        self.bot_settings = BOT_SETTINGS.copy()

        # Esegui backtest iniziale se ML plugin è disponibile
        if run_backtest and self.ml_plugin:
            print(f"[{self.symbol}] 🔍 Esecuzione del backtest per ottimizzazione ML...")
            backtest_results = run_backtest(self.symbol, self.interval, self.ml_plugin)
            print(f"[{self.symbol}] 📊 Risultati backtest: {backtest_results}")

        self.indicator_params = {
            "LC_RSI_NPERIODI": 11,
            "LC_RSI_MA_NPERIODI": 9,
            "FAST_LENGTH": 12,
            "SLOW_LENGTH": 26,
            "SIGNAL_LENGTH": 18,
            "LC_TIPO_MA": "WMA",
            "LC_MA1_NPERIODI": 5,
            "LC_MA2_NPERIODI": 10,
            "LC_MA3_NPERIODI": 60,
            "LC_MA4_NPERIODI": 223,
            "MA_TYPE_INPUT": "SMA + Bollinger Bands",
            "MA_LENGTH_INPUT": 23,
            "BB_MULT_INPUT": 3.4
        }
        # Registra il bot in maniera thread-safe
        register_bot(self.symbol, self)

    def stop(self):
        self.active = False
        print(f"[{self.symbol}] Bot in pausa.")

    def start(self):
        self.active = True
        print(f"[{self.symbol}] Bot riattivato.")

    def terminate(self):
        self.running = False
        self.active = False
        print(f"[{self.symbol}] Bot terminato.")

    def get_latest_data(self):
        max_attempts = 10 if (time.time() - self.start_time) < 20 else 5
        attempt = 0
        price = None
        while attempt < max_attempts:
            price = retry_on_failure(lambda: get_latest_price(self.symbol))
            if price:
                break
            attempt += 1
            log_error(f"[{self.symbol}] Nessun prezzo ricevuto, tentativo {attempt}/{max_attempts}")
            time.sleep(3)
        if not price:
            log_error(f"[{self.symbol}] Errore nel recupero del prezzo dopo {max_attempts} tentativi.")
            return None

        df = retry_on_failure(lambda: get_historical_data(self.client, self.symbol, self.interval))
        if df is None or df.empty:
            log_error(f"[{self.symbol}] Nessun dato storico ricevuto.")
            return None

        return compute_indicators(df, self.indicator_params)

    def run(self):
        print(f"[{self.symbol}] Bot avviato con ciclo ogni {self.cycle_interval}s.")
        while self.running:
            if not self.active:
                print(f"[{self.symbol}] Bot in pausa, attendo...")
                time.sleep(self.cycle_interval)
                continue

            try:
                new_config = retry_on_failure(lambda: load_config_for_pair(self.symbol))
                if new_config:
                    self.interval = new_config.get("INTERVAL", self.interval)
                    self.cycle_interval = new_config.get("CYCLE_INTERVAL", self.cycle_interval)
                    self.bot_settings = new_config.get("BOT_SETTINGS", self.bot_settings)
                    self.indicator_params = new_config.get("INDICATOR_PARAMS", self.indicator_params)
            except Exception as e:
                log_error(f"[{self.symbol}] Errore nel caricamento della configurazione: {e}")

            df = self.get_latest_data()
            if df is None or df.empty:
                log_error(f"[{self.symbol}] Nessun dato aggiornato, salto ciclo.")
                time.sleep(self.cycle_interval)
                continue

            price = df["Close"].iloc[-1]
            signal = indicator_signal(df, self.buy_price is not None)
            print(f"[{self.symbol}] Segnale: {signal} | Prezzo: {price}")

            # Integrazione ML: analizza il segnale base e aggiorna se il modello fornisce una previsione forte
            if self.ml_plugin:
                try:
                    ml_signal, confidence = self.ml_plugin.analyze(df, signal, price)
                    print(f"[{self.symbol}] ML: {ml_signal} (Confidenza: {confidence})")
                    if ml_signal != signal and confidence > 0.75:
                        signal = ml_signal
                except Exception as e:
                    log_error(f"[{self.symbol}] Errore nell'analisi ML: {e}")

            # Logica di trading (esempio semplificato)
            if signal == "buy" and self.buy_price is None:
                qty = calculate_trade_quantity(self.client, self.symbol, price)
                order = retry_on_failure(lambda: self.client.create_order(
                    symbol=self.symbol,
                    side="BUY",
                    type="MARKET",
                    quantity=format_quantity(qty)
                ))
                if order:
                    self.buy_price = price
                    self.qty = qty
                    notify_trade("BUY", self.symbol, qty, price)
                    log_trade_event("BUY", self.symbol, qty, price, profit=0)
            elif signal == "sell" and self.buy_price is not None:
                qty = self.qty
                order = retry_on_failure(lambda: self.client.create_order(
                    symbol=self.symbol,
                    side="SELL",
                    type="MARKET",
                    quantity=format_quantity(qty)
                ))
                if order:
                    profit = ((price - self.buy_price) / self.buy_price) * 100
                    notify_trade("SELL", self.symbol, qty, price, profit=profit)
                    log_trade_event("SELL", self.symbol, qty, price, profit=profit)
                    self.buy_price = None
                    self.qty = None
            time.sleep(self.cycle_interval)
            
if __name__ == "__main__":
    bot = SingleBot()
    bot.run()
