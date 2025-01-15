import telebot
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class TelegramService:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.bot = telebot.TeleBot(self.bot_token)
        self.send_startup_message()

    def send_message(self, message):
        try:
            self.bot.send_message(self.chat_id, message, parse_mode='HTML')
        except Exception as e:
            print(f"Failed to send telegram message: {str(e)}")

    def send_startup_message(self):
        self.send_message("🚀 <b>Telegram Bot Started</b>")

    def position_opened(self, position):
        message = (
            "🟢 <b>Position Opened</b>\n\n"
            f"Symbol: {position.symbol}\n"
            f"Type: {position.type}\n"
            f"Entry: {position.price_open}\n"
            f"SL: {position.sl}\n"
            f"TP: {position.tp}\n"
            f"Volume: {position.volume}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.send_message(message)

    def position_closed(self, position, reason=""):
        message = (
            "🔴 <b>Position Closed</b>\n\n"
            f"Symbol: {position.symbol}\n"
            f"Type: {position.type}\n"
            f"Entry: {position.price_open}\n"
            f"Exit: {position.price_close}\n"
            f"Profit: {position.profit}\n"
            f"Reason: {reason}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.send_message(message)

    def position_replaced(self, old_position, new_position):
        message = (
            "🔄 <b>Position Replaced</b>\n\n"
            f"Symbol: {new_position.symbol}\n"
            f"Type: {new_position.type}\n"
            f"New Entry: {new_position.price_open}\n"
            f"New SL: {new_position.sl}\n"
            f"New TP: {new_position.tp}\n"
            f"Volume: {new_position.volume}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.send_message(message)

    def trailing_stop_updated(self, position, new_sl):
        message = (
            "📊 <b>Trailing Stop Updated</b>\n\n"
            f"Symbol: {position.symbol}\n"
            f"Type: {position.type}\n"
            f"Entry: {position.price_open}\n"
            f"New SL: {new_sl}\n"
            f"TP: {position.tp}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.send_message(message)

    def position_status_changed(self, position):
        message = (
            f"🔄 Position Status Changed\n\n"
            f"Symbol: {position.symbol}\n"
            f"Type: {position.type}\n"
            f"Status: {position.status}\n"
            f"Volume: {position.volume}\n"
            f"Entry: {position.price_open}\n"
            f"Exit: {position.price_close}\n"
            f"Profit: {position.profit}\n"
            f"SL: {position.sl}\n"
            f"TP: {position.tp}"
        )
        self.send_message(message)

    def send_webhook_url(self, url):
        message = (
            "🔗 New Webhook URL Available\n\n"
            f"URL: {url}/webhook\n\n"
            "TradingView Alert Setup:\n"
            "1. Go to TradingView Alert Settings\n"
            "2. Set Webhook URL as above\n"
            "3. Use format:\n"
            "{\n"
            '  "action": "OPEN",\n'
            '  "symbol": "{{ticker}}",\n'
            '  "type": "BUY",\n'
            '  "price": {{close}}\n'
            "}"
        )
        self.send_message(message)

    def webhook_received(self, webhook_url):
        message = (
            f"🔗 New Webhook URL\n\n"
            f"URL: {webhook_url}/webhook\n\n"
            f"Use this URL in TradingView alerts"
        )
        self.send_message(message)