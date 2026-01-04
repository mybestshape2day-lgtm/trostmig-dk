"""
Trading Intelligence System - Signal Logger
============================================
DEL 1 & 2: Logger alle signals med komplet kontekst og tracker outcomes.

Gemmer:
- Signal data (type, pris, tid)
- Market conditions (regime, volatilitet, korrelationer)
- Indikatorer (RSI, MACD, Stoch, etc.)
- Pattern match info
- Risk factors
- Score breakdown
- Outcomes på forskellige tidspunkter
"""

import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SignalType(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class SignalStatus(Enum):
    PENDING = "PENDING"
    TRACKING = "TRACKING"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"


class OutcomeResult(Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"
    PENDING = "PENDING"


@dataclass
class MarketConditions:
    """Market conditions ved signal tidspunkt"""
    regime: str
    volatility: str
    liquidity: str
    session: str
    correlation_status: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class IndicatorSnapshot:
    """Snapshot af alle indikatorer"""
    stoch_k: float
    stoch_d: float
    rsi: float
    atr: float
    ema_9: float
    ema_21: float
    ema_50: float
    ema_200: float
    macd: float
    macd_signal: float
    macd_hist: float
    bb_upper: float
    bb_middle: float
    bb_lower: float
    adx: float

    @property
    def bollinger_position(self) -> float:
        """Hvor er prisen i forhold til Bollinger Bands (0-1)"""
        if self.bb_upper == self.bb_lower:
            return 0.5
        return (self.ema_9 - self.bb_lower) / (self.bb_upper - self.bb_lower)

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['bollinger_position'] = round(self.bollinger_position, 3)
        return d


@dataclass
class PatternMatchInfo:
    """Info om pattern matching"""
    similar_setups_found: int
    success_rate: float
    avg_gain_similar: float
    avg_loss_similar: float

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RiskFactors:
    """Risk factors ved signal tidspunkt"""
    calendar_status: str
    news_active: bool
    anomaly_detected: bool
    overall_risk: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ScoreBreakdown:
    """Score breakdown"""
    total: float
    base: float
    trend_mult: float = 1.0
    stoch_mult: float = 1.0
    session_mult: float = 1.0
    risk_mult: float = 1.0
    pattern_mult: float = 1.0

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ConfigurationUsed:
    """Konfiguration brugt til dette signal"""
    stoch_oversold: int = 30
    stoch_overbought: int = 70
    min_score: int = 65
    rsi_oversold: int = 30
    rsi_overbought: int = 70
    atr_stop_mult: float = 2.0
    atr_tp_mult: float = 3.0

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PriceSnapshot:
    """Pris snapshot på et tidspunkt"""
    price: float
    pnl: float
    pnl_pct: float
    timestamp: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SignalOutcome:
    """Outcome af et signal"""
    tracked_until: str
    snapshots: Dict[str, PriceSnapshot] = field(default_factory=dict)
    max_profit: float = 0.0
    max_profit_pct: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    peak_time: str = ""
    result: str = "PENDING"
    target_hit: bool = False
    target_price: Optional[float] = None
    target_time: Optional[str] = None
    stop_hit: bool = False
    final_pnl: float = 0.0
    final_pnl_pct: float = 0.0

    def to_dict(self) -> Dict:
        d = {
            'tracked_until': self.tracked_until,
            'snapshots': {k: v.to_dict() if hasattr(v, 'to_dict') else v
                         for k, v in self.snapshots.items()},
            'max_profit': round(self.max_profit, 2),
            'max_profit_pct': round(self.max_profit_pct, 4),
            'max_drawdown': round(self.max_drawdown, 2),
            'max_drawdown_pct': round(self.max_drawdown_pct, 4),
            'peak_time': self.peak_time,
            'result': self.result,
            'target_hit': self.target_hit,
            'target_price': self.target_price,
            'target_time': self.target_time,
            'stop_hit': self.stop_hit,
            'final_pnl': round(self.final_pnl, 2),
            'final_pnl_pct': round(self.final_pnl_pct, 4)
        }
        return d


@dataclass
class SignalRecord:
    """Komplet signal record"""
    id: str
    timestamp: str
    signal_type: str
    entry_price: float

    market_conditions: MarketConditions
    indicators: IndicatorSnapshot
    pattern_match: PatternMatchInfo
    risk_factors: RiskFactors
    score: ScoreBreakdown
    configuration: ConfigurationUsed

    suggested_stop: float
    suggested_target: float

    outcome: Optional[SignalOutcome] = None
    status: str = "PENDING"
    notes: str = ""

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'signal_type': self.signal_type,
            'entry_price': self.entry_price,
            'market_conditions': self.market_conditions.to_dict(),
            'indicators': self.indicators.to_dict(),
            'pattern_match': self.pattern_match.to_dict(),
            'risk_factors': self.risk_factors.to_dict(),
            'score': self.score.to_dict(),
            'configuration': self.configuration.to_dict(),
            'suggested_stop': self.suggested_stop,
            'suggested_target': self.suggested_target,
            'outcome': self.outcome.to_dict() if self.outcome else None,
            'status': self.status,
            'notes': self.notes
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'SignalRecord':
        """Opret SignalRecord fra dictionary"""
        return cls(
            id=data['id'],
            timestamp=data['timestamp'],
            signal_type=data['signal_type'],
            entry_price=data['entry_price'],
            market_conditions=MarketConditions(**data['market_conditions']),
            indicators=IndicatorSnapshot(**{k: v for k, v in data['indicators'].items()
                                           if k != 'bollinger_position'}),
            pattern_match=PatternMatchInfo(**data['pattern_match']),
            risk_factors=RiskFactors(**data['risk_factors']),
            score=ScoreBreakdown(**data['score']),
            configuration=ConfigurationUsed(**data['configuration']),
            suggested_stop=data['suggested_stop'],
            suggested_target=data['suggested_target'],
            outcome=None,  # Simplified - would need proper parsing
            status=data['status'],
            notes=data.get('notes', '')
        )


class SignalLogger:
    """
    Logger og tracker alle trading signals.
    """

    TRACKING_INTERVALS = [1, 3, 5, 10, 15, 30, 60]  # minutter

    def __init__(self, history_file: Path = None):
        if history_file is None:
            history_file = Path(__file__).parent.parent / "data" / "signal_history.json"

        self.history_file = history_file
        self.signals: List[SignalRecord] = []
        self._load_history()

    def _load_history(self) -> None:
        """Indlæser signal historik fra fil"""
        if not self.history_file.exists():
            self._save_history()
            return

        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Simpel loading - i praksis ville vi parse fuldt
            self._raw_signals = data.get('signals', [])
            logger.info(f"Indlæst {len(self._raw_signals)} signals fra historik")

        except Exception as e:
            logger.error(f"Fejl ved indlæsning af signal historik: {e}")
            self._raw_signals = []

    def _save_history(self) -> None:
        """Gemmer signal historik til fil"""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        # Kombiner eksisterende raw signals med nye
        all_signals = self._raw_signals + [s.to_dict() for s in self.signals]

        data = {
            'signals': all_signals,
            'metadata': {
                'last_updated': datetime.utcnow().isoformat() + 'Z',
                'total_signals': len(all_signals),
                'schema_version': '1.0'
            }
        }

        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _generate_signal_id(self) -> str:
        """Genererer unikt signal ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique = str(uuid.uuid4())[:6]
        return f"sig_{timestamp}_{unique}"

    def _determine_session(self, timestamp: datetime) -> str:
        """Bestemmer trading session baseret på UTC tid"""
        hour = timestamp.hour

        if 0 <= hour < 7:
            return "ASIA"
        elif 7 <= hour < 8:
            return "LONDON_OPEN"
        elif 8 <= hour < 13:
            return "LONDON"
        elif 13 <= hour < 14:
            return "NY_OPEN"
        elif 14 <= hour < 17:
            return "OVERLAP"
        elif 17 <= hour < 21:
            return "NY"
        else:
            return "NY_CLOSE"

    def log_signal(self,
                   signal_type: str,
                   entry_price: float,
                   regime: str,
                   volatility: str,
                   liquidity: str,
                   indicators: Dict[str, float],
                   correlations: Dict[str, float],
                   pattern_success_rate: float,
                   pattern_matches: int,
                   risk_level: str,
                   calendar_status: str,
                   news_active: bool,
                   score_total: float,
                   score_breakdown: Dict[str, float],
                   suggested_stop: float,
                   suggested_target: float,
                   configuration: Dict[str, Any] = None) -> SignalRecord:
        """
        Logger et nyt signal med alle detaljer.

        Returns:
            SignalRecord objekt
        """
        now = datetime.utcnow()
        signal_id = self._generate_signal_id()

        # Opret market conditions
        market_conditions = MarketConditions(
            regime=regime,
            volatility=volatility,
            liquidity=liquidity,
            session=self._determine_session(now),
            correlation_status=correlations
        )

        # Opret indicator snapshot
        indicator_snapshot = IndicatorSnapshot(
            stoch_k=indicators.get('Stoch_K', 50),
            stoch_d=indicators.get('Stoch_D', 50),
            rsi=indicators.get('RSI', 50),
            atr=indicators.get('ATR', 0),
            ema_9=indicators.get('EMA_9', entry_price),
            ema_21=indicators.get('EMA_21', entry_price),
            ema_50=indicators.get('EMA_50', entry_price),
            ema_200=indicators.get('EMA_200', entry_price),
            macd=indicators.get('MACD', 0),
            macd_signal=indicators.get('MACD_Signal', 0),
            macd_hist=indicators.get('MACD_Hist', 0),
            bb_upper=indicators.get('BB_Upper', entry_price),
            bb_middle=indicators.get('BB_Middle', entry_price),
            bb_lower=indicators.get('BB_Lower', entry_price),
            adx=indicators.get('ADX', 20)
        )

        # Pattern match info
        avg_gain = (pattern_success_rate / 100) * 5  # Estimat
        avg_loss = ((100 - pattern_success_rate) / 100) * -2  # Estimat

        pattern_match = PatternMatchInfo(
            similar_setups_found=pattern_matches,
            success_rate=pattern_success_rate,
            avg_gain_similar=avg_gain,
            avg_loss_similar=avg_loss
        )

        # Risk factors
        risk_factors = RiskFactors(
            calendar_status=calendar_status,
            news_active=news_active,
            anomaly_detected=risk_level in ['CRITICAL', 'HIGH'],
            overall_risk=risk_level
        )

        # Score breakdown
        score = ScoreBreakdown(
            total=score_total,
            base=score_breakdown.get('base', score_total * 0.6),
            trend_mult=score_breakdown.get('trend_mult', 1.0),
            stoch_mult=score_breakdown.get('stoch_mult', 1.0),
            session_mult=score_breakdown.get('session_mult', 1.0),
            risk_mult=score_breakdown.get('risk_mult', 1.0),
            pattern_mult=score_breakdown.get('pattern_mult', 1.0)
        )

        # Configuration
        config = ConfigurationUsed(**(configuration or {}))

        # Opret signal record
        signal = SignalRecord(
            id=signal_id,
            timestamp=now.isoformat() + 'Z',
            signal_type=signal_type,
            entry_price=entry_price,
            market_conditions=market_conditions,
            indicators=indicator_snapshot,
            pattern_match=pattern_match,
            risk_factors=risk_factors,
            score=score,
            configuration=config,
            suggested_stop=suggested_stop,
            suggested_target=suggested_target,
            status="PENDING"
        )

        self.signals.append(signal)
        self._save_history()

        logger.info(f"Signal logged: {signal_id} - {signal_type} @ ${entry_price:.2f}")
        return signal

    def update_outcome(self, signal_id: str, current_price: float,
                       minutes_elapsed: int) -> Optional[SignalRecord]:
        """
        Opdaterer outcome for et signal.

        Args:
            signal_id: Signal ID
            current_price: Nuværende pris
            minutes_elapsed: Minutter siden entry

        Returns:
            Opdateret SignalRecord eller None
        """
        signal = self.find_signal(signal_id)
        if not signal:
            return None

        entry_price = signal.entry_price
        is_long = signal.signal_type == "LONG"

        # Beregn PnL
        if is_long:
            pnl = current_price - entry_price
        else:
            pnl = entry_price - current_price

        pnl_pct = (pnl / entry_price) * 100

        # Opret eller opdater outcome
        if signal.outcome is None:
            signal.outcome = SignalOutcome(
                tracked_until=datetime.utcnow().isoformat() + 'Z'
            )

        # Tilføj snapshot
        interval_key = f"{minutes_elapsed}min"
        signal.outcome.snapshots[interval_key] = PriceSnapshot(
            price=current_price,
            pnl=pnl,
            pnl_pct=pnl_pct,
            timestamp=datetime.utcnow().isoformat() + 'Z'
        )

        # Opdater max profit/drawdown
        if pnl > signal.outcome.max_profit:
            signal.outcome.max_profit = pnl
            signal.outcome.max_profit_pct = pnl_pct
            signal.outcome.peak_time = interval_key

        if pnl < signal.outcome.max_drawdown:
            signal.outcome.max_drawdown = pnl
            signal.outcome.max_drawdown_pct = pnl_pct

        # Check target/stop
        if is_long:
            if current_price >= signal.suggested_target and not signal.outcome.target_hit:
                signal.outcome.target_hit = True
                signal.outcome.target_price = current_price
                signal.outcome.target_time = interval_key
            if current_price <= signal.suggested_stop:
                signal.outcome.stop_hit = True
        else:
            if current_price <= signal.suggested_target and not signal.outcome.target_hit:
                signal.outcome.target_hit = True
                signal.outcome.target_price = current_price
                signal.outcome.target_time = interval_key
            if current_price >= signal.suggested_stop:
                signal.outcome.stop_hit = True

        # Opdater tracked_until
        signal.outcome.tracked_until = datetime.utcnow().isoformat() + 'Z'

        # Opdater status
        signal.status = "TRACKING"

        self._save_history()
        return signal

    def complete_signal(self, signal_id: str, final_price: float) -> Optional[SignalRecord]:
        """
        Marker signal som completed og bestem resultat.

        Args:
            signal_id: Signal ID
            final_price: Final pris

        Returns:
            Opdateret SignalRecord
        """
        signal = self.find_signal(signal_id)
        if not signal or not signal.outcome:
            return None

        entry_price = signal.entry_price
        is_long = signal.signal_type == "LONG"

        # Beregn final PnL
        if is_long:
            final_pnl = final_price - entry_price
        else:
            final_pnl = entry_price - final_price

        final_pnl_pct = (final_pnl / entry_price) * 100

        signal.outcome.final_pnl = final_pnl
        signal.outcome.final_pnl_pct = final_pnl_pct

        # Bestem resultat
        if signal.outcome.target_hit:
            signal.outcome.result = "WIN"
        elif signal.outcome.stop_hit:
            signal.outcome.result = "LOSS"
        elif final_pnl > 0:
            signal.outcome.result = "WIN"
        elif final_pnl < 0:
            signal.outcome.result = "LOSS"
        else:
            signal.outcome.result = "BREAKEVEN"

        signal.status = "COMPLETED"
        self._save_history()

        logger.info(f"Signal completed: {signal_id} - {signal.outcome.result} ({final_pnl_pct:+.2f}%)")
        return signal

    def find_signal(self, signal_id: str) -> Optional[SignalRecord]:
        """Finder signal by ID"""
        for signal in self.signals:
            if signal.id == signal_id:
                return signal
        return None

    def get_pending_signals(self) -> List[SignalRecord]:
        """Henter alle pending signals"""
        return [s for s in self.signals if s.status in ["PENDING", "TRACKING"]]

    def get_completed_signals(self) -> List[Dict]:
        """Henter alle completed signals (inkl. fra fil)"""
        completed = []

        # Fra hukommelse
        for s in self.signals:
            if s.status == "COMPLETED":
                completed.append(s.to_dict())

        # Fra fil (raw signals)
        for s in self._raw_signals:
            if s.get('status') == "COMPLETED":
                completed.append(s)

        return completed

    def get_all_signals(self) -> List[Dict]:
        """Henter alle signals som dicts"""
        all_signals = [s.to_dict() for s in self.signals]
        all_signals.extend(self._raw_signals)
        return all_signals

    def get_signals_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Henter signals inden for datointerval"""
        all_signals = self.get_all_signals()

        filtered = []
        for s in all_signals:
            timestamp = s.get('timestamp', '')[:10]
            if start_date <= timestamp <= end_date:
                filtered.append(s)

        return filtered

    def get_signal_count(self) -> Dict:
        """Returnerer signal statistik"""
        all_signals = self.get_all_signals()

        return {
            'total': len(all_signals),
            'pending': sum(1 for s in all_signals if s.get('status') == 'PENDING'),
            'tracking': sum(1 for s in all_signals if s.get('status') == 'TRACKING'),
            'completed': sum(1 for s in all_signals if s.get('status') == 'COMPLETED'),
            'wins': sum(1 for s in all_signals
                       if s.get('outcome', {}).get('result') == 'WIN'),
            'losses': sum(1 for s in all_signals
                         if s.get('outcome', {}).get('result') == 'LOSS')
        }
