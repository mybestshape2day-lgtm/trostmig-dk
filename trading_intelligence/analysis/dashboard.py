"""
Trading Intelligence System - Dashboard
=======================================
DEL 5: Visualisering af status, signals og historik.

Features:
- Current Status panel
- Price chart med indikatorer
- Correlation plot
- Signal historie
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

from .regime import MarketRegime, TrendState
from .sentiment import SentimentReport, MarketSentiment
from .patterns import PatternAnalysis
from .signals import TradingSignal, SignalType, SignalStrength

logger = logging.getLogger(__name__)


class Dashboard:
    """
    Genererer dashboard visualiseringer.
    """

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path(__file__).parent.parent / "visualization" / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Farver
        self.colors = {
            'bullish': '#2ECC71',
            'bearish': '#E74C3C',
            'neutral': '#95A5A6',
            'price': '#2E86AB',
            'ema_fast': '#E74C3C',
            'ema_slow': '#F39C12',
            'volume': '#3498DB',
            'signal_long': '#27AE60',
            'signal_short': '#C0392B',
            'background': '#1a1a2e',
            'text': '#FFFFFF'
        }

    def create_full_dashboard(self, df: pd.DataFrame,
                               regime: MarketRegime,
                               sentiment: SentimentReport,
                               pattern: PatternAnalysis,
                               signal: TradingSignal,
                               signals_history: List[TradingSignal] = None,
                               save: bool = True) -> Optional[Path]:
        """
        Opretter komplet dashboard med alle komponenter.

        Args:
            df: DataFrame med OHLCV og indikatorer
            regime: Nuværende MarketRegime
            sentiment: Nuværende SentimentReport
            pattern: Nuværende PatternAnalysis
            signal: Nuværende TradingSignal
            signals_history: Liste af historiske signals
            save: Gem som fil

        Returns:
            Sti til gemt fil
        """
        # Opret figur med grid layout
        fig = plt.figure(figsize=(20, 14))
        fig.patch.set_facecolor('#1a1a2e')

        gs = GridSpec(4, 3, figure=fig, height_ratios=[0.8, 2, 1, 1],
                      hspace=0.3, wspace=0.25)

        # Row 1: Status panels (3 kolonner)
        ax_regime = fig.add_subplot(gs[0, 0])
        ax_sentiment = fig.add_subplot(gs[0, 1])
        ax_signal = fig.add_subplot(gs[0, 2])

        # Row 2: Price chart (full width)
        ax_price = fig.add_subplot(gs[1, :])

        # Row 3: RSI og MACD
        ax_rsi = fig.add_subplot(gs[2, :2])
        ax_pattern = fig.add_subplot(gs[2, 2])

        # Row 4: Stochastic og Signal history
        ax_stoch = fig.add_subplot(gs[3, :2])
        ax_history = fig.add_subplot(gs[3, 2])

        # Tegn alle komponenter
        self._draw_regime_panel(ax_regime, regime)
        self._draw_sentiment_panel(ax_sentiment, sentiment)
        self._draw_signal_panel(ax_signal, signal)
        self._draw_price_chart(ax_price, df, signal)
        self._draw_rsi(ax_rsi, df)
        self._draw_pattern_panel(ax_pattern, pattern)
        self._draw_stochastic(ax_stoch, df)
        self._draw_signal_history(ax_history, signals_history or [])

        # Titel
        fig.suptitle(f'Gold Futures Trading Dashboard - {datetime.now().strftime("%Y-%m-%d %H:%M")}',
                     fontsize=16, fontweight='bold', color='white', y=0.98)

        plt.tight_layout()

        if save:
            filepath = self.output_dir / f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight',
                       facecolor=fig.get_facecolor(), edgecolor='none')
            plt.close()
            logger.info(f"Dashboard gemt: {filepath}")
            return filepath
        else:
            plt.show()
            return None

    def _style_panel(self, ax, title: str):
        """Fælles stil for info panels"""
        ax.set_facecolor('#16213e')
        ax.set_title(title, fontsize=12, fontweight='bold', color='white', pad=10)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

    def _draw_regime_panel(self, ax, regime: MarketRegime):
        """Tegner regime status panel"""
        self._style_panel(ax, "MARKET REGIME")

        # Trend farve
        if regime.is_bullish:
            trend_color = self.colors['bullish']
        elif regime.is_bearish:
            trend_color = self.colors['bearish']
        else:
            trend_color = self.colors['neutral']

        # Tegn info
        ax.text(0.5, 0.75, regime.trend.value, fontsize=14, fontweight='bold',
                ha='center', va='center', color=trend_color,
                transform=ax.transAxes)

        ax.text(0.5, 0.45, f"Vol: {regime.volatility.value}", fontsize=10,
                ha='center', va='center', color='white', transform=ax.transAxes)

        ax.text(0.5, 0.25, f"Liq: {regime.liquidity.value}", fontsize=10,
                ha='center', va='center', color='white', transform=ax.transAxes)

        ax.text(0.5, 0.08, f"ADX: {regime.adx_value:.1f}", fontsize=9,
                ha='center', va='center', color='#888', transform=ax.transAxes)

    def _draw_sentiment_panel(self, ax, sentiment: SentimentReport):
        """Tegner sentiment panel"""
        self._style_panel(ax, "MARKET SENTIMENT")

        # Sentiment farve
        if sentiment.sentiment == MarketSentiment.RISK_ON:
            color = self.colors['bullish']
        elif sentiment.sentiment == MarketSentiment.RISK_OFF:
            color = self.colors['bearish']
        else:
            color = self.colors['neutral']

        ax.text(0.5, 0.7, sentiment.sentiment.value, fontsize=14, fontweight='bold',
                ha='center', va='center', color=color, transform=ax.transAxes)

        ax.text(0.5, 0.45, f"Confidence: {sentiment.confidence:.0%}", fontsize=10,
                ha='center', va='center', color='white', transform=ax.transAxes)

        # Prisændringer
        changes = f"GC: {sentiment.gold_change:+.1f}%  SPX: {sentiment.sp500_change:+.1f}%"
        ax.text(0.5, 0.2, changes, fontsize=9,
                ha='center', va='center', color='#888', transform=ax.transAxes)

    def _draw_signal_panel(self, ax, signal: TradingSignal):
        """Tegner signal panel"""
        self._style_panel(ax, "CURRENT SIGNAL")

        # Signal farve
        if signal.signal_type == SignalType.LONG_ENTRY:
            color = self.colors['signal_long']
            icon = "▲ LONG"
        elif signal.signal_type == SignalType.SHORT_ENTRY:
            color = self.colors['signal_short']
            icon = "▼ SHORT"
        else:
            color = self.colors['neutral']
            icon = "— NO SIGNAL"

        ax.text(0.5, 0.7, icon, fontsize=14, fontweight='bold',
                ha='center', va='center', color=color, transform=ax.transAxes)

        ax.text(0.5, 0.45, f"Strength: {signal.strength.value}", fontsize=10,
                ha='center', va='center', color='white', transform=ax.transAxes)

        ax.text(0.5, 0.25, f"Criteria: {signal.criteria_met}/{signal.criteria_total}", fontsize=10,
                ha='center', va='center', color='white', transform=ax.transAxes)

        if signal.suggested_stop_loss:
            ax.text(0.5, 0.08, f"SL: ${signal.suggested_stop_loss:.0f} | TP: ${signal.suggested_take_profit:.0f}",
                    fontsize=8, ha='center', va='center', color='#888', transform=ax.transAxes)

    def _draw_price_chart(self, ax, df: pd.DataFrame, signal: TradingSignal):
        """Tegner pris chart med EMAs"""
        ax.set_facecolor('#16213e')

        # Pris
        ax.plot(df.index, df['Close'], color=self.colors['price'],
                linewidth=1.5, label='Close')

        # EMAs
        if 'EMA_9' in df.columns:
            ax.plot(df.index, df['EMA_9'], color=self.colors['ema_fast'],
                    linewidth=1, linestyle='--', alpha=0.7, label='EMA 9')
        if 'EMA_21' in df.columns:
            ax.plot(df.index, df['EMA_21'], color=self.colors['ema_slow'],
                    linewidth=1, linestyle='--', alpha=0.7, label='EMA 21')

        # Bollinger Bands
        if all(col in df.columns for col in ['BB_Upper', 'BB_Lower']):
            ax.fill_between(df.index, df['BB_Upper'], df['BB_Lower'],
                           alpha=0.1, color='white')

        # Signal marker
        if signal.signal_type != SignalType.NO_SIGNAL:
            marker_color = self.colors['signal_long'] if signal.signal_type == SignalType.LONG_ENTRY else self.colors['signal_short']
            marker = '^' if signal.signal_type == SignalType.LONG_ENTRY else 'v'
            ax.scatter([df.index[-1]], [signal.price], color=marker_color,
                      marker=marker, s=200, zorder=5, edgecolors='white', linewidth=2)

        ax.set_ylabel('Price (USD)', color='white')
        ax.tick_params(colors='white')
        ax.legend(loc='upper left', facecolor='#16213e', edgecolor='none',
                  labelcolor='white', fontsize=8)
        ax.grid(True, alpha=0.2, color='white')
        ax.set_title(f'Gold Futures (GC) - ${df["Close"].iloc[-1]:.2f}',
                    fontsize=11, color='white')

        # Formater x-akse
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, color='white')

    def _draw_rsi(self, ax, df: pd.DataFrame):
        """Tegner RSI indikator"""
        ax.set_facecolor('#16213e')

        if 'RSI' not in df.columns:
            ax.text(0.5, 0.5, 'RSI data ikke tilgængelig', ha='center',
                   va='center', color='white', transform=ax.transAxes)
            return

        ax.plot(df.index, df['RSI'], color='#9B59B6', linewidth=1)
        ax.axhline(y=70, color=self.colors['bearish'], linestyle='--', alpha=0.5)
        ax.axhline(y=30, color=self.colors['bullish'], linestyle='--', alpha=0.5)
        ax.fill_between(df.index, 70, 100, alpha=0.1, color=self.colors['bearish'])
        ax.fill_between(df.index, 0, 30, alpha=0.1, color=self.colors['bullish'])

        ax.set_ylim(0, 100)
        ax.set_ylabel('RSI', color='white')
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.2, color='white')

        # Seneste værdi
        latest_rsi = df['RSI'].iloc[-1]
        ax.text(0.98, 0.9, f'{latest_rsi:.1f}', transform=ax.transAxes,
               ha='right', va='top', color='white', fontsize=10,
               bbox=dict(boxstyle='round', facecolor='#9B59B6', alpha=0.8))

    def _draw_stochastic(self, ax, df: pd.DataFrame):
        """Tegner Stochastic indikator"""
        ax.set_facecolor('#16213e')

        if 'Stoch_K' not in df.columns:
            ax.text(0.5, 0.5, 'Stochastic data ikke tilgængelig', ha='center',
                   va='center', color='white', transform=ax.transAxes)
            return

        ax.plot(df.index, df['Stoch_K'], color='#3498DB', linewidth=1, label='%K')
        if 'Stoch_D' in df.columns:
            ax.plot(df.index, df['Stoch_D'], color='#F39C12', linewidth=1, label='%D')

        ax.axhline(y=80, color=self.colors['bearish'], linestyle='--', alpha=0.5)
        ax.axhline(y=20, color=self.colors['bullish'], linestyle='--', alpha=0.5)
        ax.fill_between(df.index, 80, 100, alpha=0.1, color=self.colors['bearish'])
        ax.fill_between(df.index, 0, 20, alpha=0.1, color=self.colors['bullish'])

        ax.set_ylim(0, 100)
        ax.set_ylabel('Stochastic', color='white')
        ax.tick_params(colors='white')
        ax.legend(loc='upper left', facecolor='#16213e', edgecolor='none',
                 labelcolor='white', fontsize=8)
        ax.grid(True, alpha=0.2, color='white')

    def _draw_pattern_panel(self, ax, pattern: PatternAnalysis):
        """Tegner pattern analyse panel"""
        self._style_panel(ax, "PATTERN ANALYSIS")

        if pattern.total_matches == 0:
            ax.text(0.5, 0.5, 'Ingen matches', fontsize=12,
                   ha='center', va='center', color='#888', transform=ax.transAxes)
            return

        # Prediction
        if pattern.predicted_direction == "BULLISH":
            color = self.colors['bullish']
        elif pattern.predicted_direction == "BEARISH":
            color = self.colors['bearish']
        else:
            color = self.colors['neutral']

        ax.text(0.5, 0.8, pattern.predicted_direction, fontsize=12, fontweight='bold',
                ha='center', va='center', color=color, transform=ax.transAxes)

        ax.text(0.5, 0.6, f"Matches: {pattern.total_matches}", fontsize=10,
                ha='center', va='center', color='white', transform=ax.transAxes)

        ax.text(0.5, 0.4, f"Bull: {pattern.bullish_success_rate:.0f}%", fontsize=10,
                ha='center', va='center', color=self.colors['bullish'], transform=ax.transAxes)

        ax.text(0.5, 0.25, f"Bear: {pattern.bearish_success_rate:.0f}%", fontsize=10,
                ha='center', va='center', color=self.colors['bearish'], transform=ax.transAxes)

        ax.text(0.5, 0.08, f"Conf: {pattern.prediction_confidence:.0%}", fontsize=9,
                ha='center', va='center', color='#888', transform=ax.transAxes)

    def _draw_signal_history(self, ax, signals: List[TradingSignal]):
        """Tegner signal historik"""
        self._style_panel(ax, "SIGNAL HISTORY")

        if not signals:
            ax.text(0.5, 0.5, 'Ingen signaler', fontsize=12,
                   ha='center', va='center', color='#888', transform=ax.transAxes)
            return

        # Vis seneste 5 signaler
        recent = [s for s in signals if s.signal_type != SignalType.NO_SIGNAL][-5:]

        for i, signal in enumerate(reversed(recent)):
            y_pos = 0.85 - (i * 0.16)

            if signal.signal_type == SignalType.LONG_ENTRY:
                color = self.colors['signal_long']
                icon = "▲"
            else:
                color = self.colors['signal_short']
                icon = "▼"

            date_str = signal.timestamp.strftime('%m-%d') if hasattr(signal.timestamp, 'strftime') else str(signal.timestamp)[:5]
            text = f"{icon} {date_str} ${signal.price:.0f} ({signal.strength.value})"

            ax.text(0.5, y_pos, text, fontsize=9,
                   ha='center', va='center', color=color, transform=ax.transAxes)

    def create_simple_status(self, regime: MarketRegime,
                              sentiment: SentimentReport,
                              signal: TradingSignal) -> str:
        """
        Genererer simpel tekst-status til konsol output.

        Returns:
            Formateret status tekst
        """
        lines = []
        lines.append("=" * 60)
        lines.append("  GOLD FUTURES TRADING STATUS")
        lines.append("=" * 60)

        # Regime
        lines.append(f"\n  REGIME: {regime.combined_regime}")
        lines.append(f"    ADX: {regime.adx_value:.1f} | Price: ${regime.price:.2f}")

        # Sentiment
        lines.append(f"\n  SENTIMENT: {sentiment.sentiment.value} ({sentiment.confidence:.0%})")
        lines.append(f"    Gold: {sentiment.gold_change:+.2f}% | S&P: {sentiment.sp500_change:+.2f}%")

        # Signal
        signal_icon = "▲ LONG" if signal.signal_type == SignalType.LONG_ENTRY else \
                      "▼ SHORT" if signal.signal_type == SignalType.SHORT_ENTRY else "— NONE"
        lines.append(f"\n  SIGNAL: {signal_icon} ({signal.strength.value})")
        lines.append(f"    Criteria: {signal.criteria_met}/{signal.criteria_total}")

        if signal.reasons:
            lines.append(f"    Reasons: {', '.join(signal.reasons[:3])}")

        if signal.suggested_stop_loss:
            lines.append(f"    SL: ${signal.suggested_stop_loss:.2f} | TP: ${signal.suggested_take_profit:.2f}")
            lines.append(f"    R:R = 1:{signal.risk_reward_ratio:.1f}")

        lines.append("\n" + "=" * 60)

        return "\n".join(lines)
