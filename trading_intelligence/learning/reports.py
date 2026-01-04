"""
Trading Intelligence System - Learning Reports
===============================================
DEL 7: Genererer ugentlige læringsrapporter.

Features:
- Ugentlig performance opsummering
- Trend analysis over tid
- Forbedringsfremskridt
- Eksport til HTML/JSON
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

from .performance import PerformanceAnalyzer, OverallMetrics
from .optimizer import StrategyOptimizer, ImprovementSuggestion

logger = logging.getLogger(__name__)


@dataclass
class WeeklyReport:
    """Ugentlig læringsrapport"""
    week_start: datetime
    week_end: datetime

    # Performance
    total_signals: int
    completed_signals: int
    win_rate: float
    profit_factor: float
    avg_profit: float

    # Sammenligning med tidligere uger
    win_rate_change: float
    signals_change: int

    # Bedste og værste
    best_regime: str
    worst_regime: str
    best_session: str

    # Forbedringsforslag
    suggestions: List[Dict]

    # Status
    learning_progress: str  # IMPROVING, STABLE, DECLINING

    def to_dict(self) -> Dict:
        return {
            'week_start': self.week_start.isoformat(),
            'week_end': self.week_end.isoformat(),
            'total_signals': self.total_signals,
            'completed_signals': self.completed_signals,
            'win_rate': round(self.win_rate, 2),
            'profit_factor': round(self.profit_factor, 2),
            'avg_profit': round(self.avg_profit, 2),
            'win_rate_change': round(self.win_rate_change, 2),
            'signals_change': self.signals_change,
            'best_regime': self.best_regime,
            'worst_regime': self.worst_regime,
            'best_session': self.best_session,
            'suggestions': self.suggestions,
            'learning_progress': self.learning_progress
        }


class ReportGenerator:
    """
    Genererer læringsrapporter.
    """

    def __init__(self, signals: List[Dict], reports_dir: Path = None):
        """
        Args:
            signals: Liste af signal dicts
            reports_dir: Directory til at gemme rapporter
        """
        self.signals = signals

        if reports_dir is None:
            reports_dir = Path(__file__).parent.parent / "reports"
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.weekly_reports: List[WeeklyReport] = []
        self._load_previous_reports()

    def _load_previous_reports(self) -> None:
        """Indlæser tidligere rapporter"""
        reports_file = self.reports_dir / "weekly_reports.json"
        if reports_file.exists():
            try:
                with open(reports_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Gemmer rå data for sammenligning
                self.previous_reports = data.get('reports', [])
            except Exception as e:
                logger.warning(f"Kunne ikke indlæse rapporter: {e}")
                self.previous_reports = []
        else:
            self.previous_reports = []

    def generate_weekly_report(self, week_offset: int = 0) -> WeeklyReport:
        """
        Genererer rapport for en specifik uge.

        Args:
            week_offset: 0 = denne uge, -1 = sidste uge, etc.

        Returns:
            WeeklyReport
        """
        # Beregn uge start/slut
        today = datetime.utcnow()
        week_start = today - timedelta(days=today.weekday() + (week_offset * -7))
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

        # Filtrer signals for denne uge
        week_signals = []
        for s in self.signals:
            try:
                ts_str = s.get('timestamp', '2000-01-01T00:00:00')
                # Remove Z suffix and timezone info for comparison
                ts_str = ts_str.replace('Z', '').split('+')[0]
                ts = datetime.fromisoformat(ts_str)
                if week_start <= ts <= week_end:
                    week_signals.append(s)
            except (ValueError, TypeError):
                continue

        completed = [s for s in week_signals if s.get('status') == 'COMPLETED']

        # Beregn metrics
        if completed:
            analyzer = PerformanceAnalyzer(completed)
            metrics = analyzer.calculate_overall_metrics()
            regime_perf = analyzer.analyze_by_regime()
            session_perf = analyzer.analyze_by_session()

            win_rate = metrics.win_rate
            profit_factor = metrics.profit_factor
            avg_profit = metrics.avg_win

            # Find bedste/værste
            best_regime = max(regime_perf.items(), key=lambda x: x[1].win_rate)[0] if regime_perf else "N/A"
            worst_regime = min(regime_perf.items(), key=lambda x: x[1].win_rate)[0] if regime_perf else "N/A"

            best_session = max(session_perf, key=lambda x: x.win_rate).session if session_perf else "N/A"
        else:
            win_rate = 0
            profit_factor = 0
            avg_profit = 0
            best_regime = "N/A"
            worst_regime = "N/A"
            best_session = "N/A"

        # Sammenlign med sidste uge
        previous_week = self._get_previous_week_metrics(week_start)
        win_rate_change = win_rate - previous_week.get('win_rate', win_rate)
        signals_change = len(week_signals) - previous_week.get('total_signals', len(week_signals))

        # Forbedringsforslag
        if completed:
            optimizer = StrategyOptimizer(completed)
            suggestions = optimizer.generate_improvement_suggestions()
            suggestions_data = [s.to_dict() for s in suggestions[:5]]
        else:
            suggestions_data = []

        # Bestem learning progress
        if len(self.previous_reports) >= 2:
            recent_rates = [r.get('win_rate', 50) for r in self.previous_reports[-3:]]
            if all(recent_rates[i] <= recent_rates[i+1] for i in range(len(recent_rates)-1)):
                learning_progress = "IMPROVING"
            elif all(recent_rates[i] >= recent_rates[i+1] for i in range(len(recent_rates)-1)):
                learning_progress = "DECLINING"
            else:
                learning_progress = "STABLE"
        else:
            learning_progress = "STABLE"

        report = WeeklyReport(
            week_start=week_start,
            week_end=week_end,
            total_signals=len(week_signals),
            completed_signals=len(completed),
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_profit=avg_profit,
            win_rate_change=win_rate_change,
            signals_change=signals_change,
            best_regime=best_regime,
            worst_regime=worst_regime,
            best_session=best_session,
            suggestions=suggestions_data,
            learning_progress=learning_progress
        )

        return report

    def _get_previous_week_metrics(self, current_week_start: datetime) -> Dict:
        """Henter metrics fra forrige uge"""
        previous_start = (current_week_start - timedelta(days=7)).isoformat()

        for report in self.previous_reports:
            if report.get('week_start', '').startswith(previous_start[:10]):
                return report

        return {}

    def save_weekly_report(self, report: WeeklyReport) -> Path:
        """
        Gemmer ugentlig rapport til fil.

        Returns:
            Sti til gemt fil
        """
        # Tilføj til historik
        self.previous_reports.append(report.to_dict())

        # Gem historik
        reports_file = self.reports_dir / "weekly_reports.json"
        with open(reports_file, 'w', encoding='utf-8') as f:
            json.dump({
                'reports': self.previous_reports[-52:],  # Gem max 1 års rapporter
                'last_updated': datetime.utcnow().isoformat()
            }, f, indent=2, ensure_ascii=False)

        # Gem også individuel rapport
        week_str = report.week_start.strftime('%Y-W%W')
        individual_file = self.reports_dir / f"report_{week_str}.json"
        with open(individual_file, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"Saved weekly report: {individual_file}")

        return individual_file

    def generate_html_report(self, report: WeeklyReport) -> str:
        """
        Genererer HTML version af rapport.

        Returns:
            HTML string
        """
        # Progress emoji
        progress_icons = {
            'IMPROVING': '📈',
            'STABLE': '➡️',
            'DECLINING': '📉'
        }
        progress_icon = progress_icons.get(report.learning_progress, '❓')

        # Win rate color
        if report.win_rate >= 60:
            wr_color = '#22c55e'
        elif report.win_rate >= 50:
            wr_color = '#eab308'
        else:
            wr_color = '#ef4444'

        # Change indicators
        wr_change = f"+{report.win_rate_change:.1f}%" if report.win_rate_change > 0 else f"{report.win_rate_change:.1f}%"
        sig_change = f"+{report.signals_change}" if report.signals_change > 0 else str(report.signals_change)

        html = f"""<!DOCTYPE html>
<html lang="da">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ugentlig Læringsrapport - {report.week_start.strftime('%d/%m/%Y')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e8e8e8;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 30px;
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
        }}
        h1 {{ font-size: 2em; margin-bottom: 10px; }}
        .subtitle {{ color: #9ca3af; font-size: 1.1em; }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 25px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .metric-label {{ color: #9ca3af; font-size: 0.9em; }}
        .metric-change {{
            font-size: 0.85em;
            margin-top: 8px;
            padding: 4px 10px;
            border-radius: 20px;
            display: inline-block;
        }}
        .positive {{ background: rgba(34, 197, 94, 0.2); color: #22c55e; }}
        .negative {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; }}
        .neutral {{ background: rgba(156, 163, 175, 0.2); color: #9ca3af; }}
        .section {{
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
        }}
        .section h2 {{
            font-size: 1.3em;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .insights-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
        }}
        .insight {{
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .insight-label {{ color: #9ca3af; font-size: 0.85em; margin-bottom: 5px; }}
        .insight-value {{ font-size: 1.1em; font-weight: 500; }}
        .suggestion {{
            background: rgba(255,255,255,0.03);
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 4px solid;
        }}
        .suggestion.HIGH {{ border-color: #ef4444; }}
        .suggestion.MEDIUM {{ border-color: #eab308; }}
        .suggestion.LOW {{ border-color: #22c55e; }}
        .suggestion-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        .suggestion-type {{
            font-size: 0.75em;
            padding: 3px 8px;
            border-radius: 4px;
            background: rgba(255,255,255,0.1);
        }}
        .suggestion-message {{ color: #d1d5db; }}
        .suggestion-impact {{
            font-size: 0.85em;
            color: #9ca3af;
            margin-top: 8px;
            font-style: italic;
        }}
        .progress-indicator {{
            text-align: center;
            font-size: 1.5em;
            padding: 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
        }}
        .footer {{
            text-align: center;
            color: #6b7280;
            font-size: 0.85em;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Ugentlig Læringsrapport</h1>
            <p class="subtitle">
                Uge {report.week_start.strftime('%W')} |
                {report.week_start.strftime('%d. %b')} - {report.week_end.strftime('%d. %b %Y')}
            </p>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value" style="color: {wr_color}">{report.win_rate:.1f}%</div>
                <div class="metric-label">Win Rate</div>
                <div class="metric-change {'positive' if report.win_rate_change > 0 else 'negative' if report.win_rate_change < 0 else 'neutral'}">
                    {wr_change} vs. forrige uge
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{report.total_signals}</div>
                <div class="metric-label">Signals</div>
                <div class="metric-change {'positive' if report.signals_change > 0 else 'negative' if report.signals_change < 0 else 'neutral'}">
                    {sig_change} vs. forrige uge
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{report.profit_factor:.2f}</div>
                <div class="metric-label">Profit Factor</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">${report.avg_profit:.0f}</div>
                <div class="metric-label">Avg Profit</div>
            </div>
        </div>

        <div class="section">
            <h2>🎯 Ugens Insights</h2>
            <div class="insights-grid">
                <div class="insight">
                    <div class="insight-label">Bedste Regime</div>
                    <div class="insight-value">✅ {report.best_regime}</div>
                </div>
                <div class="insight">
                    <div class="insight-label">Værste Regime</div>
                    <div class="insight-value">⚠️ {report.worst_regime}</div>
                </div>
                <div class="insight">
                    <div class="insight-label">Bedste Session</div>
                    <div class="insight-value">🕐 {report.best_session}</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>💡 Forbedringsforsalg</h2>
            {''.join(f'''
            <div class="suggestion {s.get('priority', 'LOW')}">
                <div class="suggestion-header">
                    <strong>{s.get('message', '')}</strong>
                    <span class="suggestion-type">{s.get('type', '')}</span>
                </div>
                <div class="suggestion-impact">{s.get('expected_impact', '')}</div>
            </div>
            ''' for s in report.suggestions) if report.suggestions else '<p style="color: #9ca3af">Ingen forbedringsforslag denne uge.</p>'}
        </div>

        <div class="progress-indicator">
            {progress_icon} Learning Progress: <strong>{report.learning_progress}</strong>
        </div>

        <div class="footer">
            Genereret {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC | Trading Intelligence System
        </div>
    </div>
</body>
</html>"""

        # Gem HTML
        week_str = report.week_start.strftime('%Y-W%W')
        html_file = self.reports_dir / f"report_{week_str}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"Saved HTML report: {html_file}")

        return html

    def get_learning_trend(self, weeks: int = 4) -> Dict:
        """
        Analyserer læringstrent over flere uger.

        Args:
            weeks: Antal uger at analysere

        Returns:
            Dict med trend info
        """
        if len(self.previous_reports) < 2:
            return {
                'status': 'INSUFFICIENT_DATA',
                'message': 'Mindst 2 ugers data kræves'
            }

        recent = self.previous_reports[-weeks:]

        win_rates = [r.get('win_rate', 0) for r in recent]
        signals = [r.get('total_signals', 0) for r in recent]

        # Beregn trends
        if len(win_rates) >= 2:
            wr_trend = (win_rates[-1] - win_rates[0]) / max(len(win_rates) - 1, 1)
            sig_trend = (signals[-1] - signals[0]) / max(len(signals) - 1, 1)
        else:
            wr_trend = 0
            sig_trend = 0

        return {
            'status': 'OK',
            'weeks_analyzed': len(recent),
            'win_rate_trend': round(wr_trend, 2),
            'win_rate_avg': round(sum(win_rates) / len(win_rates), 2),
            'signal_trend': round(sig_trend, 1),
            'signal_avg': round(sum(signals) / len(signals), 1),
            'best_week': max(recent, key=lambda r: r.get('win_rate', 0)),
            'worst_week': min(recent, key=lambda r: r.get('win_rate', 0)),
            'improvement': 'POSITIVE' if wr_trend > 1 else 'NEGATIVE' if wr_trend < -1 else 'STABLE'
        }
