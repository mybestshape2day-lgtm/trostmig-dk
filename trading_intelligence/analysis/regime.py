"""
Trading Intelligence System - Regime Detection
===============================================
DEL 1: Klassificerer nuværende markedstilstand.

Output:
- Trend: STRONG_UPTREND, WEAK_UPTREND, RANGING, WEAK_DOWNTREND, STRONG_DOWNTREND
- Volatility: HIGH_VOL, NORMAL_VOL, LOW_VOL
- Liquidity: HIGH_LIQUIDITY, NORMAL_LIQUIDITY, LOW_LIQUIDITY
- Combined Regime: Samlet markedstilstand
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TrendState(Enum):
    """Trend tilstande"""
    STRONG_UPTREND = "STRONG_UPTREND"
    WEAK_UPTREND = "WEAK_UPTREND"
    RANGING = "RANGING"
    WEAK_DOWNTREND = "WEAK_DOWNTREND"
    STRONG_DOWNTREND = "STRONG_DOWNTREND"


class VolatilityState(Enum):
    """Volatilitet tilstande"""
    HIGH_VOL = "HIGH_VOL"
    NORMAL_VOL = "NORMAL_VOL"
    LOW_VOL = "LOW_VOL"


class LiquidityState(Enum):
    """Likviditet tilstande"""
    HIGH_LIQUIDITY = "HIGH_LIQUIDITY"
    NORMAL_LIQUIDITY = "NORMAL_LIQUIDITY"
    LOW_LIQUIDITY = "LOW_LIQUIDITY"


@dataclass
class MarketRegime:
    """Container for komplet markedsregime"""
    timestamp: datetime
    trend: TrendState
    volatility: VolatilityState
    liquidity: LiquidityState

    # Underliggende værdier
    adx_value: float
    ema_slope: float
    atr_ratio: float
    volume_ratio: float

    # Trend detaljer
    ema_9: float
    ema_21: float
    ema_50: float
    price: float

    @property
    def combined_regime(self) -> str:
        """Returnerer kombineret regime string"""
        return f"{self.trend.value} + {self.volatility.value} + {self.liquidity.value}"

    @property
    def is_trending(self) -> bool:
        """Er markedet i trend?"""
        return self.trend in [TrendState.STRONG_UPTREND, TrendState.STRONG_DOWNTREND,
                              TrendState.WEAK_UPTREND, TrendState.WEAK_DOWNTREND]

    @property
    def is_bullish(self) -> bool:
        """Er trenden bullish?"""
        return self.trend in [TrendState.STRONG_UPTREND, TrendState.WEAK_UPTREND]

    @property
    def is_bearish(self) -> bool:
        """Er trenden bearish?"""
        return self.trend in [TrendState.STRONG_DOWNTREND, TrendState.WEAK_DOWNTREND]

    def to_dict(self) -> Dict:
        """Konverter til dictionary for database lagring"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'trend': self.trend.value,
            'volatility': self.volatility.value,
            'liquidity': self.liquidity.value,
            'combined_regime': self.combined_regime,
            'adx_value': round(self.adx_value, 2),
            'ema_slope': round(self.ema_slope, 4),
            'atr_ratio': round(self.atr_ratio, 2),
            'volume_ratio': round(self.volume_ratio, 2),
            'price': round(self.price, 2)
        }


class RegimeDetector:
    """
    Detekterer markedsregime baseret på tekniske indikatorer.

    Bruger:
    - ADX til trend styrke
    - EMA slope til trend retning
    - ATR til volatilitet
    - Volume til likviditet
    """

    def __init__(self, adx_trending_threshold: float = 25,
                 adx_ranging_threshold: float = 20,
                 vol_high_threshold: float = 1.5,
                 vol_low_threshold: float = 0.7,
                 liq_high_threshold: float = 1.5,
                 liq_low_threshold: float = 0.7,
                 ema_slope_period: int = 5):
        """
        Args:
            adx_trending_threshold: ADX over dette = trending marked
            adx_ranging_threshold: ADX under dette = ranging marked
            vol_high_threshold: ATR ratio over dette = høj volatilitet
            vol_low_threshold: ATR ratio under dette = lav volatilitet
            liq_high_threshold: Volume ratio over dette = høj likviditet
            liq_low_threshold: Volume ratio under dette = lav likviditet
            ema_slope_period: Periode til beregning af EMA slope
        """
        self.adx_trending = adx_trending_threshold
        self.adx_ranging = adx_ranging_threshold
        self.vol_high = vol_high_threshold
        self.vol_low = vol_low_threshold
        self.liq_high = liq_high_threshold
        self.liq_low = liq_low_threshold
        self.ema_slope_period = ema_slope_period

    def detect_trend(self, df: pd.DataFrame) -> Tuple[TrendState, float, float]:
        """
        Detekterer trend baseret på ADX og EMA slope.

        Args:
            df: DataFrame med ADX, EMA_9, EMA_21, EMA_50 kolonner

        Returns:
            Tuple af (TrendState, adx_value, ema_slope)
        """
        if 'ADX' not in df.columns:
            raise ValueError("DataFrame mangler ADX kolonne")

        latest = df.iloc[-1]
        adx = latest['ADX']

        # Beregn EMA slope (ændring over periode)
        if 'EMA_21' in df.columns and len(df) > self.ema_slope_period:
            ema_21_now = latest['EMA_21']
            ema_21_prev = df['EMA_21'].iloc[-self.ema_slope_period]
            ema_slope = (ema_21_now - ema_21_prev) / ema_21_prev * 100  # Procent ændring
        else:
            ema_slope = 0

        # Bestem trend retning fra EMA alignment
        price = latest['Close']
        ema_9 = latest.get('EMA_9', price)
        ema_21 = latest.get('EMA_21', price)
        ema_50 = latest.get('EMA_50', price)

        # Bullish alignment: price > ema_9 > ema_21 > ema_50
        bullish_alignment = price > ema_9 > ema_21 > ema_50
        # Bearish alignment: price < ema_9 < ema_21 < ema_50
        bearish_alignment = price < ema_9 < ema_21 < ema_50

        # Klassificer trend
        if adx > self.adx_trending:
            # Stærk trend
            if ema_slope > 0.5 or bullish_alignment:
                trend = TrendState.STRONG_UPTREND
            elif ema_slope < -0.5 or bearish_alignment:
                trend = TrendState.STRONG_DOWNTREND
            elif ema_slope > 0:
                trend = TrendState.WEAK_UPTREND
            else:
                trend = TrendState.WEAK_DOWNTREND
        elif adx < self.adx_ranging:
            # Ranging marked
            trend = TrendState.RANGING
        else:
            # Mellem trending og ranging
            if ema_slope > 0.2:
                trend = TrendState.WEAK_UPTREND
            elif ema_slope < -0.2:
                trend = TrendState.WEAK_DOWNTREND
            else:
                trend = TrendState.RANGING

        return trend, adx, ema_slope

    def detect_volatility(self, df: pd.DataFrame, period: int = 20) -> Tuple[VolatilityState, float]:
        """
        Klassificerer volatilitet baseret på ATR.

        Args:
            df: DataFrame med ATR kolonne
            period: Periode til gennemsnitsberegning

        Returns:
            Tuple af (VolatilityState, atr_ratio)
        """
        if 'ATR' not in df.columns:
            raise ValueError("DataFrame mangler ATR kolonne")

        current_atr = df['ATR'].iloc[-1]
        avg_atr = df['ATR'].iloc[-period:].mean()

        atr_ratio = current_atr / avg_atr if avg_atr > 0 else 1.0

        if atr_ratio > self.vol_high:
            vol_state = VolatilityState.HIGH_VOL
        elif atr_ratio < self.vol_low:
            vol_state = VolatilityState.LOW_VOL
        else:
            vol_state = VolatilityState.NORMAL_VOL

        return vol_state, atr_ratio

    def detect_liquidity(self, df: pd.DataFrame, period: int = 20) -> Tuple[LiquidityState, float]:
        """
        Vurderer likviditet baseret på volume.

        Args:
            df: DataFrame med Volume kolonne
            period: Periode til gennemsnitsberegning

        Returns:
            Tuple af (LiquidityState, volume_ratio)
        """
        if 'Volume' not in df.columns:
            logger.warning("Ingen Volume data - antager NORMAL_LIQUIDITY")
            return LiquidityState.NORMAL_LIQUIDITY, 1.0

        current_vol = df['Volume'].iloc[-1]
        avg_vol = df['Volume'].iloc[-period:].mean()

        # Håndter manglende volume data (f.eks. forex)
        if avg_vol == 0 or pd.isna(avg_vol):
            return LiquidityState.NORMAL_LIQUIDITY, 1.0

        vol_ratio = current_vol / avg_vol

        if vol_ratio > self.liq_high:
            liq_state = LiquidityState.HIGH_LIQUIDITY
        elif vol_ratio < self.liq_low:
            liq_state = LiquidityState.LOW_LIQUIDITY
        else:
            liq_state = LiquidityState.NORMAL_LIQUIDITY

        return liq_state, vol_ratio

    def detect_regime(self, df: pd.DataFrame) -> MarketRegime:
        """
        Detekterer komplet markedsregime.

        Args:
            df: DataFrame med OHLCV og indikatorer (ADX, ATR, EMAs)

        Returns:
            MarketRegime objekt med alle tilstande
        """
        # Valider input
        required_cols = ['Close', 'ADX', 'ATR']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Manglende kolonner: {missing}")

        # Detekter komponenter
        trend, adx_value, ema_slope = self.detect_trend(df)
        volatility, atr_ratio = self.detect_volatility(df)
        liquidity, volume_ratio = self.detect_liquidity(df)

        # Hent seneste værdier
        latest = df.iloc[-1]
        timestamp = df.index[-1] if hasattr(df.index[-1], 'isoformat') else datetime.now()

        regime = MarketRegime(
            timestamp=timestamp,
            trend=trend,
            volatility=volatility,
            liquidity=liquidity,
            adx_value=adx_value,
            ema_slope=ema_slope,
            atr_ratio=atr_ratio,
            volume_ratio=volume_ratio,
            ema_9=latest.get('EMA_9', latest['Close']),
            ema_21=latest.get('EMA_21', latest['Close']),
            ema_50=latest.get('EMA_50', latest['Close']),
            price=latest['Close']
        )

        logger.info(f"Regime detekteret: {regime.combined_regime}")
        return regime

    def detect_regime_history(self, df: pd.DataFrame) -> List[MarketRegime]:
        """
        Detekterer regime for hver dag i historisk data.

        Args:
            df: DataFrame med OHLCV og indikatorer

        Returns:
            Liste af MarketRegime objekter
        """
        regimes = []
        min_period = 30  # Minimum data til regime detection

        for i in range(min_period, len(df)):
            try:
                subset = df.iloc[:i+1]
                regime = self.detect_regime(subset)
                regimes.append(regime)
            except Exception as e:
                logger.warning(f"Kunne ikke detektere regime for index {i}: {e}")

        return regimes

    def get_regime_summary(self, regimes: List[MarketRegime]) -> Dict:
        """
        Genererer opsummering af regime historie.

        Args:
            regimes: Liste af MarketRegime objekter

        Returns:
            Dict med statistik
        """
        if not regimes:
            return {}

        trend_counts = {}
        vol_counts = {}
        liq_counts = {}

        for r in regimes:
            trend_counts[r.trend.value] = trend_counts.get(r.trend.value, 0) + 1
            vol_counts[r.volatility.value] = vol_counts.get(r.volatility.value, 0) + 1
            liq_counts[r.liquidity.value] = liq_counts.get(r.liquidity.value, 0) + 1

        total = len(regimes)

        return {
            'total_periods': total,
            'trend_distribution': {k: round(v/total*100, 1) for k, v in trend_counts.items()},
            'volatility_distribution': {k: round(v/total*100, 1) for k, v in vol_counts.items()},
            'liquidity_distribution': {k: round(v/total*100, 1) for k, v in liq_counts.items()},
            'current_regime': regimes[-1].to_dict() if regimes else None
        }
