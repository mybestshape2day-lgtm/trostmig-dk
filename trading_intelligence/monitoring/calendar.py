"""
Trading Intelligence System - Economic Calendar
================================================
DEL 1: Tracker vigtige økonomiske events og advarer før high-impact releases.

Risk Levels:
- CRITICAL: HIGH impact event < 30 min (no trades)
- ELEVATED: HIGH impact event < 60 min OR MEDIUM impact < 30 min
- NORMAL: No imminent events
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CalendarStatus(Enum):
    """Calendar risk status"""
    CLEAR = "CLEAR"
    ELEVATED = "ELEVATED"
    CRITICAL = "CRITICAL"


class EventImpact(Enum):
    """Event impact levels"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class EconomicEvent:
    """Økonomisk event"""
    date: str
    time: str
    timezone: str
    event: str
    impact: str
    currency: str
    warning_minutes: int
    expected: Optional[str] = None
    previous: Optional[str] = None
    description: Optional[str] = None

    @property
    def datetime_utc(self) -> datetime:
        """Returnerer event datetime i UTC"""
        dt_str = f"{self.date}T{self.time}"
        return datetime.fromisoformat(dt_str)

    def to_dict(self) -> Dict:
        return {
            'date': self.date,
            'time': self.time,
            'event': self.event,
            'impact': self.impact,
            'currency': self.currency,
            'expected': self.expected,
            'previous': self.previous,
            'description': self.description
        }


@dataclass
class CalendarCheck:
    """Resultat af calendar check"""
    status: CalendarStatus
    has_upcoming: bool
    next_event: Optional[EconomicEvent]
    minutes_until: Optional[int]
    risk_level: str
    recommendation: str
    all_upcoming: List[EconomicEvent] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'status': self.status.value,
            'has_upcoming': self.has_upcoming,
            'next_event': self.next_event.to_dict() if self.next_event else None,
            'minutes_until': self.minutes_until,
            'risk_level': self.risk_level,
            'recommendation': self.recommendation,
            'upcoming_count': len(self.all_upcoming)
        }


class EconomicCalendar:
    """
    Scanner og manager for økonomisk kalender.

    Indlæser events fra JSON fil og checker for kommende high-impact events.
    """

    def __init__(self, events_file: Path = None):
        """
        Args:
            events_file: Sti til economic_events.json
        """
        if events_file is None:
            events_file = Path(__file__).parent.parent / "data" / "economic_events.json"

        self.events_file = events_file
        self.events: List[EconomicEvent] = []
        self._load_events()

    def _load_events(self) -> None:
        """Indlæser events fra JSON fil"""
        if not self.events_file.exists():
            logger.warning(f"Economic events fil ikke fundet: {self.events_file}")
            return

        try:
            with open(self.events_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.events = []
            for event_data in data.get('events', []):
                event = EconomicEvent(
                    date=event_data['date'],
                    time=event_data['time'],
                    timezone=event_data.get('timezone', 'UTC'),
                    event=event_data['event'],
                    impact=event_data['impact'],
                    currency=event_data['currency'],
                    warning_minutes=event_data.get('warning_minutes', 60),
                    expected=event_data.get('expected'),
                    previous=event_data.get('previous'),
                    description=event_data.get('description')
                )
                self.events.append(event)

            logger.info(f"Indlæst {len(self.events)} økonomiske events")

        except Exception as e:
            logger.error(f"Fejl ved indlæsning af events: {e}")

    def reload_events(self) -> None:
        """Genindlæser events fra fil"""
        self._load_events()

    def check_upcoming_events(self, now: datetime = None,
                               lookahead_hours: int = 24) -> CalendarCheck:
        """
        Checker for kommende events indenfor warning window.

        Args:
            now: Nuværende tid (default: datetime.utcnow())
            lookahead_hours: Timer fremad at scanne

        Returns:
            CalendarCheck med status og detaljer
        """
        now = now or datetime.utcnow()
        lookahead = now + timedelta(hours=lookahead_hours)

        upcoming = []
        for event in self.events:
            try:
                event_time = event.datetime_utc
                minutes_until = (event_time - now).total_seconds() / 60

                # Event er i fremtiden og inden for warning window
                if 0 < minutes_until <= event.warning_minutes:
                    upcoming.append((event, minutes_until))
                # Event er i fremtiden og inden for lookahead
                elif 0 < minutes_until <= lookahead_hours * 60:
                    upcoming.append((event, minutes_until))

            except Exception as e:
                logger.warning(f"Fejl ved parsing af event {event.event}: {e}")

        # Sorter efter tid
        upcoming.sort(key=lambda x: x[1])

        if not upcoming:
            return CalendarCheck(
                status=CalendarStatus.CLEAR,
                has_upcoming=False,
                next_event=None,
                minutes_until=None,
                risk_level="NORMAL",
                recommendation="No upcoming economic events - safe to trade",
                all_upcoming=[]
            )

        next_event, minutes_until = upcoming[0]
        risk_level = self._calculate_risk_level(next_event, minutes_until)
        status = self._determine_status(risk_level)
        recommendation = self._generate_recommendation(next_event, minutes_until, risk_level)

        return CalendarCheck(
            status=status,
            has_upcoming=True,
            next_event=next_event,
            minutes_until=int(minutes_until),
            risk_level=risk_level,
            recommendation=recommendation,
            all_upcoming=[e for e, _ in upcoming]
        )

    def _calculate_risk_level(self, event: EconomicEvent, minutes_until: float) -> str:
        """Beregner risk level baseret på event impact og tid"""
        impact = event.impact.upper()

        if impact == "HIGH":
            if minutes_until <= 30:
                return "CRITICAL"
            elif minutes_until <= 60:
                return "ELEVATED"
            else:
                return "WARNING"
        elif impact == "MEDIUM":
            if minutes_until <= 30:
                return "ELEVATED"
            else:
                return "NORMAL"
        else:  # LOW
            return "NORMAL"

    def _determine_status(self, risk_level: str) -> CalendarStatus:
        """Konverterer risk level til CalendarStatus"""
        if risk_level == "CRITICAL":
            return CalendarStatus.CRITICAL
        elif risk_level in ["ELEVATED", "WARNING"]:
            return CalendarStatus.ELEVATED
        else:
            return CalendarStatus.CLEAR

    def _generate_recommendation(self, event: EconomicEvent,
                                   minutes_until: float, risk_level: str) -> str:
        """Genererer anbefaling baseret på event"""
        hours = int(minutes_until // 60)
        mins = int(minutes_until % 60)
        time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"

        if risk_level == "CRITICAL":
            return f"⚠️ CRITICAL: {event.event} in {time_str} - EXIT ALL POSITIONS"
        elif risk_level == "ELEVATED":
            return f"⚡ ELEVATED: {event.event} in {time_str} - Reduce position size"
        elif risk_level == "WARNING":
            return f"📅 WARNING: {event.event} in {time_str} - Monitor closely"
        else:
            return f"ℹ️ Upcoming: {event.event} in {time_str}"

    def get_events_for_date(self, date: str) -> List[EconomicEvent]:
        """Henter alle events for en specifik dato"""
        return [e for e in self.events if e.date == date]

    def get_high_impact_events(self, days_ahead: int = 7) -> List[EconomicEvent]:
        """Henter alle HIGH impact events de næste N dage"""
        now = datetime.utcnow()
        cutoff = now + timedelta(days=days_ahead)

        high_impact = []
        for event in self.events:
            if event.impact.upper() == "HIGH":
                try:
                    event_time = event.datetime_utc
                    if now <= event_time <= cutoff:
                        high_impact.append(event)
                except:
                    pass

        return sorted(high_impact, key=lambda e: e.datetime_utc)

    def add_event(self, event_data: Dict) -> bool:
        """
        Tilføjer ny event til kalenderen og gemmer til fil.

        Args:
            event_data: Dict med event felter

        Returns:
            True hvis success
        """
        try:
            event = EconomicEvent(
                date=event_data['date'],
                time=event_data['time'],
                timezone=event_data.get('timezone', 'UTC'),
                event=event_data['event'],
                impact=event_data['impact'],
                currency=event_data.get('currency', 'USD'),
                warning_minutes=event_data.get('warning_minutes', 60),
                expected=event_data.get('expected'),
                previous=event_data.get('previous'),
                description=event_data.get('description')
            )

            self.events.append(event)
            self._save_events()
            logger.info(f"Tilføjet event: {event.event}")
            return True

        except Exception as e:
            logger.error(f"Fejl ved tilføjelse af event: {e}")
            return False

    def _save_events(self) -> None:
        """Gemmer events til JSON fil"""
        data = {
            "events": [
                {
                    "date": e.date,
                    "time": e.time,
                    "timezone": e.timezone,
                    "event": e.event,
                    "impact": e.impact,
                    "currency": e.currency,
                    "warning_minutes": e.warning_minutes,
                    "expected": e.expected,
                    "previous": e.previous,
                    "description": e.description
                }
                for e in self.events
            ],
            "metadata": {
                "last_updated": datetime.utcnow().isoformat(),
                "source": "Manual entry"
            }
        }

        with open(self.events_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
