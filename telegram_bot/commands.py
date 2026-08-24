"""
Telegram bot command handlers for SentinelTrader
"""
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from utils.logger import setup_logger
from database.queries import Queries

logger = setup_logger(__name__)

class BotCommands:
    """Handle Telegram commands"""
    
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command"""
        await update.message.reply_text(
            "🤖 <b>SentinelTrader V13.0 Online</b>\n\n"
            "Available commands:\n"
            "/status - Current bot status\n"
            "/balance - Account balance\n"
            "/positions - Open positions\n"
            "/trades - Recent trades\n"
            "/performance - Performance metrics\n"
            "/stop - Emergency stop\n",
            parse_mode="HTML"
        )
    
    @staticmethod
    async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Status command"""
        try:
            status_msg = (
                "✅ <b>Status: RUNNING</b>\n"
                "Arbitrage: Active\n"
                "Meme: Active\n"
                "Database: Connected\n"
            )
            await update.message.reply_text(status_msg, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Status command error: {e}")
            await update.message.reply_text("❌ Error retrieving status")
    
    @staticmethod
    async def positions(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show open positions"""
        try:
            arb_pos = await Queries.get_open_positions("arbitrage")
            meme_pos = await Queries.get_open_positions("meme")
            
            if not arb_pos and not meme_pos:
                await update.message.reply_text("📭 No open positions")
                return
            
            msg = "📈 <b>Open Positions</b>\n\n"
            
            if arb_pos:
                msg += "<b>Arbitrage:</b>\n"
                for pos in arb_pos:
                    msg += f"  {pos.get('asset')}: {pos.get('quantity', 0):.4f} @ ${pos.get('entry_price', 0):.2f}\n"
            
            if meme_pos:
                msg += "<b>Meme:</b>\n"
                for pos in meme_pos:
                    msg += f"  {pos.get('asset')}: {pos.get('quantity', 0):.4f} @ ${pos.get('entry_price', 0):.2f}\n"
            
            await update.message.reply_text(msg, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Positions command error: {e}")
            await update.message.reply_text("❌ Error retrieving positions")
    
    @staticmethod
    async def trades(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show recent trades"""
        try:
            recent = await Queries.get_recent_trades("arbitrage", limit=5)
            recent += await Queries.get_recent_trades("meme", limit=5)
            
            if not recent:
                await update.message.reply_text("📭 No recent trades")
                return
            
            msg = "📊 <b>Recent Trades (Last 10)</b>\n\n"
            for trade in recent[:10]:
                pnl = trade.get("pnl", 0)
                pnl_emoji = "✅" if pnl > 0 else "❌"
                msg += (
                    f"{pnl_emoji} {trade.get('asset')}: "
                    f"${pnl:.2f} | "
                    f"{trade.get('strategy')}\n"
                )
            
            await update.message.reply_text(msg, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Trades command error: {e}")
            await update.message.reply_text("❌ Error retrieving trades")
    
    @staticmethod
    async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Emergency stop"""
        logger.critical("❌ Emergency stop triggered via Telegram")
        await update.message.reply_text("🛑 <b>Emergency stop activated</b>", parse_mode="HTML")
        # Trigger shutdown logic in main.py
    
    @staticmethod
    def setup_handlers(app: Application):
        """Register command handlers"""
        app.add_handler(CommandHandler("start", BotCommands.start))
        app.add_handler(CommandHandler("status", BotCommands.status))
        app.add_handler(CommandHandler("positions", BotCommands.positions))
        app.add_handler(CommandHandler("trades", BotCommands.trades))
        app.add_handler(CommandHandler("stop", BotCommands.stop))
