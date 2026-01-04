"""
Trading Intelligence System - News Sentiment Scanner
=====================================================
DEL 2: Tracker breaking news og sentiment der påvirker guld.

Sentiment Types:
- DOVISH: Fed/central bank dovish → Bullish for gold
- HAWKISH: Fed/central bank hawkish → Bearish for gold
- GEOPOLITICAL: Tension/conflict → Bullish for gold (safe haven)
- RISK_ON: Market optimism → Bearish for gold
- RISK_OFF: Market fear → Bullish for gold
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class NewsSentiment(Enum):
    """News sentiment types"""
    DOVISH = "DOVISH"
    HAWKISH = "HAWKISH"
    GEOPOLITICAL = "GEOPOLITICAL"
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    NEUTRAL = "NEUTRAL"


class GoldImpact(Enum):
    """Impact på guld"""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


@dataclass
class NewsEvent:
    """News event"""
    timestamp: str
    headline: str
    source: str
    sentiment: str
    impact: str
    gold_impact: str
    duration_minutes: int
    tags: List[str] = field(default_factory=list)

    @property
    def datetime_utc(self) -> datetime:
        """Returnerer event datetime"""
        return datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))

    def is_active(self, now: datetime = None) -> bool:
        """Checker om news event stadig er aktiv"""
        now = now or datetime.utcnow()
        event_time = self.datetime_utc.replace(tzinfo=None)
        minutes_since = (now - event_time).total_seconds() / 60
        return 0 <= minutes_since <= self.duration_minutes

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'headline': self.headline,
            'source': self.source,
            'sentiment': self.sentiment,
            'impact': self.impact,
            'gold_impact': self.gold_impact,
            'duration_minutes': self.duration_minutes,
            'tags': self.tags
        }


@dataclass
class NewsCheck:
    """Resultat af news check"""
    has_active_news: bool
    active_count: int
    latest_news: Optional[NewsEvent]
    gold_bias: str  # BULLISH, BEARISH, NEUTRAL
    volatility_expected: bool
    sentiment_summary: Dict[str, int]
    recommendation: str

    def to_dict(self) -> Dict:
        return {
            'has_active_news': self.has_active_news,
            'active_count': self.active_count,
            'latest_news': self.latest_news.to_dict() if self.latest_news else None,
            'gold_bias': self.gold_bias,
            'volatility_expected': self.volatility_expected,
            'sentiment_summary': self.sentiment_summary,
            'recommendation': self.recommendation
        }


class NewsScanner:
    """
    Scanner for breaking news og sentiment analyse.

    Indlæser news fra JSON fil og analyserer aktive events.
    """

    # Sentiment keywords for automatisk klassificering
    BULLISH_KEYWORDS = [
        "rate cut", "dovish", "inflation fears", "geopolitical tension",
        "safe haven", "dollar weakness", "QE", "stimulus", "recession fears",
        "uncertainty", "crisis", "war", "conflict", "sanctions"
    ]

    BEARISH_KEYWORDS = [
        "rate hike", "hawkish", "strong dollar", "risk on",
        "tapering", "quantitative tightening", "economic strength",
        "growth", "optimism", "rally"
    ]

    def __init__(self, news_file: Path = None):
        """
        Args:
            news_file: Sti til news_events.json
        """
        if news_file is None:
            news_file = Path(__file__).parent.parent / "data" / "news_events.json"

        self.news_file = news_file
        self.events: List[NewsEvent] = []
        self._load_events()

    def _load_events(self) -> None:
        """Indlæser news events fra JSON"""
        if not self.news_file.exists():
            logger.warning(f"News events fil ikke fundet: {self.news_file}")
            return

        try:
            with open(self.news_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.events = []
            for event_data in data.get('events', []):
                event = NewsEvent(
                    timestamp=event_data['timestamp'],
                    headline=event_data['headline'],
                    source=event_data['source'],
                    sentiment=event_data['sentiment'],
                    impact=event_data['impact'],
                    gold_impact=event_data['gold_impact'],
                    duration_minutes=event_data.get('duration_minutes', 120),
                    tags=event_data.get('tags', [])
                )
                self.events.append(event)

            logger.info(f"Indlæst {len(self.events)} news events")

        except Exception as e:
            logger.error(f"Fejl ved indlæsning af news: {e}")

    def reload_events(self) -> None:
        """Genindlæser events"""
        self._load_events()

    def check_active_news(self, now: datetime = None) -> NewsCheck:
        """
        Checker for aktive news events.

        Args:
            now: Nuværende tid

        Returns:
            NewsCheck med aktiv news analyse
        """
        now = now or datetime.utcnow()

        active_news = [e for e in self.events if e.is_active(now)]

        if not active_news:
            return NewsCheck(
                has_active_news=False,
                active_count=0,
                latest_news=None,
                gold_bias="NEUTRAL",
                volatility_expected=False,
                sentiment_summary={},
                recommendation="No active news - normal trading conditions"
            )

        # Sorter efter timestamp (nyeste først)
        active_news.sort(key=lambda e: e.datetime_utc, reverse=True)
        latest = active_news[0]

        # Beregn gold bias
        gold_bias = self._calculate_gold_bias(active_news)

        # Check for high impact news
        volatility_expected = any(e.impact == "HIGH" for e in active_news)

        # Sentiment summary
        sentiment_summary = {}
        for e in active_news:
            sentiment_summary[e.sentiment] = sentiment_summary.get(e.sentiment, 0) + 1

        # Generer recommendation
        recommendation = self._generate_recommendation(active_news, gold_bias, volatility_expected)

        return NewsCheck(
            has_active_news=True,
            active_count=len(active_news),
            latest_news=latest,
            gold_bias=gold_bias,
            volatility_expected=volatility_expected,
            sentiment_summary=sentiment_summary,
            recommendation=recommendation
        )

    def _calculate_gold_bias(self, active_news: List[NewsEvent]) -> str:
        """Beregner samlet gold bias fra aktive news"""
        bullish_count = sum(1 for e in active_news if e.gold_impact == "BULLISH")
        bearish_count = sum(1 for e in active_news if e.gold_impact == "BEARISH")

        # Vægt efter impact
        bullish_weight = sum(2 if e.impact == "HIGH" else 1
                           for e in active_news if e.gold_impact == "BULLISH")
        bearish_weight = sum(2 if e.impact == "HIGH" else 1
                           for e in active_news if e.gold_impact == "BEARISH")

        if bullish_weight > bearish_weight * 1.5:
            return "BULLISH"
        elif bearish_weight > bullish_weight * 1.5:
            return "BEARISH"
        else:
            return "NEUTRAL"

    def _generate_recommendation(self, active_news: List[NewsEvent],
                                   gold_bias: str, volatility_expected: bool) -> str:
        """Genererer trading anbefaling"""
        latest = active_news[0]

        if volatility_expected:
            return f"⚠️ HIGH IMPACT NEWS: {latest.headline[:50]}... - Expect volatility"

        if gold_bias == "BULLISH":
            return f"📈 News bias BULLISH for gold: {latest.headline[:50]}..."
        elif gold_bias == "BEARISH":
            return f"📉 News bias BEARISH for gold: {latest.headline[:50]}..."
        else:
            return f"📰 Active news: {latest.headline[:50]}... - Mixed signals"

    def analyze_headline(self, headline: str) -> Dict:
        """
        Analyserer en headline for sentiment og gold impact.

        Args:
            headline: News headline tekst

        Returns:
            Dict med sentiment analyse
        """
        headline_lower = headline.lower()

        # Check for bullish keywords
        bullish_matches = [kw for kw in self.BULLISH_KEYWORDS if kw in headline_lower]
        bearish_matches = [kw for kw in self.BEARISH_KEYWORDS if kw in headline_lower]

        if len(bullish_matches) > len(bearish_matches):
            gold_impact = "BULLISH"
            sentiment = "DOVISH" if any(kw in headline_lower for kw in ["rate cut", "dovish", "stimulus"]) else "RISK_OFF"
        elif len(bearish_matches) > len(bullish_matches):
            gold_impact = "BEARISH"
            sentiment = "HAWKISH" if any(kw in headline_lower for kw in ["rate hike", "hawkish", "tapering"]) else "RISK_ON"
        else:
            gold_impact = "NEUTRAL"
            sentiment = "NEUTRAL"

        return {
            'headline': headline,
            'gold_impact': gold_impact,
            'sentiment': sentiment,
            'bullish_keywords': bullish_matches,
            'bearish_keywords': bearish_matches
        }

    def add_news(self, headline: str, source: str = "Manual",
                 sentiment: str = None, impact: str = "MEDIUM",
                 gold_impact: str = None, duration_minutes: int = 120) -> bool:
        """
        Tilføjer ny news event.

        Args:
            headline: News headline
            source: Kilde
            sentiment: Sentiment (auto-detected hvis None)
            impact: Impact level
            gold_impact: Gold impact (auto-detected hvis None)
            duration_minutes: Hvor længe news er aktiv

        Returns:
            True hvis success
        """
        try:
            # Auto-detect sentiment hvis ikke angivet
            if sentiment is None or gold_impact is None:
                analysis = self.analyze_headline(headline)
                sentiment = sentiment or analysis['sentiment']
                gold_impact = gold_impact or analysis['gold_impact']

            event = NewsEvent(
                timestamp=datetime.utcnow().isoformat() + 'Z',
                headline=headline,
                source=source,
                sentiment=sentiment,
                impact=impact,
                gold_impact=gold_impact,
                duration_minutes=duration_minutes,
                tags=[]
            )

            self.events.append(event)
            self._save_events()
            logger.info(f"Tilføjet news: {headline[:50]}...")
            return True

        except Exception as e:
            logger.error(f"Fejl ved tilføjelse af news: {e}")
            return False

    def _save_events(self) -> None:
        """Gemmer events til JSON fil"""
        data = {
            "events": [e.to_dict() for e in self.events],
            "metadata": {
                "last_updated": datetime.utcnow().isoformat() + 'Z',
                "note": "Add breaking news manually or via API integration later"
            }
        }

        with open(self.news_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_recent_news(self, hours: int = 24) -> List[NewsEvent]:
        """Henter news fra de seneste N timer"""
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=hours)

        recent = []
        for e in self.events:
            try:
                event_time = e.datetime_utc.replace(tzinfo=None)
                if event_time >= cutoff:
                    recent.append(e)
            except:
                pass

        return sorted(recent, key=lambda e: e.datetime_utc, reverse=True)
