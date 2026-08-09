import asyncio
import logging
import uuid
from datetime import datetime
import ccxt.async_support as ccxt

logger = logging.getLogger(__name__)

class OrderExecutor:
    """Places orders on Kraken (live) or simulates (paper/backtest)."""
    def __init__(self, config, env, db, risk_manager):
        self.config = config
        self.env = env
        self.db = db
        self.risk = risk_manager
        self.mode = config['mode']
        self.exchange = None
        
        if self.mode == 'live' and env.get('KRAKEN_API_KEY'):
            try:
                self.exchange = ccxt.kraken({
                    'apiKey': env['KRAKEN_API_KEY'],
                    'secret': env['KRAKEN_SECRET'],
                    'enableRateLimit': True,
                })
            except Exception as e:
                logger.error(f"Exchange init error: {e}")

    async def place_order(self, signal, size):
        """Place entry order based on signal."""
        if self.mode == 'live' and self.exchange:
            try:
                side = 'buy' if signal.action == 'BUY' else 'sell'
                order = await self.exchange.create_order(
                    symbol='BTC/USD',
                    type='limit',
                    side=side,
                    amount=size,
                    price=signal.entry_price
                )
                trade = {
                    'id': str(order.get('id', str(uuid.uuid4()))),
                    'strategy': signal.strategy,
                    'side': side,
                    'entry_price': float(order['price']),
                    'size': size,
                    'stop_price': signal.stop_price,
                    'take_profit': signal.take_profit,
                    'entry_time': datetime.utcnow().isoformat(),
                    'exit_price': None,
                    'exit_time': None,
                    'pnl': None,
                    'status': 'open'
                }
                self.risk.add_position(trade)
                logger.info(f"Live order: {trade['id']}")
                return trade
            except Exception as e:
                logger.error(f"Order error: {e}")
                return None
        else:
            # Paper/backtest: simulate
            slippage = 0.001
            entry_price = signal.entry_price * (1 + slippage if signal.action == 'BUY' else 1 - slippage)
            trade = {
                'id': str(uuid.uuid4()),
                'strategy': signal.strategy,
                'side': 'buy' if signal.action == 'BUY' else 'sell',
                'entry_price': entry_price,
                'size': size,
                'stop_price': signal.stop_price,
                'take_profit': signal.take_profit,
                'entry_time': datetime.utcnow().isoformat(),
                'exit_price': None,
                'exit_time': None,
                'pnl': None,
                'status': 'open'
            }
            self.risk.add_position(trade)
            logger.info(f"Paper entry: {trade['strategy']}")
            return trade

    async def manage_positions(self, ticker, candles_5m):
        """Check stop/take profit for all open positions."""
        current_price = ticker['last']
        
        for pos in list(self.risk.open_positions):
            exit_reason = None
            
            if pos['side'] == 'buy':
                if current_price >= pos['take_profit']:
                    exit_reason = 'take_profit'
                elif current_price <= pos['stop_price']:
                    exit_reason = 'stop_loss'
            else:  # sell
                if current_price <= pos['take_profit']:
                    exit_reason = 'take_profit'
                elif current_price >= pos['stop_price']:
                    exit_reason = 'stop_loss'
            
            if exit_reason:
                await self._exit_position(pos, current_price, exit_reason)

    async def _exit_position(self, pos, exit_price, reason):
        """Close position at market price."""
        if self.mode == 'live' and self.exchange:
            try:
                side = 'sell' if pos['side'] == 'buy' else 'buy'
                order = await self.exchange.create_order(
                    symbol='BTC/USD',
                    type='market',
                    side=side,
                    amount=pos['size']
                )
                exit_price = float(order['price'])
            except Exception as e:
                logger.error(f"Exit error: {e}")
                return
        else:
            # Simulate slippage
            slippage = 0.001
            exit_price = exit_price * (1 - slippage if pos['side'] == 'buy' else 1 + slippage)

        if pos['side'] == 'buy':
            pnl = (exit_price - pos['entry_price']) * pos['size']
        else:
            pnl = (pos['entry_price'] - exit_price) * pos['size']

        pos['exit_price'] = exit_price
        pos['exit_time'] = datetime.utcnow().isoformat()
        pos['pnl'] = pnl
        pos['status'] = 'closed'
        pos['exit_reason'] = reason
        
        self.risk.remove_position(pos['id'])
        self.db.update_trade(pos)
        self.risk.update_daily_pnl(pnl)
        
        logger.info(f"Exit: {reason}, P&L: {pnl:.2f}")
