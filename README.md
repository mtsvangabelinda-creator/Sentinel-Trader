SentinelTrader is a lightweight, single-asset (BTC/USD) day trading system designed to run indefinitely on a free cloud server. It combines three rule‑based strategies (Trend‑Following, Mean Reversion, Momentum Burst) that activate based on real‑time market regime detection. A built‑in Sentinel blocks toxic conditions, while an automatic optimization engine continuously searches for better parameters using Optuna, validates them in a shadow paper environment, and promotes winning configurations without human intervention.

The system progresses itself through three stages: historical backtest → live paper simulation → micro live test with real money—all on the same server. Once live, it trades autonomously and improves itself weekly.

**Built for:**
- Developers who want a fully automated, self‑evolving trading bot.
- Quant learners interested in realistic walk‑forward optimization and Bayesian A/B testing.
- Anyone who believes a profitable system can run on a $0/month server.

**Disclaimer:** This software is for educational purposes only. Trade at your own risk. Past performance does not guarantee future results.
