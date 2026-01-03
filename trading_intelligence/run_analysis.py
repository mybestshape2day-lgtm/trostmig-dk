#!/usr/bin/env python3
"""
Trading Intelligence System - Hovedscript
==========================================
Henter 3 måneders guld futures data, beregner indikatorer,
gemmer i database og genererer visualiseringer.

Brug:
    python run_analysis.py
    python run_analysis.py --days 180
    python run_analysis.py --no-charts
"""

import sys
import argparse
from pathlib import Path

# Tilføj parent directory til path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import SYMBOLS, DB_PATH
from data import DataFetcher, CorrelationTracker
from indicators import TechnicalIndicators
from database import DatabaseManager
from visualization import ChartGenerator


def main(period_days: int = 90, generate_charts: bool = True):
    """
    Hovedfunktion der kører komplet analyse.

    Args:
        period_days: Antal dage at analysere
        generate_charts: Generer visualiseringer
    """
    print("=" * 60)
    print("  TRADING INTELLIGENCE SYSTEM - Guld Futures Analyse")
    print("=" * 60)

    # Initialiser moduler
    fetcher = DataFetcher()
    indicators = TechnicalIndicators()
    correlations = CorrelationTracker()
    db = DatabaseManager()
    charts = ChartGenerator()

    # ========================================
    # TRIN 1: Hent markedsdata
    # ========================================
    print(f"\n[1/5] Henter {period_days} dages data...")

    # Hent guld futures
    gold_df = fetcher.fetch_gold_futures(period_days)
    if gold_df.empty:
        print("FEJL: Kunne ikke hente guld data")
        return

    print(f"      ✓ Guld (GC=F): {len(gold_df)} datapunkter")
    print(f"      Periode: {gold_df.index[0].date()} til {gold_df.index[-1].date()}")
    print(f"      Seneste pris: ${gold_df['Close'].iloc[-1]:.2f}")

    # Hent korrelerede markeder
    correlated_data = fetcher.fetch_correlated_markets(period_days)
    all_data = {SYMBOLS.PRIMARY_SYMBOL: gold_df}
    all_data.update(correlated_data)

    print(f"      ✓ Korrelerede markeder: {len(correlated_data)} hentet")

    # ========================================
    # TRIN 2: Beregn tekniske indikatorer
    # ========================================
    print("\n[2/5] Beregner tekniske indikatorer...")

    gold_with_indicators = indicators.calculate_all(gold_df)

    indicator_cols = [col for col in gold_with_indicators.columns
                     if col not in ['Open', 'High', 'Low', 'Close', 'Volume']]
    print(f"      ✓ Beregnede indikatorer: {len(indicator_cols)}")
    print(f"      Indikatorer: {', '.join(indicator_cols[:8])}...")

    # Vis seneste værdier
    latest = gold_with_indicators.iloc[-1]
    print(f"\n      Seneste indikatorværdier:")
    print(f"        RSI: {latest.get('RSI', 'N/A'):.1f}")
    print(f"        MACD: {latest.get('MACD', 'N/A'):.2f}")
    print(f"        Stoch K: {latest.get('Stoch_K', 'N/A'):.1f}")
    print(f"        ADX: {latest.get('ADX', 'N/A'):.1f}")
    print(f"        ATR: ${latest.get('ATR', 'N/A'):.2f}")

    # ========================================
    # TRIN 3: Korrelationsanalyse
    # ========================================
    print("\n[3/5] Analyserer markedskorrelationer...")

    corr_analysis = correlations.analyze_correlations(all_data)

    if corr_analysis.get('correlations'):
        print("      ✓ Korrelationer med guld:")
        for name, data in corr_analysis['correlations'].items():
            corr = data['correlation']
            strength = data['strength']
            print(f"        {name}: {corr:+.3f} ({strength})")

    if corr_analysis.get('insights'):
        print("\n      Insights:")
        for insight in corr_analysis['insights'][:3]:
            print(f"        • {insight}")

    # ========================================
    # TRIN 4: Gem i database
    # ========================================
    print("\n[4/5] Gemmer data i SQLite database...")

    # Gem OHLCV data for alle symboler
    total_ohlcv = 0
    for symbol, df in all_data.items():
        rows = db.save_ohlcv(symbol, df)
        total_ohlcv += rows

    # Gem indikatorer
    indicator_rows = db.save_indicators_bulk(SYMBOLS.PRIMARY_SYMBOL, gold_with_indicators)

    # Gem metadata
    db.set_metadata('last_run', {
        'date': str(gold_df.index[-1]),
        'period_days': period_days,
        'symbols': list(all_data.keys())
    })

    stats = db.get_stats()
    print(f"      ✓ Database: {DB_PATH}")
    print(f"      OHLCV rækker: {stats['ohlcv_data']}")
    print(f"      Indikator rækker: {stats['technical_indicators']}")
    print(f"      Unikke symboler: {stats['unique_symbols']}")

    # ========================================
    # TRIN 5: Generer visualiseringer
    # ========================================
    if generate_charts:
        print("\n[5/5] Genererer visualiseringer...")

        # Teknisk analyse chart
        chart1 = charts.plot_price_with_indicators(
            gold_with_indicators,
            SYMBOLS.PRIMARY_SYMBOL
        )
        print(f"      ✓ Teknisk analyse: {chart1}")

        # Korrelationsmatrix
        corr_matrix = correlations.calculate_correlation_matrix(all_data)
        if not corr_matrix.empty:
            chart2 = charts.plot_correlation_matrix(corr_matrix)
            print(f"      ✓ Korrelationsmatrix: {chart2}")

        # Multi-asset sammenligning
        chart3 = charts.plot_multi_asset(all_data)
        print(f"      ✓ Multi-asset plot: {chart3}")
    else:
        print("\n[5/5] Springer visualiseringer over (--no-charts)")

    # ========================================
    # RAPPORT
    # ========================================
    report = charts.generate_summary_report(gold_with_indicators, SYMBOLS.PRIMARY_SYMBOL)
    print("\n" + report)

    print("\n" + "=" * 60)
    print("  ANALYSE FÆRDIG")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Guld Futures Trading Analyse')
    parser.add_argument('--days', type=int, default=90,
                        help='Antal dage at analysere (default: 90)')
    parser.add_argument('--no-charts', action='store_true',
                        help='Spring visualiseringer over')

    args = parser.parse_args()
    main(period_days=args.days, generate_charts=not args.no_charts)
