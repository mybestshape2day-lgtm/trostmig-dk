#!/usr/bin/env python3
"""
Trading Intelligence System - Risk Monitor
===========================================
Fase 3: Real-time overvågning og risk scanning.

Brug:
    python run_monitor.py              # Kør én gang
    python run_monitor.py --continuous # Kør løbende
    python run_monitor.py --test       # Test med simulerede anomalier
"""

import sys
import argparse
import time
from pathlib import Path
from datetime import datetime

# Tilføj parent directory til path
sys.path.insert(0, str(Path(__file__).parent))

from config import SYMBOLS
from data import DataFetcher
from indicators import TechnicalIndicators
from monitoring import (
    EconomicCalendar, NewsScanner, AnomalyDetector,
    RiskAggregator, AlertSystem, RiskLevel
)


def run_single_scan(verbose: bool = True) -> dict:
    """
    Kører én komplet risk scan.

    Returns:
        Dict med scan resultater
    """
    print("=" * 70)
    print("  TRADING INTELLIGENCE - RISK MONITOR")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 70)

    # Initialiser
    fetcher = DataFetcher()
    indicators = TechnicalIndicators()
    risk_aggregator = RiskAggregator()
    alert_system = AlertSystem()

    # ========================================
    # 1. Hent data
    # ========================================
    print("\n[1/4] Henter markedsdata...")

    gold_df = fetcher.fetch_gold_futures(period_days=30)
    if gold_df.empty:
        print("FEJL: Kunne ikke hente guld data")
        return {'error': 'No gold data'}

    gold_with_indicators = indicators.calculate_all(gold_df)
    print(f"      ✓ Guld: {len(gold_df)} datapunkter, pris: ${gold_df['Close'].iloc[-1]:.2f}")

    # Hent korrelerede markeder
    market_data = {}
    dxy_df = fetcher.fetch_ohlcv('DX-Y.NYB', period_days=30)
    if not dxy_df.empty:
        market_data['DX-Y.NYB'] = dxy_df
        print(f"      ✓ DXY: {len(dxy_df)} datapunkter")

    # ========================================
    # 2. Economic Calendar Check
    # ========================================
    print("\n[2/4] Checker økonomisk kalender...")

    calendar = EconomicCalendar()
    calendar_check = calendar.check_upcoming_events()

    if calendar_check.has_upcoming:
        print(f"      ⚠️  Status: {calendar_check.status.value}")
        print(f"      Next: {calendar_check.next_event.event} in {calendar_check.minutes_until} min")
    else:
        print(f"      ✓ Status: {calendar_check.status.value} - No upcoming events")

    # ========================================
    # 3. News Check
    # ========================================
    print("\n[3/4] Checker breaking news...")

    news_scanner = NewsScanner()
    news_check = news_scanner.check_active_news()

    if news_check.has_active_news:
        print(f"      📰 Active news: {news_check.active_count}")
        print(f"      Gold bias: {news_check.gold_bias}")
        if news_check.latest_news:
            print(f"      Latest: {news_check.latest_news.headline[:50]}...")
    else:
        print(f"      ✓ No active news events")

    # ========================================
    # 4. Anomaly Scan
    # ========================================
    print("\n[4/4] Scanner for anomalier...")

    anomaly_detector = AnomalyDetector()
    anomaly_scan = anomaly_detector.run_full_scan(
        gold_with_indicators,
        market_data.get('DX-Y.NYB')
    )

    print(f"      Flash Crash: {'⚠️ DETECTED' if anomaly_scan.flash_crash.detected else '✓ OK'}")
    print(f"      Volume: {anomaly_scan.volume.severity.value} ({anomaly_scan.volume.value:.1f}x avg)")
    print(f"      Correlation: {'⚠️ BREAK' if anomaly_scan.correlation.detected else '✓ OK'}")

    # ========================================
    # 5. Master Risk Assessment
    # ========================================
    print("\n" + "=" * 70)
    print("  MASTER RISK ASSESSMENT")
    print("=" * 70)

    risk_report = risk_aggregator.calculate_master_risk(gold_with_indicators, market_data)

    # Vis risk level med farve-indikator
    level_icons = {
        RiskLevel.CRITICAL: "⛔",
        RiskLevel.HIGH: "⚠️",
        RiskLevel.ELEVATED: "📊",
        RiskLevel.NORMAL: "✅"
    }

    icon = level_icons.get(risk_report.overall_risk, "❓")
    print(f"\n  {icon} Overall Risk: {risk_report.overall_risk.value}")
    print(f"  Can Trade: {'Yes' if risk_report.can_trade else 'NO'}")
    print(f"  Action Required: {'Yes' if risk_report.action_required else 'No'}")

    print(f"\n  Risk Factor Counts:")
    print(f"    Critical: {risk_report.critical_count}")
    print(f"    High: {risk_report.high_count}")
    print(f"    Elevated: {risk_report.elevated_count}")

    if risk_report.risk_factors:
        print(f"\n  Active Risk Factors:")
        for factor in risk_report.risk_factors[:5]:
            print(f"    • {factor}")

    print(f"\n  Recommendation:")
    print(f"    {risk_report.recommendation}")

    # ========================================
    # 6. Check for alerts
    # ========================================
    alert = alert_system.check_and_alert(risk_report)

    if alert:
        print(f"\n  🔔 ALERT GENERATED:")
        print(f"    {alert.title}")
        print(f"    {alert.message}")

    print("\n" + "=" * 70)

    return {
        'timestamp': datetime.utcnow().isoformat(),
        'risk_level': risk_report.overall_risk.value,
        'can_trade': risk_report.can_trade,
        'price': float(gold_df['Close'].iloc[-1]),
        'calendar_status': calendar_check.status.value,
        'news_active': news_check.has_active_news,
        'anomalies': anomaly_scan.total_anomalies,
        'risk_factors': risk_report.risk_factors,
        'alert': alert.to_dict() if alert else None
    }


def run_continuous(interval_seconds: int = 60):
    """
    Kører kontinuerlig overvågning.

    Args:
        interval_seconds: Sekunder mellem scans
    """
    print("Starting continuous monitoring...")
    print(f"Scan interval: {interval_seconds} seconds")
    print("Press Ctrl+C to stop\n")

    scan_count = 0

    try:
        while True:
            scan_count += 1
            print(f"\n{'='*70}")
            print(f"  SCAN #{scan_count} - {datetime.utcnow().strftime('%H:%M:%S')} UTC")
            print(f"{'='*70}")

            try:
                result = run_single_scan(verbose=False)

                # Kort status
                level = result.get('risk_level', 'UNKNOWN')
                price = result.get('price', 0)
                can_trade = result.get('can_trade', False)

                print(f"\n  Quick Status: {level} | ${price:.2f} | Trade: {'Yes' if can_trade else 'NO'}")

            except Exception as e:
                print(f"  Scan error: {e}")

            # Vent til næste scan
            print(f"\n  Next scan in {interval_seconds} seconds...")
            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")


def run_test_scenario():
    """
    Kører test med simulerede anomalier.
    """
    print("=" * 70)
    print("  TEST MODE - Simulating Risk Scenarios")
    print("=" * 70)

    # Test 1: Normal conditions
    print("\n[TEST 1] Normal market conditions")
    result = run_single_scan()
    print(f"Result: {result.get('risk_level')}")

    # Her kunne vi tilføje mere avancerede tests
    # f.eks. manipulere data til at simulere flash crash

    print("\n[TEST COMPLETE]")


def main():
    parser = argparse.ArgumentParser(description='Trading Risk Monitor')
    parser.add_argument('--continuous', '-c', action='store_true',
                        help='Run continuous monitoring')
    parser.add_argument('--interval', '-i', type=int, default=60,
                        help='Scan interval in seconds (default: 60)')
    parser.add_argument('--test', '-t', action='store_true',
                        help='Run test scenarios')

    args = parser.parse_args()

    if args.test:
        run_test_scenario()
    elif args.continuous:
        run_continuous(args.interval)
    else:
        result = run_single_scan()
        print(f"\nScan complete. Risk Level: {result.get('risk_level')}")


if __name__ == "__main__":
    main()
