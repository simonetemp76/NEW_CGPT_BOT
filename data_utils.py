#!/usr/bin/env python3
"""
data_utils.py

Funzioni per:
- Recupero dati storici da Binance.
- Calcolo degli indicatori tecnici.
"""

import pandas as pd
import numpy as np
np.NaN = np.nan
import pandas_ta as ta
from datetime import datetime, timedelta

def get_historical_data(client, symbol, interval, lookback_days=90):
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=lookback_days)
    start_str = start_time.strftime("%d %b %Y")
    print(f"Scaricando dati per {symbol} dal {start_str}...")
    klines = client.get_historical_klines(symbol, interval, start_str)
    if not klines:
        return pd.DataFrame()
    df = pd.DataFrame(klines, columns=[
        "Open Time", "Open", "High", "Low", "Close", "Volume",
        "Close Time", "Quote Asset Volume", "Number of Trades",
        "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume", "Ignore"
    ])
    df["Open Time"] = pd.to_datetime(df["Open Time"], unit='ms')
    df["Close Time"] = pd.to_datetime(df["Close Time"], unit='ms')
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df.set_index("Open Time", inplace=True)
    df = df[["Open", "High", "Low", "Close", "Volume"]]
    return df

def compute_indicators(data, params):
    data["OBV"] = ta.obv(data["Close"], data["Volume"])
    try:
        print("[data_utils] Calcolo OBV_MA...")
        data["OBV_MA"] = ta.ema(data["OBV"], length=9).fillna(0)
    except Exception as e:
        print(f"[data_utils] Errore OBV_MA: {e}")
        data["OBV_MA"] = 0
    data["RSI"] = ta.rsi(data["Close"], length=params["LC_RSI_NPERIODI"])
    data["RSI_MA"] = ta.ema(data["RSI"], length=params["LC_RSI_MA_NPERIODI"])
    macd = ta.macd(data["Close"],
                   fast=params["FAST_LENGTH"],
                   slow=params["SLOW_LENGTH"],
                   signal=params["SIGNAL_LENGTH"])
    data = data.join(macd)
    data.rename(columns={
        f"MACD_{params['FAST_LENGTH']}_{params['SLOW_LENGTH']}_{params['SIGNAL_LENGTH']}": "MACD",
        f"MACDs_{params['FAST_LENGTH']}_{params['SLOW_LENGTH']}_{params['SIGNAL_LENGTH']}": "MACD_signal",
        f"MACDh_{params['FAST_LENGTH']}_{params['SLOW_LENGTH']}_{params['SIGNAL_LENGTH']}": "MACD_hist"
    }, inplace=True)
    if params["LC_TIPO_MA"] == "EMA":
        data["lcMa1"] = ta.ema(data["Close"], length=params["LC_MA1_NPERIODI"])
        data["lcMa2"] = ta.ema(data["Close"], length=params["LC_MA2_NPERIODI"])
        data["lcMa3"] = ta.ema(data["Close"], length=params["LC_MA3_NPERIODI"])
        data["lcMa4"] = ta.ema(data["Close"], length=params["LC_MA4_NPERIODI"])
    elif params["LC_TIPO_MA"] == "SMA":
        data["lcMa1"] = ta.sma(data["Close"], length=params["LC_MA1_NPERIODI"])
        data["lcMa2"] = ta.sma(data["Close"], length=params["LC_MA2_NPERIODI"])
        data["lcMa3"] = ta.sma(data["Close"], length=params["LC_MA3_NPERIODI"])
        data["lcMa4"] = ta.sma(data["Close"], length=params["LC_MA4_NPERIODI"])
    elif params["LC_TIPO_MA"] == "WMA":
        data["lcMa1"] = ta.wma(data["Close"], length=params["LC_MA1_NPERIODI"])
        data["lcMa2"] = ta.wma(data["Close"], length=params["LC_MA2_NPERIODI"])
        data["lcMa3"] = ta.wma(data["Close"], length=params["LC_MA3_NPERIODI"])
        data["lcMa4"] = ta.wma(data["Close"], length=params["LC_MA4_NPERIODI"])
    if params["MA_TYPE_INPUT"] in ["SMA", "SMA + Bollinger Bands"]:
        data["smoothingMA"] = data["OBV"].rolling(window=params["MA_LENGTH_INPUT"]).mean()
    elif params["MA_TYPE_INPUT"] == "EMA":
        data["smoothingMA"] = ta.ema(data["OBV"], length=params["MA_LENGTH_INPUT"])
    elif params["MA_TYPE_INPUT"] == "SMMA (RMA)":
        data["smoothingMA"] = data["OBV"].ewm(alpha=1/params["MA_LENGTH_INPUT"], adjust=False).mean()
    elif params["MA_TYPE_INPUT"] == "WMA":
        data["smoothingMA"] = ta.wma(data["OBV"], length=params["MA_LENGTH_INPUT"])
    elif params["MA_TYPE_INPUT"] == "VWMA":
        data["smoothingMA"] = (data["OBV"] * data["Volume"]).rolling(window=params["MA_LENGTH_INPUT"]).sum() / data["Volume"].rolling(window=params["MA_LENGTH_INPUT"]).sum()
    else:
        data["smoothingMA"] = np.nan
    if params["MA_TYPE_INPUT"] == "SMA + Bollinger Bands":
        data["smoothingStDev"] = data["OBV"].rolling(window=params["MA_LENGTH_INPUT"]).std() * params["BB_MULT_INPUT"]
        data["upperBand"] = data["smoothingMA"] + data["smoothingStDev"]
        data["lowerBand"] = data["smoothingMA"] - data["smoothingStDev"]
        data["midUpperBand"] = data["smoothingMA"] + data["smoothingStDev"] / 2
        data["midLowerBand"] = data["smoothingMA"] - data["smoothingStDev"] / 2
    else:
        data["smoothingStDev"] = np.nan
        data["upperBand"] = np.nan
        data["lowerBand"] = np.nan
        data["midUpperBand"] = np.nan
        data["midLowerBand"] = np.nan
    return data
