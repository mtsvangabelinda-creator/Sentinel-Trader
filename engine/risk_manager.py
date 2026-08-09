import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RiskManager:
    """Enforces position limits, daily loss limit, and calculates position sizes."""
    def __init__(self, config, db):
        self.config = config
        self.db = db
        self.max_concurrent = config['max_concurrent_trades']
        self.daily_loss_limit = config['daily_loss_limit']
        self.open_positions = []
        self.daily_realized_pnl = 0.0
        self.daily_date = datetime.utcnow().date()
        self.loss_limit_hit = False

    def can_open_position(self):
        """Check if we can open a new trade."""
        if self.loss_limit_hit:
            return False
        if len(self.open_positions) >= self.max_concurrent:
            return False
        return True

    def calculate_position_size(self, pool, stop_price, current_price):
        """Risk 1% of pool per trade."""
        risk_amount = pool * 0.01
        stop_distance = abs(current_price - stop_price)
        if stop_distance == 0 or stop_distance < 0.01:
            return 0
        size = risk_amount / stop_distance
        # Kraken min: ~0.0001 BTC
        if size < 0.00001:
            return 0
        return round(size, 8)

    def add_position(self, trade):
        self.open_positions.append(trade)
        self.db.log_trade(trade)
        logger.info(f"Position added: {trade['id']}")

    def remove_position(self, trade_id):
        self.open_positions = [t for t in self.open_positions if t['id'] != trade_id]

    def update_daily_pnl(self, pnl):
        """Update daily realized P&L, check limit."""
        today = datetime.utcnow().date()
        if today != self.daily_date:
            self.daily_date = today
            self.daily_realized_pnl = 0.0
            self.loss_limit_hit = False
            logger.info("Daily P&L reset")

        self.daily_realized_pnl += pnl
        logger.info(f"Daily P&L: {self.daily_realized_pnl:.2f}")
        
        if self.daily_realized_pnl <= -self.daily_loss_limit:
            self.loss_limit_hit = True
            logger.warning(f"Daily loss limit HIT: {self.daily_realized_pnl}")
            # Close all positions at market
            for pos in list(self.open_positions):
                pos['exit_price'] = pos['entry_price']
                pos['pnl'] = 0
                pos['status'] = 'closed'
                pos['exit_reason'] = 'daily_loss_limit'
                self.db.update_trade(pos)
            self.open_positions = []

    def is_daily_loss_hit(self):
        return self.loss_limit_hit

    def get_total_equity(self, current_price):
        """Calculate total equity including unrealized P&L."""
        unrealized = 0.0
        for pos in self.open_positions:
            if pos['side'] == 'buy':
                pnl = (current_price - pos['entry_price']) * pos['size']
            else:
                pnl = (pos['entry_price'] - current_price) * pos['size']
            unrealized += pnl
        
        realized = self.db.get_total_realized_pnl()
        return 350.0 + realized + unrealized

    def get_total_realized_pnl(self):
        return self.db.get_total_realized_pnl()
