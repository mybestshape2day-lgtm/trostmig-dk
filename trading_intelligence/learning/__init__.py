"""
Strategy Factory - Self-Evolving Trading Intelligence

The Loop:
Data -> Analysis -> Risk Check -> Signal -> Trade -> Log ->
  -> Performance Review -> Strategy Factory -> New Rules ->
    -> Back to Analysis (with improved rules)

Components:
- PatternMiner: Discovers profitable patterns in historical data
- RuleEvolution: Generates and evolves trading rules
- AutoTuner: Optimizes parameters automatically
- StrategyFactory: Main orchestrator
- FeedbackLoop: Connects signals to outcomes
"""

from .pattern_miner import PatternMiner
from .rule_evolution import RuleEvolution
from .auto_tuner import AutoTuner
from .strategy_factory import StrategyFactory
from .feedback_loop import FeedbackLoop

__all__ = [
    'PatternMiner',
    'RuleEvolution',
    'AutoTuner',
    'StrategyFactory',
    'FeedbackLoop'
]
