"""
Trading Intelligence System - Visualisering
============================================
Modul til at plotte pris, indikatorer og korrelationer.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

from config import SYMBOLS, BASE_DIR


class ChartGenerator:
    """
    Genererer visualiseringer for trading data.

    Understøtter:
    - Candlestick/linje charts
    - Indikator overlays
    - Multi-panel layouts
    - Korrelationsplots
    """

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or BASE_DIR / "visualization" / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.symbol_names = SYMBOLS.SYMBOL_NAMES

        # Stil indstillinger
        plt.style.use('seaborn-v0_8-darkgrid')
        self.colors = {
            'price': '#2E86AB',
            'ema_short': '#A23B72',
            'ema_long': '#F18F01',
            'volume': '#C73E1D',
            'bullish': '#2ECC71',
            'bearish': '#E74C3C',
            'neutral': '#95A5A6'
        }

    def plot_price_with_indicators(self, df: pd.DataFrame, symbol: str = "GC=F",
                                    save: bool = True) -> Optional[Path]:
        """
        Plotter pris med tekniske indikatorer i multi-panel layout.

        Args:
            df: DataFrame med OHLCV og indikatorer
            symbol: Ticker symbol
            save: Gem som fil

        Returns:
            Sti til gemt fil hvis save=True
        """
        fig, axes = plt.subplots(4, 1, figsize=(14, 12),
                                  gridspec_kw={'height_ratios': [3, 1, 1, 1]})
        fig.suptitle(f'{self.symbol_names.get(symbol, symbol)} - Teknisk Analyse',
                     fontsize=14, fontweight='bold')

        # Panel 1: Pris og EMAs
        ax1 = axes[0]
        ax1.plot(df.index, df['Close'], label='Close', color=self.colors['price'], linewidth=1.5)

        # Plot EMAs hvis de findes
        ema_cols = [col for col in df.columns if col.startswith('EMA_')]
        for i, col in enumerate(sorted(ema_cols)):
            color = plt.cm.viridis(i / max(len(ema_cols), 1))
            ax1.plot(df.index, df[col], label=col, linestyle='--', alpha=0.7)

        # Bollinger Bands
        if all(col in df.columns for col in ['BB_Upper', 'BB_Middle', 'BB_Lower']):
            ax1.fill_between(df.index, df['BB_Upper'], df['BB_Lower'],
                           alpha=0.1, color='gray', label='Bollinger Bands')
            ax1.plot(df.index, df['BB_Middle'], '--', color='gray', alpha=0.5)

        ax1.set_ylabel('Pris (USD)')
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)

        # Panel 2: RSI
        ax2 = axes[1]
        if 'RSI' in df.columns:
            ax2.plot(df.index, df['RSI'], color='purple', linewidth=1)
            ax2.axhline(y=70, color='red', linestyle='--', alpha=0.5)
            ax2.axhline(y=30, color='green', linestyle='--', alpha=0.5)
            ax2.fill_between(df.index, 70, 100, alpha=0.1, color='red')
            ax2.fill_between(df.index, 0, 30, alpha=0.1, color='green')
            ax2.set_ylim(0, 100)
        ax2.set_ylabel('RSI')
        ax2.grid(True, alpha=0.3)

        # Panel 3: MACD
        ax3 = axes[2]
        if all(col in df.columns for col in ['MACD', 'MACD_Signal', 'MACD_Hist']):
            ax3.plot(df.index, df['MACD'], label='MACD', color='blue', linewidth=1)
            ax3.plot(df.index, df['MACD_Signal'], label='Signal', color='orange', linewidth=1)

            # Histogram med farver
            colors = [self.colors['bullish'] if x >= 0 else self.colors['bearish']
                     for x in df['MACD_Hist']]
            ax3.bar(df.index, df['MACD_Hist'], color=colors, alpha=0.5, width=0.8)
            ax3.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
            ax3.legend(loc='upper left', fontsize=8)
        ax3.set_ylabel('MACD')
        ax3.grid(True, alpha=0.3)

        # Panel 4: Stokastisk
        ax4 = axes[3]
        if all(col in df.columns for col in ['Stoch_K', 'Stoch_D']):
            ax4.plot(df.index, df['Stoch_K'], label='%K', color='blue', linewidth=1)
            ax4.plot(df.index, df['Stoch_D'], label='%D', color='orange', linewidth=1)
            ax4.axhline(y=80, color='red', linestyle='--', alpha=0.5)
            ax4.axhline(y=20, color='green', linestyle='--', alpha=0.5)
            ax4.fill_between(df.index, 80, 100, alpha=0.1, color='red')
            ax4.fill_between(df.index, 0, 20, alpha=0.1, color='green')
            ax4.set_ylim(0, 100)
            ax4.legend(loc='upper left', fontsize=8)
        ax4.set_ylabel('Stokastisk')
        ax4.set_xlabel('Dato')
        ax4.grid(True, alpha=0.3)

        # Formater x-aksen
        for ax in axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()

        if save:
            filepath = self.output_dir / f"{symbol.replace('=', '_')}_technical_analysis.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            return filepath
        else:
            plt.show()
            return None

    def plot_correlation_matrix(self, corr_matrix: pd.DataFrame,
                                 save: bool = True) -> Optional[Path]:
        """
        Plotter korrelationsmatrix som heatmap.

        Args:
            corr_matrix: Korrelationsmatrix DataFrame
            save: Gem som fil

        Returns:
            Sti til gemt fil
        """
        fig, ax = plt.subplots(figsize=(10, 8))

        # Heatmap
        im = ax.imshow(corr_matrix, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)

        # Labels
        ax.set_xticks(np.arange(len(corr_matrix.columns)))
        ax.set_yticks(np.arange(len(corr_matrix.index)))
        ax.set_xticklabels(corr_matrix.columns, rotation=45, ha='right')
        ax.set_yticklabels(corr_matrix.index)

        # Tilføj værdier
        for i in range(len(corr_matrix.index)):
            for j in range(len(corr_matrix.columns)):
                value = corr_matrix.iloc[i, j]
                color = 'white' if abs(value) > 0.5 else 'black'
                ax.text(j, i, f'{value:.2f}', ha='center', va='center', color=color)

        # Colorbar
        cbar = plt.colorbar(im)
        cbar.set_label('Korrelation')

        ax.set_title('Korrelationsmatrix - Guld og Relaterede Markeder', fontweight='bold')
        plt.tight_layout()

        if save:
            filepath = self.output_dir / "correlation_matrix.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            return filepath
        else:
            plt.show()
            return None

    def plot_multi_asset(self, data: Dict[str, pd.DataFrame],
                         save: bool = True) -> Optional[Path]:
        """
        Plotter flere aktiver normaliseret til sammenligning.

        Args:
            data: Dict med symbol -> DataFrame
            save: Gem som fil

        Returns:
            Sti til gemt fil
        """
        fig, ax = plt.subplots(figsize=(14, 8))

        for symbol, df in data.items():
            if 'Close' not in df.columns or df.empty:
                continue

            # Normaliser til 100 ved start
            normalized = (df['Close'] / df['Close'].iloc[0]) * 100
            label = self.symbol_names.get(symbol, symbol)
            ax.plot(df.index, normalized, label=label, linewidth=1.5)

        ax.axhline(y=100, color='gray', linestyle='--', alpha=0.5)
        ax.set_xlabel('Dato')
        ax.set_ylabel('Normaliseret Pris (Start = 100)')
        ax.set_title('Relativ Performance - Guld vs Korrelerede Markeder', fontweight='bold')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()

        if save:
            filepath = self.output_dir / "multi_asset_comparison.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            return filepath
        else:
            plt.show()
            return None

    def plot_rolling_correlation(self, base_series: pd.Series, other_series: pd.Series,
                                   window: int = 30, title: str = "Rullende Korrelation",
                                   save: bool = True) -> Optional[Path]:
        """
        Plotter rullende korrelation over tid.

        Args:
            base_series: Basis prisserie
            other_series: Sammenligning prisserie
            window: Rullende vindue
            title: Plot titel
            save: Gem som fil

        Returns:
            Sti til gemt fil
        """
        # Beregn rullende korrelation
        combined = pd.DataFrame({'base': base_series, 'other': other_series}).dropna()
        rolling_corr = combined['base'].rolling(window=window).corr(combined['other'])

        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(rolling_corr.index, rolling_corr, color='blue', linewidth=1)
        ax.fill_between(rolling_corr.index, 0, rolling_corr,
                       where=rolling_corr >= 0, alpha=0.3, color='green')
        ax.fill_between(rolling_corr.index, 0, rolling_corr,
                       where=rolling_corr < 0, alpha=0.3, color='red')

        ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.3)
        ax.axhline(y=-0.5, color='gray', linestyle='--', alpha=0.3)

        ax.set_ylim(-1, 1)
        ax.set_xlabel('Dato')
        ax.set_ylabel('Korrelation')
        ax.set_title(f'{title} ({window}-dages vindue)', fontweight='bold')
        ax.grid(True, alpha=0.3)

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()

        if save:
            safe_title = title.replace(' ', '_').replace('/', '_')
            filepath = self.output_dir / f"rolling_correlation_{safe_title}.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            return filepath
        else:
            plt.show()
            return None

    def generate_summary_report(self, df: pd.DataFrame, symbol: str = "GC=F") -> str:
        """
        Genererer tekst-baseret opsummering af indikatorer.

        Args:
            df: DataFrame med pris og indikatorer
            symbol: Ticker symbol

        Returns:
            Formateret rapport tekst
        """
        if df.empty:
            return "Ingen data tilgængelig"

        latest = df.iloc[-1]
        report = []

        report.append("=" * 60)
        report.append(f"  TRADING RAPPORT - {self.symbol_names.get(symbol, symbol)}")
        report.append(f"  Dato: {df.index[-1].strftime('%Y-%m-%d')}")
        report.append("=" * 60)

        # Pris
        report.append(f"\n  PRIS: ${latest['Close']:.2f}")
        if len(df) > 1:
            daily_change = ((latest['Close'] - df.iloc[-2]['Close']) / df.iloc[-2]['Close']) * 100
            report.append(f"  Daglig \u00e6ndring: {daily_change:+.2f}%")

        # RSI
        if 'RSI' in df.columns:
            rsi = latest['RSI']
            rsi_status = "OVERKØBT" if rsi > 70 else "OVERSOLGT" if rsi < 30 else "NEUTRAL"
            report.append(f"\n  RSI: {rsi:.1f} ({rsi_status})")

        # MACD
        if all(col in df.columns for col in ['MACD', 'MACD_Signal']):
            macd_status = "BULLISH" if latest['MACD'] > latest['MACD_Signal'] else "BEARISH"
            report.append(f"  MACD: {macd_status}")

        # Stokastisk
        if all(col in df.columns for col in ['Stoch_K', 'Stoch_D']):
            stoch = latest['Stoch_K']
            stoch_status = "OVERKØBT" if stoch > 80 else "OVERSOLGT" if stoch < 20 else "NEUTRAL"
            report.append(f"  Stokastisk %K: {stoch:.1f} ({stoch_status})")

        # ADX (trend styrke)
        if 'ADX' in df.columns:
            adx = latest['ADX']
            trend = "STÆRK TREND" if adx > 25 else "SVAG/INGEN TREND"
            report.append(f"  ADX: {adx:.1f} ({trend})")

        # ATR
        if 'ATR' in df.columns:
            report.append(f"  ATR: ${latest['ATR']:.2f}")

        report.append("\n" + "=" * 60)

        return "\n".join(report)
