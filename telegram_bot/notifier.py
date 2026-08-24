"""
Telegram notifications for SentinelTrader
"""
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError
from utils.logger import setup_logger
from config.settings import settings

logger = setup_logger(__name__)

class Notifier:
    """Send Telegram notifications"""
    
    def __init__(self):
        self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        self.chat_id = settings.TELEGRAM_CHAT_ID
    
    async def send_alert(self, message: str) -> bool:
        """Send alert message"""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="HTML"
            )
            return True
        except TelegramError as e:
            logger.error(f"Telegram send error: {e}")
            return False
    
    async def send_trade_notification(self, trade: dict) -> bool:
        """Send trade execution notification"""
        try:
            message = (
                f"<b>💰 Trade Executed</b>\n"
                f"<b>Strategy:</b> {trade.get('strategy', 'N/A')}\n"
                f"<b>Asset:</b> {trade.get('asset', 'N/A')}\n"
                f"<b>Entry:</b> ${trade.get('entry_price', 0):.2f}\n"
                f"<b>Qty:</b> {trade.get('quantity', 0):.4f}\n"
                f"<b>SL:</b> ${trade.get('sl', 0):.2f}\n"
                f"<b>TP:</b> ${trade.get('tp', 0):.2f}\n"
            )
            return await self.send_alert(message)
        except Exception as e:
            logger.error(f"Trade notification error: {e}")
            return False
    
    async def send_risk_alert(self, event: dict) -> bool:
        """Send risk event alert"""
        try:
            severity_emoji = "⚠️" if event.get("severity") == "high" else "🚨"
            
            message = (
                f"{severity_emoji} <b>Risk Alert</b>\n"
                f"<b>Event:</b> {event.get('event_type', 'N/A')}\n"
                f"<b>Strategy:</b> {event.get('strategy', 'N/A')}\n"
                f"<b>Severity:</b> {event.get('severity', 'N/A')}\n"
                f"<b>Description:</b> {event.get('description', 'N/A')}\n"
            )
            return await self.send_alert(message)
        except Exception as e:
            logger.error(f"Risk alert error: {e}")
            return False
    
    async def send_performance_update(self, metrics: dict) -> bool:
        """Send performance update"""
        try:
            message = (
                f"<b>📊 Performance Update</b>\n"
                f"<b>Strategy:</b> {metrics.get('strategy', 'N/A')}\n"
                f"<b>Daily Return:</b> {metrics.get('daily_return', 0)*100:.2f}%\n"
                f"<b>Sharpe Ratio:</b> {metrics.get('sharpe_ratio', 0):.2f}\n"
                f"<b>Max Drawdown:</b> {metrics.get('max_drawdown', 0)*100:.2f}%\n"
                f"<b>Trades:</b> {metrics.get('trade_count', 0)}\n"
            )
            return await self.send_alert(message)
        except Exception as e:
            logger.error(f"Performance update error: {e}")
            return False
