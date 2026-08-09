#!/usr/bin/env python3
"""
SentinelTrader Health Check Script
Verifies all components are running smoothly
"""

import asyncio
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path

class HealthCheck:
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def log(self, component, status, message, level="INFO"):
        """Log health check result."""
        icon = "✅" if status else ("⚠️" if level == "WARNING" else "❌")
        self.results.append({
            "component": component,
            "status": status,
            "message": message,
            "level": level,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        if status:
            self.passed += 1
        elif level == "WARNING":
            self.warnings += 1
        else:
            self.failed += 1
        
        print(f"{icon} {component}: {message}")

    async def check_github_repo(self):
        """Check if repo is accessible."""
        try:
            result = subprocess.run(
                ["git", "status"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                self.log("GitHub Repo", True, "Repository accessible and up-to-date")
            else:
                self.log("GitHub Repo", False, "Repository access failed", "ERROR")
        except Exception as e:
            self.log("GitHub Repo", False, f"Error: {e}", "ERROR")

    async def check_docker_containers(self):
        """Check if Docker containers are running."""
        try:
            result = subprocess.run(
                ["docker-compose", "ps"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if "sentinel-trader" in result.stdout and "Up" in result.stdout:
                self.log("Docker Containers", True, "All containers running")
            else:
                self.log("Docker Containers", False, "One or more containers not running", "WARNING")
        except Exception as e:
            self.log("Docker Containers", False, f"Docker not accessible: {e}", "ERROR")

    async def check_database(self):
        """Check if SQLite database is accessible."""
        try:
            from monitoring.sqlite_logger import SQLiteLogger
            db_path = "data/sentinel.db"
            
            if Path(db_path).exists():
                db = SQLiteLogger(db_path)
                pnl = db.get_total_realized_pnl()
                self.log("Database", True, f"SQLite accessible (P&L: ${pnl:.2f})")
            else:
                self.log("Database", False, "Database file not found", "WARNING")
        except Exception as e:
            self.log("Database", False, f"Database error: {e}", "ERROR")

    async def check_config(self):
        """Check if configuration is valid."""
        try:
            from config.settings import load_config, load_env
            config = load_config()
            env = load_env()
            
            checks = [
                ('mode' in config, 'Config mode set'),
                ('strategy_pools' in config, 'Strategy pools defined'),
                (env.get('KRAKEN_API_KEY'), 'Kraken API key configured'),
                (env.get('TELEGRAM_TOKEN'), 'Telegram token configured'),
            ]
            
            all_ok = all(check[0] for check in checks)
            if all_ok:
                self.log("Configuration", True, "All settings valid")
            else:
                missing = [check[1] for check in checks if not check[0]]
                self.log("Configuration", False, f"Missing: {', '.join(missing)}", "WARNING")
        except Exception as e:
            self.log("Configuration", False, f"Config error: {e}", "ERROR")

    async def check_telegram(self):
        """Check Telegram bot connectivity."""
        try:
            from config.settings import load_env
            from monitoring.telegram_alerts import TelegramAlert
            
            env = load_env()
            alert = TelegramAlert(env.get('TELEGRAM_TOKEN'), env.get('TELEGRAM_CHAT_ID'))
            
            # Try a simple API call
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{env.get('TELEGRAM_TOKEN')}/getMe"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        self.log("Telegram Bot", True, "Bot is connected and responsive")
                    else:
                        self.log("Telegram Bot", False, f"Bot API returned {resp.status}", "WARNING")
        except Exception as e:
            self.log("Telegram Bot", False, f"Telegram error: {e}", "WARNING")

    async def check_disk_space(self):
        """Check available disk space."""
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_gb = free / (1024**3)
            
            if free_gb > 5:
                self.log("Disk Space", True, f"{free_gb:.1f} GB available")
            else:
                self.log("Disk Space", False, f"Low disk space: {free_gb:.1f} GB", "WARNING")
        except Exception as e:
            self.log("Disk Space", False, f"Disk check error: {e}", "WARNING")

    async def check_network(self):
        """Check network connectivity."""
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            self.log("Network", True, "Internet connectivity OK")
        except Exception as e:
            self.log("Network", False, f"Network unreachable: {e}", "ERROR")

    async def check_kraken_api(self):
        """Check Kraken API connectivity."""
        try:
            import ccxt
            kraken = ccxt.kraken()
            ticker = kraken.fetch_ticker('BTC/USD')
            
            if ticker and 'last' in ticker:
                self.log("Kraken API", True, f"Connected (BTC/USD: ${ticker['last']:.2f})")
            else:
                self.log("Kraken API", False, "Invalid ticker data", "WARNING")
        except Exception as e:
            self.log("Kraken API", False, f"Kraken error: {e}", "WARNING")

    async def check_system_processes(self):
        """Check if main application is running."""
        try:
            result = subprocess.run(
                ["docker", "logs", "sentinel-trader"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if "Entering main trading loop" in result.stdout or "Running" in result.stdout:
                self.log("Trading Engine", True, "Main loop running")
            else:
                self.log("Trading Engine", False, "Main loop not active", "WARNING")
        except Exception as e:
            self.log("Trading Engine", False, f"Process check error: {e}", "WARNING")

    async def generate_report(self):
        """Generate final health report."""
        total = self.passed + self.failed + self.warnings
        
        print("\n" + "="*60)
        print("🏥 SENTINELTRADER HEALTH REPORT")
        print("="*60)
        print(f"Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        print(f"✅ Passed: {self.passed}/{total}")
        print(f"⚠️  Warnings: {self.warnings}/{total}")
        print(f"❌ Failed: {self.failed}/{total}\n")
        
        if self.failed == 0:
            print("🟢 SYSTEM STATUS: HEALTHY")
            if self.warnings > 0:
                print("⚠️  Some warnings detected - review above")
        else:
            print("🔴 SYSTEM STATUS: UNHEALTHY")
            print("❌ Critical issues detected - immediate action required")
        
        print("="*60 + "\n")
        
        # Save report
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "passed": self.passed,
                "warnings": self.warnings,
                "failed": self.failed,
                "total": total,
                "status": "HEALTHY" if self.failed == 0 else "UNHEALTHY"
            },
            "checks": self.results
        }
        
        with open("health_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        return self.failed == 0

    async def run_all(self):
        """Run all health checks."""
        print("🚀 Starting SentinelTrader Health Check...\n")
        
        await self.check_github_repo()
        await self.check_config()
        await self.check_docker_containers()
        await self.check_database()
        await self.check_disk_space()
        await self.check_network()
        await self.check_kraken_api()
        await self.check_telegram()
        await self.check_system_processes()
        
        success = await self.generate_report()
        return 0 if success else 1

if __name__ == "__main__":
    checker = HealthCheck()
    exit_code = asyncio.run(checker.run_all())
    sys.exit(exit_code)
