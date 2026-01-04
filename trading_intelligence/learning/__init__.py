"""
Learning Module - Signal Tracking og Performance Learning
=========================================================
Fase 4: Logger signals, tracker outcomes, og lærer fra resultater.

Moduler:
- signal_logger: Logger alle signals med komplet kontekst
- outcome_tracker: Tracker pris efter signal
- performance: Beregner metrics og statistik
- optimizer: Finder optimale parametre
- reports: Genererer læringsrapporter
"""

from .signal_logger import SignalLogger, SignalRecord
from .performance import PerformanceAnalyzer
from .optimizer import StrategyOptimizer
from .reports import ReportGenerator
