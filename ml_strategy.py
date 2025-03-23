#!/usr/bin/env python3
"""
ml_strategy.py

Modulo per la strategia ML:
- Carica, addestra e ottimizza un modello RandomForest per le previsioni di trading.
- Utilizza dati storici e indicatori calcolati in data_utils.
"""

import numpy as np
np.NaN = np.nan
import pandas_ta as ta
import pandas as pd
import joblib
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from data_utils import get_historical_data, compute_indicators
from config import API_KEY, API_SECRET, USE_TESTNET, ML_RETRAIN_INTERVAL, FEATURE_NAMES
from binance.client import Client
from error_handler import retry_on_failure

MODEL_PATH = "models/ml_model.pkl"

class MLStrategy:
    def __init__(self):
        self.model = self.load_model()
        self.trade_count = 0
        self.feature_names = FEATURE_NAMES
        if not hasattr(self.model, 'estimators_'):
            print("[MLStrategy] Addestramento iniziale del modello...")
            self.retrain_model()

    def load_model(self):
        try:
            if os.path.exists(MODEL_PATH):
                print("[MLStrategy] Caricamento modello esistente...")
                return joblib.load(MODEL_PATH)
            else:
                print("[MLStrategy] Creazione nuovo modello...")
                return RandomForestClassifier(n_estimators=100, random_state=42)
        except Exception as e:
            print(f"[MLStrategy] Errore nel caricamento del modello: {e}")
            return RandomForestClassifier(n_estimators=100, random_state=42)

    def save_model(self):
        try:
            os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
            joblib.dump(self.model, MODEL_PATH)
            print("[MLStrategy] Modello salvato!")
        except Exception as e:
            print(f"[MLStrategy] Errore nel salvataggio del modello: {e}")

    def optimize_hyperparameters(self, X_train, y_train):
        param_grid = {
            "n_estimators": [100, 200],
            "max_depth": [10, 20],
            "min_samples_split": [2, 5],
            "min_samples_leaf": [1, 2]
        }
        model = RandomForestClassifier(random_state=42)
        tscv = TimeSeriesSplit(n_splits=5)
        grid_search = GridSearchCV(model, param_grid, cv=tscv, scoring="accuracy", n_jobs=-1)
        grid_search.fit(X_train, y_train)
        print(f"[MLStrategy] Migliori iperparametri: {grid_search.best_params_}")
        return grid_search.best_estimator_

    def _ensure_indicators(self, df):
        if "MACD" not in df.columns:
            df["MACD"] = ta.macd(df["Close"], fast=12, slow=26, signal=9)["MACD_12_26_9"]
        if "ATR" not in df.columns:
            df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], length=14)
        if "BB_WIDTH" not in df.columns:
            bb = ta.bbands(df["Close"], length=20, std=2)
            df["BB_WIDTH"] = bb["BBU_20_2.0"] - bb["BBL_20_2.0"]
        return df

    def retrain_model(self):
        print("[MLStrategy] Inizio retraining del modello...")
        client = Client(API_KEY, API_SECRET, testnet=USE_TESTNET)
        df = retry_on_failure(lambda: get_historical_data(client, "BTCUSDT", "1h", lookback_days=500))
        if df is None or df.empty:
            print("[MLStrategy] Nessun dato per retraining.")
            return
        params = {
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
        df = compute_indicators(df, params)
        df = self._ensure_indicators(df)
        try:
            X = df[self.feature_names]
        except KeyError as e:
            print(f"[MLStrategy] Errore: {e}")
            return
        df["target"] = np.where(df["Close"].shift(-1) > df["Close"], 1, 0)
        df.dropna(inplace=True)
        if len(df) < 100:
            print("[MLStrategy] Dati insufficienti per retraining.")
            return
        X = df[self.feature_names]
        y = df["target"]
        best_model = self.optimize_hyperparameters(X, y)
        self.model = best_model
        self.save_model()
        print("[MLStrategy] Retraining completato.")

    def analyze(self, data, base_signal, price):
        try:
            features = data[self.feature_names].iloc[-1].values.reshape(1, -1)
        except Exception as e:
            print(f"[MLStrategy] Errore nell'estrazione delle feature: {e}")
            return base_signal, 0.5
        prediction = self.model.predict(features)[0]
        confidence = max(self.model.predict_proba(features)[0])
        signal = "buy" if prediction == 1 else "sell"
        return signal, confidence

if __name__ == "__main__":
    ml = MLStrategy()
    print("Test MLStrategy:", ml.analyze(pd.DataFrame(), "hold", 0))
