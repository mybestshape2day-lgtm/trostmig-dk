#!/usr/bin/env python3
"""
Trading Intelligence System - Web Dashboard
============================================
Phase 5: Flask web application that brings all phases together.

Start serveren:
    python app.py

Åbn derefter: http://localhost:5000
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify
import json
import logging

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

# Import our modules
from data.fetcher import DataFetcher
from data.correlations import CorrelationAnalyzer
from indicators.technical import TechnicalIndicators
from analysis.regime import RegimeDetector
from analysis.sentiment import MarketSentiment
from analysis.patterns import PatternMatcher
from analysis.signals import SignalGenerator
from monitoring.risk import RiskMonitor
from learning.performance import PerformanceAnalyzer

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Cache for data (refresh every 5 minutes)
cache = {
    'data': None,
    'last_update': None,
    'cache_duration': timedelta(minutes=5)
}


def get_cached_data():
    """Henter eller opdaterer cached data"""
    now = datetime.utcnow()

    if cache['data'] is None or cache['last_update'] is None or \
       (now - cache['last_update']) > cache['cache_duration']:
        cache['data'] = fetch_all_data()
        cache['last_update'] = now

    return cache['data']


def fetch_all_data():
    """Henter al markedsdata og beregner indikatorer"""
    try:
        # Phase 1: Hent data
        fetcher = DataFetcher()
        gold_data = fetcher.get_gold_data(days=90)

        if gold_data.empty:
            return {'error': 'Kunne ikke hente data'}

        correlated = fetcher.get_correlated_markets(days=90)

        # Beregn indikatorer
        tech = TechnicalIndicators(gold_data)
        indicators = tech.calculate_all()

        # Korrelationer
        corr_analyzer = CorrelationAnalyzer(gold_data, correlated)
        correlations = corr_analyzer.calculate_all()

        # Phase 2: Regime og sentiment
        regime_detector = RegimeDetector(gold_data, indicators)
        regime = regime_detector.detect_current_regime()
        regime_history = regime_detector.get_regime_history()

        sentiment_analyzer = MarketSentiment(gold_data, correlated)
        sentiment = sentiment_analyzer.analyze()

        # Patterns
        pattern_matcher = PatternMatcher(gold_data, indicators)
        patterns = pattern_matcher.find_current_patterns()
        historical = pattern_matcher.find_historical_matches()

        # Signals
        signal_gen = SignalGenerator(gold_data, indicators, regime, sentiment, patterns)
        signal = signal_gen.generate_signal()

        # Phase 3: Risk monitoring
        risk_monitor = RiskMonitor()
        risk_status = risk_monitor.get_current_status()

        # Phase 4: Performance (if data exists)
        signals_file = Path(__file__).parent / "data" / "signal_history.json"
        performance = None
        if signals_file.exists():
            with open(signals_file, 'r') as f:
                signal_data = json.load(f)
                signals = signal_data.get('signals', [])
                completed = [s for s in signals if s.get('status') == 'COMPLETED']
                if completed:
                    analyzer = PerformanceAnalyzer(completed)
                    metrics = analyzer.calculate_overall_metrics()
                    performance = {
                        'win_rate': round(metrics.win_rate, 1),
                        'profit_factor': round(metrics.profit_factor, 2),
                        'total_trades': metrics.completed_signals,
                        'wins': metrics.wins,
                        'losses': metrics.losses,
                        'expected_value': round(metrics.expected_value, 2)
                    }

        # Seneste pris og ændring
        latest = gold_data.iloc[-1]
        prev = gold_data.iloc[-2] if len(gold_data) > 1 else latest
        price_change = ((latest['Close'] - prev['Close']) / prev['Close']) * 100

        # Seneste indikatorer
        latest_ind = indicators.iloc[-1] if not indicators.empty else {}

        return {
            'timestamp': datetime.utcnow().isoformat(),
            'price': {
                'current': round(float(latest['Close']), 2),
                'open': round(float(latest['Open']), 2),
                'high': round(float(latest['High']), 2),
                'low': round(float(latest['Low']), 2),
                'change_pct': round(price_change, 2),
                'volume': int(latest.get('Volume', 0))
            },
            'indicators': {
                'rsi': round(float(latest_ind.get('RSI', 50)), 1),
                'macd': round(float(latest_ind.get('MACD', 0)), 2),
                'macd_signal': round(float(latest_ind.get('MACD_Signal', 0)), 2),
                'stoch_k': round(float(latest_ind.get('Stoch_K', 50)), 1),
                'stoch_d': round(float(latest_ind.get('Stoch_D', 50)), 1),
                'adx': round(float(latest_ind.get('ADX', 0)), 1),
                'atr': round(float(latest_ind.get('ATR', 0)), 2),
                'bb_upper': round(float(latest_ind.get('BB_Upper', 0)), 2),
                'bb_lower': round(float(latest_ind.get('BB_Lower', 0)), 2),
                'ema_9': round(float(latest_ind.get('EMA_9', 0)), 2),
                'ema_21': round(float(latest_ind.get('EMA_21', 0)), 2),
                'ema_50': round(float(latest_ind.get('EMA_50', 0)), 2)
            },
            'regime': {
                'current': regime.value if hasattr(regime, 'value') else str(regime),
                'history': [{'date': str(r['date']), 'regime': r['regime'].value if hasattr(r['regime'], 'value') else str(r['regime'])} for r in regime_history[-5:]] if regime_history else []
            },
            'sentiment': {
                'overall': sentiment.overall.value if hasattr(sentiment.overall, 'value') else str(sentiment.overall),
                'dxy_trend': sentiment.dxy_trend,
                'yield_trend': sentiment.yield_trend,
                'equity_trend': sentiment.equity_trend
            },
            'patterns': [{'name': p.pattern_name, 'score': p.confidence} for p in patterns[:3]] if patterns else [],
            'signal': {
                'direction': signal.direction.value if hasattr(signal.direction, 'value') else str(signal.direction),
                'strength': signal.strength.value if hasattr(signal.strength, 'value') else str(signal.strength),
                'score': signal.score,
                'entry': round(signal.entry_price, 2) if signal.entry_price else None,
                'stop_loss': round(signal.stop_loss, 2) if signal.stop_loss else None,
                'take_profit': round(signal.take_profit, 2) if signal.take_profit else None,
                'criteria': signal.criteria_met[:5] if signal.criteria_met else []
            },
            'risk': {
                'level': risk_status.get('risk_level', 'UNKNOWN'),
                'score': risk_status.get('risk_score', 0),
                'alerts': risk_status.get('active_alerts', [])[:3]
            },
            'correlations': {
                'dxy': round(correlations.get('DX-Y.NYB', {}).get('correlation', 0), 2),
                'treasury': round(correlations.get('^TNX', {}).get('correlation', 0), 2),
                'sp500': round(correlations.get('^GSPC', {}).get('correlation', 0), 2),
                'silver': round(correlations.get('SI=F', {}).get('correlation', 0), 2),
                'oil': round(correlations.get('CL=F', {}).get('correlation', 0), 2)
            },
            'performance': performance
        }

    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}


@app.route('/')
def dashboard():
    """Hovedside med dashboard"""
    return render_template('dashboard.html')


@app.route('/api/data')
def api_data():
    """API endpoint for data"""
    data = get_cached_data()
    return jsonify(data)


@app.route('/api/refresh')
def api_refresh():
    """Force refresh af data"""
    cache['data'] = None
    cache['last_update'] = None
    data = get_cached_data()
    return jsonify(data)


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  TRADING INTELLIGENCE - WEB DASHBOARD")
    print("=" * 60)
    print("\n  Starter server...")
    print("  Åbn: http://localhost:5000")
    print("\n  Tryk Ctrl+C for at stoppe\n")
    print("=" * 60 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
