#!/usr/bin/env python3
"""
backtesting_engine.py

Modulo per eseguire il backtest della strategia.
Recupera dati storici, calcola indicatori e simula trade.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pandas_ta as ta
from datetime import datetime, timedelta
from binance.client import Client
import symbols_config
from strategy_params import INTERVAL, LOOKBACK_DAYS, LC_RSI_NPERIODI, LC_RSI_MA_NPERIODI, FAST_LENGTH, SLOW_LENGTH, SIGNAL_LENGTH, LC_TIPO_MA, LC_MA1_NPERIODI, LC_MA2_NPERIODI, LC_MA3_NPERIODI, LC_MA4_NPERIODI, MA_TYPE_INPUT, MA_LENGTH_INPUT, BB_MULT_INPUT
from config import COMMISSION_RATE, SLIPPAGE_RATE, INITIAL_CAPITAL, BOT_SETTINGS
from telegram_notifications import send_telegram_message

def get_historical_data(symbol, interval, lookback_days):
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=lookback_days)
    start_str = start_time.strftime("%d %b %Y")
    print(f"Scaricando dati per {symbol} dal {start_str}...")
    client = Client("", "", testnet=True)
    klines = client.get_historical_klines(symbol, interval, start_str)
    if not klines:
        return pd.DataFrame()
    df = pd.DataFrame(klines, columns=[
        "Open Time", "Open", "High", "Low", "Close", "Volume",
        "Close Time", "Quote Asset Volume", "Number of Trades",
        "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume", "Ignore"
    ])
    df["Open Time"] = pd.to_datetime(df["Open Time"], unit='ms')
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df.set_index("Open Time", inplace=True)
    df = df[["Open", "High", "Low", "Close", "Volume"]]
    return df

def compute_indicators(data):
    data["OBV"] = ta.obv(data["Close"], data["Volume"])
    data["RSI"] = ta.rsi(data["Close"], length=LC_RSI_NPERIODI)
    data["RSI_MA"] = ta.ema(data["RSI"], length=LC_RSI_MA_NPERIODI)
    macd = ta.macd(data["Close"], fast=FAST_LENGTH, slow=SLOW_LENGTH, signal=SIGNAL_LENGTH)
    data = data.join(macd)
    data.rename(columns={
        f"MACD_{FAST_LENGTH}_{SLOW_LENGTH}_{SIGNAL_LENGTH}": "MACD",
        f"MACDs_{FAST_LENGTH}_{SLOW_LENGTH}_{SIGNAL_LENGTH}": "MACD_signal",
        f"MACDh_{FAST_LENGTH}_{SLOW_LENGTH}_{SIGNAL_LENGTH}": "MACD_hist"
    }, inplace=True)
    if LC_TIPO_MA == "EMA":
        data["lcMa1"] = ta.ema(data["Close"], length=LC_MA1_NPERIODI)
        data["lcMa2"] = ta.ema(data["Close"], length=LC_MA2_NPERIODI)
        data["lcMa3"] = ta.ema(data["Close"], length=LC_MA3_NPERIODI)
        data["lcMa4"] = ta.ema(data["Close"], length=LC_MA4_NPERIODI)
    elif LC_TIPO_MA == "SMA":
        data["lcMa1"] = ta.sma(data["Close"], length=LC_MA1_NPERIODI)
        data["lcMa2"] = ta.sma(data["Close"], length=LC_MA2_NPERIODI)
        data["lcMa3"] = ta.sma(data["Close"], length=LC_MA3_NPERIODI)
        data["lcMa4"] = ta.sma(data["Close"], length=LC_MA4_NPERIODI)
    elif LC_TIPO_MA == "WMA":
        data["lcMa1"] = ta.wma(data["Close"], length=LC_MA1_NPERIODI)
        data["lcMa2"] = ta.wma(data["Close"], length=LC_MA2_NPERIODI)
        data["lcMa3"] = ta.wma(data["Close"], length=LC_MA3_NPERIODI)
        data["lcMa4"] = ta.wma(data["Close"], length=LC_MA4_NPERIODI)
    if MA_TYPE_INPUT in ["SMA", "SMA + Bollinger Bands"]:
        data["smoothingMA"] = data["OBV"].rolling(window=MA_LENGTH_INPUT).mean()
    elif MA_TYPE_INPUT == "EMA":
        data["smoothingMA"] = ta.ema(data["OBV"], length=MA_LENGTH_INPUT)
    if MA_TYPE_INPUT == "SMA + Bollinger Bands":
        data["smoothingStDev"] = data["OBV"].rolling(window=MA_LENGTH_INPUT).std() * BB_MULT_INPUT
        data["upperBand"] = data["smoothingMA"] + data["smoothingStDev"]
        data["lowerBand"] = data["smoothingMA"] - data["smoothingStDev"]
    return data

def simulate_strategy(data):
    trades = []
    ordine_aperto = False
    prezzo_apertura = 0.0
    profitto_totale = 0.0

    def is_crossover(s1, s2, i):
        return (s1.iloc[i-1] < s2.iloc[i-1]) and (s1.iloc[i] >= s2.iloc[i])
    def is_crossunder(s1, s2, i):
        return (s1.iloc[i-1] > s2.iloc[i-1]) and (s1.iloc[i] <= s2.iloc[i])
    
    for i in range(1, len(data)):
        row = data.iloc[i]
        if not ordine_aperto:
            if is_crossover(data["RSI"], data["RSI_MA"], i) and (not np.isnan(data["lowerBand"].iloc[i-1]) and is_crossover(data["OBV"], data["lowerBand"], i)):
                ordine_aperto = True
                prezzo_apertura = row["Close"]
                trades.append({"Entry Time": data.index[i], "Entry Price": prezzo_apertura})
        else:
            profit = (row["Close"] - prezzo_apertura) / prezzo_apertura * 100
            exit_signal = False
            if row["Close"] < row["lcMa1"]:
                exit_signal = True
            if (not np.isnan(data["upperBand"].iloc[i-1])) and is_crossunder(data["OBV"], data["upperBand"], i):
                exit_signal = True
            if exit_signal:
                trades[-1].update({"Exit Time": data.index[i], "Exit Price": row["Close"], "Profit %": profit})
                profitto_totale += profit
                ordine_aperto = False
    print(f"Profitto totale strategia: {profitto_totale:.2f}%")
    return trades

def analyze_and_plot(symbol, data, trades):
    plt.figure(figsize=(14, 10))
    plt.subplot(4,1,1)
    plt.plot(data.index, data["Close"], label="Close Price")
    plt.title(f"{symbol} - Prezzo di Chiusura")
    plt.legend()
    plt.subplot(4,1,2)
    plt.plot(data.index, data["RSI"], label="RSI", color="purple")
    plt.plot(data.index, data["RSI_MA"], label="RSI MA", color="yellow")
    plt.axhline(70, color="red", linestyle="--", label="Overbought")
    plt.axhline(30, color="green", linestyle="--", label="Oversold")
    plt.title(f"{symbol} - RSI")
    plt.legend()
    plt.subplot(4,1,3)
    plt.plot(data.index, data["MACD"], label="MACD", color="blue")
    plt.plot(data.index, data["MACD_signal"], label="Signal", color="red")
    plt.bar(data.index, data["MACD_hist"], label="Histogram", color="grey")
    plt.axhline(0, color="black", linestyle="--")
    plt.title(f"{symbol} - MACD")
    plt.legend()
    plt.subplot(4,1,4)
    plt.plot(data.index, data["OBV"], label="OBV", color="teal")
    if not data["upperBand"].isnull().all():
        plt.plot(data.index, data["smoothingMA"], label="Smoothing MA", color="orange")
        plt.plot(data.index, data["upperBand"], label="Upper Band", color="green")
        plt.plot(data.index, data["lowerBand"], label="Lower Band", color="red")
    plt.title(f"{symbol} - OBV e Bollinger Bands")
    plt.legend()
    plt.tight_layout()
    plt.show()

class Backtester:
    def __init__(self, symbol=None, interval=None, lookback=5000):
        self.symbol = symbol if symbol is not None else symbols_config.SYMBOLS[0]
        self.interval = interval if interval is not None else INTERVAL
        self.lookback = lookback

    def run_backtest(self):
        print(f"Eseguo backtest per {self.symbol} su intervallo {self.interval}...")
        df = get_historical_data(self.symbol, self.interval, LOOKBACK_DAYS)
        if df.empty:
            print("Nessun dato storico disponibile.")
            return None
        df = compute_indicators(df)
        trades = simulate_strategy(df)
        analyze_and_plot(self.symbol, df, trades)
        return trades

if __name__ == "__main__":
    bt = Backtester()
    bt.run_backtest()
