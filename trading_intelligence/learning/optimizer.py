"""
Trading Intelligence System - Strategy Optimizer
=================================================
DEL 4 & 6: Finder optimale parametre og genererer forbedringsforslagautomatisk.

Features:
- Parameter impact analysis
- Optimal configuration finder
- Auto-adjust multipliers
- Improvement suggestions
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ParameterPerformance:
    """Performance for en specifik parameter værdi"""
    parameter: str
    value: float
    count: int
    wins: int
    win_rate: float
    avg_profit: float

    def to_dict(self) -> Dict:
        return {
            'parameter': self.parameter,
            'value': self.value,
            'count': self.count,
            'wins': self.wins,
            'win_rate': round(self.win_rate, 2),
            'avg_profit': round(self.avg_profit, 2)
        }


@dataclass
class OptimalParameter:
    """Optimal værdi for en parameter"""
    parameter: str
    current_value: float
    optimal_value: float
    optimal_win_rate: float
    sample_size: int
    confidence: str  # HIGH, MEDIUM, LOW

    def to_dict(self) -> Dict:
        return {
            'parameter': self.parameter,
            'current': self.current_value,
            'optimal': self.optimal_value,
            'win_rate': round(self.optimal_win_rate, 2),
            'sample_size': self.sample_size,
            'confidence': self.confidence
        }


@dataclass
class ImprovementSuggestion:
    """Et forbedringsforslay"""
    type: str  # PARAMETER, REGIME_FILTER, SESSION_FOCUS, etc.
    priority: str  # HIGH, MEDIUM, LOW
    message: str
    expected_impact: str
    current_value: Optional[str] = None
    suggested_value: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'type': self.type,
            'priority': self.priority,
            'message': self.message,
            'expected_impact': self.expected_impact,
            'current_value': self.current_value,
            'suggested_value': self.suggested_value
        }


class StrategyOptimizer:
    """
    Optimerer trading strategi baseret på historisk performance.
    """

    # Parametre vi kan optimere og deres mulige værdier
    OPTIMIZABLE_PARAMS = {
        'stoch_oversold': [15, 20, 25, 30, 35],
        'stoch_overbought': [65, 70, 75, 80, 85],
        'min_score': [55, 60, 65, 70, 75, 80],
        'rsi_oversold': [25, 30, 35],
        'rsi_overbought': [65, 70, 75],
        'atr_stop_mult': [1.5, 2.0, 2.5, 3.0],
        'atr_tp_mult': [2.0, 2.5, 3.0, 3.5, 4.0]
    }

    MIN_SAMPLES_HIGH_CONF = 30
    MIN_SAMPLES_MED_CONF = 15
    MIN_SAMPLES_LOW_CONF = 5

    def __init__(self, signals: List[Dict], current_config: Dict = None):
        """
        Args:
            signals: Liste af completed signal dicts
            current_config: Nuværende konfiguration
        """
        self.signals = [s for s in signals if s.get('status') == 'COMPLETED']
        self.current_config = current_config or {
            'stoch_oversold': 30,
            'stoch_overbought': 70,
            'min_score': 65,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'atr_stop_mult': 2.0,
            'atr_tp_mult': 3.0
        }

    def analyze_parameter_impact(self) -> Dict[str, List[ParameterPerformance]]:
        """
        Analyserer hvordan forskellige parameter værdier påvirker performance.

        Returns:
            Dict med parameter -> liste af ParameterPerformance
        """
        results = {}

        for param, possible_values in self.OPTIMIZABLE_PARAMS.items():
            param_results = []

            for value in possible_values:
                # Find signals der brugte denne værdi
                matching_signals = [
                    s for s in self.signals
                    if s.get('configuration', {}).get(param) == value
                ]

                if not matching_signals:
                    continue

                wins = [s for s in matching_signals
                       if s.get('outcome', {}).get('result') == 'WIN']

                win_rate = (len(wins) / len(matching_signals) * 100) if matching_signals else 0

                avg_profit = np.mean([
                    s.get('outcome', {}).get('max_profit', 0)
                    for s in wins
                ]) if wins else 0

                param_results.append(ParameterPerformance(
                    parameter=param,
                    value=value,
                    count=len(matching_signals),
                    wins=len(wins),
                    win_rate=win_rate,
                    avg_profit=avg_profit
                ))

            results[param] = param_results

        return results

    def find_optimal_configuration(self) -> Dict[str, OptimalParameter]:
        """
        Finder den optimale værdi for hver parameter.

        Returns:
            Dict med parameter -> OptimalParameter
        """
        param_analysis = self.analyze_parameter_impact()
        optimal = {}

        for param, performances in param_analysis.items():
            if not performances:
                continue

            # Filter by minimum samples
            valid_options = [p for p in performances if p.count >= self.MIN_SAMPLES_LOW_CONF]

            if not valid_options:
                continue

            # Find bedste win rate
            best = max(valid_options, key=lambda p: p.win_rate)

            # Bestem confidence baseret på sample size
            if best.count >= self.MIN_SAMPLES_HIGH_CONF:
                confidence = "HIGH"
            elif best.count >= self.MIN_SAMPLES_MED_CONF:
                confidence = "MEDIUM"
            else:
                confidence = "LOW"

            optimal[param] = OptimalParameter(
                parameter=param,
                current_value=self.current_config.get(param, best.value),
                optimal_value=best.value,
                optimal_win_rate=best.win_rate,
                sample_size=best.count,
                confidence=confidence
            )

        return optimal

    def calculate_regime_multipliers(self, regime_performance: Dict) -> Dict[str, float]:
        """
        Beregner anbefalede multipliers for hvert regime.

        Args:
            regime_performance: Dict fra PerformanceAnalyzer.analyze_by_regime()

        Returns:
            Dict med regime -> multiplier
        """
        multipliers = {}

        for regime, perf in regime_performance.items():
            win_rate = perf.get('win_rate', 50)

            # Beregn multiplier baseret på win rate
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
            elif win_rate > 25:
                multiplier = 0.80
            else:
                multiplier = 0.70

            multipliers[regime] = multiplier

        return multipliers

    def generate_improvement_suggestions(self,
                                          regime_perf: Dict = None,
                                          session_perf: List = None) -> List[ImprovementSuggestion]:
        """
        Genererer konkrete forbedringsforslagbaseret på analyse.

        Returns:
            Liste af ImprovementSuggestion
        """
        suggestions = []

        # 1. Parameter justeringer
        optimal = self.find_optimal_configuration()

        for param, opt in optimal.items():
            current = self.current_config.get(param)
            if current != opt.optimal_value and opt.confidence in ['HIGH', 'MEDIUM']:
                diff = opt.optimal_win_rate - self._get_current_win_rate(param, current)

                suggestions.append(ImprovementSuggestion(
                    type="PARAMETER",
                    priority="HIGH" if opt.confidence == "HIGH" else "MEDIUM",
                    message=f"Change {param} from {current} to {opt.optimal_value}",
                    expected_impact=f"Expected +{diff:.1f}% win rate based on {opt.sample_size} signals",
                    current_value=str(current),
                    suggested_value=str(opt.optimal_value)
                ))

        # 2. Regime filter suggestions
        if regime_perf:
            for regime, perf in regime_perf.items():
                # Handle both dict and dataclass objects
                if hasattr(perf, 'win_rate'):
                    win_rate = perf.win_rate
                    total = perf.total
                else:
                    win_rate = perf.get('win_rate', 50)
                    total = perf.get('total', 0)

                if win_rate < 40 and total >= 20:
                    suggestions.append(ImprovementSuggestion(
                        type="REGIME_FILTER",
                        priority="MEDIUM",
                        message=f"Consider avoiding {regime} regime",
                        expected_impact=f"Only {win_rate:.1f}% win rate over {total} signals",
                        current_value="Enabled",
                        suggested_value="Disabled/Reduced"
                    ))

                elif win_rate > 70 and total >= 20:
                    suggestions.append(ImprovementSuggestion(
                        type="REGIME_FOCUS",
                        priority="LOW",
                        message=f"Increase focus on {regime} regime",
                        expected_impact=f"{win_rate:.1f}% win rate - high probability setup",
                        current_value="Normal",
                        suggested_value="Increased weight"
                    ))

        # 3. Session suggestions
        if session_perf:
            # Find best and worst sessions
            # Handle both dict and dataclass objects
            def get_total(s):
                return s.total if hasattr(s, 'total') else s.get('total', 0)

            def get_win_rate(s):
                return s.win_rate if hasattr(s, 'win_rate') else s.get('win_rate', 0)

            def get_session_name(s):
                return s.session if hasattr(s, 'session') else s.get('session', '')

            valid_sessions = [s for s in session_perf if get_total(s) >= 10]

            if valid_sessions:
                best_session = max(valid_sessions, key=get_win_rate)
                worst_session = min(valid_sessions, key=get_win_rate)

                if get_win_rate(best_session) > 70:
                    suggestions.append(ImprovementSuggestion(
                        type="SESSION_FOCUS",
                        priority="MEDIUM",
                        message=f"Focus more on {get_session_name(best_session)} session",
                        expected_impact=f"{get_win_rate(best_session):.1f}% win rate - highest probability period",
                        current_value="Normal",
                        suggested_value="Primary focus"
                    ))

                if get_win_rate(worst_session) < 40:
                    suggestions.append(ImprovementSuggestion(
                        type="SESSION_AVOID",
                        priority="MEDIUM",
                        message=f"Avoid trading during {get_session_name(worst_session)} session",
                        expected_impact=f"Only {get_win_rate(worst_session):.1f}% win rate",
                        current_value="Enabled",
                        suggested_value="Disabled"
                    ))

        # 4. Score threshold suggestion
        score_analysis = self._analyze_score_threshold()
        if score_analysis:
            suggestions.append(score_analysis)

        # Sorter efter prioritet
        priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        suggestions.sort(key=lambda s: priority_order.get(s.priority, 3))

        return suggestions

    def _get_current_win_rate(self, param: str, value: float) -> float:
        """Henter win rate for nuværende parameter værdi"""
        matching = [s for s in self.signals
                   if s.get('configuration', {}).get(param) == value]

        if not matching:
            return 50.0

        wins = sum(1 for s in matching if s.get('outcome', {}).get('result') == 'WIN')
        return (wins / len(matching) * 100) if matching else 50.0

    def _analyze_score_threshold(self) -> Optional[ImprovementSuggestion]:
        """Analyserer om vi bør ændre min_score threshold"""
        # Grupper signals efter score
        by_score = {}
        for threshold in [55, 60, 65, 70, 75, 80]:
            above_threshold = [s for s in self.signals
                              if s.get('score', {}).get('total', 0) >= threshold]
            if above_threshold:
                wins = sum(1 for s in above_threshold
                          if s.get('outcome', {}).get('result') == 'WIN')
                by_score[threshold] = {
                    'count': len(above_threshold),
                    'win_rate': wins / len(above_threshold) * 100
                }

        # Find optimal threshold (balance mellem win rate og antal signals)
        best_threshold = None
        best_score = 0

        for threshold, data in by_score.items():
            if data['count'] >= 10:
                # Score = win_rate * log(count) for at balance kvalitet og kvantitet
                score = data['win_rate'] * np.log(data['count'] + 1)
                if score > best_score:
                    best_score = score
                    best_threshold = threshold

        if best_threshold and best_threshold != self.current_config.get('min_score', 65):
            current = self.current_config.get('min_score', 65)
            return ImprovementSuggestion(
                type="SCORE_THRESHOLD",
                priority="MEDIUM",
                message=f"Adjust minimum score from {current} to {best_threshold}",
                expected_impact=f"{by_score[best_threshold]['win_rate']:.1f}% win rate with {by_score[best_threshold]['count']} signals",
                current_value=str(current),
                suggested_value=str(best_threshold)
            )

        return None

    def apply_optimal_config(self, config_file: Path = None) -> Dict:
        """
        Anvender optimal konfiguration og gemmer til fil.

        Args:
            config_file: Sti til config fil (optional)

        Returns:
            Den nye konfiguration
        """
        optimal = self.find_optimal_configuration()

        new_config = self.current_config.copy()

        for param, opt in optimal.items():
            if opt.confidence in ['HIGH', 'MEDIUM']:
                new_config[param] = opt.optimal_value

        # Gem til fil hvis angivet
        if config_file:
            config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(config_file, 'w') as f:
                json.dump({
                    'config': new_config,
                    'optimized_at': datetime.utcnow().isoformat(),
                    'based_on_signals': len(self.signals)
                }, f, indent=2)

        self.current_config = new_config
        logger.info(f"Applied optimal configuration based on {len(self.signals)} signals")

        return new_config

    def get_optimization_summary(self) -> Dict:
        """Returnerer komplet optimerings-oversigt"""
        optimal = self.find_optimal_configuration()
        param_analysis = self.analyze_parameter_impact()

        return {
            'current_config': self.current_config,
            'optimal_config': {k: v.to_dict() for k, v in optimal.items()},
            'parameter_analysis': {
                k: [p.to_dict() for p in v]
                for k, v in param_analysis.items()
            },
            'signals_analyzed': len(self.signals),
            'generated_at': datetime.utcnow().isoformat() + 'Z'
        }
