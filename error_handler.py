import time
import logging
from functools import wraps
from telegram_notifications import send_telegram_message

logger = logging.getLogger("ErrorHandler")
logger.setLevel(logging.ERROR)
if not logger.handlers:
    file_handler = logging.FileHandler("logs/error.log")
    file_handler.setLevel(logging.ERROR)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

def log_error(error_message: str, exception: Exception = None):
    full_message = error_message
    if exception:
        full_message += f" - Eccezione: {exception}"
    logger.error(full_message)
    print(full_message)

def handle_critical_error(error_message: str, exception: Exception = None):
    full_message = error_message
    if exception:
        full_message += f" - Eccezione: {exception}"
    logger.error(full_message)
    print(full_message)
    send_telegram_message(f"❌ ERRORE CRITICO\n{full_message}")

def retry_on_failure(func, retries: int = 3, delay: int = 2, backoff: int = 2):
    last_exception = None
    current_delay = delay
    for i in range(retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            logger.error(f"Ritentativo {i+1}/{retries} fallito. Attendo {current_delay} sec. Eccezione: {e}")
            time.sleep(current_delay)
            current_delay *= backoff
    handle_critical_error("retry_on_failure: tutti i tentativi falliti.", last_exception)
    raise last_exception

def retry_on_failure_decorator(retries: int = 3, delay: int = 2, backoff: int = 2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            for i in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.error(f"Ritentativo {i+1}/{retries} fallito. Attendo {current_delay} sec. Eccezione: {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff
            handle_critical_error(f"{func.__name__}: tutti i tentativi falliti.", last_exception)
            raise last_exception
        return wrapper
    return decorator

def handle_graceful_shutdown(signum, frame):
    error_message = "Arresto improvviso del programma rilevato."
    logger.error(error_message)
    send_telegram_message(error_message)
    exit(1)
