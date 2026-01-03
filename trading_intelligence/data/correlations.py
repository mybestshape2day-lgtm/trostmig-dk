"""
Trading Intelligence System - Korrelationsanalyse
==================================================
Modul til at tracke korrelationer mellem guld og andre markeder.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import logging

from config import SYMBOLS

logger = logging.getLogger(__name__)


class CorrelationTracker:
    """
    Tracker og analyserer korrelationer mellem guld og relaterede markeder.

    Korrelerede markeder:
    - DXY (US Dollar Index) - typisk negativ korrelation
    - 10Y Treasury Yields - varierende korrelation
    - S&P 500 - varierende (safe haven vs risk-on)
    - Sølv - typisk positiv korrelation
    - Crude Oil - varierende korrelation
    """

    def __init__(self):
        self.symbol_config = SYMBOLS

    def calculate_correlation_matrix(self, data: Dict[str, pd.DataFrame],
                                     price_column: str = 'Close') -> pd.DataFrame:
        """
        Beregner korrelationsmatrix mellem alle symboler.

        Args:
            data: Dict med symbol -> DataFrame med OHLCV data
            price_column: Kolonne at bruge til korrelation

        Returns:
            Korrelationsmatrix som DataFrame
        """
        # Kombiner close priser til én DataFrame
        combined = pd.DataFrame()

        for symbol, df in data.items():
            if price_column in df.columns:
                name = self.symbol_config.SYMBOL_NAMES.get(symbol, symbol)
                combined[name] = df[price_column]

        if combined.empty:
            return pd.DataFrame()

        # Håndter manglende data
        combined = combined.dropna()

        return combined.corr()

    def calculate_rolling_correlation(self, series1: pd.Series, series2: pd.Series,
                                       window: int = 30) -> pd.Series:
        """
        Beregner rullende korrelation mellem to serier.

        Args:
            series1: Første prisserie
            series2: Anden prisserie
            window: Rullende vindue (dage)

        Returns:
            Series med rullende korrelation
        """
        # Synkroniser indeks
        combined = pd.DataFrame({'s1': series1, 's2': series2}).dropna()

        if len(combined) < window:
            return pd.Series()

        return combined['s1'].rolling(window=window).corr(combined['s2'])

    def analyze_correlations(self, data: Dict[str, pd.DataFrame],
                              base_symbol: str = None) -> Dict:
        """
        Udfører komplet korrelationsanalyse.

        Args:
            data: Dict med alle markedsdata
            base_symbol: Basis symbol (default: guld)

        Returns:
            Dict med korrelationsanalyse resultater
        """
        base_symbol = base_symbol or self.symbol_config.PRIMARY_SYMBOL

        if base_symbol not in data:
            logger.error(f"Base symbol {base_symbol} ikke fundet i data")
            return {}

        base_data = data[base_symbol]['Close']
        results = {
            'base_symbol': base_symbol,
            'analysis_date': datetime.now().isoformat(),
            'correlations': {},
            'rolling_correlations': {},
            'insights': []
        }

        for symbol, df in data.items():
            if symbol == base_symbol:
                continue

            if 'Close' not in df.columns:
                continue

            # Synkroniser data
            combined = pd.DataFrame({
                'base': base_data,
                'other': df['Close']
            }).dropna()

            if len(combined) < 10:
                continue

            # Simpel korrelation
            corr = combined['base'].corr(combined['other'])
            symbol_name = self.symbol_config.SYMBOL_NAMES.get(symbol, symbol)

            results['correlations'][symbol_name] = {
                'symbol': symbol,
                'correlation': round(corr, 4),
                'strength': self._classify_correlation(corr),
                'data_points': len(combined)
            }

            # Rullende korrelation (30 dage)
            rolling_corr = self.calculate_rolling_correlation(
                combined['base'], combined['other'], window=30
            )
            if not rolling_corr.empty:
                results['rolling_correlations'][symbol_name] = {
                    'current': round(rolling_corr.iloc[-1], 4) if not pd.isna(rolling_corr.iloc[-1]) else None,
                    'mean': round(rolling_corr.mean(), 4),
                    'std': round(rolling_corr.std(), 4),
                    'min': round(rolling_corr.min(), 4),
                    'max': round(rolling_corr.max(), 4)
                }

            # Generer insights
            self._add_insight(results, symbol_name, corr)

        return results

    def _classify_correlation(self, corr: float) -> str:
        """Klassificerer korrelationsstyrke"""
        abs_corr = abs(corr)
        if abs_corr >= 0.7:
            return 'Stærk'
        elif abs_corr >= 0.4:
            return 'Moderat'
        elif abs_corr >= 0.2:
            return 'Svag'
        else:
            return 'Ubetydelig'

    def _add_insight(self, results: Dict, symbol_name: str, corr: float) -> None:
        """Tilføjer insights baseret på korrelation"""
        if 'Dollar' in symbol_name and corr < -0.3:
            results['insights'].append(
                f"Guld viser forventet negativ korrelation ({corr:.2f}) med {symbol_name}. "
                "Dollar svaghed kan understøtte guldpriser."
            )
        elif 'Silver' in symbol_name and corr > 0.7:
            results['insights'].append(
                f"Stærk positiv korrelation ({corr:.2f}) med {symbol_name}. "
                "Sølv kan bruges som proxy-indikator for guld."
            )
        elif 'S&P' in symbol_name:
            if corr > 0.3:
                results['insights'].append(
                    f"Positiv korrelation ({corr:.2f}) med {symbol_name} indikerer risk-on sentiment."
                )
            elif corr < -0.3:
                results['insights'].append(
                    f"Negativ korrelation ({corr:.2f}) med {symbol_name} indikerer safe-haven efterspørgsel."
                )

    def get_correlation_signals(self, data: Dict[str, pd.DataFrame]) -> List[Dict]:
        """
        Genererer handelssignaler baseret på korrelationsafvigelser.

        Args:
            data: Dict med markedsdata

        Returns:
            Liste af signal-dicts
        """
        signals = []
        analysis = self.analyze_correlations(data)

        if not analysis:
            return signals

        # Check for korrelations-breaks
        for symbol_name, rolling in analysis.get('rolling_correlations', {}).items():
            if rolling.get('current') is None:
                continue

            current = rolling['current']
            mean = rolling['mean']
            std = rolling['std']

            # Z-score af nuværende korrelation
            if std > 0:
                z_score = (current - mean) / std

                if abs(z_score) > 2:
                    signals.append({
                        'type': 'correlation_divergence',
                        'symbol': symbol_name,
                        'current_correlation': current,
                        'historical_mean': mean,
                        'z_score': round(z_score, 2),
                        'interpretation': 'Usædvanlig korrelation - potentiel mean reversion'
                    })

        return signals

    def create_returns_df(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Opretter DataFrame med daglige afkast for alle symboler.

        Args:
            data: Dict med markedsdata

        Returns:
            DataFrame med procentvise daglige afkast
        """
        returns = pd.DataFrame()

        for symbol, df in data.items():
            if 'Close' in df.columns:
                name = self.symbol_config.SYMBOL_NAMES.get(symbol, symbol)
                returns[name] = df['Close'].pct_change() * 100

        return returns.dropna()
