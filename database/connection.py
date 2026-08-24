import asyncpg
from typing import Optional
from config.settings import settings
from utils.logger import setup_logger

logger = setup_logger(__name__)

class Database:
    """PostgreSQL connection manager for SentinelTrader"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Create connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                settings.DATABASE_URL,
                min_size=5,
                max_size=20,
                command_timeout=10
            )
            logger.info("Database connection pool created")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise
    
    async def disconnect(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def execute(self, query: str, *args):
        """Execute query"""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args) -> list:
        """Fetch multiple rows"""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args) -> Optional[dict]:
        """Fetch single row"""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args):
        """Fetch single value"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

db = Database()
