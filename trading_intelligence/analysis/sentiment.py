"""
Trading Intelligence System - Sentiment Analyzer
=================================================
DEL 2: Tracker korrelationer og market sentiment.

Korrelerede markeder:
- DXY (US Dollar Index)
- ^TNX (10-Year Treasury Yield)
- ^GSPC (S&P 500)
- SI=F (Silver futures)
- CL=F (Crude Oil)

Market Sentiment:
- RISK_ON: S&P up + DXY down + Gold up
- RISK_OFF: S&P down + DXY up + Gold up
- NEUTRAL: Andre kombinationer
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MarketSentiment(Enum):
    """Market sentiment tilstande"""
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    NEUTRAL = "NEUTRAL"
    UNCERTAIN = "UNCERTAIN"


@dataclass
class CorrelationData:
    """Container for korrelationsdata"""
    symbol: str
    symbol_name: str
    correlation: float
    rolling_correlation: float
    correlation_change: float  # Ændring i korrelation
    is_diverging: bool  # True hvis ændring > 0.3

    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'name': self.symbol_name,
            'correlation': round(float(self.correlation), 3),
            'rolling_correlation': round(float(self.rolling_correlation), 3),
            'correlation_change': round(float(self.correlation_change), 3),
            'is_diverging': bool(self.is_diverging)
        }


@dataclass
class SentimentReport:
    """Komplet sentiment rapport"""
    timestamp: datetime
    sentiment: MarketSentiment
    correlations: Dict[str, CorrelationData]

    # Underliggende bevægelser
    gold_change: float  # Procent ændring
    sp500_change: float
    dxy_change: float
    yields_change: float

    # Confidence
    confidence: float  # 0-1 baseret på hvor klart signalet er

    # Alerts
    divergence_alerts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'sentiment': self.sentiment.value,
            'confidence': round(self.confidence, 2),
            'gold_change_pct': round(self.gold_change, 2),
            'sp500_change_pct': round(self.sp500_change, 2),
            'dxy_change_pct': round(self.dxy_change, 2),
            'yields_change_pct': round(self.yields_change, 2),
            'correlations': {k: v.to_dict() for k, v in self.correlations.items()},
            'divergence_alerts': self.divergence_alerts
        }


class SentimentAnalyzer:
    """
    Analyserer market sentiment baseret på korrelationer og prisbevægelser.
    """

    SYMBOL_NAMES = {
        "DX-Y.NYB": "US Dollar Index",
        "^TNX": "10Y Treasury Yield",
        "^GSPC": "S&P 500",
        "SI=F": "Silver Futures",
        "CL=F": "Crude Oil Futures",
        "GC=F": "Gold Futures"
    }

    def __init__(self, correlation_period: int = 20,
                 divergence_threshold: float = 0.3,
                 change_lookback: int = 5):
        """
        Args:
            correlation_period: Periode til rolling correlation
            divergence_threshold: Ændring i korrelation der trigger alert
            change_lookback: Periode til at beregne prisændringer
        """
        self.correlation_period = correlation_period
        self.divergence_threshold = divergence_threshold
        self.change_lookback = change_lookback

    def calculate_correlations(self, gold_df: pd.DataFrame,
                                market_data: Dict[str, pd.DataFrame]) -> Dict[str, CorrelationData]:
        """
        Beregner korrelationer mellem guld og andre markeder.

        Args:
            gold_df: DataFrame med guld OHLCV
            market_data: Dict med symbol -> DataFrame

        Returns:
            Dict med symbol -> CorrelationData
        """
        correlations = {}
        gold_returns = gold_df['Close'].pct_change().dropna()

        for symbol, df in market_data.items():
            if df.empty or 'Close' not in df.columns:
                continue

            try:
                other_returns = df['Close'].pct_change().dropna()

                # Synkroniser data
                combined = pd.DataFrame({
                    'gold': gold_returns,
                    'other': other_returns
                }).dropna()

                if len(combined) < self.correlation_period:
                    continue

                # Fuld korrelation
                full_corr = combined['gold'].corr(combined['other'])

                # Rolling korrelation (seneste)
                rolling = combined['gold'].rolling(self.correlation_period).corr(combined['other'])
                current_rolling = rolling.iloc[-1] if not rolling.empty else full_corr

                # Korrelation før (for at måle ændring)
                prev_rolling = rolling.iloc[-self.correlation_period] if len(rolling) > self.correlation_period else full_corr
                corr_change = current_rolling - prev_rolling

                # Check for divergens
                is_diverging = abs(corr_change) > self.divergence_threshold

                correlations[symbol] = CorrelationData(
                    symbol=symbol,
                    symbol_name=self.SYMBOL_NAMES.get(symbol, symbol),
                    correlation=full_corr,
                    rolling_correlation=current_rolling,
                    correlation_change=corr_change,
                    is_diverging=is_diverging
                )

            except Exception as e:
                logger.warning(f"Fejl ved korrelationsberegning for {symbol}: {e}")

        return correlations

    def calculate_price_changes(self, gold_df: pd.DataFrame,
                                 market_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """
        Beregner prisændringer for alle markeder.

        Returns:
            Dict med symbol -> procent ændring
        """
        changes = {}

        # Guld
        if len(gold_df) >= self.change_lookback:
            gold_change = (gold_df['Close'].iloc[-1] / gold_df['Close'].iloc[-self.change_lookback] - 1) * 100
            changes['GC=F'] = gold_change

        # Andre markeder
        for symbol, df in market_data.items():
            if len(df) >= self.change_lookback:
                change = (df['Close'].iloc[-1] / df['Close'].iloc[-self.change_lookback] - 1) * 100
                changes[symbol] = change

        return changes

    def determine_sentiment(self, gold_change: float, sp500_change: float,
                            dxy_change: float) -> Tuple[MarketSentiment, float]:
        """
        Bestemmer market sentiment baseret på prisændringer.

        Logic:
        - RISK_ON: S&P up + DXY down + Gold up (reflation)
        - RISK_OFF: S&P down + DXY up + Gold up (safe haven)
        - NEUTRAL: Andre kombinationer

        Returns:
            Tuple af (sentiment, confidence)
        """
        # Thresholds for "op" og "ned"
        up_threshold = 0.3  # > 0.3% = op
        down_threshold = -0.3  # < -0.3% = ned

        gold_up = gold_change > up_threshold
        gold_down = gold_change < down_threshold
        sp_up = sp500_change > up_threshold
        sp_down = sp500_change < down_threshold
        dxy_up = dxy_change > up_threshold
        dxy_down = dxy_change < down_threshold

        # RISK_ON: Alt stiger undtagen dollar (reflation/inflation trade)
        if sp_up and dxy_down and gold_up:
            confidence = min(abs(sp500_change) + abs(dxy_change) + abs(gold_change), 3) / 3
            return MarketSentiment.RISK_ON, confidence

        # RISK_OFF: Safe haven - S&P ned, dollar op, guld op
        if sp_down and dxy_up and gold_up:
            confidence = min(abs(sp500_change) + abs(dxy_change) + abs(gold_change), 3) / 3
            return MarketSentiment.RISK_OFF, confidence

        # Alternative RISK_OFF: S&P ned og guld op (uanset dollar)
        if sp_down and gold_up:
            confidence = min(abs(sp500_change) + abs(gold_change), 2) / 2 * 0.7
            return MarketSentiment.RISK_OFF, confidence

        # Alternative RISK_ON: S&P op og guld op og dollar ned
        if sp_up and gold_up:
            confidence = min(abs(sp500_change) + abs(gold_change), 2) / 2 * 0.7
            return MarketSentiment.RISK_ON, confidence

        # UNCERTAIN: Modstridende signaler
        if (gold_up and sp_up and dxy_up) or (gold_down and sp_down and dxy_down):
            return MarketSentiment.UNCERTAIN, 0.3

        # NEUTRAL: Ingen klart signal
        return MarketSentiment.NEUTRAL, 0.5

    def analyze(self, gold_df: pd.DataFrame,
                market_data: Dict[str, pd.DataFrame]) -> SentimentReport:
        """
        Udfører komplet sentiment analyse.

        Args:
            gold_df: DataFrame med guld OHLCV
            market_data: Dict med symbol -> DataFrame for korrelerede markeder

        Returns:
            SentimentReport med alle data
        """
        # Beregn korrelationer
        correlations = self.calculate_correlations(gold_df, market_data)

        # Beregn prisændringer
        changes = self.calculate_price_changes(gold_df, market_data)

        # Hent ændringer for sentiment-beregning
        gold_change = changes.get('GC=F', 0)
        sp500_change = changes.get('^GSPC', 0)
        dxy_change = changes.get('DX-Y.NYB', 0)
        yields_change = changes.get('^TNX', 0)

        # Bestem sentiment
        sentiment, confidence = self.determine_sentiment(gold_change, sp500_change, dxy_change)

        # Generer divergence alerts
        alerts = []
        for symbol, corr_data in correlations.items():
            if corr_data.is_diverging:
                direction = "styrket" if corr_data.correlation_change > 0 else "svækket"
                alerts.append(
                    f"{corr_data.symbol_name} korrelation {direction} markant "
                    f"({corr_data.correlation_change:+.2f})"
                )

        # Opret rapport
        timestamp = gold_df.index[-1] if hasattr(gold_df.index[-1], 'isoformat') else datetime.now()

        report = SentimentReport(
            timestamp=timestamp,
            sentiment=sentiment,
            correlations=correlations,
            gold_change=gold_change,
            sp500_change=sp500_change,
            dxy_change=dxy_change,
            yields_change=yields_change,
            confidence=confidence,
            divergence_alerts=alerts
        )

        logger.info(f"Sentiment: {sentiment.value} (confidence: {confidence:.2f})")
        return report

    def get_correlation_matrix(self, gold_df: pd.DataFrame,
                                market_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Opretter korrelationsmatrix mellem alle markeder.

        Returns:
            DataFrame med korrelationsmatrix
        """
        # Kombiner alle returns
        all_returns = pd.DataFrame()

        # Tilføj guld
        gold_returns = gold_df['Close'].pct_change().dropna()
        all_returns['Gold'] = gold_returns

        # Tilføj andre markeder
        for symbol, df in market_data.items():
            if 'Close' in df.columns:
                name = self.SYMBOL_NAMES.get(symbol, symbol)
                returns = df['Close'].pct_change().dropna()
                all_returns[name] = returns

        # Beregn korrelationsmatrix
        return all_returns.corr()

    def get_rolling_correlations(self, gold_df: pd.DataFrame,
                                  market_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Beregner rolling correlations for alle markeder over tid.

        Returns:
            DataFrame med rolling correlations (kolonner = markeder)
        """
        gold_returns = gold_df['Close'].pct_change().dropna()
        rolling_corrs = pd.DataFrame(index=gold_returns.index)

        for symbol, df in market_data.items():
            if 'Close' in df.columns:
                name = self.SYMBOL_NAMES.get(symbol, symbol)
                other_returns = df['Close'].pct_change().dropna()

                # Synkroniser
                combined = pd.DataFrame({
                    'gold': gold_returns,
                    'other': other_returns
                }).dropna()

                # Rolling correlation
                rolling = combined['gold'].rolling(self.correlation_period).corr(combined['other'])
                rolling_corrs[name] = rolling

        return rolling_corrs.dropna()
