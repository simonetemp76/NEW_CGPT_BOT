import asyncio
import importlib
import os
import datetime
import psutil
import json
import symbols_config
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CallbackContext, CallbackQueryHandler, CommandHandler, MessageHandler, filters

# Stati della conversazione
MAIN, CONFIG_PAIR, CONFIG_CATEGORY, CONFIG_PARAM, CONFIG_VALUE, PERF_SELECT, BOT_SELECT, SYMBOLS_MENU, SYMBOLS_ADD, SYMBOLS_REMOVE, PERF_LOG = range(11)

def parse_callback_data(data: str) -> str:
    if data in {"heartbeat", "resources", "perf_log", "cancel"}:
        return data
    parts = data.split("_", 1)
    return parts[1] if len(parts) > 1 else parts[0]

def read_performance_log(filename="performance_log.json"):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            from logging_system import log_error
            log_error(f"Errore lettura {filename}: {e}")
            return "Errore nella lettura dello storico."
    else:
        return "Nessun log disponibile."

async def get_wallet_balance_async(update: Update, context: CallbackContext) -> str:
    from wallet import get_wallet_balance as sync_get_wallet_balance
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, sync_get_wallet_balance)
    return result

def send_heartbeat_now():
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"💡 Heartbeat: Bot attivo. Orario: {current_time}"
    from telegram_notifications import send_telegram_message
    send_telegram_message(message)
    return message

def get_resources_status():
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_usage = psutil.virtual_memory().percent
    return f"Stato risorse:\nCPU: {cpu_usage}%\nMemoria: {memory_usage}%"

async def main_menu(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [InlineKeyboardButton("⚙️ Modifica Configurazione", callback_data="main_config")],
        [InlineKeyboardButton("💰 Wallet", callback_data="main_wallet")],
        [InlineKeyboardButton("📈 Performance", callback_data="main_perf")],
        [InlineKeyboardButton("🤖 Gestisci Bot", callback_data="main_bot")],
        [InlineKeyboardButton("🔗 Gestisci Coppie", callback_data="main_symbols")],
        [InlineKeyboardButton("📋 Coppie Attive", callback_data="pairs")],
        [InlineKeyboardButton("💓 Heartbeat", callback_data="heartbeat")],
        [InlineKeyboardButton("💻 Stato Sistema", callback_data="resources")],
        [InlineKeyboardButton("📊 Storico Performance", callback_data="perf_log")],
        [InlineKeyboardButton("❌ Annulla", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("Scegli un'azione:", reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text("Scegli un'azione:", reply_markup=reply_markup)
    return MAIN

async def main_choice(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    import importlib
    importlib.reload(symbols_config)
    current_symbols = symbols_config.SYMBOLS
    data = parse_callback_data(query.data)
    if data == "config":
        keyboard = [[InlineKeyboardButton(pair, callback_data=f"pair_{pair}")] for pair in current_symbols]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Seleziona una coppia per modificare la configurazione:", reply_markup=reply_markup)
        return CONFIG_PAIR
    elif data == "wallet":
        wallet_info = await get_wallet_balance_async(update, context)
        await query.edit_message_text(text=f"Saldo Wallet:\n{wallet_info}")
        return ConversationHandler.END
    elif data == "perf":
        keyboard = [[InlineKeyboardButton(pair, callback_data=f"perf_{pair}")] for pair in current_symbols]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Seleziona una coppia per visualizzare le performance:", reply_markup=reply_markup)
        return PERF_SELECT
    elif data == "bot":
        keyboard = [[InlineKeyboardButton(pair, callback_data=f"bot_{pair}")] for pair in current_symbols]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Seleziona una coppia per gestire il bot:", reply_markup=reply_markup)
        return BOT_SELECT
    elif data == "symbols":
        return await manage_symbols_menu(update, context)
    elif data == "pairs":
        await pairs(update, context)
        return ConversationHandler.END
    elif data == "heartbeat":
        message = send_heartbeat_now()
        await query.edit_message_text(f"Heartbeat inviato:\n{message}")
        return ConversationHandler.END
    elif data == "resources":
        status = get_resources_status()
        await query.edit_message_text(status)
        return ConversationHandler.END
    elif data == "perf_log":
        log_content = read_performance_log()
        if len(log_content) > 4000:
            log_content = log_content[-4000:]
        await query.edit_message_text(f"Storico Performance:\n{log_content}")
        return ConversationHandler.END
    else:
        await query.edit_message_text("Operazione annullata.")
        return ConversationHandler.END

async def manage_symbols_menu(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        message_func = query.edit_message_text
    else:
        message_func = update.message.reply_text
    import importlib
    importlib.reload(symbols_config)
    current_symbols = symbols_config.SYMBOLS
    text = "Coppie attive:\n\n" + "\n".join(f"• {s}" for s in current_symbols)
    text += "\n\nScegli un'azione:"
    keyboard = [
        [InlineKeyboardButton("Aggiungi coppia", callback_data="symbols_add")],
        [InlineKeyboardButton("Rimuovi coppia", callback_data="symbols_remove")],
        [InlineKeyboardButton("Annulla", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message_func(text=text, reply_markup=reply_markup)
    return SYMBOLS_MENU

def _save_symbols_to_file(symbols_list):
    import os
    module_path = os.path.abspath(symbols_config.__file__)
    with open(module_path, "w", encoding="utf-8") as f:
        f.write("# File generato automaticamente.\n\n")
        f.write("SYMBOLS = [\n")
        for sym in symbols_list:
            f.write(f"    '{sym}',\n")
        f.write("]\n")

async def symbols_add_choice(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Inserisci il nome della nuova coppia (es. BTCUSDT):")
    return SYMBOLS_ADD

async def symbols_add_value(update: Update, context: CallbackContext) -> int:
    import importlib
    importlib.reload(symbols_config)
    current_symbols = list(symbols_config.SYMBOLS)
    new_symbol = update.message.text.strip().upper()
    if new_symbol in current_symbols:
        await update.message.reply_text(f"La coppia '{new_symbol}' esiste già.")
        return ConversationHandler.END
    from binance.client import Client
    from config import API_KEY, API_SECRET, USE_TESTNET
    client = Client(API_KEY, API_SECRET, testnet=USE_TESTNET)
    symbol_info = client.get_symbol_info(new_symbol)
    if symbol_info is None:
        await update.message.reply_text(f"La coppia '{new_symbol}' non esiste su Binance.")
        return ConversationHandler.END
    current_symbols.append(new_symbol)
    _save_symbols_to_file(current_symbols)
    from config_manager import add_pair_to_config  # Assicurati che questa funzione sia definita
    add_pair_to_config(new_symbol)
    from multi_bot import start_bot_for_pair
    start_bot_for_pair(new_symbol)
    await update.message.reply_text(f"Coppia '{new_symbol}' aggiunta e bot avviato.")
    return ConversationHandler.END

async def symbols_remove_choice(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    import importlib
    importlib.reload(symbols_config)
    current_symbols = symbols_config.SYMBOLS
    keyboard = [[InlineKeyboardButton(sym, callback_data=f"rm_{sym}")] for sym in current_symbols]
    keyboard.append([InlineKeyboardButton("Annulla", callback_data="cancel")])
    await query.edit_message_text("Seleziona la coppia da rimuovere:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SYMBOLS_REMOVE

async def symbols_remove_execute(update: Update, context: CallbackContext) -> int:
    import importlib
    importlib.reload(symbols_config)
    current_symbols = list(symbols_config.SYMBOLS)
    query = update.callback_query
    await query.answer()
    symbol_to_remove = parse_callback_data(query.data)
    if symbol_to_remove not in current_symbols:
        await query.edit_message_text(f"La coppia '{symbol_to_remove}' non è presente.")
        return ConversationHandler.END
    current_symbols.remove(symbol_to_remove)
    _save_symbols_to_file(current_symbols)
    from multi_bot import stop_bot_for_pair
    stop_bot_for_pair(symbol_to_remove)
    from config_manager import remove_pair_from_config  # Assicurati che questa funzione sia definita
    remove_pair_from_config(symbol_to_remove)
    await query.edit_message_text(f"La coppia '{symbol_to_remove}' è stata rimossa e il bot fermato.")
    return ConversationHandler.END

async def config_pair(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    selected_pair = parse_callback_data(query.data)
    context.user_data["selected_pair"] = selected_pair
    from config_manager import load_config_for_pair
    conf = load_config_for_pair(selected_pair)
    config_text = f"Configurazione per {selected_pair}:\n\n" + "\n".join(f"{k}: {v}" for k, v in conf.items())
    keyboard = [
        [InlineKeyboardButton("GENERAL", callback_data="cat_GENERAL")],
        [InlineKeyboardButton("BOT_SETTINGS", callback_data="cat_BOT_SETTINGS")],
        [InlineKeyboardButton("Annulla", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(config_text + "\n\nScegli categoria da modificare:", reply_markup=reply_markup)
    return CONFIG_CATEGORY

async def config_category(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    cat = parse_callback_data(query.data)
    context.user_data["category"] = cat
    from config import BOT_SETTINGS, GENERAL_PARAMS
    params = GENERAL_PARAMS if cat == "GENERAL" else list(BOT_SETTINGS.keys())
    keyboard = [[InlineKeyboardButton(param, callback_data=f"param_{param}")] for param in params]
    keyboard.append([InlineKeyboardButton("Annulla", callback_data="cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"Categoria {cat}: seleziona il parametro:", reply_markup=reply_markup)
    return CONFIG_PARAM

async def config_param(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    param = parse_callback_data(query.data)
    context.user_data["param"] = param
    await query.edit_message_text(f"Hai scelto {param}. Invia il nuovo valore:")
    return CONFIG_VALUE

async def config_value(update: Update, context: CallbackContext) -> int:
    new_value = update.message.text
    pair = context.user_data.get("selected_pair")
    category = context.user_data.get("category")
    param = context.user_data.get("param")
    from config_manager import load_config_for_pair, save_config_for_pair
    conf = load_config_for_pair(pair)
    if category == "GENERAL":
        conf[param] = new_value
    else:
        if "BOT_SETTINGS" not in conf:
            conf["BOT_SETTINGS"] = {}
        conf["BOT_SETTINGS"][param] = new_value
    save_config_for_pair(pair, conf)
    await update.message.reply_text(f"Impostazione {param} per {pair} aggiornata a {new_value}.")
    return ConversationHandler.END

async def perf_selected(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    selected_pair = parse_callback_data(query.data)
    context.user_data["selected_pair"] = selected_pair
    from performance_monitor import get_performance_for_symbol
    perf_info = await get_performance_for_symbol(selected_pair)
    await query.edit_message_text(f"Performance per {selected_pair}:\n{perf_info}")
    return ConversationHandler.END

async def bot_selected(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    selected_pair = parse_callback_data(query.data)
    context.user_data["selected_pair"] = selected_pair
    from bot_registry import active_bots
    bot = active_bots.get(selected_pair)
    if bot:
        keyboard = [[InlineKeyboardButton("Spegni Bot", callback_data="bot_stop")],
                    [InlineKeyboardButton("Annulla", callback_data="cancel")]]
    else:
        await query.edit_message_text(f"Nessun bot attivo per {selected_pair}.")
        return ConversationHandler.END
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"Hai selezionato {selected_pair}. Scegli azione per il bot:", reply_markup=reply_markup)
    return BOT_SELECT

async def bot_action(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    action = parse_callback_data(query.data)
    selected_pair = context.user_data.get("selected_pair")
    from bot_registry import active_bots
    bot = active_bots.get(selected_pair)
    if not bot:
        await query.edit_message_text(f"Nessun bot attivo per {selected_pair}.")
        return ConversationHandler.END
    if action == "stop":
        bot.stop()
        await query.edit_message_text(f"Bot per {selected_pair} messo in pausa.")
    elif action == "start":
        bot.start()
        await query.edit_message_text(f"Bot per {selected_pair} riattivato.")
    else:
        await query.edit_message_text("Azione non valida.")
    return ConversationHandler.END

async def cancel_menu(update: Update, context: CallbackContext) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Operazione annullata.")
    else:
        await update.message.reply_text("Operazione annullata.")
    return ConversationHandler.END

from telegram.ext import ConversationHandler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("menu", main_menu)],
    states={
        MAIN: [CallbackQueryHandler(main_choice, pattern=r"^(main_wallet|main_config|main_perf|main_bot|main_symbols|pairs|heartbeat|resources|perf_log|cancel)$")],
        CONFIG_PAIR: [CallbackQueryHandler(config_pair, pattern=r"^pair_")],
        CONFIG_CATEGORY: [CallbackQueryHandler(config_category, pattern=r"^cat_"), CallbackQueryHandler(cancel_menu, pattern=r"^cancel$")],
        CONFIG_PARAM: [CallbackQueryHandler(config_param, pattern=r"^param_"), CallbackQueryHandler(cancel_menu, pattern=r"^cancel$")],
        CONFIG_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, config_value)],
        PERF_SELECT: [CallbackQueryHandler(perf_selected, pattern=r"^perf_")],
        BOT_SELECT: [CallbackQueryHandler(bot_selected, pattern=r"^bot_(?!stop|start)"), CallbackQueryHandler(bot_action, pattern=r"^(bot_stop|bot_start)$"), CallbackQueryHandler(cancel_menu, pattern=r"^cancel$")],
        SYMBOLS_MENU: [CallbackQueryHandler(symbols_add_choice, pattern=r"^symbols_add$"), CallbackQueryHandler(symbols_remove_choice, pattern=r"^symbols_remove$"), CallbackQueryHandler(cancel_menu, pattern=r"^cancel$")],
        SYMBOLS_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, symbols_add_value), CallbackQueryHandler(cancel_menu, pattern=r"^cancel$")],
        SYMBOLS_REMOVE: [CallbackQueryHandler(symbols_remove_execute, pattern=r"^rm_"), CallbackQueryHandler(cancel_menu, pattern=r"^cancel$")],
    },
    fallbacks=[CommandHandler("cancel", cancel_menu)]
)

async def pairs(update: Update, context: CallbackContext) -> None:
    import importlib
    importlib.reload(symbols_config)
    current_symbols = symbols_config.SYMBOLS
    text = "Coppie attive:\n\n" + "\n".join(f"• {s}" for s in current_symbols) if current_symbols else "Nessuna coppia attiva."
    if update.message:
        await update.message.reply_text(text)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text)

pairs_handler = CommandHandler("pairs", pairs)
