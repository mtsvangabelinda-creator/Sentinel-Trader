import aiohttp
from typing import Dict, Optional
from utils.logger import setup_logger
from utils.helpers import exponential_backoff

logger = setup_logger(__name__)

class JupiterFetcher:
    """Fetch Solana DEX data from Jupiter"""
    
    BASE_URL = "https://quote-api.jup.ag/v6"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @exponential_backoff(max_retries=3)
    async def get_quote(self, input_mint: str, output_mint: str, amount: int) -> Optional[Dict]:
        """Get swap quote"""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        url = f"{self.BASE_URL}/quote"
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": amount,
            "slippageBps": 50
        }
        
        try:
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
        except Exception as e:
            logger.error(f"Jupiter quote error: {e}")
            raise
