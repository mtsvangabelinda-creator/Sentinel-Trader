import logging
import numpy as np
from scipy.stats import ttest_ind, norm

logger = logging.getLogger(__name__)

class PromotionEngine:
    def __init__(self, config, db, alert):
        self.config = config
        self.db = db
        self.alert = alert

    async def evaluate(self, candidate, shadow_results):
        """Bayesian A/B test and hard checks for promotion."""
        # Get live trades from same period
        start_date = shadow_results.get('start_date')
        end_date = shadow_results.get('end_date')
        
        live_trades = self.db.get_trades_between(start_date, end_date)
        
        if len(live_trades) < 10:
            logger.warning("Not enough live trades for comparison")
            return False
        
        shadow_trades = shadow_results.get('trades', [])
        if len(shadow_trades) < 20:
            logger.warning("Not enough shadow trades")
            return False
        
        # Compute metrics
        shadow_sharpe = shadow_results['sharpe']
        shadow_pf = shadow_results['profit_factor']
        shadow_dd = shadow_results['max_dd']
        
        live_sharpe = 0.0
        live_dd = 0.0
        if live_trades:
            live_pnls = [t['pnl'] for t in live_trades if t.get('pnl')]
            if live_pnls:
                live_sharpe = np.mean(live_pnls) / (np.std(live_pnls) + 1e-6) * np.sqrt(252)
        
        # Hard checks
        checks_pass = (
            shadow_pf >= self.config['promotion']['min_profit_factor'] and
            shadow_dd < live_dd * self.config['promotion']['max_dd_ratio'] + 0.05 and
            len(shadow_trades) >= self.config['shadow']['min_trades']
        )
        
        if not checks_pass:
            logger.warning(f"Hard checks failed: PF={shadow_pf:.2f}, DD={shadow_dd:.2f} vs {live_dd:.2f}")
            return False
        
        # Bayesian prob (shadow > live Sharpe)
        if live_sharpe > 0:
            prob_shadow_better = 1 / (1 + np.exp(-(shadow_sharpe - live_sharpe)))
        else:
            prob_shadow_better = 0.75 if shadow_sharpe > 0 else 0.0
        
        logger.info(f"Promotion eval: P(shadow>live)={prob_shadow_better:.2f}, "
                   f"shadow_sharpe={shadow_sharpe:.2f}, live_sharpe={live_sharpe:.2f}")
        
        return prob_shadow_better >= self.config['promotion']['prob_threshold']
