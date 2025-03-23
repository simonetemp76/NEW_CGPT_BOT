#!/usr/bin/env python3
"""
money_management.py

Modulo per il calcolo della quantità di trading e altre operazioni relative al money management.
"""
from binance.client import Client
from config import RISK_PERCENT
try:
    from config import RISK_PERCENT_USDC
except (ImportError, AttributeError):
    RISK_PERCENT_USDC = RISK_PERCENT
from decimal import Decimal, ROUND_DOWN
from logging_system import log_error

def get_base_asset(symbol: str) -> str:
    if "USDT" in symbol:
        return symbol.replace("USDT", "")
    if "USDC" in symbol:
        return symbol.replace("USDC", "")
    if symbol.endswith("BTC"):
        return symbol[:-3]
    half = len(symbol) // 2
    return symbol[:half]

def get_quote_asset(symbol: str) -> str:
    if "USDT" in symbol:
        return "USDT"
    if "USDC" in symbol:
        return "USDC"
    if symbol.endswith("BTC"):
        return "BTC"
    half = len(symbol) // 2
    return symbol[half:]

def calculate_trade_quantity(client: Client, symbol: str, price: float, atr: float = None, side: str = "BUY") -> float:
    try:
        if side.upper() == "BUY":
            asset = get_quote_asset(symbol)
            risk_percent = RISK_PERCENT_USDC if asset == "USDC" else RISK_PERCENT
        else:
            asset = get_base_asset(symbol)
            risk_percent = RISK_PERCENT

        symbol_info = client.get_symbol_info(symbol)
        account_info = client.get_account()

        balance = None
        for item in account_info['balances']:
            if item['asset'] == asset:
                balance = float(item['free'])
                break
        if balance is None:
            print(f"Saldo per {asset} non trovato.")
            return 0.0

        risk_amount = balance * risk_percent
        if atr is not None and atr > 0:
            stop_loss_distance = atr
            raw_quantity = risk_amount / (stop_loss_distance * price)
        else:
            raw_quantity = risk_amount / price

        lot_size_filter = next(x for x in symbol_info['filters'] if x['filterType'] == 'LOT_SIZE')
        step_size = Decimal(lot_size_filter['stepSize'])
        min_qty = Decimal(lot_size_filter['minQty'])
        max_qty = Decimal(lot_size_filter['maxQty'])

        raw_quantity_dec = Decimal(str(raw_quantity))
        quotient = (raw_quantity_dec / step_size).to_integral_value(rounding=ROUND_DOWN)
        quantity = quotient * step_size

        if quantity < min_qty:
            print("La quantità calcolata è inferiore al minimo consentito.")
            return 0.0

        min_notional_filter = next((x for x in symbol_info['filters'] if x['filterType'] == 'MIN_NOTIONAL'), None)
        if min_notional_filter:
            min_notional = Decimal(min_notional_filter['minNotional'])
            order_value = quantity * Decimal(str(price))
            if order_value < min_notional:
                adjusted_quantity = min_notional / Decimal(str(price))
                quotient = (adjusted_quantity / step_size).to_integral_value(rounding=ROUND_DOWN)
                adjusted_quantity = quotient * step_size
                if adjusted_quantity < min_qty:
                    print(f"Quantità troppo bassa per {symbol}")
                    return 0.0
                print(f"Quantità troppo bassa ({order_value:.2f}), adeguo a {adjusted_quantity}")
                quantity = adjusted_quantity

        if quantity > max_qty:
            quantity = max_qty

        return float(quantity)

    except Exception as e:
        error_message = f"Errore nel calcolo della quantità di trading: {e}"
        print(error_message)
        log_error(error_message)
        return 0.0

def round_step_size(quantity, step_size):
    """
    Arrotonda la quantità in base allo step size.
    """
    quantity = Decimal(str(quantity))
    step_size = Decimal(str(step_size))
    precision = abs(step_size.as_tuple().exponent)
    return float(quantity.quantize(Decimal(10) ** -precision, rounding=ROUND_DOWN))

def format_quantity(qty):
    """
    Formatta la quantità per rimuovere zeri non significativi.
    """
    s = f"{qty:.8f}".rstrip('0').rstrip('.')
    return s
