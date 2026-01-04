"""
Trading Intelligence System - Performance Analyzer
===================================================
DEL 3: Beregner success rates, statistik og performance metrics.

Analyserer:
- Overall performance (win rate, profit factor)
- Performance by regime
- Performance by session
- Score accuracy
- Time-based patterns
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class OverallMetrics:
    """Samlede performance metrics"""
    total_signals: int
    completed_signals: int
    wins: int
    losses: int
    breakeven: int
    win_rate: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    profit_factor: float
    expected_value: float
    avg_time_to_target: float  # minutter
    avg_max_drawdown: float

    def to_dict(self) -> Dict:
        return {
            'total_signals': self.total_signals,
            'completed_signals': self.completed_signals,
            'wins': self.wins,
            'losses': self.losses,
            'breakeven': self.breakeven,
            'win_rate': round(self.win_rate, 2),
            'avg_win': round(self.avg_win, 2),
            'avg_loss': round(self.avg_loss, 2),
            'largest_win': round(self.largest_win, 2),
            'largest_loss': round(self.largest_loss, 2),
            'profit_factor': round(self.profit_factor, 2),
            'expected_value': round(self.expected_value, 2),
            'avg_time_to_target': round(self.avg_time_to_target, 1),
            'avg_max_drawdown': round(self.avg_max_drawdown, 2)
        }


@dataclass
class RegimePerformance:
    """Performance for et specifikt regime"""
    regime: str
    total: int
    wins: int
    losses: int
    win_rate: float
    avg_profit: float
    avg_loss: float
    recommended_multiplier: float

    def to_dict(self) -> Dict:
        return {
            'regime': self.regime,
            'total': self.total,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate': round(self.win_rate, 2),
            'avg_profit': round(self.avg_profit, 2),
            'avg_loss': round(self.avg_loss, 2),
            'recommended_multiplier': round(self.recommended_multiplier, 2)
        }


@dataclass
class SessionPerformance:
    """Performance for en trading session"""
    session: str
    total: int
    wins: int
    win_rate: float
    avg_profit: float
    best_time: str

    def to_dict(self) -> Dict:
        return {
            'session': self.session,
            'total': self.total,
            'wins': self.wins,
            'win_rate': round(self.win_rate, 2),
            'avg_profit': round(self.avg_profit, 2),
            'best_time': self.best_time
        }


@dataclass
class ScoreAccuracy:
    """Accuracy for et score range"""
    range_label: str
    min_score: int
    max_score: int
    predicted_accuracy: float
    actual_accuracy: float
    difference: float
    count: int

    def to_dict(self) -> Dict:
        return {
            'range': self.range_label,
            'predicted': round(self.predicted_accuracy, 1),
            'actual': round(self.actual_accuracy, 1),
            'difference': round(self.difference, 1),
            'count': self.count
        }


class PerformanceAnalyzer:
    """
    Analyserer trading performance baseret på signal historik.
    """

    SCORE_RANGES = [
        {'min': 80, 'max': 100, 'label': 'Very High (80-100)'},
        {'min': 70, 'max': 79, 'label': 'High (70-79)'},
        {'min': 60, 'max': 69, 'label': 'Medium (60-69)'},
        {'min': 50, 'max': 59, 'label': 'Low (50-59)'},
        {'min': 0, 'max': 49, 'label': 'Very Low (0-49)'}
    ]

    SESSIONS = ['ASIA', 'LONDON_OPEN', 'LONDON', 'NY_OPEN', 'OVERLAP', 'NY', 'NY_CLOSE']

    def __init__(self, signals: List[Dict]):
        """
        Args:
            signals: Liste af signal dicts fra SignalLogger
        """
        self.signals = signals
        self.completed = [s for s in signals if s.get('status') == 'COMPLETED']

    def calculate_overall_metrics(self) -> OverallMetrics:
        """Beregner samlede performance metrics"""
        if not self.completed:
            return OverallMetrics(
                total_signals=len(self.signals),
                completed_signals=0,
                wins=0, losses=0, breakeven=0,
                win_rate=0, avg_win=0, avg_loss=0,
                largest_win=0, largest_loss=0,
                profit_factor=0, expected_value=0,
                avg_time_to_target=0, avg_max_drawdown=0
            )

        wins = [s for s in self.completed if s.get('outcome', {}).get('result') == 'WIN']
        losses = [s for s in self.completed if s.get('outcome', {}).get('result') == 'LOSS']
        breakeven = [s for s in self.completed if s.get('outcome', {}).get('result') == 'BREAKEVEN']

        # Win rate
        win_rate = (len(wins) / len(self.completed) * 100) if self.completed else 0

        # Average win/loss
        win_pnls = [s.get('outcome', {}).get('max_profit', 0) for s in wins]
        loss_pnls = [abs(s.get('outcome', {}).get('max_drawdown', 0)) for s in losses]

        avg_win = np.mean(win_pnls) if win_pnls else 0
        avg_loss = np.mean(loss_pnls) if loss_pnls else 0

        # Largest win/loss
        largest_win = max(win_pnls) if win_pnls else 0
        largest_loss = min([s.get('outcome', {}).get('max_drawdown', 0) for s in losses]) if losses else 0

        # Profit factor
        total_wins = sum(win_pnls) if win_pnls else 0
        total_losses = sum(loss_pnls) if loss_pnls else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        # Expected value per trade
        expected_value = (win_rate/100 * avg_win) - ((100-win_rate)/100 * avg_loss)

        # Average time to target
        target_times = []
        for s in wins:
            target_time = s.get('outcome', {}).get('target_time', '')
            if target_time and 'min' in target_time:
                try:
                    minutes = int(target_time.replace('min', ''))
                    target_times.append(minutes)
                except:
                    pass
        avg_time_to_target = np.mean(target_times) if target_times else 0

        # Average max drawdown
        drawdowns = [abs(s.get('outcome', {}).get('max_drawdown', 0)) for s in self.completed]
        avg_max_drawdown = np.mean(drawdowns) if drawdowns else 0

        return OverallMetrics(
            total_signals=len(self.signals),
            completed_signals=len(self.completed),
            wins=len(wins),
            losses=len(losses),
            breakeven=len(breakeven),
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            profit_factor=profit_factor,
            expected_value=expected_value,
            avg_time_to_target=avg_time_to_target,
            avg_max_drawdown=avg_max_drawdown
        )

    def analyze_by_regime(self) -> Dict[str, RegimePerformance]:
        """Analyserer performance per regime"""
        by_regime = {}

        for signal in self.completed:
            regime = signal.get('market_conditions', {}).get('regime', 'UNKNOWN')

            if regime not in by_regime:
                by_regime[regime] = {'signals': [], 'wins': 0, 'losses': 0}

            by_regime[regime]['signals'].append(signal)

            result = signal.get('outcome', {}).get('result', '')
            if result == 'WIN':
                by_regime[regime]['wins'] += 1
            elif result == 'LOSS':
                by_regime[regime]['losses'] += 1

        # Beregn metrics per regime
        results = {}
        for regime, data in by_regime.items():
            total = len(data['signals'])
            wins = data['wins']
            losses = data['losses']
            win_rate = (wins / total * 100) if total > 0 else 0

            # Beregn avg profit/loss
            win_signals = [s for s in data['signals']
                          if s.get('outcome', {}).get('result') == 'WIN']
            loss_signals = [s for s in data['signals']
                           if s.get('outcome', {}).get('result') == 'LOSS']

            avg_profit = np.mean([s.get('outcome', {}).get('max_profit', 0)
                                 for s in win_signals]) if win_signals else 0
            avg_loss = np.mean([abs(s.get('outcome', {}).get('max_drawdown', 0))
                               for s in loss_signals]) if loss_signals else 0

            # Beregn anbefalet multiplier baseret på win rate
            if win_rate > 75:
                multiplier = 1.30
            elif win_rate > 65:
                multiplier = 1.20
            elif win_rate > 55:
                multiplier = 1.10
            elif win_rate > 45:
                multiplier = 1.00
            elif win_rate > 35:
                multiplier = 0.90
            else:
                multiplier = 0.70

            results[regime] = RegimePerformance(
                regime=regime,
                total=total,
                wins=wins,
                losses=losses,
                win_rate=win_rate,
                avg_profit=avg_profit,
                avg_loss=avg_loss,
                recommended_multiplier=multiplier
            )

        return results

    def analyze_by_session(self) -> List[SessionPerformance]:
        """Analyserer performance per trading session"""
        results = []

        for session in self.SESSIONS:
            session_signals = [s for s in self.completed
                              if s.get('market_conditions', {}).get('session') == session]

            if not session_signals:
                results.append(SessionPerformance(
                    session=session,
                    total=0, wins=0, win_rate=0,
                    avg_profit=0, best_time='N/A'
                ))
                continue

            wins = [s for s in session_signals
                   if s.get('outcome', {}).get('result') == 'WIN']

            win_rate = (len(wins) / len(session_signals) * 100) if session_signals else 0

            avg_profit = np.mean([s.get('outcome', {}).get('max_profit', 0)
                                 for s in wins]) if wins else 0

            # Find best time (mest profitable tidspunkt)
            best_time = self._find_best_time(wins)

            results.append(SessionPerformance(
                session=session,
                total=len(session_signals),
                wins=len(wins),
                win_rate=win_rate,
                avg_profit=avg_profit,
                best_time=best_time
            ))

        return results

    def _find_best_time(self, signals: List[Dict]) -> str:
        """Finder det tidspunkt med højest profit"""
        if not signals:
            return 'N/A'

        # Grupper efter peak_time
        by_time = {}
        for s in signals:
            peak = s.get('outcome', {}).get('peak_time', '')
            if peak:
                if peak not in by_time:
                    by_time[peak] = []
                by_time[peak].append(s.get('outcome', {}).get('max_profit', 0))

        if not by_time:
            return 'N/A'

        # Find tid med højest gennemsnit
        best_time = max(by_time.keys(), key=lambda t: np.mean(by_time[t]))
        return best_time

    def analyze_score_accuracy(self) -> List[ScoreAccuracy]:
        """Analyserer hvor præcis vores score er"""
        results = []

        for score_range in self.SCORE_RANGES:
            signals_in_range = [s for s in self.completed
                               if score_range['min'] <= s.get('score', {}).get('total', 0) <= score_range['max']]

            if not signals_in_range:
                results.append(ScoreAccuracy(
                    range_label=score_range['label'],
                    min_score=score_range['min'],
                    max_score=score_range['max'],
                    predicted_accuracy=(score_range['min'] + score_range['max']) / 2,
                    actual_accuracy=0,
                    difference=0,
                    count=0
                ))
                continue

            wins = [s for s in signals_in_range
                   if s.get('outcome', {}).get('result') == 'WIN']

            predicted = (score_range['min'] + score_range['max']) / 2
            actual = (len(wins) / len(signals_in_range) * 100) if signals_in_range else 0

            results.append(ScoreAccuracy(
                range_label=score_range['label'],
                min_score=score_range['min'],
                max_score=score_range['max'],
                predicted_accuracy=predicted,
                actual_accuracy=actual,
                difference=actual - predicted,
                count=len(signals_in_range)
            ))

        return results

    def analyze_by_signal_type(self) -> Dict[str, Dict]:
        """Analyserer LONG vs SHORT performance"""
        results = {}

        for signal_type in ['LONG', 'SHORT']:
            type_signals = [s for s in self.completed
                          if s.get('signal_type') == signal_type]

            if not type_signals:
                results[signal_type] = {'total': 0, 'win_rate': 0}
                continue

            wins = [s for s in type_signals
                   if s.get('outcome', {}).get('result') == 'WIN']

            results[signal_type] = {
                'total': len(type_signals),
                'wins': len(wins),
                'win_rate': round(len(wins) / len(type_signals) * 100, 2) if type_signals else 0,
                'avg_profit': round(np.mean([s.get('outcome', {}).get('max_profit', 0)
                                            for s in wins]), 2) if wins else 0
            }

        return results

    def calculate_rolling_win_rate(self, window: int = 50) -> List[Dict]:
        """Beregner rullende win rate over tid"""
        if len(self.completed) < window:
            return []

        # Sorter efter timestamp
        sorted_signals = sorted(self.completed, key=lambda s: s.get('timestamp', ''))

        rolling = []
        for i in range(window, len(sorted_signals) + 1):
            window_signals = sorted_signals[i-window:i]
            wins = sum(1 for s in window_signals
                      if s.get('outcome', {}).get('result') == 'WIN')
            win_rate = wins / window * 100

            rolling.append({
                'index': i,
                'timestamp': window_signals[-1].get('timestamp', ''),
                'win_rate': round(win_rate, 2),
                'window_size': window
            })

        return rolling

    def get_full_analysis(self) -> Dict:
        """Returnerer komplet performance analyse"""
        return {
            'overall': self.calculate_overall_metrics().to_dict(),
            'by_regime': {k: v.to_dict() for k, v in self.analyze_by_regime().items()},
            'by_session': [s.to_dict() for s in self.analyze_by_session()],
            'score_accuracy': [s.to_dict() for s in self.analyze_score_accuracy()],
            'by_signal_type': self.analyze_by_signal_type(),
            'rolling_win_rate': self.calculate_rolling_win_rate(),
            'generated_at': datetime.utcnow().isoformat() + 'Z'
        }
