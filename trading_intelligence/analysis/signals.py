"""
Trading Intelligence System - Signal Generator
===============================================
DEL 4: Genererer trading signals baseret på alle analysekomponenter.

Signal Logic:
- Kombinerer regime, indikatorer, patterns og sentiment
- Tæller opfyldte kriterier for signal styrke
- Output: JSON med signal, styrke, reasons
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
import json
import logging

from .regime import MarketRegime, TrendState, VolatilityState
from .sentiment import SentimentReport, MarketSentiment
from .patterns import PatternAnalysis, EMACrossState, StochLevel, RSILevel

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Signal typer"""
    LONG_ENTRY = "LONG_ENTRY"
    SHORT_ENTRY = "SHORT_ENTRY"
    LONG_EXIT = "LONG_EXIT"
    SHORT_EXIT = "SHORT_EXIT"
    NO_SIGNAL = "NO_SIGNAL"


class SignalStrength(Enum):
    """Signal styrke"""
    STRONG = "STRONG"  # 5/5 eller 4/5 kriterier
    MEDIUM = "MEDIUM"  # 3/5 kriterier
    WEAK = "WEAK"  # 2/5 kriterier
    NO_SIGNAL = "NO_SIGNAL"


@dataclass
class TradingSignal:
    """Komplet trading signal"""
    timestamp: datetime
    signal_type: SignalType
    strength: SignalStrength
    price: float

    # Underliggende analyse
    regime: str
    pattern_success_rate: float
    sentiment: str

    # Opfyldte kriterier
    criteria_met: int
    criteria_total: int
    reasons: List[str] = field(default_factory=list)

    # Risiko parametre
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None
    risk_reward_ratio: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat() if hasattr(self.timestamp, 'isoformat') else str(self.timestamp),
            'signal': self.signal_type.value,
            'strength': self.strength.value,
            'price': round(self.price, 2),
            'regime': self.regime,
            'pattern_success_rate': round(self.pattern_success_rate, 1),
            'sentiment': self.sentiment,
            'criteria_met': self.criteria_met,
            'criteria_total': self.criteria_total,
            'reasons': self.reasons,
            'suggested_stop_loss': round(self.suggested_stop_loss, 2) if self.suggested_stop_loss else None,
            'suggested_take_profit': round(self.suggested_take_profit, 2) if self.suggested_take_profit else None,
            'risk_reward_ratio': round(self.risk_reward_ratio, 2) if self.risk_reward_ratio else None
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class SignalGenerator:
    """
    Genererer trading signals baseret på alle analysekomponenter.

    Long Entry kriterier:
    1. Regime = STRONG_UPTREND eller WEAK_UPTREND
    2. EMA_9 crosses above EMA_21
    3. Stochastic < 30 (oversold)
    4. Pattern match success rate > 60%
    5. Market sentiment = RISK_ON

    Short Entry kriterier:
    1. Regime = STRONG_DOWNTREND eller WEAK_DOWNTREND
    2. EMA_9 crosses below EMA_21
    3. Stochastic > 70 (overbought)
    4. Pattern match success rate > 60% (bearish)
    5. Market sentiment = RISK_OFF
    """

    def __init__(self,
                 min_criteria_strong: int = 4,
                 min_criteria_medium: int = 3,
                 min_criteria_weak: int = 2,
                 min_pattern_success: float = 60,
                 atr_stop_multiplier: float = 2.0,
                 atr_tp_multiplier: float = 3.0):
        """
        Args:
            min_criteria_*: Minimum kriterier for signal styrke
            min_pattern_success: Minimum pattern success rate
            atr_stop_multiplier: ATR multiplier for stop loss
            atr_tp_multiplier: ATR multiplier for take profit
        """
        self.min_strong = min_criteria_strong
        self.min_medium = min_criteria_medium
        self.min_weak = min_criteria_weak
        self.min_pattern_success = min_pattern_success
        self.atr_stop = atr_stop_multiplier
        self.atr_tp = atr_tp_multiplier

    def _check_long_criteria(self, df: pd.DataFrame,
                              regime: MarketRegime,
                              pattern: PatternAnalysis,
                              sentiment: SentimentReport) -> Tuple[int, List[str]]:
        """
        Checker long entry kriterier.

        Returns:
            Tuple af (antal opfyldte kriterier, liste af reasons)
        """
        criteria_met = 0
        reasons = []
        latest = df.iloc[-1]

        # 1. Trend regime (uptrend)
        if regime.trend in [TrendState.STRONG_UPTREND, TrendState.WEAK_UPTREND]:
            criteria_met += 1
            reasons.append(f"Trend: {regime.trend.value}")

        # 2. EMA crossover (bullish)
        if 'EMA_9' in df.columns and 'EMA_21' in df.columns:
            ema9 = latest['EMA_9']
            ema21 = latest['EMA_21']
            ema9_prev = df['EMA_9'].iloc[-2] if len(df) > 1 else ema9
            ema21_prev = df['EMA_21'].iloc[-2] if len(df) > 1 else ema21

            # Bullish cross eller bullish aligned
            if ema9_prev <= ema21_prev and ema9 > ema21:
                criteria_met += 1
                reasons.append("EMA9 bullish cross over EMA21")
            elif ema9 > ema21:
                criteria_met += 0.5  # Halvt point for alignment uden kryds
                reasons.append("EMA bullish aligned")

        # 3. Stochastic oversold
        if 'Stoch_K' in df.columns:
            stoch = latest['Stoch_K']
            if stoch < 30:
                criteria_met += 1
                reasons.append(f"Stochastic oversold ({stoch:.1f})")
            elif stoch < 50:
                criteria_met += 0.5
                reasons.append(f"Stochastic neutral-low ({stoch:.1f})")

        # 4. Pattern success rate
        if pattern.bullish_success_rate > self.min_pattern_success:
            criteria_met += 1
            reasons.append(f"Pattern bullish {pattern.bullish_success_rate:.0f}% success")

        # 5. Market sentiment
        if sentiment.sentiment == MarketSentiment.RISK_ON:
            criteria_met += 1
            reasons.append("Sentiment: RISK_ON")
        elif sentiment.sentiment == MarketSentiment.NEUTRAL:
            criteria_met += 0.5
            reasons.append("Sentiment: NEUTRAL")

        return int(criteria_met), reasons

    def _check_short_criteria(self, df: pd.DataFrame,
                               regime: MarketRegime,
                               pattern: PatternAnalysis,
                               sentiment: SentimentReport) -> Tuple[int, List[str]]:
        """
        Checker short entry kriterier.

        Returns:
            Tuple af (antal opfyldte kriterier, liste af reasons)
        """
        criteria_met = 0
        reasons = []
        latest = df.iloc[-1]

        # 1. Trend regime (downtrend)
        if regime.trend in [TrendState.STRONG_DOWNTREND, TrendState.WEAK_DOWNTREND]:
            criteria_met += 1
            reasons.append(f"Trend: {regime.trend.value}")

        # 2. EMA crossover (bearish)
        if 'EMA_9' in df.columns and 'EMA_21' in df.columns:
            ema9 = latest['EMA_9']
            ema21 = latest['EMA_21']
            ema9_prev = df['EMA_9'].iloc[-2] if len(df) > 1 else ema9
            ema21_prev = df['EMA_21'].iloc[-2] if len(df) > 1 else ema21

            # Bearish cross eller bearish aligned
            if ema9_prev >= ema21_prev and ema9 < ema21:
                criteria_met += 1
                reasons.append("EMA9 bearish cross under EMA21")
            elif ema9 < ema21:
                criteria_met += 0.5
                reasons.append("EMA bearish aligned")

        # 3. Stochastic overbought
        if 'Stoch_K' in df.columns:
            stoch = latest['Stoch_K']
            if stoch > 70:
                criteria_met += 1
                reasons.append(f"Stochastic overbought ({stoch:.1f})")
            elif stoch > 50:
                criteria_met += 0.5
                reasons.append(f"Stochastic neutral-high ({stoch:.1f})")

        # 4. Pattern success rate (bearish)
        if pattern.bearish_success_rate > self.min_pattern_success:
            criteria_met += 1
            reasons.append(f"Pattern bearish {pattern.bearish_success_rate:.0f}% success")

        # 5. Market sentiment
        if sentiment.sentiment == MarketSentiment.RISK_OFF:
            criteria_met += 1
            reasons.append("Sentiment: RISK_OFF")
        elif sentiment.sentiment == MarketSentiment.NEUTRAL:
            criteria_met += 0.5
            reasons.append("Sentiment: NEUTRAL")

        return int(criteria_met), reasons

    def _determine_strength(self, criteria_met: int) -> SignalStrength:
        """Bestemmer signal styrke baseret på opfyldte kriterier"""
        if criteria_met >= self.min_strong:
            return SignalStrength.STRONG
        elif criteria_met >= self.min_medium:
            return SignalStrength.MEDIUM
        elif criteria_met >= self.min_weak:
            return SignalStrength.WEAK
        else:
            return SignalStrength.NO_SIGNAL

    def _calculate_risk_params(self, price: float, atr: float,
                                is_long: bool) -> Tuple[float, float, float]:
        """
        Beregner stop loss, take profit og risk/reward.

        Returns:
            Tuple af (stop_loss, take_profit, risk_reward_ratio)
        """
        if is_long:
            stop_loss = price - (atr * self.atr_stop)
            take_profit = price + (atr * self.atr_tp)
        else:
            stop_loss = price + (atr * self.atr_stop)
            take_profit = price - (atr * self.atr_tp)

        risk = abs(price - stop_loss)
        reward = abs(take_profit - price)
        rr_ratio = reward / risk if risk > 0 else 0

        return stop_loss, take_profit, rr_ratio

    def generate_signal(self, df: pd.DataFrame,
                        regime: MarketRegime,
                        pattern: PatternAnalysis,
                        sentiment: SentimentReport) -> TradingSignal:
        """
        Genererer trading signal baseret på alle komponenter.

        Args:
            df: DataFrame med OHLCV og indikatorer
            regime: MarketRegime analyse
            pattern: PatternAnalysis
            sentiment: SentimentReport

        Returns:
            TradingSignal objekt
        """
        latest = df.iloc[-1]
        price = latest['Close']
        atr = latest.get('ATR', price * 0.02)  # Default 2% af pris

        # Check long kriterier
        long_criteria, long_reasons = self._check_long_criteria(df, regime, pattern, sentiment)
        long_strength = self._determine_strength(long_criteria)

        # Check short kriterier
        short_criteria, short_reasons = self._check_short_criteria(df, regime, pattern, sentiment)
        short_strength = self._determine_strength(short_criteria)

        # Bestem signal type baseret på stærkeste signal
        if long_strength != SignalStrength.NO_SIGNAL and long_criteria >= short_criteria:
            signal_type = SignalType.LONG_ENTRY
            strength = long_strength
            criteria_met = long_criteria
            reasons = long_reasons
            success_rate = pattern.bullish_success_rate
            stop_loss, take_profit, rr_ratio = self._calculate_risk_params(price, atr, True)

        elif short_strength != SignalStrength.NO_SIGNAL:
            signal_type = SignalType.SHORT_ENTRY
            strength = short_strength
            criteria_met = short_criteria
            reasons = short_reasons
            success_rate = pattern.bearish_success_rate
            stop_loss, take_profit, rr_ratio = self._calculate_risk_params(price, atr, False)

        else:
            signal_type = SignalType.NO_SIGNAL
            strength = SignalStrength.NO_SIGNAL
            criteria_met = max(long_criteria, short_criteria)
            reasons = ["Ikke nok kriterier opfyldt"]
            success_rate = 50
            stop_loss, take_profit, rr_ratio = None, None, None

        timestamp = df.index[-1] if hasattr(df.index[-1], 'isoformat') else datetime.now()

        signal = TradingSignal(
            timestamp=timestamp,
            signal_type=signal_type,
            strength=strength,
            price=price,
            regime=regime.combined_regime,
            pattern_success_rate=success_rate,
            sentiment=sentiment.sentiment.value,
            criteria_met=criteria_met,
            criteria_total=5,
            reasons=reasons,
            suggested_stop_loss=stop_loss,
            suggested_take_profit=take_profit,
            risk_reward_ratio=rr_ratio
        )

        logger.info(f"Signal genereret: {signal_type.value} ({strength.value})")
        return signal

    def generate_signal_history(self, df: pd.DataFrame,
                                 regimes: List[MarketRegime],
                                 patterns: List[PatternAnalysis],
                                 sentiments: List[SentimentReport]) -> List[TradingSignal]:
        """
        Genererer signals for historisk data.

        Bruges til backtesting og validering.
        """
        signals = []

        min_len = min(len(regimes), len(patterns), len(sentiments))

        for i in range(min_len):
            # Brug subset af data op til dette punkt
            idx = 30 + i  # Offset for regime beregning
            if idx >= len(df):
                break

            subset = df.iloc[:idx+1]
            signal = self.generate_signal(
                subset,
                regimes[i],
                patterns[i],
                sentiments[i]
            )
            signals.append(signal)

        return signals

    def evaluate_signals(self, signals: List[TradingSignal],
                         df: pd.DataFrame,
                         forward_periods: int = 24) -> Dict:
        """
        Evaluerer historiske signals mod faktiske outcomes.

        Returns:
            Dict med performance metrics
        """
        results = {
            'total_signals': 0,
            'long_signals': 0,
            'short_signals': 0,
            'profitable_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'avg_profit': 0,
            'avg_loss': 0,
            'profit_factor': 0
        }

        profits = []
        losses = []

        for signal in signals:
            if signal.signal_type == SignalType.NO_SIGNAL:
                continue

            results['total_signals'] += 1

            # Find index i df
            try:
                idx = df.index.get_loc(signal.timestamp)
            except:
                continue

            if idx + forward_periods >= len(df):
                continue

            entry_price = signal.price
            exit_price = df['Close'].iloc[idx + forward_periods]

            if signal.signal_type == SignalType.LONG_ENTRY:
                results['long_signals'] += 1
                pnl = (exit_price - entry_price) / entry_price * 100
            else:
                results['short_signals'] += 1
                pnl = (entry_price - exit_price) / entry_price * 100

            if pnl > 0:
                results['profitable_trades'] += 1
                profits.append(pnl)
            else:
                results['losing_trades'] += 1
                losses.append(abs(pnl))

        # Beregn metrics
        if results['total_signals'] > 0:
            results['win_rate'] = results['profitable_trades'] / results['total_signals'] * 100

        if profits:
            results['avg_profit'] = np.mean(profits)
        if losses:
            results['avg_loss'] = np.mean(losses)

        if results['avg_loss'] > 0:
            results['profit_factor'] = (
                sum(profits) / sum(losses) if losses else float('inf')
            )

        return results
