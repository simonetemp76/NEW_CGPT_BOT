import json
import os
from typing import Dict, Any
from config import BOT_SETTINGS, SYMBOLS

DYNAMIC_CONFIG_PATH = "dynamic_config.json"

class ConfigManager:
    def __init__(self):
        self.dynamic_config = self._load_dynamic_config()

    def _load_dynamic_config(self) -> Dict[str, Any]:
        if os.path.exists(DYNAMIC_CONFIG_PATH):
            try:
                with open(DYNAMIC_CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Errore caricamento config dinamica: {e}")
                return {}
        return {}

    def _save_dynamic_config(self):
        try:
            with open(DYNAMIC_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.dynamic_config, f, indent=4, ensure_ascii=False)
            print(f"Config dinamica salvata in {DYNAMIC_CONFIG_PATH}.")
        except Exception as e:
            print(f"Errore salvataggio config dinamica: {e}")

    def get_config(self, symbol: str = None) -> Dict[str, Any]:
        if symbol and symbol in self.dynamic_config:
            return self.dynamic_config[symbol]
        return BOT_SETTINGS

    def update_config(self, symbol: str, new_settings: Dict[str, Any]):
        if symbol not in self.dynamic_config:
            self.dynamic_config[symbol] = {}
        self.dynamic_config[symbol].update(new_settings)
        self._save_dynamic_config()
        print(f"Config aggiornata per {symbol}.")

    def reset_config(self, symbol: str = None):
        if symbol:
            if symbol in self.dynamic_config:
                del self.dynamic_config[symbol]
                self._save_dynamic_config()
                print(f"Config ripristinata per {symbol}.")
        else:
            self.dynamic_config = {}
            self._save_dynamic_config()
            print("Config ripristinata per tutti.")

    def backup_config(self, backup_path: str = "config_backup.json"):
        try:
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(self.dynamic_config, f, indent=4, ensure_ascii=False)
            print(f"Backup config salvato in {backup_path}.")
        except Exception as e:
            print(f"Errore salvataggio backup: {e}")

    def restore_config(self, backup_path: str = "config_backup.json"):
        if os.path.exists(backup_path):
            try:
                with open(backup_path, "r", encoding="utf-8") as f:
                    self.dynamic_config = json.load(f)
                self._save_dynamic_config()
                print(f"Config ripristinata da {backup_path}.")
            except Exception as e:
                print(f"Errore ripristino config: {e}")
        else:
            print(f"Backup {backup_path} non trovato.")

config_manager = ConfigManager()

def get_bot_settings(symbol: str = None) -> Dict[str, Any]:
    return config_manager.get_config(symbol)

def update_bot_settings(symbol: str, new_settings: Dict[str, Any]):
    config_manager.update_config(symbol, new_settings)

def reset_bot_settings(symbol: str = None):
    config_manager.reset_config(symbol)

def backup_bot_settings(backup_path: str = "config_backup.json"):
    config_manager.backup_config(backup_path)

def restore_bot_settings(backup_path: str = "config_backup.json"):
    config_manager.restore_config(backup_path)

def load_config_for_pair(symbol: str) -> Dict[str, Any]:
    return config_manager.get_config(symbol)

def initialize_symbols_config():
    if os.path.exists(DYNAMIC_CONFIG_PATH):
        print(f"{DYNAMIC_CONFIG_PATH} esiste già.")
        return
    default_config = {symbol: BOT_SETTINGS for symbol in SYMBOLS}
    try:
        with open(DYNAMIC_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        print(f"File {DYNAMIC_CONFIG_PATH} inizializzato con successo.")
    except Exception as e:
        print(f"Errore inizializzazione {DYNAMIC_CONFIG_PATH}: {e}")

if __name__ == "__main__":
    initialize_symbols_config()
    print("Impostazioni di default:", get_bot_settings())
    update_bot_settings("BTCUSDT", {"percent_loss": 5, "rsi_lower": 25})
    print("Config BTCUSDT aggiornata:", get_bot_settings("BTCUSDT"))
    reset_bot_settings("BTCUSDT")
    print("Config BTCUSDT ripristinata:", get_bot_settings("BTCUSDT"))
    backup_bot_settings()
    restore_bot_settings()
