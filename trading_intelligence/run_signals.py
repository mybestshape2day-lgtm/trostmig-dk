#!/usr/bin/env python3
"""
Trading Intelligence System - Signal Analysis
==============================================
Fase 2: Kører komplet AI-analyse og genererer trading signals.

Brug:
    python run_signals.py
    python run_signals.py --days 180
    python run_signals.py --no-dashboard
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Tilføj parent directory til path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import SYMBOLS, DB_PATH
from data import DataFetcher, CorrelationTracker
from indicators import TechnicalIndicators
from database import DatabaseManager
from analysis import (
    RegimeDetector, SentimentAnalyzer, PatternMatcher,
    SignalGenerator, Dashboard
)


def main(period_days: int = 90, generate_dashboard: bool = True):
    """
    Hovedfunktion der kører komplet Fase 2 analyse.

    Args:
        period_days: Antal dage historisk data
        generate_dashboard: Generer dashboard visualisering
    """
    print("=" * 70)
    print("  TRADING INTELLIGENCE SYSTEM - Fase 2: AI Signal Analyse")
    print("=" * 70)

    # Initialiser alle moduler
    print("\n[0/6] Initialiserer moduler...")
    fetcher = DataFetcher()
    indicators = TechnicalIndicators()
    db = DatabaseManager()

    regime_detector = RegimeDetector()
    sentiment_analyzer = SentimentAnalyzer()
    pattern_matcher = PatternMatcher()
    signal_generator = SignalGenerator()
    dashboard = Dashboard()

    # ========================================
    # TRIN 1: Hent markedsdata
    # ========================================
    print(f"\n[1/6] Henter {period_days} dages data...")

    gold_df = fetcher.fetch_gold_futures(period_days)
    if gold_df.empty:
        print("FEJL: Kunne ikke hente guld data")
        return

    print(f"      ✓ Guld: {len(gold_df)} datapunkter")
    print(f"      Seneste pris: ${gold_df['Close'].iloc[-1]:.2f}")

    # Hent korrelerede markeder
    market_data = fetcher.fetch_correlated_markets(period_days)
    print(f"      ✓ Korrelerede markeder: {len(market_data)}")

    # ========================================
    # TRIN 2: Beregn tekniske indikatorer
    # ========================================
    print("\n[2/6] Beregner tekniske indikatorer...")

    gold_with_indicators = indicators.calculate_all(gold_df)
    print(f"      ✓ 17 indikatorer beregnet")

    # ========================================
    # TRIN 3: Regime Detection
    # ========================================
    print("\n[3/6] Detekterer markedsregime...")

    current_regime = regime_detector.detect_regime(gold_with_indicators)
    regime_history = regime_detector.detect_regime_history(gold_with_indicators)

    print(f"      ✓ Nuværende regime: {current_regime.combined_regime}")
    print(f"      ADX: {current_regime.adx_value:.1f}")
    print(f"      EMA slope: {current_regime.ema_slope:.2f}%")

    # ========================================
    # TRIN 4: Sentiment Analyse
    # ========================================
    print("\n[4/6] Analyserer market sentiment...")

    sentiment = sentiment_analyzer.analyze(gold_df, market_data)

    print(f"      ✓ Sentiment: {sentiment.sentiment.value}")
    print(f"      Confidence: {sentiment.confidence:.0%}")
    print(f"      Gold ændring: {sentiment.gold_change:+.2f}%")
    print(f"      S&P ændring: {sentiment.sp500_change:+.2f}%")
    print(f"      DXY ændring: {sentiment.dxy_change:+.2f}%")

    if sentiment.divergence_alerts:
        print(f"      ⚠️  Alerts:")
        for alert in sentiment.divergence_alerts:
            print(f"         - {alert}")

    # ========================================
    # TRIN 5: Pattern Matching
    # ========================================
    print("\n[5/6] Søger efter lignende historiske patterns...")

    pattern_analysis = pattern_matcher.analyze_patterns(
        gold_with_indicators,
        regime_history,
        current_regime
    )

    print(f"      ✓ Matches fundet: {pattern_analysis.total_matches}")
    if pattern_analysis.total_matches > 0:
        print(f"      Bullish success rate: {pattern_analysis.bullish_success_rate:.1f}%")
        print(f"      Bearish success rate: {pattern_analysis.bearish_success_rate:.1f}%")
        print(f"      Gennemsnitlig 24h outcome: {pattern_analysis.avg_outcome_24h:+.2f}%")
        print(f"      Prediction: {pattern_analysis.predicted_direction} ({pattern_analysis.prediction_confidence:.0%})")

    # ========================================
    # TRIN 6: Signal Generation
    # ========================================
    print("\n[6/6] Genererer trading signal...")

    signal = signal_generator.generate_signal(
        gold_with_indicators,
        current_regime,
        pattern_analysis,
        sentiment
    )

    # Vis signal
    print("\n" + "=" * 70)
    print("  SIGNAL OUTPUT")
    print("=" * 70)

    if signal.signal_type.value != "NO_SIGNAL":
        signal_icon = "▲ LONG ENTRY" if signal.signal_type.value == "LONG_ENTRY" else "▼ SHORT ENTRY"
        print(f"\n  📊 {signal_icon}")
        print(f"  Styrke: {signal.strength.value}")
        print(f"  Pris: ${signal.price:.2f}")
        print(f"  Kriterier: {signal.criteria_met}/{signal.criteria_total}")
        print(f"\n  Årsager:")
        for reason in signal.reasons:
            print(f"    ✓ {reason}")

        if signal.suggested_stop_loss:
            print(f"\n  Risk Management:")
            print(f"    Stop Loss: ${signal.suggested_stop_loss:.2f}")
            print(f"    Take Profit: ${signal.suggested_take_profit:.2f}")
            print(f"    Risk/Reward: 1:{signal.risk_reward_ratio:.1f}")
    else:
        print("\n  ⏸️  INTET SIGNAL")
        print(f"  Kun {signal.criteria_met}/{signal.criteria_total} kriterier opfyldt")
        print("  Afventer bedre setup...")

    # Gem i database
    print("\n  Gemmer i database...")
    db.set_metadata('latest_signal', signal.to_dict())
    db.set_metadata('latest_regime', current_regime.to_dict())
    db.set_metadata('latest_sentiment', sentiment.to_dict())

    # ========================================
    # Dashboard
    # ========================================
    if generate_dashboard:
        print("\n  Genererer dashboard...")
        dashboard_path = dashboard.create_full_dashboard(
            gold_with_indicators,
            current_regime,
            sentiment,
            pattern_analysis,
            signal
        )
        print(f"  ✓ Dashboard: {dashboard_path}")

    # Simpel status
    print("\n" + dashboard.create_simple_status(current_regime, sentiment, signal))

    # JSON output
    print("\n  JSON Signal Output:")
    print("-" * 70)
    print(signal.to_json())
    print("-" * 70)

    print("\n✅ Analyse færdig!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Gold Futures AI Signal Analyse')
    parser.add_argument('--days', type=int, default=90,
                        help='Antal dage at analysere (default: 90)')
    parser.add_argument('--no-dashboard', action='store_true',
                        help='Spring dashboard visualisering over')

    args = parser.parse_args()
    main(period_days=args.days, generate_dashboard=not args.no_dashboard)
