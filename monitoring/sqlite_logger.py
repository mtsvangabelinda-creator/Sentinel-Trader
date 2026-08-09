import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class SQLiteLogger:
    def __init__(self, db_path):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                strategy TEXT,
                side TEXT,
                entry_price REAL,
                size REAL,
                stop_price REAL,
                take_profit REAL,
                entry_time TEXT,
                exit_price REAL,
                exit_time TEXT,
                pnl REAL,
                status TEXT,
                exit_reason TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS equity_snapshots (
                timestamp TEXT,
                equity REAL
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS events (
                timestamp TEXT,
                event TEXT,
                data TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS candles (
                interval TEXT,
                timestamp INTEGER,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                PRIMARY KEY (interval, timestamp)
            )
        ''')
        conn.commit()
        conn.close()

    def insert_candle(self, interval, candle):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                INSERT OR REPLACE INTO candles (interval, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (interval, int(candle[0]), float(candle[1]), float(candle[2]), 
                  float(candle[3]), float(candle[4]), float(candle[5])))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"Candle insert error: {e}")

    def log_trade(self, trade):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                INSERT OR REPLACE INTO trades 
                (id, strategy, side, entry_price, size, stop_price, take_profit, entry_time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (str(trade['id']), trade['strategy'], trade['side'], 
                  float(trade['entry_price']), float(trade['size']),
                  float(trade['stop_price']), float(trade['take_profit']),
                  trade['entry_time'], 'open'))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Trade log error: {e}")

    def update_trade(self, trade):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                UPDATE trades SET exit_price=?, exit_time=?, pnl=?, status=?, exit_reason=?
                WHERE id=?
            ''', (float(trade.get('exit_price')), trade.get('exit_time'), 
                  float(trade.get('pnl')), trade['status'], 
                  trade.get('exit_reason'), str(trade['id'])))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Trade update error: {e}")

    def log_equity(self, equity):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('INSERT INTO equity_snapshots (timestamp, equity) VALUES (?, ?)',
                     (datetime.utcnow().isoformat(), float(equity)))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"Equity log error: {e}")

    def log_event(self, event, data=None):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('INSERT INTO events (timestamp, event, data) VALUES (?, ?, ?)',
                     (datetime.utcnow().isoformat(), event, json.dumps(data) if data else ''))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"Event log error: {e}")

    def get_total_realized_pnl(self):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('SELECT SUM(pnl) FROM trades WHERE status="closed"')
            result = c.fetchone()[0]
            conn.close()
            return result if result else 0.0
        except:
            return 0.0

    def get_recent_trades(self, n):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('SELECT * FROM trades WHERE status="closed" ORDER BY exit_time DESC LIMIT ?', (n,))
            rows = c.fetchall()
            conn.close()
            trades = []
            for row in rows:
                trades.append({
                    'id': row[0],
                    'strategy': row[1],
                    'side': row[2],
                    'entry_price': row[3],
                    'size': row[4],
                    'stop_price': row[5],
                    'take_profit': row[6],
                    'entry_time': row[7],
                    'exit_price': row[8],
                    'exit_time': row[9],
                    'pnl': row[10],
                    'status': row[11],
                    'exit_reason': row[12]
                })
            return trades
        except Exception as e:
            logger.debug(f"Get trades error: {e}")
            return []

    def get_recent_closed_trades(self, n):
        return self.get_recent_trades(n)

    def get_trades_between(self, start_date, end_date):
        """Get trades between two dates."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''SELECT * FROM trades WHERE status="closed" 
                        AND exit_time >= ? AND exit_time <= ?
                        ORDER BY exit_time''',
                     (str(start_date), str(end_date)))
            rows = c.fetchall()
            conn.close()
            trades = []
            for row in rows:
                trades.append({'pnl': row[10]})
            return trades
        except:
            return []

    def get_max_drawdown_over_period(self, start_date, end_date):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''SELECT equity FROM equity_snapshots WHERE timestamp >= ? AND timestamp <= ?
                        ORDER BY timestamp''', (str(start_date), str(end_date)))
            rows = c.fetchall()
            conn.close()
            if not rows:
                return 0.0
            equity = [row[0] for row in rows]
            peak = equity[0]
            max_dd = 0.0
            for e in equity:
                if e > peak:
                    peak = e
                dd = (peak - e) / peak if peak > 0 else 0
                max_dd = max(max_dd, dd)
            return max_dd
        except:
            return 0.0

    def get_open_positions(self):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('SELECT * FROM trades WHERE status="open"')
            rows = c.fetchall()
            conn.close()
            positions = []
            for row in rows:
                positions.append({
                    'id': row[0],
                    'strategy': row[1],
                    'side': row[2],
                    'entry_price': row[3],
                    'size': row[4],
                    'stop_price': row[5],
                    'take_profit': row[6],
                    'entry_time': row[7]
                })
            return positions
        except:
            return []
