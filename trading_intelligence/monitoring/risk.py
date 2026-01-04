"""
Trading Intelligence System - Master Risk Aggregator
=====================================================
DEL 4: Kombinerer alle risiko-faktorer til samlet risikovurdering.

Risk Levels:
- CRITICAL: Minimum én kritisk alert → EXIT ALL POSITIONS
- HIGH: Flere high alerts → REDUCE POSITIONS
- ELEVATED: Enkelte high alerts → CAUTION
- NORMAL: Ingen alerts → SAFE TO TRADE
"""

import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import logging

from .calendar import EconomicCalendar, CalendarCheck, CalendarStatus
from .news import NewsScanner, NewsCheck
from .anomaly import AnomalyDetector, AnomalyScan, AnomalySeverity

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Master risk levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    ELEVATED = "ELEVATED"
    NORMAL = "NORMAL"


@dataclass
class RiskReport:
    """Komplet risiko rapport"""
    timestamp: datetime
    overall_risk: RiskLevel
    critical_count: int
    high_count: int
    elevated_count: int

    # Komponenter
    calendar: CalendarCheck
    news: NewsCheck
    anomalies: AnomalyScan

    # Recommendation
    recommendation: str
    action_required: bool
    can_trade: bool

    # Detaljer
    risk_factors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'overall_risk': self.overall_risk.value,
            'critical_count': self.critical_count,
            'high_count': self.high_count,
            'elevated_count': self.elevated_count,
            'calendar': self.calendar.to_dict(),
            'news': self.news.to_dict(),
            'anomalies': self.anomalies.to_dict(),
            'recommendation': self.recommendation,
            'action_required': self.action_required,
            'can_trade': self.can_trade,
            'risk_factors': self.risk_factors
        }


class RiskAggregator:
    """
    Aggregerer alle risiko-kilder til samlet vurdering.
    """

    def __init__(self):
        self.calendar = EconomicCalendar()
        self.news_scanner = NewsScanner()
        self.anomaly_detector = AnomalyDetector()

        # Historik
        self.risk_history: List[RiskReport] = []
        self.last_risk_level: RiskLevel = RiskLevel.NORMAL

    def calculate_master_risk(self, gold_df: pd.DataFrame,
                               market_data: Dict[str, pd.DataFrame] = None) -> RiskReport:
        """
        Beregner samlet risikovurdering.

        Args:
            gold_df: DataFrame med guld OHLCV og indikatorer
            market_data: Dict med symbol -> DataFrame for andre markeder

        Returns:
            RiskReport med komplet risikovurdering
        """
        market_data = market_data or {}

        # 1. Check economic calendar
        calendar_check = self.calendar.check_upcoming_events()

        # 2. Check news
        news_check = self.news_scanner.check_active_news()

        # 3. Run anomaly scan
        dxy_df = market_data.get('DX-Y.NYB')
        vix_df = market_data.get('^VIX')
        anomaly_scan = self.anomaly_detector.run_full_scan(gold_df, dxy_df, vix_df)

        # 4. Aggreger risk factors
        critical_count = 0
        high_count = 0
        elevated_count = 0
        risk_factors = []

        # Calendar risk
        if calendar_check.status == CalendarStatus.CRITICAL:
            critical_count += 1
            risk_factors.append(f"Calendar: {calendar_check.recommendation}")
        elif calendar_check.status == CalendarStatus.ELEVATED:
            elevated_count += 1
            risk_factors.append(f"Calendar: {calendar_check.recommendation}")

        # News risk
        if news_check.volatility_expected:
            high_count += 1
            risk_factors.append(f"News: High impact news active")
        elif news_check.has_active_news:
            elevated_count += 1
            risk_factors.append(f"News: {news_check.gold_bias} bias")

        # Anomaly risk
        if anomaly_scan.any_critical:
            critical_count += 1
            if anomaly_scan.flash_crash.detected:
                risk_factors.append(f"Anomaly: {anomaly_scan.flash_crash.description}")
            if anomaly_scan.volume.severity == AnomalySeverity.CRITICAL:
                risk_factors.append(f"Anomaly: {anomaly_scan.volume.description}")

        if anomaly_scan.any_high:
            high_count += 1
            if anomaly_scan.volume.severity == AnomalySeverity.HIGH:
                risk_factors.append(f"Anomaly: {anomaly_scan.volume.description}")
            if anomaly_scan.correlation.detected:
                risk_factors.append(f"Anomaly: {anomaly_scan.correlation.description}")
            if anomaly_scan.vix.detected:
                risk_factors.append(f"Anomaly: {anomaly_scan.vix.description}")

        # 5. Bestem overall risk level
        if critical_count > 0:
            overall_risk = RiskLevel.CRITICAL
        elif high_count >= 2:
            overall_risk = RiskLevel.HIGH
        elif high_count >= 1 or elevated_count >= 2:
            overall_risk = RiskLevel.ELEVATED
        else:
            overall_risk = RiskLevel.NORMAL

        # 6. Generer recommendation
        recommendation, action_required, can_trade = self._generate_recommendation(
            overall_risk, critical_count, high_count, risk_factors
        )

        # 7. Opret rapport
        report = RiskReport(
            timestamp=datetime.utcnow(),
            overall_risk=overall_risk,
            critical_count=critical_count,
            high_count=high_count,
            elevated_count=elevated_count,
            calendar=calendar_check,
            news=news_check,
            anomalies=anomaly_scan,
            recommendation=recommendation,
            action_required=action_required,
            can_trade=can_trade,
            risk_factors=risk_factors
        )

        # 8. Opdater historik
        self.risk_history.append(report)
        if len(self.risk_history) > 1000:
            self.risk_history = self.risk_history[-500:]

        self.last_risk_level = overall_risk

        logger.info(f"Risk Level: {overall_risk.value} | Critical: {critical_count} | High: {high_count}")

        return report

    def _generate_recommendation(self, risk_level: RiskLevel,
                                   critical: int, high: int,
                                   factors: List[str]) -> tuple:
        """Genererer anbefaling baseret på risk level"""

        if risk_level == RiskLevel.CRITICAL:
            return (
                "⛔ EXIT ALL POSITIONS - Critical risk detected. "
                "Do not enter new trades until risk clears.",
                True,
                False
            )

        elif risk_level == RiskLevel.HIGH:
            return (
                "⚠️ REDUCE POSITIONS - Multiple risk factors present. "
                "Tighten stops and reduce exposure.",
                True,
                False
            )

        elif risk_level == RiskLevel.ELEVATED:
            return (
                "📊 CAUTION - Risk factors detected. "
                "Trade with reduced size and close monitoring.",
                False,
                True
            )

        else:
            return (
                "✅ NORMAL - No significant risk factors. "
                "Safe to trade with standard position sizing.",
                False,
                True
            )

    def check_risk_change(self, current: RiskReport) -> Optional[Dict]:
        """
        Checker om risk level har ændret sig.

        Returns:
            Dict med ændringsinfo hvis risiko er steget, ellers None
        """
        if len(self.risk_history) < 2:
            return None

        previous = self.risk_history[-2]

        # Risk level prioritet
        priority = {
            RiskLevel.NORMAL: 0,
            RiskLevel.ELEVATED: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3
        }

        current_priority = priority[current.overall_risk]
        previous_priority = priority[previous.overall_risk]

        if current_priority > previous_priority:
            return {
                'type': 'RISK_INCREASE',
                'from': previous.overall_risk.value,
                'to': current.overall_risk.value,
                'new_factors': [f for f in current.risk_factors if f not in previous.risk_factors],
                'requires_action': current.action_required
            }

        return None

    def get_risk_summary(self) -> str:
        """Returnerer tekst-opsummering af nuværende risiko"""
        if not self.risk_history:
            return "No risk data available"

        current = self.risk_history[-1]

        lines = [
            "=" * 50,
            "  MASTER RISK STATUS",
            "=" * 50,
            f"  Overall: {current.overall_risk.value}",
            f"  Can Trade: {'Yes' if current.can_trade else 'NO'}",
            f"  Action Required: {'Yes' if current.action_required else 'No'}",
            "",
            f"  Critical Factors: {current.critical_count}",
            f"  High Factors: {current.high_count}",
            f"  Elevated Factors: {current.elevated_count}",
            "",
            "  Risk Factors:"
        ]

        for factor in current.risk_factors[:5]:
            lines.append(f"    • {factor}")

        lines.extend([
            "",
            f"  Recommendation:",
            f"    {current.recommendation}",
            "=" * 50
        ])

        return "\n".join(lines)

    def emergency_protocol(self) -> Dict:
        """
        Emergency exit protocol ved CRITICAL risk.

        Returns:
            Dict med emergency actions
        """
        if not self.risk_history:
            return {'status': 'NO_DATA'}

        current = self.risk_history[-1]

        if current.overall_risk != RiskLevel.CRITICAL:
            return {'status': 'NOT_CRITICAL', 'risk_level': current.overall_risk.value}

        return {
            'status': 'EMERGENCY',
            'action': 'EXIT_ALL',
            'reason': current.risk_factors,
            'executed_at': datetime.utcnow().isoformat(),
            'recommendation': 'Do not enter new trades until risk level returns to NORMAL',
            'next_check': 'Automatic in 60 seconds'
        }
