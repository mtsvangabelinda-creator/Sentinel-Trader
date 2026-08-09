import sqlite3
import logging
import json
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

async def generate_dashboard(config, db):
    """Generate static HTML dashboard."""
    try:
        conn = sqlite3.connect(config['db_path'])
        c = conn.cursor()
        
        # Get recent equity
        c.execute('SELECT timestamp, equity FROM equity_snapshots ORDER BY timestamp DESC LIMIT 1000')
        equity_rows = c.fetchall()
        
        # Get recent trades
        c.execute('SELECT * FROM trades WHERE status="closed" ORDER BY exit_time DESC LIMIT 20')
        trade_rows = c.fetchall()
        
        # Get open positions
        c.execute('SELECT * FROM trades WHERE status="open"')
        open_rows = c.fetchall()
        
        conn.close()
        
        # Build HTML
        equity_points = []
        for row in reversed(equity_rows):
            equity_points.append({'t': row[0][:10], 'e': row[1]})
        
        trade_table = ""
        for row in trade_rows:
            pnl = row[10] or 0
            pnl_class = "green" if pnl > 0 else "red"
            trade_table += f"""
            <tr>
                <td>{row[0][:8]}</td>
                <td>{row[1]}</td>
                <td>{row[2]}</td>
                <td>${row[3]:.2f}</td>
                <td>{row[4]:.8f}</td>
                <td>${pnl:.2f}</td>
            </tr>
            """
        
        open_table = ""
        if open_rows:
            for row in open_rows:
                open_table += f"""
                <tr>
                    <td>{row[0][:8]}</td>
                    <td>{row[1]}</td>
                    <td>{row[2]}</td>
                    <td>${row[3]:.2f}</td>
                    <td>{row[4]:.8f}</td>
                    <td>${row[5]:.2f}</td>
                    <td>${row[6]:.2f}</td>
                </tr>
                """
        else:
            open_table = "<tr><td colspan='7'>No open positions</td></tr>"
        
        # Calculate stats
        if equity_rows:
            current_equity = equity_rows[0][1]
            start_equity = equity_rows[-1][1]
            total_return = ((current_equity - start_equity) / start_equity * 100) if start_equity > 0 else 0
        else:
            current_equity = 350.0
            total_return = 0.0
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>SentinelTrader Dashboard</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #0f0f0f;
            color: #fff;
        }}
        .header {{
            margin-bottom: 30px;
        }}
        h1 {{
            margin: 0;
            font-size: 32px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: #1a1a1a;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #00ff88;
        }}
        .stat-label {{
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            margin-top: 8px;
        }}
        .positive {{
            color: #00ff88;
        }}
        .negative {{
            color: #ff4444;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: #1a1a1a;
            border-radius: 8px;
            overflow: hidden;
        }}
        th {{
            background: #2a2a2a;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 1px solid #333;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #222;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        .green {{ color: #00ff88; }}
        .red {{ color: #ff4444; }}
        .section {{
            margin-bottom: 40px;
        }}
        h2 {{
            font-size: 20px;
            margin: 0 0 15px 0;
            border-bottom: 2px solid #00ff88;
            padding-bottom: 10px;
        }}
        .timestamp {{
            font-size: 12px;
            color: #666;
            margin-top: 20px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔒 SentinelTrader</h1>
        <p>Autonomous BTC/USD Trading System</p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <div class="stat-label">Current Equity</div>
            <div class="stat-value">${current_equity:,.2f}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Total Return</div>
            <div class="stat-value {('positive' if total_return > 0 else 'negative')}">{total_return:+.2f}%</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Closed Trades</div>
            <div class="stat-value">{len(trade_rows)}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Open Positions</div>
            <div class="stat-value">{len(open_rows)}</div>
        </div>
    </div>
    
    <div class="section">
        <h2>📊 Open Positions</h2>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Strategy</th>
                    <th>Side</th>
                    <th>Entry</th>
                    <th>Size</th>
                    <th>Stop</th>
                    <th>Target</th>
                </tr>
            </thead>
            <tbody>
                {open_table}
            </tbody>
        </table>
    </div>
    
    <div class="section">
        <h2>📈 Recent Trades</h2>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Strategy</th>
                    <th>Side</th>
                    <th>Entry</th>
                    <th>Size</th>
                    <th>P&L</th>
                </tr>
            </thead>
            <tbody>
                {trade_table}
            </tbody>
        </table>
    </div>
    
    <div class="timestamp">
        Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
    </div>
</body>
</html>
        """
        
        dashboard_path = Path('dashboard/index.html')
        dashboard_path.parent.mkdir(parents=True, exist_ok=True)
        dashboard_path.write_text(html)
        logger.debug("Dashboard generated")
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
