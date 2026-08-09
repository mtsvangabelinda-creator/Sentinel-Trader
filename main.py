#!/usr/bin/env python3
"""
SentinelTrader Main Entry Point
Orchestrates all components in a single async event loop.
Handles lifecycle stages (backtest, paper, live) and weekly self-optimization.
"""
import asyncio
import logging
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

from config.settings import load_config, load_env
from engine.data_feed import DataFeed
from engine.regime import RegimeClassifier
from engine.sentinel import Sentinel
from engine.risk_manager import RiskManager
from engine.order_executor import OrderExecutor
from strategies.trend_following import TrendFollowing
from strategies.mean_reversion import MeanReversion
from strategies.momentum_burst import MomentumBurst
from monitoring.sqlite_logger import SQLiteLogger
from monitoring.telegram_alerts import TelegramAlert
from optimizer.auto_optimizer import AutoOptimizer
from optimizer.shadow_runner import ShadowRunner
from optimizer.promotion import PromotionEngine
from optimizer.rollback import RollbackManager
from simulation.run_backtest import run_initial_backtest
from dashboard.generate import generate_dashboard

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main")

class SentinelTrader:
    def __init__(self):
        self.env = load_env()
        self.config = load_config()
        
        # Create data directory if not exists
        Path(self.config['data_dir']).mkdir(parents=True, exist_ok=True)
        
        self.db = SQLiteLogger(self.config['db_path'])
        self.alert = TelegramAlert(
            self.env.get('TELEGRAM_TOKEN'),
            self.env.get('TELEGRAM_CHAT_ID')
        )
        self.data = DataFeed(self.config, self.db)
        self.regime = RegimeClassifier(self.config)
        self.sentinel = Sentinel(self.config)
        self.risk = RiskManager(self.config, self.db)
        self.executor = OrderExecutor(self.config, self.env, self.db, self.risk)
        
        self.strategies = {
            'trend': TrendFollowing(self.config),
            'meanrev': MeanReversion(self.config),
            'momentum': MomentumBurst(self.config)
        }
        
        self.optimizer = AutoOptimizer(self.config, self.db, self.alert)
        self.shadow = ShadowRunner(self.config, self.db)
        self.promotion = PromotionEngine(self.config, self.db, self.alert)
        self.rollback = RollbackManager(self.config, self.db, self.alert)

        # Stage flags
        self.mode = self.config.get('mode', 'backtest')
        self.stage_file = Path(self.config['data_dir']) / 'stage.flag'
        self.ready_for_paper = False
        self.ready_for_live = False
        self.last_dashboard_update = 0
        self.next_weekly_opt = None

    async def run(self):
        """Main async event loop, ticks every 5 seconds."""
        logger.info(f"Starting SentinelTrader in mode: {self.mode}")

        # Load or set stage
        await self._check_stage()

        # Initial backtest if needed (only once)
        if self.mode == 'backtest' and not self.config.get('initial_config_done'):
            await self._initial_backtest()

        # Start data feed
        await self.data.start()

        # Calculate next optimization time
        self._calculate_next_optimization()

        # Start weekly optimizer scheduler
        asyncio.create_task(self._weekly_optimizer_loop())

        # Main loop
        logger.info("Entering main trading loop...")
        while True:
            try:
                # 1. Get latest data
                candles_1m = self.data.get_candles('1m')
                candles_5m = self.data.get_candles('5m')
                ticker = self.data.get_ticker()

                if candles_5m is None or len(candles_5m) < 2 or ticker is None:
                    await asyncio.sleep(5)
                    continue

                # 2. Update regime
                regime = self.regime.update(candles_5m)
                logger.debug(f"Regime: {regime}")

                # 3. Sentinel check
                sentinel_green = self.sentinel.check(ticker, candles_5m)
                if not sentinel_green:
                    logger.debug("Sentinel red, blocking new entries")

                # 4. Evaluate strategies for entry signals
                if sentinel_green and not self.risk.is_daily_loss_hit():
                    for name, strat in self.strategies.items():
                        if not strat.is_active(regime):
                            continue
                        
                        try:
                            signal = strat.evaluate(candles_1m, candles_5m, ticker)
                            if signal and signal.action != 'NONE':
                                if self.risk.can_open_position():
                                    pool = self.config['strategy_pools'][name]
                                    size = self.risk.calculate_position_size(
                                        pool, signal.stop_price, ticker['last']
                                    )
                                    if size > 0:
                                        trade = await self.executor.place_order(signal, size)
                                        if trade:
                                            logger.info(f"Entry signal {name}: {signal.action}")
                                            await self.alert.send_message(
                                                f"📈 {name.upper()} Entry: {signal.action} @ {ticker['last']:.2f}"
                                            )
                        except Exception as e:
                            logger.error(f"Strategy {name} error: {e}", exc_info=True)

                # 5. Manage existing positions
                await self.executor.manage_positions(ticker, candles_5m)

                # 6. Update equity snapshot
                equity = self.risk.get_total_equity(ticker['last'])
                self.db.log_equity(equity)

                # 7. Regenerate dashboard every 5 minutes
                now = time.time()
                if now - self.last_dashboard_update > 300:
                    await generate_dashboard(self.config, self.db)
                    self.last_dashboard_update = now

                # 8. Sleep until next tick
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Main loop error: {e}", exc_info=True)
                try:
                    await self.alert.send_error(f"Main loop error: {e}")
                except:
                    pass
                await asyncio.sleep(5)

    async def _check_stage(self):
        """Read stage flag file to determine progression."""
        if self.stage_file.exists():
            with open(self.stage_file, 'r') as f:
                stage = f.read().strip()
                if stage == 'PAPER':
                    self.mode = 'paper'
                elif stage == 'LIVE':
                    self.mode = 'live'
        self.config['mode'] = self.mode
        logger.info(f"Operating mode: {self.mode}")

    async def _initial_backtest(self):
        """Run initial historical backtest and if passes, flag for paper."""
        logger.info("Running initial backtest...")
        await self.alert.send_message("🔄 Starting Stage 0 backtest...")
        
        passed, metrics = await run_initial_backtest(self.config, self.db, self.alert)
        
        if passed:
            logger.info("Initial backtest PASSED. Metrics: " + str(metrics))
            self.config['initial_config_done'] = True
            self.config.save()
            self.stage_file.write_text('PAPER')
            await self.alert.send_message(
                f"✅ STAGE 0 PASSED\nSharpe: {metrics['sharpe']:.2f}\n"
                f"Max DD: {metrics['max_dd']*100:.1f}%\n"
                f"Profit Factor: {metrics['profit_factor']:.2f}\n"
                f"Win Rate: {metrics['win_rate']*100:.1f}%\n"
                f"Trades: {metrics['num_trades']}\n\n"
                f"Transitioning to Stage 1 (Paper Trading)..."
            )
            self.mode = 'paper'
            self.config['mode'] = 'paper'
        else:
            logger.error("Initial backtest FAILED.")
            await self.alert.send_error(
                f"❌ STAGE 0 FAILED\nMetrics: {metrics}\nHuman review required."
            )
            sys.exit(1)

    def _calculate_next_optimization(self):
        """Calculate next Sunday 00:00 UTC."""
        now = datetime.utcnow()
        days_ahead = 6 - now.weekday()  # Sunday=6
        if days_ahead <= 0:
            days_ahead += 7
        next_sunday = now + timedelta(days=days_ahead)
        self.next_weekly_opt = next_sunday.replace(hour=0, minute=0, second=0, microsecond=0)
        logger.info(f"Next optimization scheduled for {self.next_weekly_opt}")

    async def _weekly_optimizer_loop(self):
        """Run weekly optimization every Sunday at 00:00 UTC."""
        while True:
            now = datetime.utcnow()
            if now >= self.next_weekly_opt:
                logger.info("Starting weekly optimization...")
                await self.alert.send_message("🔍 Starting weekly parameter optimization...")
                
                try:
                    candidate = await self.optimizer.run()
                    if candidate:
                        logger.info("Candidate parameters found, running shadow test...")
                        shadow_results = await self.shadow.run(candidate)
                        
                        if await self.promotion.evaluate(candidate, shadow_results):
                            logger.info("Promotion approved, applying new config...")
                            self.config.update(candidate)
                            self.config.save()
                            
                            # Backup old config
                            import shutil
                            shutil.copy('config/btc_config.yaml', 'config/btc_config.yaml.backup')
                            
                            await self.alert.send_message("🔄 Auto-promotion: New config deployed.")
                            asyncio.create_task(self.rollback.monitor())
                        else:
                            logger.info("Promotion failed statistical tests.")
                            await self.alert.send_message("⏳ Candidate didn't pass promotion criteria. Keeping current config.")
                    else:
                        logger.info("No candidate generated.")
                except Exception as e:
                    logger.error(f"Optimization failed: {e}", exc_info=True)
                    await self.alert.send_error(f"Optimization error: {e}")
                
                # Schedule next Sunday
                self._calculate_next_optimization()
                sleep_secs = (self.next_weekly_opt - datetime.utcnow()).total_seconds()
                if sleep_secs > 0:
                    await asyncio.sleep(min(sleep_secs, 3600))  # sleep up to 1h at a time
            else:
                # Sleep until next check
                sleep_secs = (self.next_weekly_opt - datetime.utcnow()).total_seconds()
                if sleep_secs > 0:
                    await asyncio.sleep(min(sleep_secs, 3600))

if __name__ == "__main__":
    import time
    trader = SentinelTrader()
    try:
        asyncio.run(trader.run())
    except KeyboardInterrupt:
        logger.info("Shutdown requested.")
        sys.exit(0)
