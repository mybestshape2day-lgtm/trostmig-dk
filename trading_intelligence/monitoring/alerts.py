"""
Trading Intelligence System - Alert System
==========================================
DEL 6: Notification system til risk alerts.

Features:
- Log alle risk changes
- Audio alert support (via playsound)
- Desktop notification support
- Alert historik
"""

import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum
import logging

from .risk import RiskLevel, RiskReport

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Alert typer"""
    RISK_CRITICAL = "RISK_CRITICAL"
    RISK_HIGH = "RISK_HIGH"
    RISK_ELEVATED = "RISK_ELEVATED"
    RISK_CLEARED = "RISK_CLEARED"
    CALENDAR_WARNING = "CALENDAR_WARNING"
    NEWS_BREAKING = "NEWS_BREAKING"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"


@dataclass
class Alert:
    """En alert"""
    timestamp: datetime
    alert_type: AlertType
    title: str
    message: str
    severity: str
    acknowledged: bool = False
    data: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'type': self.alert_type.value,
            'title': self.title,
            'message': self.message,
            'severity': self.severity,
            'acknowledged': self.acknowledged,
            'data': self.data
        }


class AlertSystem:
    """
    Håndterer alerts og notifications.
    """

    def __init__(self, alerts_file: Path = None):
        """
        Args:
            alerts_file: Sti til alerts log fil
        """
        if alerts_file is None:
            alerts_file = Path(__file__).parent.parent / "data" / "alerts_history.json"

        self.alerts_file = alerts_file
        self.alerts: List[Alert] = []
        self.last_risk_level: Optional[RiskLevel] = None

        # Callbacks for custom notifications
        self.on_critical_alert: Optional[Callable] = None
        self.on_high_alert: Optional[Callable] = None

        self._load_alerts()

    def _load_alerts(self) -> None:
        """Indlæser alerts fra fil"""
        if self.alerts_file.exists():
            try:
                with open(self.alerts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for alert_data in data.get('alerts', [])[-100:]:  # Kun seneste 100
                    alert = Alert(
                        timestamp=datetime.fromisoformat(alert_data['timestamp']),
                        alert_type=AlertType(alert_data['type']),
                        title=alert_data['title'],
                        message=alert_data['message'],
                        severity=alert_data['severity'],
                        acknowledged=alert_data.get('acknowledged', False),
                        data=alert_data.get('data', {})
                    )
                    self.alerts.append(alert)

            except Exception as e:
                logger.warning(f"Kunne ikke indlæse alerts: {e}")

    def _save_alerts(self) -> None:
        """Gemmer alerts til fil"""
        self.alerts_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'alerts': [a.to_dict() for a in self.alerts[-500:]],
            'last_updated': datetime.utcnow().isoformat()
        }

        with open(self.alerts_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def check_and_alert(self, risk_report: RiskReport) -> Optional[Alert]:
        """
        Checker risk report og genererer alert hvis nødvendigt.

        Args:
            risk_report: RiskReport fra RiskAggregator

        Returns:
            Alert hvis genereret, ellers None
        """
        current_level = risk_report.overall_risk
        alert = None

        # Check for risk level ændring
        if self.last_risk_level is None:
            self.last_risk_level = current_level
            return None

        # Risk eskaleret
        if self._risk_escalated(self.last_risk_level, current_level):
            if current_level == RiskLevel.CRITICAL:
                alert = self._create_critical_alert(risk_report)
            elif current_level == RiskLevel.HIGH:
                alert = self._create_high_alert(risk_report)
            elif current_level == RiskLevel.ELEVATED:
                alert = self._create_elevated_alert(risk_report)

        # Risk cleared
        elif current_level == RiskLevel.NORMAL and self.last_risk_level != RiskLevel.NORMAL:
            alert = Alert(
                timestamp=datetime.utcnow(),
                alert_type=AlertType.RISK_CLEARED,
                title="Risk Cleared",
                message="Market risk has returned to NORMAL. Safe to resume trading.",
                severity="INFO",
                data={'previous_level': self.last_risk_level.value}
            )

        # Gem alert
        if alert:
            self.alerts.append(alert)
            self._save_alerts()
            self._trigger_notification(alert)
            logger.warning(f"ALERT: {alert.title} - {alert.message}")

        self.last_risk_level = current_level
        return alert

    def _risk_escalated(self, old: RiskLevel, new: RiskLevel) -> bool:
        """Checker om risk level er steget"""
        priority = {
            RiskLevel.NORMAL: 0,
            RiskLevel.ELEVATED: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3
        }
        return priority[new] > priority[old]

    def _create_critical_alert(self, report: RiskReport) -> Alert:
        """Opretter CRITICAL alert"""
        factors = ", ".join(report.risk_factors[:3]) if report.risk_factors else "Multiple risk factors"

        return Alert(
            timestamp=datetime.utcnow(),
            alert_type=AlertType.RISK_CRITICAL,
            title="⛔ CRITICAL RISK - EXIT ALL POSITIONS",
            message=f"Critical market risk detected. {factors}",
            severity="CRITICAL",
            data={
                'risk_factors': report.risk_factors,
                'recommendation': report.recommendation
            }
        )

    def _create_high_alert(self, report: RiskReport) -> Alert:
        """Opretter HIGH alert"""
        return Alert(
            timestamp=datetime.utcnow(),
            alert_type=AlertType.RISK_HIGH,
            title="⚠️ HIGH RISK - Reduce Positions",
            message=f"Elevated market risk. High: {report.high_count}, Elevated: {report.elevated_count}",
            severity="HIGH",
            data={
                'risk_factors': report.risk_factors,
                'recommendation': report.recommendation
            }
        )

    def _create_elevated_alert(self, report: RiskReport) -> Alert:
        """Opretter ELEVATED alert"""
        return Alert(
            timestamp=datetime.utcnow(),
            alert_type=AlertType.RISK_ELEVATED,
            title="📊 ELEVATED RISK - Caution",
            message="Market conditions require attention.",
            severity="MEDIUM",
            data={
                'risk_factors': report.risk_factors
            }
        )

    def _trigger_notification(self, alert: Alert) -> None:
        """Trigger notification callbacks"""
        try:
            if alert.alert_type == AlertType.RISK_CRITICAL and self.on_critical_alert:
                self.on_critical_alert(alert)
            elif alert.alert_type == AlertType.RISK_HIGH and self.on_high_alert:
                self.on_high_alert(alert)
        except Exception as e:
            logger.error(f"Notification callback fejl: {e}")

    def add_calendar_alert(self, event_name: str, minutes_until: int) -> Alert:
        """Tilføjer calendar warning alert"""
        alert = Alert(
            timestamp=datetime.utcnow(),
            alert_type=AlertType.CALENDAR_WARNING,
            title=f"📅 Upcoming: {event_name}",
            message=f"High impact event in {minutes_until} minutes",
            severity="HIGH" if minutes_until <= 30 else "MEDIUM",
            data={'event': event_name, 'minutes_until': minutes_until}
        )

        self.alerts.append(alert)
        self._save_alerts()
        return alert

    def add_news_alert(self, headline: str, gold_impact: str) -> Alert:
        """Tilføjer breaking news alert"""
        alert = Alert(
            timestamp=datetime.utcnow(),
            alert_type=AlertType.NEWS_BREAKING,
            title=f"📰 Breaking News",
            message=headline[:100],
            severity="MEDIUM",
            data={'headline': headline, 'gold_impact': gold_impact}
        )

        self.alerts.append(alert)
        self._save_alerts()
        return alert

    def acknowledge_alert(self, alert_index: int) -> bool:
        """Marker alert som acknowledged"""
        if 0 <= alert_index < len(self.alerts):
            self.alerts[alert_index].acknowledged = True
            self._save_alerts()
            return True
        return False

    def get_unacknowledged(self) -> List[Alert]:
        """Henter alle ubekræftede alerts"""
        return [a for a in self.alerts if not a.acknowledged]

    def get_recent_alerts(self, hours: int = 24) -> List[Alert]:
        """Henter alerts fra seneste N timer"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [a for a in self.alerts if a.timestamp >= cutoff]

    def get_alert_summary(self) -> Dict:
        """Returnerer opsummering af alerts"""
        recent = self.get_recent_alerts(24)

        summary = {
            'total_24h': len(recent),
            'critical': sum(1 for a in recent if a.alert_type == AlertType.RISK_CRITICAL),
            'high': sum(1 for a in recent if a.alert_type == AlertType.RISK_HIGH),
            'unacknowledged': len(self.get_unacknowledged()),
            'latest': recent[0].to_dict() if recent else None
        }

        return summary

    def clear_old_alerts(self, days: int = 7) -> int:
        """Rydder gamle alerts"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        old_count = len(self.alerts)
        self.alerts = [a for a in self.alerts if a.timestamp >= cutoff]
        self._save_alerts()
        return old_count - len(self.alerts)
