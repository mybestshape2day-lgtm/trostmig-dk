"""
Monitoring Module - Real-time Overvågning
==========================================
Fase 3: Event tracking, anomali-detektering og risk aggregation.

Moduler:
- calendar: Economic Calendar scanner
- news: News sentiment tracker
- anomaly: Flash crash, volume og correlation anomali detektering
- risk: Master Risk Aggregator
- alerts: Notification system
"""

from .calendar import EconomicCalendar, CalendarStatus
from .news import NewsScanner, NewsSentiment
from .anomaly import AnomalyDetector, AnomalyType
from .risk import RiskAggregator, RiskLevel, RiskReport
from .alerts import AlertSystem
