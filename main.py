"""
Main entry point for SentinelTrader V13.0
"""
import asyncio
import signal
import sys
from datetime import datetime
from utils.logger import setup_logger
from config.settings import settings
from database.connection import db
from database.models import SCHEMA
from whitelist.kraken_whitelist import KrakenWhitelist
from adaptive.regime_detection import RegimeDetector
from adaptive.genetic_programming import GeneticProgramming
from adaptive.rl_agent import RLAgent
from adaptive.oversight_loop import OversightLoop
from strategies.arbitrage_strategy import ArbitrageStrategy
from strategies.meme_strategy import MemeStrategy
from execution.order_manager import OrderManager
from execution.lifecycle_monitor import LifecycleMonitor
from execution.risk_manager import RiskManager
from telegram_bot.notifier import Notifier
from compounding.equity_tracker import EquityTracker
from data_harvester.auto_seed import AutoSeed
from dashboard.metrics_exporter import MetricsExporter

logger = setup_logger(__name__)

class SentinelTrader:
    """Main bot class for SentinelTrader V13.0"""
    
    def __init__(self):
        self.running = True
        self.whitelist = KrakenWhitelist()
        self.regime_detector = RegimeDetector()
        self.rl_agents = {
            "arbitrage": RLAgent("arbitrage"),
            "meme": RLAgent("meme")
        }
        self.oversight = OversightLoop()
        self.arbitrage_strategy = ArbitrageStrategy()
        self.meme_strategy = MemeStrategy()
        self.order_manager = OrderManager()
        self.lifecycle_monitor = LifecycleMonitor()
        self.risk_manager = RiskManager()
        self.notifier = Notifier()
        self.equity_tracker = EquityTracker(settings.INITIAL_CAPITAL)
        logger.info("SentinelTrader initialized")
    
    async def initialize(self):
        """Initialize bot"""
        logger.info("=" * 80)
        logger.info("🚀 SENTINELTRADER V13.0 - INITIALIZATION")
        logger.info("=" * 80)
        
        try:
            # Connect database
            await db.connect()
            logger.info("✅ Database connected")
            
            # Connect Kraken
            await self.order_manager.connect()
            logger.info("✅ Kraken connected")
            
            # Connect Redis/whitelist
            await self.whitelist.connect()
            logger.info("✅ Whitelist initialized")
            
            # Start Prometheus metrics
            MetricsExporter.start_server(port=8000)
            logger.info("✅ Prometheus metrics started")
            
            # Auto-seed data
            seeded = await AutoSeed.seed_all()
            if seeded:
                logger.info("✅ Historical data seeded")
            else:
                logger.warning("⚠️  Data seeding incomplete")
            
            # Send startup notification
            await self.notifier.send_alert("✅ <b>SentinelTrader V13.0 started</b>")
            
            logger.info("✅ Initialization complete")
            logger.info("=" * 80)
        
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            await self.notifier.send_alert(f"❌ Initialization error: {e}")
            raise
    
    async def run(self):
        """Main bot loop"""
        try:
            await self.initialize()
            
            # Start parallel tasks
            tasks = [
                self.oversight.run(),
                self.lifecycle_monitor.run(),
                self._main_trading_loop()
            ]
            
            await asyncio.gather(*tasks, return_exceptions=False)
        
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)
            await self.notifier.send_alert(f"❌ Fatal error: {e}")
            raise
        
        finally:
            await self.shutdown()
    
    async def _main_trading_loop(self):
        """Main trading execution loop"""
        logger.info("🔄 Main trading loop started")
        
        iteration = 0
        while self.running:
            try:
                iteration += 1
                logger.debug(f"Trading loop iteration {iteration}")
                
                # Update equity
                metrics = await self.equity_tracker.get_performance_metrics()
                if metrics:
                    await MetricsExporter.update_sharpe("arbitrage", metrics.get("sharpe_ratio", 0))
                    await MetricsExporter.update_drawdown("arbitrage", metrics.get("max_drawdown", 0))
                
                await asyncio.sleep(60)  # Check every minute
            
            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                await asyncio.sleep(10)
    
    async def shutdown(self):
        """Shutdown bot gracefully"""
        logger.info("=" * 80)
        logger.info("🛑 SENTINELTRADER - SHUTDOWN")
        logger.info("=" * 80)
        
        self.running = False
        self.lifecycle_monitor.stop()
        
        await self.order_manager.disconnect()
        await self.whitelist.disconnect()
        await db.disconnect()
        
        logger.info("✅ Shutdown complete")

async def main():
    """Entry point"""
    settings.validate()
    
    bot = SentinelTrader()
    
    # Handle signals
    def signal_handler(sig, frame):
        logger.warning(f"Signal {sig} received, shutting down...")
        bot.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run bot
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Unhandled error: {e}", exc_info=True)
        sys.exit(1)
