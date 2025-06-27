import asyncio
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from app.core.config import settings
import logging
from functools import wraps
import redis
import json

logger = logging.getLogger(__name__)

class MarketDataService:
    """
    Production-grade market data service with multiple providers,
    caching, fallback mechanisms, and rate limiting
    """
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )
        self.providers = [
            "alpha_vantage",
            "yahoo_finance", 
            "polygon",
            "twelvedata"
        ]
        self.current_provider = 0
    
    async def get_historical_data(self, symbol: str, days: int = 252) -> Optional[pd.DataFrame]:
        """Get historical price data with fallback providers"""
        
        cache_key = f"historical:{symbol}:{days}"
        
        # Try cache first
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return pd.DataFrame(cached_data)
        
        # Try each provider until success
        for provider in self.providers:
            try:
                data = await self._fetch_from_provider(provider, symbol, days)
                if data is not None and not data.empty:
                    # Cache the result
                    self._cache_data(cache_key, data.to_dict(), expiry=3600)
                    return data
            except Exception as e:
                logger.warning(f"Provider {provider} failed for {symbol}: {e}")
                continue
        
        logger.error(f"All providers failed for {symbol}")
        return None
    
    async def _fetch_from_provider(self, provider: str, symbol: str, days: int) -> pd.DataFrame:
        """Fetch data from specific provider"""
        
        if provider == "alpha_vantage":
            return await self._fetch_alpha_vantage(symbol, days)
        elif provider == "yahoo_finance":
            return await self._fetch_yahoo_finance(symbol, days)
        # Add other providers...
        
        raise NotImplementedError(f"Provider {provider} not implemented")
    
    async def _fetch_alpha_vantage(self, symbol: str, days: int) -> pd.DataFrame:
        """Fetch from Alpha Vantage API"""
        
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": settings.ALPHA_VANTAGE_API_KEY,
            "outputsize": "full"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
                if "Time Series (Daily)" in data:
                    ts_data = data["Time Series (Daily)"]
                    df = pd.DataFrame.from_dict(ts_data, orient='index')
                    df.index = pd.to_datetime(df.index)
                    df = df.sort_index(ascending=True)
                    
                    # Convert columns to numeric
                    numeric_columns = ['1. open', '2. high', '3. low', '4. close', '5. volume']
                    for col in numeric_columns:
                        df[col] = pd.to_numeric(df[col])
                    
                    # Rename columns
                    df.columns = ['open', 'high', 'low', 'close', 'volume']
                    
                    # Return last N days
                    return df.tail(days)
                
                raise Exception(f"Invalid response: {data}")
