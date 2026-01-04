"""
Analysis Module - AI Intelligence Layer
========================================
Fase 2: Markedsanalyse og signalgenerering.

Moduler:
- regime: Regime Detection (trend, volatilitet, likviditet)
- sentiment: Correlation Tracker med market sentiment
- patterns: Pattern Matching Engine
- signals: Signal Generator
- dashboard: Visualisering
"""

from .regime import RegimeDetector, MarketRegime, TrendState, VolatilityState, LiquidityState
from .sentiment import SentimentAnalyzer, SentimentReport, MarketSentiment
from .patterns import PatternMatcher, PatternAnalysis
from .signals import SignalGenerator, TradingSignal, SignalType, SignalStrength
from .dashboard import Dashboard
