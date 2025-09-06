import json
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = '8107369635:AAE-1siL6UYG7VbyWkFD9mAJAeMczPVGNME'  # Replace with your bot token
OWNER_TELEGRAM_ID = 7711480832  # Replace with your Telegram ID (integer)
LOGIN_LOGS_FILE = 'login_logs.json'

def is_owner(update: Update) -> bool:
    """Check if the user is the owner"""
    return update.effective_user.id == OWNER_TELEGRAM_ID

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    if not is_owner(update):
        update.message.reply_text("Akses ditolak. Anda bukan pemilik.")
        return
    
    update.message.reply_text(
        "Halo! Saya adalah bot monitoring untuk sistem penyimpanan pribadi Anda.\n\n"
        "Gunakan /help untuk melihat daftar perintah yang tersedia."
    )

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    if not is_owner(update):
        update.message.reply_text("Akses ditolak. Anda bukan pemilik.")
        return
    
    update.message.reply_text(
        "Daftar perintah yang tersedia:\n\n"
        "/start - Menampilkan pesan selamat datang\n"
        "/list - Menampilkan semua akun yang pernah login\n"
        "/detail <username> - Menampilkan riwayat login lengkap untuk username tertentu\n"
        "/help - Menampilkan pesan bantuan ini"
    )

def list_users(update: Update, context: CallbackContext) -> None:
    """List all users who have logged in."""
    if not is_owner(update):
        update.message.reply_text("Akses ditolak. Anda bukan pemilik.")
        return
    
    try:
        with open(LOGIN_LOGS_FILE, 'r') as f:
            logs = json.load(f)
        
        if not logs:
            update.message.reply_text("Belum ada catatan login.")
            return
        
        message = "<b>Daftar Akun yang Pernah Login:</b>\n\n"
        
        # Create keyboard with usernames
        keyboard = []
        for username in logs.keys():
            last_login = logs[username][-1]['timestamp']
            message += f"• <code>{username}</code> - Terakhir login: {last_login}\n"
            keyboard.append([InlineKeyboardButton(username, callback_data=f"detail_{username}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in list_users: {e}")
        update.message.reply_text("Terjadi kesalahan saat memuat data login.")

def detail_user(update: Update, context: CallbackContext) -> None:
    """Show detailed login history for a specific user."""
    if not is_owner(update):
        update.message.reply_text("Akses ditolak. Anda bukan pemilik.")
        return
    
    if not context.args:
        update.message.reply_text("Silakan berikan username. Contoh: /detail admin")
        return
    
    username = context.args[0]
    
    try:
        with open(LOGIN_LOGS_FILE, 'r') as f:
            logs = json.load(f)
        
        if username not in logs:
            update.message.reply_text(f"Tidak ditemukan catatan login untuk username: {username}")
            return
        
        user_logs = logs[username]
        total_logins = len(user_logs)
        
        message = f"<b>Riwayat Login untuk {username}:</b>\n\n"
        message += f"Total login: {total_logins}\n\n"
        
        # Show last 5 logins (to avoid message too long)
        recent_logs = user_logs[-5:]
        for i, log in enumerate(recent_logs, 1):
            timestamp = log['timestamp']
            ip = log.get('ip', 'Unknown')
            message += f"{i}. {timestamp} (IP: {ip})\n"
        
        if total_logins > 5:
            message += f"\n...dan {total_logins - 5} login sebelumnya."
        
        update.message.reply_text(
            message,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in detail_user: {e}")
        update.message.reply_text("Terjadi kesalahan saat memuat data login.")

def button_callback(update: Update, context: CallbackContext) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    query.answer()
    
    if not is_owner(update):
        query.edit_message_text("Akses ditolak. Anda bukan pemilik.")
        return
    
    data = query.data
    
    if data.startswith('detail_'):
        username = data[7:]  # Remove 'detail_' prefix
        
        try:
            with open(LOGIN_LOGS_FILE, 'r') as f:
                logs = json.load(f)
            
            if username not in logs:
                query.edit_message_text(f"Tidak ditemukan catatan login untuk username: {username}")
                return
            
            user_logs = logs[username]
            total_logins = len(user_logs)
            
            message = f"<b>Riwayat Login untuk {username}:</b>\n\n"
            message += f"Total login: {total_logins}\n\n"
            
            # Show last 5 logins (to avoid message too long)
            recent_logs = user_logs[-5:]
            for i, log in enumerate(recent_logs, 1):
                timestamp = log['timestamp']
                ip = log.get('ip', 'Unknown')
                message += f"{i}. {timestamp} (IP: {ip})\n"
            
            if total_logins > 5:
                message += f"\n...dan {total_logins - 5} login sebelumnya."
            
            # Add back button
            keyboard = [[InlineKeyboardButton("« Kembali ke Daftar", callback_data="back_to_list")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error in button_callback: {e}")
            query.edit_message_text("Terjadi kesalahan saat memuat data login.")
    
    elif data == 'back_to_list':
        # Show list of users again
        try:
            with open(LOGIN_LOGS_FILE, 'r') as f:
                logs = json.load(f)
            
            if not logs:
                query.edit_message_text("Belum ada catatan login.")
                return
            
            message = "<b>Daftar Akun yang Pernah Login:</b>\n\n"
            
            # Create keyboard with usernames
            keyboard = []
            for username in logs.keys():
                last_login = logs[username][-1]['timestamp']
                message += f"• <code>{username}</code> - Terakhir login: {last_login}\n"
                keyboard.append([InlineKeyboardButton(username, callback_data=f"detail_{username}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error in back_to_list: {e}")
            query.edit_message_text("Terjadi kesalahan saat memuat data login.")

def main() -> None:
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(BOT_TOKEN)
    
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    
    # Register the commands
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("list", list_users))
    dispatcher.add_handler(CommandHandler("detail", detail_user))
    
    # Register callback handler for inline buttons
    dispatcher.add_handler(CallbackQueryHandler(button_callback))
    
    # Start the Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()