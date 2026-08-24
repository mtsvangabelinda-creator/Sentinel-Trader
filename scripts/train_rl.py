"""
Train RL agent on historical trades for SentinelTrader
"""
import asyncio
from adaptive.rl_agent import RLAgent
from utils.logger import setup_logger
from database.queries import Queries
from config.settings import settings

logger = setup_logger(__name__)

async def train_agents():
    """Train RL agents for both strategies"""
    logger.info("Starting RL agent training...")
    
    for strategy in ["arbitrage", "meme"]:
        try:
            agent = RLAgent(strategy)
            
            # Simulate training data
            trade_history = {
                "trades": [],
                "pnls": [],
                "holding_times": []
            }
            
            # Train agent
            success = await agent.train(trade_history)
            
            if success:
                # Save model
                model_path = f"models/rl_agent_{strategy}.pt"
                await agent.save_model(model_path)
                logger.info(f"RL agent trained and saved for {strategy}")
            else:
                logger.warning(f"RL agent training failed for {strategy}")
        
        except Exception as e:
            logger.error(f"RL training error for {strategy}: {e}")

if __name__ == "__main__":
    asyncio.run(train_agents())
