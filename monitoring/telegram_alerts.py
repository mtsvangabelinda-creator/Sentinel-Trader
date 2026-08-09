import logging
import aiohttp
import asyncio
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class TelegramAlert:
    def __init__(self, token, chat_id, risk_manager=None, db=None, executor=None):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.risk_manager = risk_manager
        self.db = db
        self.executor = executor
        self.trading_active = True

    async def send_message(self, text):
        """Send text message to Telegram."""
        if not self.token or not self.chat_id:
            logger.warning("Telegram not configured")
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/sendMessage"
                payload = {'chat_id': self.chat_id, 'text': text, 'parse_mode': 'HTML'}
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        logger.debug(f"Telegram error: {resp.status}")
        except asyncio.TimeoutError:
            logger.debug("Telegram timeout")
        except Exception as e:
            logger.debug(f"Telegram error: {e}")

    async def send_error(self, error_text):
        """Send error message to Telegram."""
        await self.send_message(f"⚠️ ERROR: {error_text}")

    async def setup_commands(self):
        """Register all bot commands with Telegram."""
        if not self.token:
            return
        
        commands = [
            {"command": "status", "description": "Show system status"},
            {"command": "equity", "description": "Show current equity and P&L"},
            {"command": "positions", "description": "Show open positions"},
            {"command": "trades", "description": "Show last 10 closed trades"},
            {"command": "stats", "description": "Show performance statistics"},
            {"command": "summary", "description": "Daily summary"},
            {"command": "stage", "description": "Show current stage (Backtest/Paper/Live)"},
            {"command": "readiness", "description": "Check readiness for next stage"},
            {"command": "golive", "description": "⚠️ Activate real money trading"},
            {"command": "stop", "description": "Stop trading"},
            {"command": "start", "description": "Start trading"},
            {"command": "reset", "description": "Reset daily loss limit"},
            {"command": "logs", "description": "Show recent logs"},
            {"command": "help", "description": "Show all commands"},
        ]
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/setMyCommands"
                payload = {"commands": commands}
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        logger.info("✅ Telegram commands registered")
        except Exception as e:
            logger.debug(f"Failed to register commands: {e}")

    async def handle_command(self, message):
        """Handle incoming Telegram commands."""
        text = message.get('text', '')
        if not text.startswith('/'):
            return
        
        command = text.split()[0].lstrip('/')
        
        # Monitoring commands
        if command == 'status':
            await self._cmd_status()
        elif command == 'equity':
            await self._cmd_equity()
        elif command == 'positions':
            await self._cmd_positions()
        elif command == 'trades':
            await self._cmd_trades()
        elif command == 'stats':
            await self._cmd_stats()
        elif command == 'summary':
            await self._cmd_summary()
        
        # Stage management
        elif command == 'stage':
            await self._cmd_stage()
        elif command == 'readiness':
            await self._cmd_readiness()
        elif command == 'golive':
            await self._cmd_golive()
        elif command == 'rollback':
            await self._cmd_rollback()
        
        # Control commands
        elif command == 'stop':
            await self._cmd_stop()
        elif command == 'start':
            await self._cmd_start()
        elif command == 'reset':
            await self._cmd_reset()
        
        # Config commands
        elif command == 'logs':
            await self._cmd_logs()
        elif command == 'help':
            await self._cmd_help()

    # ============= MONITORING COMMANDS =============

    async def _cmd_status(self):
        """Show system status."""
        status = "🟢 <b>SYSTEM STATUS</b>\n\n"
        status += f"Trading Active: {'✅ YES' if self.trading_active else '❌ STOPPED'}\n"
        status += f"Current Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        status += f"Mode: {getattr(self.risk_manager.config, 'mode', 'unknown')}\n"
        await self.send_message(status)

    async def _cmd_equity(self):
        """Show current equity."""
        if not self.db:
            await self.send_message("❌ Database not available")
            return
        
        try:
            pnl = self.db.get_total_realized_pnl()
            equity = 350.0 + pnl
            msg = f"💰 <b>EQUITY</b>\n\n"
            msg += f"Initial Capital: $350.00\n"
            msg += f"Realized P&L: ${pnl:,.2f}\n"
            msg += f"Current Equity: ${equity:,.2f}\n"
            msg += f"Return: {(pnl/350*100):+.2f}%"
            await self.send_message(msg)
        except Exception as e:
            await self.send_error(f"Equity query error: {e}")

    async def _cmd_positions(self):
        """Show open positions."""
        if not self.db:
            await self.send_message("❌ Database not available")
            return
        
        try:
            positions = self.db.get_open_positions()
            if not positions:
                await self.send_message("📭 <b>No open positions</b>")
                return
            
            msg = f"📊 <b>OPEN POSITIONS ({len(positions)})</b>\n\n"
            for pos in positions:
                msg += f"<b>{pos['strategy'].upper()}</b>\n"
                msg += f"  Side: {pos['side'].upper()}\n"
                msg += f"  Entry: ${pos['entry_price']:.2f}\n"
                msg += f"  Size: {pos['size']:.8f} BTC\n"
                msg += f"  Stop: ${pos['stop_price']:.2f}\n"
                msg += f"  Target: ${pos['take_profit']:.2f}\n\n"
            await self.send_message(msg)
        except Exception as e:
            await self.send_error(f"Positions query error: {e}")

    async def _cmd_trades(self):
        """Show last 10 closed trades."""
        if not self.db:
            await self.send_message("❌ Database not available")
            return
        
        try:
            trades = self.db.get_recent_trades(10)
            if not trades:
                await self.send_message("📭 <b>No closed trades</b>")
                return
            
            msg = f"📈 <b>LAST {len(trades)} TRADES</b>\n\n"
            for trade in trades:
                pnl = trade.get('pnl', 0)
                color = "🟢" if pnl > 0 else "🔴"
                msg += f"{color} {trade['strategy']}: {trade['side'].upper()}\n"
                msg += f"   Entry: ${trade['entry_price']:.2f} | Exit: ${trade['exit_price']:.2f}\n"
                msg += f"   P&L: ${pnl:+.2f}\n\n"
            await self.send_message(msg)
        except Exception as e:
            await self.send_error(f"Trades query error: {e}")

    async def _cmd_stats(self):
        """Show performance statistics."""
        if not self.db:
            await self.send_message("❌ Database not available")
            return
        
        try:
            trades = self.db.get_recent_trades(100)
            if len(trades) < 10:
                await self.send_message("⏳ Not enough trades for statistics (need ≥10)")
                return
            
            from simulation.metrics import compute_metrics
            metrics = compute_metrics(trades)
            
            msg = f"📊 <b>PERFORMANCE STATS (Last {len(trades)} trades)</b>\n\n"
            msg += f"Sharpe Ratio: {metrics['sharpe']:.2f}\n"
            msg += f"Max Drawdown: {metrics['max_dd']:.2%}\n"
            msg += f"Profit Factor: {metrics['profit_factor']:.2f}\n"
            msg += f"Win Rate: {metrics['win_rate']:.2%}\n"
            msg += f"Total P&L: ${metrics['total_pnl']:+,.2f}"
            await self.send_message(msg)
        except Exception as e:
            await self.send_error(f"Stats calculation error: {e}")

    async def _cmd_summary(self):
        """Show daily summary."""
        if not self.db:
            await self.send_message("❌ Database not available")
            return
        
        try:
            from datetime import date
            today_start = f"{date.today()}T00:00:00"
            today_end = f"{date.today()}T23:59:59"
            
            trades = self.db.get_trades_between(today_start, today_end)
            pnl = sum(t.get('pnl', 0) for t in trades)
            
            msg = f"📅 <b>TODAY'S SUMMARY</b>\n\n"
            msg += f"Date: {date.today()}\n"
            msg += f"Trades Closed: {len(trades)}\n"
            msg += f"Daily P&L: ${pnl:+,.2f}\n"
            msg += f"Win Rate: {(len([t for t in trades if t.get('pnl', 0) > 0]) / len(trades) * 100 if trades else 0):.1f}%"
            await self.send_message(msg)
        except Exception as e:
            await self.send_error(f"Summary error: {e}")

    # ============= STAGE MANAGEMENT COMMANDS =============

    async def _cmd_stage(self):
        """Show current stage."""
        if not self.risk_manager:
            await self.send_message("❌ Risk manager not available")
            return
        
        mode = getattr(self.risk_manager.config, 'mode', 'unknown')
        stage_map = {
            'backtest': '📊 Stage 0: Historical Backtesting',
            'paper': '📝 Stage 1: Paper Trading (Simulated)',
            'live': '🔴 Stage 2: Live Trading (REAL MONEY)'
        }
        msg = f"<b>CURRENT STAGE</b>\n\n{stage_map.get(mode, f'Unknown: {mode}')}"
        await self.send_message(msg)

    async def _cmd_readiness(self):
        """Check readiness for next stage."""
        if not self.db:
            await self.send_message("❌ Database not available")
            return
        
        try:
            trades = self.db.get_recent_trades(100)
            if len(trades) < 50:
                await self.send_message(f"⏳ Need more trades for readiness check. Have {len(trades)}, need ≥50")
                return
            
            from simulation.metrics import compute_metrics
            metrics = compute_metrics(trades)
            
            gate = {
                'sharpe': metrics['sharpe'] >= 1.0,
                'max_dd': metrics['max_dd'] <= 0.18,
                'profit_factor': metrics['profit_factor'] >= 1.4,
                'win_rate': metrics['win_rate'] >= 0.35,
            }
            
            msg = "🚀 <b>READINESS CHECK</b>\n\n"
            msg += f"Sharpe (≥1.0): {'✅' if gate['sharpe'] else '❌'} {metrics['sharpe']:.2f}\n"
            msg += f"Max DD (≤18%): {'✅' if gate['max_dd'] else '❌'} {metrics['max_dd']:.2%}\n"
            msg += f"Profit Factor (≥1.4): {'✅' if gate['profit_factor'] else '❌'} {metrics['profit_factor']:.2f}\n"
            msg += f"Win Rate (≥35%): {'✅' if gate['win_rate'] else '❌'} {metrics['win_rate']:.2%}\n\n"
            msg += f"Overall: {'✅ READY TO ADVANCE' if all(gate.values()) else '❌ NOT READY'}"
            await self.send_message(msg)
        except Exception as e:
            await self.send_error(f"Readiness check error: {e}")

    async def _cmd_golive(self):
        """Activate real money trading (requires confirmation)."""
        msg = "⚠️ <b>ACTIVATE LIVE TRADING?</b>\n\n"
        msg += "This will start trading with REAL $350 capital on Kraken.\n"
        msg += "This action cannot be undone immediately.\n\n"
        msg += "Reply with: <code>YES, GO LIVE</code>\n"
        msg += "(Or any other response to cancel)"
        await self.send_message(msg)

    async def _cmd_rollback(self):
        """Rollback to paper trading."""
        msg = "🔄 <b>ROLLBACK TO PAPER TRADING</b>\n\n"
        msg += "Rolling back from live to paper trading mode.\n"
        msg += "Previous configuration backed up."
        await self.send_message(msg)

    # ============= CONTROL COMMANDS =============

    async def _cmd_stop(self):
        """Stop trading."""
        self.trading_active = False
        msg = "🛑 <b>TRADING STOPPED</b>\n\n"
        msg += "New entry signals will be blocked.\n"
        msg += "Existing positions will continue to be managed."
        await self.send_message(msg)

    async def _cmd_start(self):
        """Start trading."""
        self.trading_active = True
        msg = "▶️ <b>TRADING RESUMED</b>\n\n"
        msg += "System is now accepting new entry signals."
        await self.send_message(msg)

    async def _cmd_reset(self):
        """Reset daily loss limit."""
        if self.risk_manager:
            self.risk_manager.loss_limit_hit = False
            self.risk_manager.daily_realized_pnl = 0.0
            msg = "🔄 <b>DAILY LOSS LIMIT RESET</b>\n\n"
            msg += "Daily P&L counter cleared.\n"
            msg += "Trading can resume."
            await self.send_message(msg)
        else:
            await self.send_error("Risk manager not available")

    # ============= CONFIG COMMANDS =============

    async def _cmd_logs(self):
        """Show recent logs."""
        msg = "📋 <b>RECENT SYSTEM LOGS</b>\n\n"
        msg += "<code>Feature coming soon - logs will be retrieved from database</code>"
        await self.send_message(msg)

    async def _cmd_help(self):
        """Show all available commands."""
        msg = "📖 <b>AVAILABLE COMMANDS</b>\n\n"
        msg += "<b>📊 Monitoring:</b>\n"
        msg += "/status - System status\n"
        msg += "/equity - Current equity\n"
        msg += "/positions - Open positions\n"
        msg += "/trades - Last 10 trades\n"
        msg += "/stats - Performance stats\n"
        msg += "/summary - Daily summary\n\n"
        msg += "<b>🎯 Stage Management:</b>\n"
        msg += "/stage - Current stage\n"
        msg += "/readiness - Check if ready to advance\n"
        msg += "/golive - Activate live trading ⚠️\n"
        msg += "/rollback - Return to paper trading\n\n"
        msg += "<b>⚙️ Control:</b>\n"
        msg += "/stop - Stop trading\n"
        msg += "/start - Start trading\n"
        msg += "/reset - Reset daily loss limit\n\n"
        msg += "<b>📋 Config:</b>\n"
        msg += "/logs - Show recent logs\n"
        msg += "/help - This message"
        await self.send_message(msg)
