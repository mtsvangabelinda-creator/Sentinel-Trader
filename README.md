# SentinelTrader

An autonomous, zero-cost algorithmic trading bot for cryptocurrency markets.

## Features
- **Two Parallel Strategies**: Arbitrage (large-cap) + Meme (small-cap)
- **Adaptive Architecture**: 9-layer system with regime detection, genetic programming, and RL optimization
- **Zero API Costs**: 100% free data sources (Kraken, Binance, DexScreener)
- **Risk Management**: Adaptive stop-loss, take-profit, position sizing via RL
- **Walk-Forward Validation**: Prevents overfitting with OOS testing
- **Telegram Integration**: Real-time alerts and manual control
- **Prometheus + Grafana**: Live performance dashboard

## Quick Start

1. Fork/clone repo
2. Add GitHub Secrets (see below)
3. Deploy to Oracle Cloud via GitHub Actions

## GitHub Secrets Required
## Architecture

Layer 1: Data Harvester → Layer 2: Whitelist → Layer 3: Regime Detection → Layer 4: Alpha Evolution → Layer 5: Signal Engine → Layer 6: Priority Ranker → Layer 7: Execution → Layer 8: RL Agent → Layer 9: Oversight

## Deploy

GitHub Actions auto-deploys on push to main.

Access Grafana: `http://ORACLE_IP:3000`
