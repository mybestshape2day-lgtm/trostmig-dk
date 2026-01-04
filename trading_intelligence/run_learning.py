#!/usr/bin/env python3
"""
Trading Intelligence System - Learning Dashboard
=================================================
Fase 4: Viser læringsstatistik og performance metrics.

Brug:
    python run_learning.py              # Vis dashboard
    python run_learning.py --report     # Generer ugentlig rapport
    python run_learning.py --optimize   # Vis optimeringsforslag
    python run_learning.py --simulate   # Kør med simulerede data
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta
import random

# Tilføj parent directory til path
sys.path.insert(0, str(Path(__file__).parent))

from learning import SignalLogger, PerformanceAnalyzer, StrategyOptimizer, ReportGenerator


def create_simulated_signals(count: int = 50) -> list:
    """
    Opretter simulerede signals til test.

    Args:
        count: Antal signals at generere

    Returns:
        Liste af signal dicts
    """
    signals = []
    base_time = datetime.utcnow() - timedelta(days=30)

    regimes = ['STRONG_UPTREND', 'WEAK_UPTREND', 'RANGING', 'WEAK_DOWNTREND', 'STRONG_DOWNTREND']
    sessions = ['ASIAN', 'LONDON', 'US', 'OVERLAP']
    directions = ['LONG', 'SHORT']

    for i in range(count):
        timestamp = base_time + timedelta(hours=random.randint(0, 720))
        direction = random.choice(directions)
        regime = random.choice(regimes)
        session = random.choice(sessions)
        score = random.randint(55, 90)

        # Simuler outcome baseret på score og regime match
        base_win_prob = 0.4 + (score - 55) / 100

        # Bonus for trend-aligned trades
        if direction == 'LONG' and 'UPTREND' in regime:
            base_win_prob += 0.15
        elif direction == 'SHORT' and 'DOWNTREND' in regime:
            base_win_prob += 0.15

        is_win = random.random() < base_win_prob

        signal = {
            'signal_id': f'SIM-{i+1:04d}',
            'timestamp': timestamp.isoformat() + 'Z',
            'symbol': 'GC=F',
            'direction': direction,
            'strength': random.choice(['STRONG', 'MEDIUM', 'WEAK']),
            'status': 'COMPLETED',
            'configuration': {
                'stoch_oversold': random.choice([20, 25, 30]),
                'stoch_overbought': random.choice([70, 75, 80]),
                'min_score': random.choice([60, 65, 70]),
                'atr_stop_mult': random.choice([1.5, 2.0, 2.5]),
                'atr_tp_mult': random.choice([2.5, 3.0, 3.5])
            },
            'market_conditions': {
                'regime': regime,
                'session': session,
                'volatility': random.choice(['LOW', 'NORMAL', 'HIGH']),
                'sentiment': random.choice(['RISK_ON', 'NEUTRAL', 'RISK_OFF'])
            },
            'score': {
                'total': score,
                'momentum': random.randint(50, 95),
                'trend': random.randint(50, 95),
                'volume': random.randint(50, 95)
            },
            'outcome': {
                'result': 'WIN' if is_win else 'LOSS',
                'max_profit': random.uniform(50, 300) if is_win else 0,
                'max_drawdown': random.uniform(-100, -10),
                'duration_minutes': random.randint(10, 180)
            }
        }

        signals.append(signal)

    return signals


def run_dashboard(signals: list, verbose: bool = True):
    """
    Viser learning dashboard.
    """
    print("=" * 70)
    print("  TRADING INTELLIGENCE - LEARNING DASHBOARD")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 70)

    if not signals:
        print("\n  Ingen signals i database.")
        print("  Brug --simulate for at teste med simulerede data.")
        return

    completed = [s for s in signals if s.get('status') == 'COMPLETED']

    print(f"\n  Signals: {len(signals)} total, {len(completed)} completed")

    if not completed:
        print("\n  Ingen completed signals endnu.")
        return

    # ========================================
    # 1. Overall Metrics
    # ========================================
    print("\n" + "-" * 70)
    print("  OVERALL PERFORMANCE")
    print("-" * 70)

    analyzer = PerformanceAnalyzer(completed)
    metrics = analyzer.calculate_overall_metrics()

    # Win rate color
    if metrics.win_rate >= 60:
        wr_status = "✅"
    elif metrics.win_rate >= 50:
        wr_status = "⚠️"
    else:
        wr_status = "❌"

    print(f"\n  {wr_status} Win Rate:      {metrics.win_rate:.1f}%")
    print(f"     Total Trades:   {metrics.completed_signals}")
    print(f"     Wins/Losses:    {metrics.wins}/{metrics.losses}")
    print(f"     Profit Factor:  {metrics.profit_factor:.2f}")
    print(f"     Avg Win:        ${metrics.avg_win:.2f}")
    print(f"     Avg Loss:       ${abs(metrics.avg_loss):.2f}")
    print(f"     Expected Value: ${metrics.expected_value:.2f}")

    # ========================================
    # 2. Performance by Regime
    # ========================================
    print("\n" + "-" * 70)
    print("  PERFORMANCE BY REGIME")
    print("-" * 70)

    regime_perf = analyzer.analyze_by_regime()

    if regime_perf:
        # Header
        print(f"\n  {'Regime':<20} {'Win Rate':>10} {'Trades':>8} {'Multiplier':>12}")
        print("  " + "-" * 52)

        for regime, data in sorted(regime_perf.items(), key=lambda x: x[1].win_rate, reverse=True):
            wr = data.win_rate
            total = data.total
            mult = data.recommended_multiplier

            # Status icon
            if wr >= 60:
                icon = "✅"
            elif wr >= 50:
                icon = "⚠️"
            else:
                icon = "❌"

            print(f"  {icon} {regime:<17} {wr:>9.1f}% {total:>7} {mult:>11.2f}x")

    # ========================================
    # 3. Performance by Session
    # ========================================
    print("\n" + "-" * 70)
    print("  PERFORMANCE BY SESSION")
    print("-" * 70)

    session_perf = analyzer.analyze_by_session()

    if session_perf:
        print(f"\n  {'Session':<15} {'Win Rate':>10} {'Trades':>8} {'Avg Profit':>12}")
        print("  " + "-" * 48)

        for data in sorted(session_perf, key=lambda x: x.win_rate, reverse=True):
            session = data.session
            wr = data.win_rate
            total = data.total
            avg = data.avg_profit

            if wr >= 60:
                icon = "✅"
            elif wr >= 50:
                icon = "⚠️"
            else:
                icon = "❌"

            print(f"  {icon} {session:<13} {wr:>9.1f}% {total:>7} ${avg:>10.2f}")

    # ========================================
    # 4. Score Accuracy
    # ========================================
    print("\n" + "-" * 70)
    print("  SCORE ACCURACY")
    print("-" * 70)

    score_accuracy = analyzer.analyze_score_accuracy()
    total_count = sum(s.count for s in score_accuracy)

    if total_count >= 10:
        # Header
        print(f"\n  {'Score Range':<20} {'Predicted':>10} {'Actual':>10} {'Count':>8}")
        print("  " + "-" * 50)

        for acc in score_accuracy:
            if acc.count < 3:
                continue

            if acc.actual_accuracy >= 60:
                icon = "✅"
            elif acc.actual_accuracy >= 50:
                icon = "⚠️"
            else:
                icon = "❌"

            print(f"  {icon} {acc.range_label:<17} {acc.predicted_accuracy:>9.0f}% {acc.actual_accuracy:>9.1f}% {acc.count:>7}")

        # Beregn simpel correlation
        valid = [s for s in score_accuracy if s.count >= 3]
        if len(valid) >= 3:
            # Simpel check: stiger actual med predicted?
            improving = sum(1 for i in range(len(valid)-1)
                           if valid[i].actual_accuracy <= valid[i+1].actual_accuracy)
            correlation = improving / (len(valid) - 1) if len(valid) > 1 else 0

            print(f"\n  Score-Outcome Alignment: {correlation:.0%}")

            if correlation > 0.6:
                print("  → Scores er gode predikatorer af succes ✅")
            elif correlation > 0.4:
                print("  → Scores har moderat prediktiv værdi ⚠️")
            else:
                print("  → Scores bør kalibreres ❌")

    print("\n" + "=" * 70)


def run_optimization(signals: list):
    """
    Viser optimeringsforslag.
    """
    print("=" * 70)
    print("  TRADING INTELLIGENCE - OPTIMIZATION ANALYSIS")
    print("=" * 70)

    completed = [s for s in signals if s.get('status') == 'COMPLETED']

    if len(completed) < 10:
        print(f"\n  Minimum 10 completed signals kræves. Har: {len(completed)}")
        return

    optimizer = StrategyOptimizer(completed)

    # ========================================
    # 1. Optimal Configuration
    # ========================================
    print("\n" + "-" * 70)
    print("  OPTIMAL PARAMETER VALUES")
    print("-" * 70)

    optimal = optimizer.find_optimal_configuration()

    if optimal:
        print(f"\n  {'Parameter':<20} {'Current':>10} {'Optimal':>10} {'Win Rate':>10} {'Conf.':>8}")
        print("  " + "-" * 60)

        for param, opt in optimal.items():
            current = opt.current_value
            best = opt.optimal_value
            wr = opt.optimal_win_rate
            conf = opt.confidence

            # Markér ændring
            changed = "→" if current != best else " "

            print(f"  {param:<20} {current:>10} {changed}{best:>9} {wr:>9.1f}% {conf:>8}")
    else:
        print("\n  Ikke nok data til at finde optimale værdier.")

    # ========================================
    # 2. Improvement Suggestions
    # ========================================
    print("\n" + "-" * 70)
    print("  IMPROVEMENT SUGGESTIONS")
    print("-" * 70)

    # Hent regime/session performance til forslag
    analyzer = PerformanceAnalyzer(completed)
    regime_perf = analyzer.analyze_by_regime()
    session_perf = analyzer.analyze_by_session()

    suggestions = optimizer.generate_improvement_suggestions(regime_perf, session_perf)

    if suggestions:
        for i, s in enumerate(suggestions[:8], 1):
            priority_icons = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}
            icon = priority_icons.get(s.priority, '⚪')

            print(f"\n  {icon} [{s.type}] {s.message}")
            print(f"     Impact: {s.expected_impact}")
            if s.current_value and s.suggested_value:
                print(f"     Change: {s.current_value} → {s.suggested_value}")
    else:
        print("\n  Ingen forbedringsforslag. Fortsæt nuværende strategi.")

    print("\n" + "=" * 70)


def run_weekly_report(signals: list):
    """
    Genererer ugentlig rapport.
    """
    print("=" * 70)
    print("  TRADING INTELLIGENCE - WEEKLY REPORT GENERATOR")
    print("=" * 70)

    generator = ReportGenerator(signals)

    print("\n  Genererer rapport for denne uge...")

    report = generator.generate_weekly_report()

    # Gem rapport
    json_file = generator.save_weekly_report(report)
    html = generator.generate_html_report(report)

    # Vis opsummering
    print(f"\n  Uge: {report.week_start.strftime('%d/%m')} - {report.week_end.strftime('%d/%m/%Y')}")
    print(f"\n  Signals:       {report.total_signals}")
    print(f"  Completed:     {report.completed_signals}")
    print(f"  Win Rate:      {report.win_rate:.1f}%")
    print(f"  Profit Factor: {report.profit_factor:.2f}")

    print(f"\n  Sammenligning med forrige uge:")
    wr_change = f"+{report.win_rate_change:.1f}%" if report.win_rate_change > 0 else f"{report.win_rate_change:.1f}%"
    sig_change = f"+{report.signals_change}" if report.signals_change > 0 else str(report.signals_change)
    print(f"    Win Rate: {wr_change}")
    print(f"    Signals:  {sig_change}")

    print(f"\n  Learning Progress: {report.learning_progress}")

    print(f"\n  Filer gemt:")
    print(f"    JSON: {json_file}")
    print(f"    HTML: {json_file.with_suffix('.html')}")

    # Learning trend
    trend = generator.get_learning_trend()
    if trend.get('status') == 'OK':
        print(f"\n  Trend over {trend['weeks_analyzed']} uger:")
        print(f"    Win Rate Trend: {trend['win_rate_trend']:+.2f}% per uge")
        print(f"    Signal Trend:   {trend['signal_trend']:+.1f} per uge")
        print(f"    Status:         {trend['improvement']}")

    print("\n" + "=" * 70)


def load_signals() -> list:
    """Indlæser signals fra fil"""
    signals_file = Path(__file__).parent / "data" / "signal_history.json"

    if signals_file.exists():
        with open(signals_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('signals', [])

    return []


def save_signals(signals: list):
    """Gemmer signals til fil"""
    signals_file = Path(__file__).parent / "data" / "signal_history.json"
    signals_file.parent.mkdir(parents=True, exist_ok=True)

    with open(signals_file, 'w', encoding='utf-8') as f:
        json.dump({
            'signals': signals,
            'metadata': {
                'created': datetime.utcnow().isoformat() + 'Z',
                'last_updated': datetime.utcnow().isoformat() + 'Z',
                'total_signals': len(signals),
                'schema_version': '1.0'
            }
        }, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description='Trading Learning Dashboard')
    parser.add_argument('--report', '-r', action='store_true',
                        help='Generate weekly report')
    parser.add_argument('--optimize', '-o', action='store_true',
                        help='Show optimization suggestions')
    parser.add_argument('--simulate', '-s', action='store_true',
                        help='Use simulated data for testing')
    parser.add_argument('--count', '-n', type=int, default=50,
                        help='Number of simulated signals (default: 50)')

    args = parser.parse_args()

    # Load eller simuler data
    if args.simulate:
        print(f"\n  📊 Genererer {args.count} simulerede signals...")
        signals = create_simulated_signals(args.count)
        save_signals(signals)
        print(f"  ✓ Signals gemt til signal_history.json\n")
    else:
        signals = load_signals()

    # Kør valgt funktion
    if args.report:
        run_weekly_report(signals)
    elif args.optimize:
        run_optimization(signals)
    else:
        run_dashboard(signals)


if __name__ == "__main__":
    main()
