#!/usr/bin/env python3
"""
strategy_plugin.py

Questo modulo definisce un sistema di plugin per le strategie di trading.
Ogni plugin deve implementare una logica di trading specifica e seguire un'interfaccia standard.
"""

from abc import ABC, abstractmethod
import importlib
import os

class StrategyPlugin(ABC):
    """
    Classe base per i plugin delle strategie.
    Tutti i plugin devono ereditare da questa classe e implementare i metodi astratti.
    """

    @abstractmethod
    def analyze(self, data, base_signal, price):
        """
        Analizza i dati e restituisce un segnale di trading.
        :param data: DataFrame contenente i dati di mercato e gli indicatori.
        :param base_signal: Segnale di base generato dalla strategia principale.
        :param price: Prezzo corrente.
        :return: Segnale di trading (es. "buy", "sell", "hold") e confidenza.
        """
        pass

    @abstractmethod
    def retrain(self, data):
        """
        Esegue il retraining del modello (se applicabile).
        :param data: DataFrame contenente i dati di mercato e gli indicatori.
        """
        pass

class PluginManager:
    """
    Gestisce il caricamento e l'utilizzo dei plugin delle strategie.
    """

    def __init__(self, plugin_dir="plugins"):
        self.plugin_dir = plugin_dir
        self.plugins = {}
        self.load_plugins()

    def load_plugins(self):
        """
        Carica tutti i plugin dalla directory specificata.
        """
        if not os.path.exists(self.plugin_dir):
            print(f"[PluginManager] Directory dei plugin non trovata: {self.plugin_dir}")
            return

        for filename in os.listdir(self.plugin_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                plugin_name = filename[:-3]  # Rimuove l'estensione .py
                try:
                    module = importlib.import_module(f"{self.plugin_dir}.{plugin_name}")
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, StrategyPlugin) and attr != StrategyPlugin:
                            self.plugins[plugin_name] = attr()
                            print(f"[PluginManager] Plugin caricato: {plugin_name}")
                except Exception as e:
                    print(f"[PluginManager] Errore nel caricamento del plugin {plugin_name}: {e}")

    def get_plugin(self, plugin_name):
        """
        Restituisce un plugin specifico.
        :param plugin_name: Nome del plugin.
        :return: Istanza del plugin, o None se non trovato.
        """
        return self.plugins.get(plugin_name)

    def list_plugins(self):
        """
        Restituisce una lista di tutti i plugin caricati.
        :return: Lista dei nomi dei plugin.
        """
        return list(self.plugins.keys())

# Esempio di plugin
class ExampleStrategy(StrategyPlugin):
    """
    Esempio di plugin per una strategia di trading.
    """

    def analyze(self, data, base_signal, price):
        """
        Implementa la logica di analisi della strategia.
        """
        # Esempio: usa il segnale di base e aggiunge una logica personalizzata
        if base_signal == "buy" and data["RSI"].iloc[-1] < 30:
            return "buy", 0.9  # Segnale e confidenza
        return base_signal, 0.5

    def retrain(self, data):
        """
        Esegue il retraining del modello (se applicabile).
        """
        print("[ExampleStrategy] Retraining del modello...")

# Esempio di utilizzo
if __name__ == "__main__":
    manager = PluginManager()
    print("Plugin caricati:", manager.list_plugins())

    # Esempio di utilizzo di un plugin
    example_plugin = manager.get_plugin("example_strategy")
    if example_plugin:
        data = {}  # Sostituisci con i dati reali
        signal, confidence = example_plugin.analyze(data, "hold", 100)
        print(f"Segnale: {signal}, Confidenza: {confidence}")