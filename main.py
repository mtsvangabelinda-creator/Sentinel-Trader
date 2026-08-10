import asyncio
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import modules
from config.settings import load_config
from monitoring.sqlite_logger import SQLiteLogger
from monitoring.telegram_alerts import TelegramAlert
from simulation.run_backtest import run_initial_backtest, run_forward_test
from engine.kraken_data_fetcher import KrakenDataFetcher


class SentinelTrader:
    """Main SentinelTrader application."""
    
    def __init__(self):
        self.config = load_config()
        self.db = SQLiteLogger('data/sentinel.db')
        self.alert = TelegramAlert(
            os.getenv('TELEGRAM_TOKEN'),
            os.getenv('TELEGRAM_CHAT_ID'),
            db=self.db
        )
        self.mode = self.config.get('mode', 'backtest')
        self.is_running = True
        logger.info(f"SentinelTrader initialized in {self.mode} mode")
    
    async def start(self):
        """Start the application."""
        logger.info("🚀 Starting SentinelTrader...")
        
        try:
            # Setup Telegram commands
            await self.alert.setup_commands()
            
            # Send startup message
            await self.alert.send_message(
                "🟢 <b>SENTINELTRADER ONLINE</b>\n\n"
                f"Mode: {self.mode.upper()}\n"
                f"Started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
                "<b>Available Commands:</b>\n"
                "/status - System status\n"
                "/equity - Current equity\n"
                "/positions - Open positions\n"
                "/trades - Recent trades\n"
                "/stats - Performance stats\n"
                "/stage - Current stage\n"
                "/backtest - Run Stage 0 backtest\n"
                "/help - All commands"
            )
            
            logger.info("✅ SentinelTrader started successfully")
            
            # Main loop
            while self.is_running:
                await asyncio.sleep(30)
                # Keep alive, wait for Telegram commands
        
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            await self.alert.send_error(f"Fatal error: {e}")
            sys.exit(1)
    
    async def run_backtest_command(self):
        """Handle /backtest command."""
        logger.info("Running backtest from Telegram command...")
        
        await self.alert.send_message(
            "🔄 <b>STARTING STAGE 0 BACKTEST</b>\n\n"
            "Fetching 30 days of data from Kraken...\n"
            "⏳ This may take 3-5 minutes..."
        )
        
        try:
            # Run backtest
            passed, metrics = await run_initial_backtest(self.config, self.db, self.alert)
            
            if not passed:
                logger.warning("Initial backtest FAILED")
                await self.alert.send_message(
                    f"❌ <b>STAGE 0 FAILED</b>\n\n"
                    f"Metrics:\n"
                    f"Sharpe: {metrics.get('sharpe', 'N/A')}\n"
                    f"Max DD: {metrics.get('max_dd', 'N/A')}\n"
                    f"Profit Factor: {metrics.get('profit_factor', 'N/A')}\n"
                    f"Win Rate: {metrics.get('win_rate', 'N/A')}\n"
                    f"Trades: {metrics.get('num_trades', 'N/A')}\n\n"
                    f"Error: {metrics.get('error', 'Unknown')}"
                )
                return
            
            logger.info("✅ Initial backtest PASSED")
            
            await self.alert.send_message(
                f"✅ <b>INITIAL BACKTEST PASSED</b>\n\n"
                f"📊 Metrics:\n"
                f"Sharpe: {metrics['sharpe']:.2f}\n"
                f"Max DD: {metrics['max_dd']*100:.1f}%\n"
                f"Profit Factor: {metrics['profit_factor']:.2f}\n"
                f"Win Rate: {metrics['win_rate']*100:.1f}%\n"
                f"Trades: {metrics['num_trades']}\n\n"
                f"🧪 Running forward test (5 days)..."
            )
            
            # Run forward test
            fw_passed, fw_metrics = await run_forward_test(self.config, self.db, self.alert, days=5)
            
            if not fw_passed or fw_metrics.get('sharpe', 0) < 0.0:
                logger.warning("Forward test underperformed")
                await self.alert.send_message(
                    f"⚠️ <b>FORWARD TEST UNDERPERFORMED</b>\n\n"
                    f"Backtest Sharpe: {metrics['sharpe']:.2f}\n"
                    f"Forward Sharpe: {fw_metrics.get('sharpe', 'N/A')}\n\n"
                    f"Adjusting parameters and retrying..."
                )
                return
            
            logger.info("✅ Forward test PASSED - Advancing to Stage 1")
            
            # Update config
            self.config['initial_config_done'] = True
            self.config['mode'] = 'paper'
            self.config.save()
            self.mode = 'paper'
            
            await self.alert.send_message(
                f"🟢 <b>STAGE 0 & FORWARD TEST PASSED</b>\n\n"
                f"📈 Backtest Sharpe: {metrics['sharpe']:.2f}\n"
                f"🧪 Forward Test Sharpe: {fw_metrics['sharpe']:.2f}\n\n"
                f"✅ Transitioning to Stage 1 (Paper Trading)...\n"
                f"System will now simulate trades for 50+ transactions before going LIVE."
            )
        
        except Exception as e:
            logger.error(f"Backtest error: {e}", exc_info=True)
            await self.alert.send_error(f"Backtest error: {e}")
    
    async def run_status_command(self):
        """Handle /status command."""
        msg = f"🟢 <b>SYSTEM STATUS</b>\n\n"
        msg += f"Mode: {self.mode.upper()}\n"
        msg += f"Status: RUNNING ✅\n"
        msg += f"Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        
        try:
            pnl = self.db.get_total_realized_pnl()
            equity = 350.0 + pnl
            msg += f"\n💰 <b>Equity:</b>\n"
            msg += f"Initial: $350.00\n"
            msg += f"P&L: ${pnl:+.2f}\n"
            msg += f"Current: ${equity:,.2f}\n"
            msg += f"Return: {(pnl/350*100):+.2f}%"
        except Exception as e:
            logger.warning(f"Error getting equity: {e}")
        
        await self.alert.send_message(msg)
    
    async def run_stage_command(self):
        """Handle /stage command."""
        stage_map = {
            'backtest': '📊 Stage 0: Historical Backtesting',
            'paper': '📝 Stage 1: Paper Trading (Simulated)',
            'live': '🔴 Stage 2: Live Trading (REAL MONEY)'
        }
        msg = f"<b>CURRENT STAGE</b>\n\n{stage_map.get(self.mode, f'Unknown: {self.mode}')}"
        await self.alert.send_message(msg)
    
    async def handle_telegram_command(self, command):
        """Route Telegram commands."""
        logger.info(f"Handling command: {command}")
        
        if command == 'backtest':
            await self.run_backtest_command()
        elif command == 'status':
            await self.run_status_command()
        elif command == 'stage':
            await self.run_stage_command()
        elif command == 'help':
            await self.alert.send_message(
                "📖 <b>AVAILABLE COMMANDS</b>\n\n"
                "<b>📊 Monitoring:</b>\n"
                "/status - System status\n"
                "/equity - Current equity\n"
                "/positions - Open positions\n"
                "/trades - Last 10 trades\n"
                "/stats - Performance stats\n"
                "/summary - Daily summary\n\n"
                "<b>🎯 Stage Management:</b>\n"
                "/stage - Current stage\n"
                "/backtest - Run Stage 0 backtest\n\n"
                "<b>⚙️ Control:</b>\n"
                "/stop - Stop trading\n"
                "/start - Start trading\n"
                "/reset - Reset daily loss limit\n\n"
                "<b>📋 Config:</b>\n"
                "/logs - Recent logs\n"
                "/help - This message"
            )
        else:
            await self.alert.send_message(f"Unknown command: /{command}\n\nType /help for available commands")


async def main():
    """Main entry point."""
    try:
        logger.info("═" * 60)
        logger.info("SENTINELTRADER - AUTONOMOUS BTC/USD TRADING SYSTEM")
        logger.info("═" * 60)
        
        # Create and start application
        app = SentinelTrader()
        await app.start()
    
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        print("\n👋 SentinelTrader shutdown")
    
    except Exception as e:
        logger.error(f"Failed to start SentinelTrader: {e}", exc_info=True)
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
