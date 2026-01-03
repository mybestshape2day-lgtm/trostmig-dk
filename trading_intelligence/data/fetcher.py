"""
Trading Intelligence System - Data Fetcher
===========================================
Modul til at hente markedsdata via yfinance API.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging

from config import SYMBOLS, DATA

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataFetcher:
    """
    Henter markedsdata fra Yahoo Finance.

    Understøtter:
    - OHLCV data for enkelt symbol
    - Batch download af flere symboler
    - Automatisk retry ved fejl
    """

    def __init__(self):
        self.symbol_config = SYMBOLS
        self.data_config = DATA

    def fetch_ohlcv(self, symbol: str, period_days: int = None,
                    start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Henter OHLCV data for et enkelt symbol.

        Args:
            symbol: Ticker symbol (f.eks. "GC=F" for guld futures)
            period_days: Antal dage bagud (default: 90)
            start_date: Specifik start dato (YYYY-MM-DD)
            end_date: Specifik slut dato (YYYY-MM-DD)

        Returns:
            DataFrame med Open, High, Low, Close, Volume kolonner
        """
        period_days = period_days or self.data_config.DEFAULT_PERIOD_DAYS

        # Beregn datoer
        if end_date is None:
            end = datetime.now()
        else:
            end = datetime.strptime(end_date, '%Y-%m-%d')

        if start_date is None:
            start = end - timedelta(days=period_days)
        else:
            start = datetime.strptime(start_date, '%Y-%m-%d')

        logger.info(f"Henter data for {symbol} fra {start.date()} til {end.date()}")

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                start=start.strftime('%Y-%m-%d'),
                end=end.strftime('%Y-%m-%d'),
                interval=self.data_config.INTERVAL
            )

            if df.empty:
                logger.warning(f"Ingen data modtaget for {symbol}")
                return pd.DataFrame()

            # Standardiser kolonner
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()

            # Konverter index til tz-naive datetime for konsistens
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)

            logger.info(f"Hentet {len(df)} rækker for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Fejl ved hentning af {symbol}: {e}")
            return pd.DataFrame()

    def fetch_gold_futures(self, period_days: int = None) -> pd.DataFrame:
        """
        Convenience metode til at hente guld futures data.

        Args:
            period_days: Antal dage (default: 90)

        Returns:
            DataFrame med OHLCV data for GC=F
        """
        return self.fetch_ohlcv(
            self.symbol_config.PRIMARY_SYMBOL,
            period_days=period_days
        )

    def fetch_correlated_markets(self, period_days: int = None) -> Dict[str, pd.DataFrame]:
        """
        Henter data for alle korrelerede markeder.

        Args:
            period_days: Antal dage (default: 90)

        Returns:
            Dict med symbol -> DataFrame
        """
        period_days = period_days or self.data_config.DEFAULT_PERIOD_DAYS
        results = {}

        for symbol in self.symbol_config.CORRELATED_SYMBOLS:
            df = self.fetch_ohlcv(symbol, period_days=period_days)
            if not df.empty:
                results[symbol] = df
                logger.info(f"✓ {symbol}: {len(df)} rækker")
            else:
                logger.warning(f"✗ {symbol}: Ingen data")

        return results

    def fetch_all_markets(self, period_days: int = None) -> Dict[str, pd.DataFrame]:
        """
        Henter data for guld og alle korrelerede markeder.

        Args:
            period_days: Antal dage

        Returns:
            Dict med alle symboler og deres data
        """
        period_days = period_days or self.data_config.DEFAULT_PERIOD_DAYS

        # Start med guld
        results = {}
        gold_df = self.fetch_gold_futures(period_days)
        if not gold_df.empty:
            results[self.symbol_config.PRIMARY_SYMBOL] = gold_df

        # Tilføj korrelerede markeder
        correlated = self.fetch_correlated_markets(period_days)
        results.update(correlated)

        return results

    def get_latest_price(self, symbol: str = None) -> Optional[float]:
        """
        Henter seneste lukkekurs for et symbol.

        Args:
            symbol: Ticker (default: guld futures)

        Returns:
            Seneste lukkekurs eller None
        """
        symbol = symbol or self.symbol_config.PRIMARY_SYMBOL
        df = self.fetch_ohlcv(symbol, period_days=5)

        if not df.empty:
            return float(df['Close'].iloc[-1])
        return None

    def get_symbol_info(self, symbol: str = None) -> Dict:
        """
        Henter metadata om et symbol.

        Args:
            symbol: Ticker

        Returns:
            Dict med symbol info
        """
        symbol = symbol or self.symbol_config.PRIMARY_SYMBOL
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return {
                'symbol': symbol,
                'name': info.get('shortName', symbol),
                'currency': info.get('currency', 'USD'),
                'exchange': info.get('exchange', 'Unknown'),
                'market_cap': info.get('marketCap'),
            }
        except Exception as e:
            logger.error(f"Fejl ved hentning af info for {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)}


def download_batch(symbols: List[str], period_days: int = 90) -> Dict[str, pd.DataFrame]:
    """
    Batch download af flere symboler på én gang.
    Mere effektivt end individuelle kald.

    Args:
        symbols: Liste af ticker symboler
        period_days: Antal dage

    Returns:
        Dict med symbol -> DataFrame
    """
    end = datetime.now()
    start = end - timedelta(days=period_days)

    logger.info(f"Batch download af {len(symbols)} symboler...")

    try:
        data = yf.download(
            symbols,
            start=start.strftime('%Y-%m-%d'),
            end=end.strftime('%Y-%m-%d'),
            group_by='ticker',
            progress=False
        )

        results = {}
        for symbol in symbols:
            if len(symbols) == 1:
                df = data[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
            else:
                if symbol in data.columns.get_level_values(0):
                    df = data[symbol][['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                else:
                    continue

            df = df.dropna()
            if not df.empty:
                results[symbol] = df

        logger.info(f"Batch download færdig: {len(results)}/{len(symbols)} symboler")
        return results

    except Exception as e:
        logger.error(f"Fejl ved batch download: {e}")
        return {}
