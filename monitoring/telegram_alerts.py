import logging
import aiohttp
import asyncio

logger = logging.getLogger(__name__)

class TelegramAlert:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"

    async def send_message(self, text):
        if not self.token or not self.chat_id:
            logger.warning("Telegram not configured")
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/sendMessage"
                payload = {'chat_id': self.chat_id, 'text': text}
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status != 200:
                        logger.debug(f"Telegram error: {resp.status}")
        except asyncio.TimeoutError:
            logger.debug("Telegram timeout")
        except Exception as e:
            logger.debug(f"Telegram error: {e}")

    async def send_error(self, error_text):
        await self.send_message(f"⚠️ ERROR: {error_text}")
