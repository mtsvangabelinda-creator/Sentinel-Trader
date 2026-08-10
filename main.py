async def _initial_backtest(self):
    """Run initial backtest with forward test validation."""
    logger.info("🔄 Starting Stage 0 backtest (Kraken data)...")
    await self.alert.send_message("🔄 Starting Stage 0 backtest...\nFetching data from Kraken...")
    
    # Run backtest
    passed, metrics = await run_initial_backtest(self.config, self.db, self.alert)
    
    if not passed:
        logger.error("Initial backtest FAILED")
        await self.alert.send_error(
            f"❌ STAGE 0 FAILED\n"
            f"Metrics: {metrics}\n"
            f"Human review required."
        )
        sys.exit(1)
    
    logger.info("✅ Initial backtest PASSED")
    await self.alert.send_message(
        f"✅ Initial Backtest PASSED\n"
        f"Sharpe: {metrics['sharpe']:.2f}\n"
        f"Max DD: {metrics['max_dd']*100:.1f}%\n"
        f"Profit Factor: {metrics['profit_factor']:.2f}\n"
        f"Win Rate: {metrics['win_rate']*100:.1f}%\n"
        f"Trades: {metrics['num_trades']}\n\n"
        f"Running forward test..."
    )
    
    # Run forward test (5 days of out-of-sample data)
    fw_passed, fw_metrics = await run_forward_test(self.config, self.db, self.alert, days=5)
    
    if not fw_passed or fw_metrics.get('sharpe', 0) < 0.0:
        logger.warning("Forward test underperformed - staying in backtest")
        await self.alert.send_message(
            f"⚠️ Forward test underperformed\n"
            f"Backtest Sharpe: {metrics['sharpe']:.2f}\n"
            f"Forward Sharpe: {fw_metrics.get('sharpe', 0):.2f}\n\n"
            f"Adjusting parameters and retrying..."
        )
        return
    
    logger.info("✅ Forward test PASSED - Advancing to Stage 1")
    
    self.config['initial_config_done'] = True
    self.config.save()
    self.stage_file.write_text('PAPER')
    
    await self.alert.send_message(
        f"🟢 STAGE 0 & FORWARD TEST PASSED\n"
        f"Backtest Sharpe: {metrics['sharpe']:.2f}\n"
        f"Forward Test Sharpe: {fw_metrics['sharpe']:.2f}\n\n"
        f"✅ Transitioning to Stage 1 (Paper Trading)..."
    )
    
    self.mode = 'paper'
    self.config['mode'] = 'paper'
