"""
Trading Intelligence System - Pattern Matching Engine
======================================================
DEL 3: Finder lignende historiske setups og analyserer outcomes.

Setup Definition:
- Regime type (trend, volatility, liquidity)
- EMA crossover tilstand
- Stokastisk niveau
- RSI niveau
- Correlation status

Output:
- Historiske matches med similarity score
- Success rate for fremtidige bevægelser
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

from .regime import MarketRegime, TrendState, VolatilityState, LiquidityState

logger = logging.getLogger(__name__)


class EMACrossState(Enum):
    """EMA crossover tilstande"""
    BULLISH_CROSS = "BULLISH_CROSS"  # EMA9 krydser over EMA21
    BEARISH_CROSS = "BEARISH_CROSS"  # EMA9 krydser under EMA21
    BULLISH_ALIGNED = "BULLISH_ALIGNED"  # EMA9 > EMA21 (ingen kryds)
    BEARISH_ALIGNED = "BEARISH_ALIGNED"  # EMA9 < EMA21 (ingen kryds)


class StochLevel(Enum):
    """Stokastisk niveauer"""
    OVERSOLD = "OVERSOLD"  # < 20
    LOW = "LOW"  # 20-40
    NEUTRAL = "NEUTRAL"  # 40-60
    HIGH = "HIGH"  # 60-80
    OVERBOUGHT = "OVERBOUGHT"  # > 80


class RSILevel(Enum):
    """RSI niveauer"""
    OVERSOLD = "OVERSOLD"  # < 30
    LOW = "LOW"  # 30-45
    NEUTRAL = "NEUTRAL"  # 45-55
    HIGH = "HIGH"  # 55-70
    OVERBOUGHT = "OVERBOUGHT"  # > 70


@dataclass
class MarketSetup:
    """Definition af et markedssetup"""
    timestamp: datetime
    price: float

    # Regime komponenter
    trend: TrendState
    volatility: VolatilityState
    liquidity: LiquidityState

    # Tekniske indikatorer
    ema_cross: EMACrossState
    stoch_level: StochLevel
    rsi_level: RSILevel

    # Råværdier
    rsi_value: float
    stoch_k: float
    stoch_d: float
    adx_value: float

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat() if hasattr(self.timestamp, 'isoformat') else str(self.timestamp),
            'price': round(self.price, 2),
            'trend': self.trend.value,
            'volatility': self.volatility.value,
            'liquidity': self.liquidity.value,
            'ema_cross': self.ema_cross.value,
            'stoch_level': self.stoch_level.value,
            'rsi_level': self.rsi_level.value,
            'rsi_value': round(self.rsi_value, 1),
            'stoch_k': round(self.stoch_k, 1),
            'adx_value': round(self.adx_value, 1)
        }

    def get_features(self) -> Tuple:
        """Returnerer tuple af features til sammenligning"""
        return (
            self.trend.value,
            self.volatility.value,
            self.liquidity.value,
            self.ema_cross.value,
            self.stoch_level.value,
            self.rsi_level.value
        )


@dataclass
class PatternMatch:
    """Et historisk pattern match"""
    setup: MarketSetup
    similarity_score: float  # 0-1

    # Outcomes (prisændringer efter setup)
    outcome_1h: Optional[float] = None  # % ændring efter 1 time (eller 1 bar)
    outcome_4h: Optional[float] = None  # % ændring efter 4 timer (eller 4 bars)
    outcome_24h: Optional[float] = None  # % ændring efter 24 timer (eller 24 bars)

    # Success (om prisen gik i forventet retning)
    was_bullish_success: Optional[bool] = None
    was_bearish_success: Optional[bool] = None

    def to_dict(self) -> Dict:
        return {
            'setup': self.setup.to_dict(),
            'similarity_score': round(self.similarity_score, 2),
            'outcome_1h': round(self.outcome_1h, 2) if self.outcome_1h else None,
            'outcome_4h': round(self.outcome_4h, 2) if self.outcome_4h else None,
            'outcome_24h': round(self.outcome_24h, 2) if self.outcome_24h else None
        }


@dataclass
class PatternAnalysis:
    """Resultat af pattern analyse"""
    current_setup: MarketSetup
    matches: List[PatternMatch]
    total_matches: int

    # Success rates
    bullish_success_rate: float  # % af matches hvor prisen steg
    bearish_success_rate: float  # % af matches hvor prisen faldt
    avg_outcome_24h: float  # Gennemsnitlig prisændring efter 24h

    # Prediction
    predicted_direction: str  # "BULLISH", "BEARISH", "NEUTRAL"
    prediction_confidence: float  # 0-1

    def to_dict(self) -> Dict:
        return {
            'current_setup': self.current_setup.to_dict(),
            'total_matches': self.total_matches,
            'bullish_success_rate': round(self.bullish_success_rate, 1),
            'bearish_success_rate': round(self.bearish_success_rate, 1),
            'avg_outcome_24h': round(self.avg_outcome_24h, 2),
            'predicted_direction': self.predicted_direction,
            'prediction_confidence': round(self.prediction_confidence, 2),
            'top_matches': [m.to_dict() for m in self.matches[:5]]
        }


class PatternMatcher:
    """
    Finder lignende historiske setups og analyserer outcomes.
    """

    def __init__(self, min_similarity: float = 0.7,
                 lookback_bars_1h: int = 1,
                 lookback_bars_4h: int = 4,
                 lookback_bars_24h: int = 24):
        """
        Args:
            min_similarity: Minimum similarity score for match (0-1)
            lookback_bars_*: Antal bars til outcome-beregning
        """
        self.min_similarity = min_similarity
        self.lookback_1h = lookback_bars_1h
        self.lookback_4h = lookback_bars_4h
        self.lookback_24h = lookback_bars_24h

    def _classify_stoch(self, stoch_k: float) -> StochLevel:
        """Klassificerer stokastisk niveau"""
        if stoch_k < 20:
            return StochLevel.OVERSOLD
        elif stoch_k < 40:
            return StochLevel.LOW
        elif stoch_k < 60:
            return StochLevel.NEUTRAL
        elif stoch_k < 80:
            return StochLevel.HIGH
        else:
            return StochLevel.OVERBOUGHT

    def _classify_rsi(self, rsi: float) -> RSILevel:
        """Klassificerer RSI niveau"""
        if rsi < 30:
            return RSILevel.OVERSOLD
        elif rsi < 45:
            return RSILevel.LOW
        elif rsi < 55:
            return RSILevel.NEUTRAL
        elif rsi < 70:
            return RSILevel.HIGH
        else:
            return RSILevel.OVERBOUGHT

    def _detect_ema_cross(self, df: pd.DataFrame, idx: int) -> EMACrossState:
        """Detekterer EMA crossover tilstand"""
        if idx < 1 or 'EMA_9' not in df.columns or 'EMA_21' not in df.columns:
            return EMACrossState.BULLISH_ALIGNED

        ema9_now = df['EMA_9'].iloc[idx]
        ema21_now = df['EMA_21'].iloc[idx]
        ema9_prev = df['EMA_9'].iloc[idx-1]
        ema21_prev = df['EMA_21'].iloc[idx-1]

        # Check for kryds
        if ema9_prev <= ema21_prev and ema9_now > ema21_now:
            return EMACrossState.BULLISH_CROSS
        elif ema9_prev >= ema21_prev and ema9_now < ema21_now:
            return EMACrossState.BEARISH_CROSS
        elif ema9_now > ema21_now:
            return EMACrossState.BULLISH_ALIGNED
        else:
            return EMACrossState.BEARISH_ALIGNED

    def create_setup(self, df: pd.DataFrame, idx: int,
                     regime: MarketRegime) -> MarketSetup:
        """
        Opretter et MarketSetup fra data.

        Args:
            df: DataFrame med indikatorer
            idx: Index i DataFrame
            regime: MarketRegime for denne periode

        Returns:
            MarketSetup objekt
        """
        row = df.iloc[idx]

        return MarketSetup(
            timestamp=df.index[idx],
            price=row['Close'],
            trend=regime.trend,
            volatility=regime.volatility,
            liquidity=regime.liquidity,
            ema_cross=self._detect_ema_cross(df, idx),
            stoch_level=self._classify_stoch(row.get('Stoch_K', 50)),
            rsi_level=self._classify_rsi(row.get('RSI', 50)),
            rsi_value=row.get('RSI', 50),
            stoch_k=row.get('Stoch_K', 50),
            stoch_d=row.get('Stoch_D', 50),
            adx_value=row.get('ADX', 20)
        )

    def calculate_similarity(self, setup1: MarketSetup, setup2: MarketSetup) -> float:
        """
        Beregner similarity score mellem to setups.

        Giver point for hver matchende feature.

        Returns:
            Similarity score (0-1)
        """
        features1 = setup1.get_features()
        features2 = setup2.get_features()

        matches = sum(1 for f1, f2 in zip(features1, features2) if f1 == f2)
        total = len(features1)

        return matches / total

    def calculate_outcome(self, df: pd.DataFrame, idx: int,
                          forward_bars: int) -> Optional[float]:
        """
        Beregner prisændring efter N bars.

        Returns:
            Procent ændring eller None hvis ikke nok data
        """
        if idx + forward_bars >= len(df):
            return None

        price_now = df['Close'].iloc[idx]
        price_future = df['Close'].iloc[idx + forward_bars]

        return ((price_future - price_now) / price_now) * 100

    def find_matches(self, df: pd.DataFrame, regimes: List[MarketRegime],
                     current_setup: MarketSetup) -> List[PatternMatch]:
        """
        Finder historiske matches for et setup.

        Args:
            df: DataFrame med historisk data og indikatorer
            regimes: Liste af MarketRegime for hver periode
            current_setup: Det nuværende setup at matche

        Returns:
            Liste af PatternMatch objekter sorteret efter similarity
        """
        matches = []

        # Start fra index 30 for at have nok data til regime
        for i in range(30, len(df) - self.lookback_24h):
            if i >= len(regimes):
                break

            # Opret setup for denne periode
            historical_setup = self.create_setup(df, i, regimes[i-30])

            # Beregn similarity
            similarity = self.calculate_similarity(current_setup, historical_setup)

            if similarity >= self.min_similarity:
                # Beregn outcomes
                outcome_1h = self.calculate_outcome(df, i, self.lookback_1h)
                outcome_4h = self.calculate_outcome(df, i, self.lookback_4h)
                outcome_24h = self.calculate_outcome(df, i, self.lookback_24h)

                match = PatternMatch(
                    setup=historical_setup,
                    similarity_score=similarity,
                    outcome_1h=outcome_1h,
                    outcome_4h=outcome_4h,
                    outcome_24h=outcome_24h,
                    was_bullish_success=outcome_24h > 0 if outcome_24h else None,
                    was_bearish_success=outcome_24h < 0 if outcome_24h else None
                )
                matches.append(match)

        # Sorter efter similarity
        matches.sort(key=lambda m: m.similarity_score, reverse=True)

        return matches

    def analyze_patterns(self, df: pd.DataFrame, regimes: List[MarketRegime],
                         current_regime: MarketRegime) -> PatternAnalysis:
        """
        Udfører komplet pattern analyse.

        Args:
            df: DataFrame med historisk data
            regimes: Liste af MarketRegime
            current_regime: Nuværende regime

        Returns:
            PatternAnalysis med matches og predictions
        """
        # Opret nuværende setup
        current_setup = self.create_setup(df, len(df)-1, current_regime)

        # Find matches
        matches = self.find_matches(df, regimes, current_setup)

        if not matches:
            return PatternAnalysis(
                current_setup=current_setup,
                matches=[],
                total_matches=0,
                bullish_success_rate=50.0,
                bearish_success_rate=50.0,
                avg_outcome_24h=0.0,
                predicted_direction="NEUTRAL",
                prediction_confidence=0.0
            )

        # Beregn success rates
        bullish_successes = sum(1 for m in matches if m.was_bullish_success)
        bearish_successes = sum(1 for m in matches if m.was_bearish_success)
        total_with_outcome = sum(1 for m in matches if m.outcome_24h is not None)

        bullish_rate = (bullish_successes / total_with_outcome * 100) if total_with_outcome > 0 else 50
        bearish_rate = (bearish_successes / total_with_outcome * 100) if total_with_outcome > 0 else 50

        # Gennemsnitlig outcome
        outcomes = [m.outcome_24h for m in matches if m.outcome_24h is not None]
        avg_outcome = np.mean(outcomes) if outcomes else 0

        # Prediction
        if bullish_rate > 60:
            predicted_direction = "BULLISH"
            prediction_confidence = (bullish_rate - 50) / 50  # 0-1 scale
        elif bearish_rate > 60:
            predicted_direction = "BEARISH"
            prediction_confidence = (bearish_rate - 50) / 50
        else:
            predicted_direction = "NEUTRAL"
            prediction_confidence = 1 - abs(bullish_rate - 50) / 50

        # Juster confidence baseret på antal matches
        if len(matches) < 5:
            prediction_confidence *= 0.5
        elif len(matches) < 10:
            prediction_confidence *= 0.75

        return PatternAnalysis(
            current_setup=current_setup,
            matches=matches,
            total_matches=len(matches),
            bullish_success_rate=bullish_rate,
            bearish_success_rate=bearish_rate,
            avg_outcome_24h=avg_outcome,
            predicted_direction=predicted_direction,
            prediction_confidence=min(prediction_confidence, 1.0)
        )

    def get_pattern_summary(self, analysis: PatternAnalysis) -> str:
        """
        Genererer læsbar opsummering af pattern analyse.
        """
        if analysis.total_matches == 0:
            return "Ingen lignende historiske setups fundet."

        summary = []
        summary.append(f"Fundet {analysis.total_matches} lignende historiske setups")
        summary.append(f"Bullish success rate: {analysis.bullish_success_rate:.1f}%")
        summary.append(f"Gennemsnitlig 24h outcome: {analysis.avg_outcome_24h:+.2f}%")
        summary.append(f"Prediction: {analysis.predicted_direction} (confidence: {analysis.prediction_confidence:.0%})")

        return " | ".join(summary)
