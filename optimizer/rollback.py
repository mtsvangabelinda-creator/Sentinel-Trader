import logging
import asyncio
import shutil
from simulation.metrics import compute_sharpe

logger = logging.getLogger(__name__)

class RollbackManager:
    def __init__(self, config, db, alert):
        self.config = config
        self.db = db
        self.alert = alert

    async def monitor(self):
        """Monitor 20 trades after promotion, rollback if fail."""
        monitor_count = 0
        target = self.config['rollback']['monitor_trades']
        
        logger.info(f"Starting rollback monitoring ({target} trades)")
        
        while monitor_count < target:
            await asyncio.sleep(60)
            
            # Get recent closed trades
            recent = self.db.get_recent_closed_trades(target + 5)
            if len(recent) >= target:
                recent = recent[-target:]
                
                pnls = [t.get('pnl', 0) for t in recent]
                sharpe = compute_sharpe(pnls) if pnls else 0.0
                max_loss_pct = max([abs(t.get('pnl', 0)) / 350 * 100 for t in recent])
                
                logger.info(f"Monitor: Sharpe={sharpe:.2f}, Max Loss={max_loss_pct:.2f}%")
                
                if sharpe < self.config['rollback']['sharpe_threshold'] or \
                   max_loss_pct > self.config['rollback']['max_loss_pct']:
                    await self._rollback()
                    return
                else:
                    monitor_count = len(recent)
                    logger.info(f"Monitoring progress: {monitor_count}/{target}")

    async def _rollback(self):
        """Restore previous configuration."""
        logger.warning("ROLLBACK TRIGGERED")
        try:
            shutil.copy('config/btc_config.yaml.backup', 'config/btc_config.yaml')
            await self.alert.send_message("⚠️ ROLLBACK: Restored previous config due to performance degradation")
        except Exception as e:
            logger.error(f"Rollback error: {e}")
            await self.alert.send_error(f"Rollback failed: {e}")
