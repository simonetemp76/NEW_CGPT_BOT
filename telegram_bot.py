from telegram import Update
from telegram.helpers import escape_markdown
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from binance.client import Client
from config import TELEGRAM_BOT_TOKEN, API_KEY, API_SECRET, USE_TESTNET, BOT_SETTINGS, TELEGRAM_CHAT_IDS
from symbols_config import SYMBOLS
from telegram_notifications import send_telegram_message
from config_manager import get_bot_settings, update_bot_settings, reset_bot_settings, backup_bot_settings, restore_bot_settings
from performance_monitor import get_performance_for_symbol
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

binance_client = Client(API_KEY, API_SECRET, testnet=USE_TESTNET)

def is_authorized(update: Update) -> bool:
    return str(update.message.from_user.id) in TELEGRAM_CHAT_IDS

async def get_wallet_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ Non autorizzato.")
        return
    try:
        account = binance_client.get_account()
        balances = [
            f"{b['asset']}: {b['free']} (libero), {b['locked']} (bloccato)"
            for b in account['balances'] if float(b['free']) > 0 or float(b['locked']) > 0
        ]
        response = "💰 **Saldo Wallet Binance:**\n\n" + "\n".join(balances)
        await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Errore: {str(e)}")

async def config_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ Non autorizzato.")
        return
    try:
        args = context.args
        if not args:
            await update.message.reply_text("Uso: /config <simbolo>")
            return
        symbol = args[0].upper()
        if symbol not in SYMBOLS:
            await update.message.reply_text(f"❌ Simbolo {symbol} non valido.")
            return
        settings = get_bot_settings(symbol)
        message = f"⚙️ **Configurazione per {symbol}:**\n" + "\n".join(f"- {k}: {v}" for k, v in settings.items())
        message = escape_markdown(message, version=2)
        await update.message.reply_text(message, parse_mode="MarkdownV2")
    except Exception as e:
        await update.message.reply_text(f"❌ Errore: {str(e)}")

async def update_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ Non autorizzato.")
        return
    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text("Uso: /updateconfig <simbolo> <chiave> <valore>")
            return
        symbol = args[0].upper()
        key = args[1]
        value_str = " ".join(args[2:])
        if symbol not in SYMBOLS:
            await update.message.reply_text(f"❌ Simbolo {symbol} non valido.")
            return
        update_bot_settings(symbol, {key: value_str})
        await update.message.reply_text(f"✅ Config per {symbol} aggiornata: {key} = {value_str}")
    except Exception as e:
        await update.message.reply_text(f"❌ Errore: {e}")

async def pairs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ Non autorizzato.")
        return
    try:
        pairs_str = "🔎 **Coppie attive:**\n" + "\n".join(SYMBOLS)
        await update.message.reply_text(pairs_str, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Errore: {str(e)}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📚 **Comandi disponibili:**\n"
        "/wallet - Saldo del wallet\n"
        "/config <simbolo> - Config per un simbolo\n"
        "/updateconfig <simbolo> <chiave> <valore> - Aggiorna config\n"
        "/pairs - Coppie attive\n"
        "/performance - Performance attuali\n"
        "/help - Aiuto\n"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ Non autorizzato.")
        return
    try:
        backup_bot_settings()
        await update.message.reply_text("✅ Backup creato.")
    except Exception as e:
        await update.message.reply_text(f"❌ Errore: {e}")

async def restore_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ Non autorizzato.")
        return
    try:
        restore_bot_settings()
        await update.message.reply_text("✅ Config ripristinata.")
    except Exception as e:
        await update.message.reply_text(f"❌ Errore: {e}")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Comando sconosciuto. Usa /help per aiuto.")

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("wallet", get_wallet_balance))
    application.add_handler(CommandHandler("config", config_command))
    application.add_handler(CommandHandler("updateconfig", update_config_command))
    application.add_handler(CommandHandler("pairs", pairs_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("backup", backup_command))
    application.add_handler(CommandHandler("restore", restore_command))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    logger.info("Avvio bot Telegram...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot arrestato.")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot interrotto manualmente.")
