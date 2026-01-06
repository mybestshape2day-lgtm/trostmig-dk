"""
Trading Intelligence System - Konfiguration
============================================
Centrale indstillinger for hele systemet.
"""

from dataclasses import dataclass, field
from typing import List
from pathlib import Path

# Basis stier
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "database" / "trading_data.db"

@dataclass
class SymbolConfig:
    """Konfiguration for handelssymboler"""
    # Primært symbol - Micro Gold Futures (MGC)
    # Brug "MGC=F" for Micro Gold eller "GC=F" for standard Gold
    PRIMARY_SYMBOL: str = "MGC=F"

    # Alternative symbols
    MICRO_GOLD: str = "MGC=F"      # Micro Gold Futures
    STANDARD_GOLD: str = "GC=F"   # Standard Gold Futures

    # Korrelerede markeder
    CORRELATED_SYMBOLS: List[str] = field(default_factory=lambda: [
        "DX-Y.NYB",    # US Dollar Index (DXY)
        "^TNX",        # 10-Year Treasury Yield
        "^GSPC",       # S&P 500
        "SI=F",        # Sølv Futures
        "CL=F",        # Crude Oil Futures
    ])

    # Navne til visning
    SYMBOL_NAMES: dict = field(default_factory=lambda: {
        "MGC=F": "Micro Gold Futures",
        "GC=F": "Gold Futures",
        "DX-Y.NYB": "US Dollar Index",
        "^TNX": "10Y Treasury Yield",
        "^GSPC": "S&P 500",
        "SI=F": "Silver Futures",
        "CL=F": "Crude Oil Futures",
    })


@dataclass
class IndicatorConfig:
    """Konfiguration for tekniske indikatorer"""
    # EMA perioder
    EMA_PERIODS: List[int] = field(default_factory=lambda: [9, 21, 50, 200])

    # Stokastisk
    STOCH_K_PERIOD: int = 14
    STOCH_D_PERIOD: int = 3
    STOCH_SMOOTH_K: int = 3

    # RSI
    RSI_PERIOD: int = 14
    RSI_OVERBOUGHT: int = 70
    RSI_OVERSOLD: int = 30

    # MACD
    MACD_FAST: int = 12
    MACD_SLOW: int = 26
    MACD_SIGNAL: int = 9

    # Bollinger Bands
    BB_PERIOD: int = 20
    BB_STD: int = 2

    # ATR
    ATR_PERIOD: int = 14

    # ADX
    ADX_PERIOD: int = 14


@dataclass
class DataConfig:
    """Konfiguration for data-indsamling"""
    # Standard periode for historisk data (dage)
    DEFAULT_PERIOD_DAYS: int = 90

    # Interval for data
    INTERVAL: str = "1d"  # Daglig data

    # Timeout for API kald (sekunder)
    API_TIMEOUT: int = 30


# Globale instanser
SYMBOLS = SymbolConfig()
INDICATORS = IndicatorConfig()
DATA = DataConfig()
