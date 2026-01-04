"""
Trading Intelligence System - Anomaly Detection
================================================
DEL 3: Detekterer farlige markedsændringer der kræver øjeblikkelig handling.

Anomaly Types:
- Flash Crash: Pludselig pris drop/spike > 3x ATR
- Volume Spike: Volume > 2.5x gennemsnit
- Correlation Break: Guld-DXY korrelation skifter til positiv
- VIX Spike: Volatilitets index > 1.5x gennemsnit
- Spread Widening: Bid-ask spread > 2x normal
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AnomalyType(Enum):
    """Typer af anomalier"""
    FLASH_CRASH = "FLASH_CRASH"
    FLASH_SPIKE = "FLASH_SPIKE"
    VOLUME_EXTREME = "VOLUME_EXTREME"
    VOLUME_HIGH = "VOLUME_HIGH"
    CORRELATION_BREAK = "CORRELATION_BREAK"
    VIX_SPIKE = "VIX_SPIKE"
    SPREAD_WIDENING = "SPREAD_WIDENING"


class AnomalySeverity(Enum):
    """Anomali alvorlighed"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NORMAL = "NORMAL"


@dataclass
class AnomalyDetection:
    """Resultat af anomali detektion"""
    detected: bool
    anomaly_type: Optional[AnomalyType]
    severity: AnomalySeverity
    value: float
    threshold: float
    description: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        return {
            'detected': self.detected,
            'type': self.anomaly_type.value if self.anomaly_type else None,
            'severity': self.severity.value,
            'value': round(float(self.value), 4),
            'threshold': round(float(self.threshold), 4),
            'description': self.description,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class AnomalyScan:
    """Komplet anomali scanning resultat"""
    flash_crash: AnomalyDetection
    volume: AnomalyDetection
    correlation: AnomalyDetection
    vix: AnomalyDetection
    any_critical: bool
    any_high: bool
    total_anomalies: int
    recommendation: str

    def to_dict(self) -> Dict:
        return {
            'flash_crash': self.flash_crash.to_dict(),
            'volume': self.volume.to_dict(),
            'correlation': self.correlation.to_dict(),
            'vix': self.vix.to_dict(),
            'any_critical': self.any_critical,
            'any_high': self.any_high,
            'total_anomalies': self.total_anomalies,
            'recommendation': self.recommendation
        }


class AnomalyDetector:
    """
    Detekterer markedsanomalier der kræver handling.
    """

    def __init__(self,
                 flash_crash_atr_mult: float = 3.0,
                 volume_high_mult: float = 2.5,
                 volume_extreme_mult: float = 5.0,
                 correlation_break_threshold: float = -0.3,
                 vix_spike_mult: float = 1.5,
                 lookback_bars: int = 5):
        """
        Args:
            flash_crash_atr_mult: ATR multiplier for flash crash detektion
            volume_high_mult: Volume multiplier for HIGH alert
            volume_extreme_mult: Volume multiplier for EXTREME alert
            correlation_break_threshold: Korrelation over dette = break
            vix_spike_mult: VIX multiplier for spike detektion
            lookback_bars: Antal bars at analysere
        """
        self.flash_crash_mult = flash_crash_atr_mult
        self.vol_high = volume_high_mult
        self.vol_extreme = volume_extreme_mult
        self.corr_break = correlation_break_threshold
        self.vix_mult = vix_spike_mult
        self.lookback = lookback_bars

    def detect_flash_crash(self, df: pd.DataFrame) -> AnomalyDetection:
        """
        Detekterer flash crash/spike baseret på ATR.

        Args:
            df: DataFrame med Close og ATR kolonner

        Returns:
            AnomalyDetection
        """
        if len(df) < 2 or 'ATR' not in df.columns:
            return AnomalyDetection(
                detected=False,
                anomaly_type=None,
                severity=AnomalySeverity.NORMAL,
                value=0,
                threshold=0,
                description="Insufficient data for flash crash detection"
            )

        # Analyser seneste bars
        lookback = min(self.lookback, len(df) - 1)
        recent = df.iloc[-lookback:]

        for i in range(1, len(recent)):
            price_change = abs(recent['Close'].iloc[i] - recent['Close'].iloc[i-1])
            atr = recent['ATR'].iloc[i]

            if atr > 0:
                magnitude = price_change / atr

                if magnitude > self.flash_crash_mult:
                    is_crash = recent['Close'].iloc[i] < recent['Close'].iloc[i-1]
                    anomaly_type = AnomalyType.FLASH_CRASH if is_crash else AnomalyType.FLASH_SPIKE

                    return AnomalyDetection(
                        detected=True,
                        anomaly_type=anomaly_type,
                        severity=AnomalySeverity.CRITICAL,
                        value=magnitude,
                        threshold=self.flash_crash_mult,
                        description=f"{'CRASH' if is_crash else 'SPIKE'}: Price moved {magnitude:.1f}x ATR in single bar"
                    )

        return AnomalyDetection(
            detected=False,
            anomaly_type=None,
            severity=AnomalySeverity.NORMAL,
            value=0,
            threshold=self.flash_crash_mult,
            description="No flash crash/spike detected"
        )

    def detect_volume_anomaly(self, df: pd.DataFrame, period: int = 20) -> AnomalyDetection:
        """
        Detekterer volume anomalier.

        Args:
            df: DataFrame med Volume kolonne
            period: Periode til gennemsnitsberegning

        Returns:
            AnomalyDetection
        """
        if 'Volume' not in df.columns or len(df) < period:
            return AnomalyDetection(
                detected=False,
                anomaly_type=None,
                severity=AnomalySeverity.NORMAL,
                value=1.0,
                threshold=self.vol_high,
                description="Insufficient volume data"
            )

        current = df['Volume'].iloc[-1]
        avg = df['Volume'].iloc[-period:].mean()

        if avg == 0 or pd.isna(avg):
            return AnomalyDetection(
                detected=False,
                anomaly_type=None,
                severity=AnomalySeverity.NORMAL,
                value=1.0,
                threshold=self.vol_high,
                description="No volume data available"
            )

        ratio = current / avg

        if ratio > self.vol_extreme:
            return AnomalyDetection(
                detected=True,
                anomaly_type=AnomalyType.VOLUME_EXTREME,
                severity=AnomalySeverity.CRITICAL,
                value=ratio,
                threshold=self.vol_extreme,
                description=f"EXTREME volume: {ratio:.1f}x average"
            )
        elif ratio > self.vol_high:
            return AnomalyDetection(
                detected=True,
                anomaly_type=AnomalyType.VOLUME_HIGH,
                severity=AnomalySeverity.HIGH,
                value=ratio,
                threshold=self.vol_high,
                description=f"HIGH volume: {ratio:.1f}x average"
            )

        return AnomalyDetection(
            detected=False,
            anomaly_type=None,
            severity=AnomalySeverity.NORMAL,
            value=ratio,
            threshold=self.vol_high,
            description=f"Normal volume: {ratio:.1f}x average"
        )

    def detect_correlation_break(self, gold_df: pd.DataFrame,
                                   dxy_df: pd.DataFrame,
                                   period: int = 10) -> AnomalyDetection:
        """
        Detekterer brud i guld-dollar korrelation.

        Normal: Guld og DXY er negativt korreleret (< -0.6)
        Break: Korrelation bliver positiv eller svagt negativ

        Args:
            gold_df: DataFrame med guld Close
            dxy_df: DataFrame med DXY Close
            period: Periode til korrelationsberegning

        Returns:
            AnomalyDetection
        """
        if gold_df.empty or dxy_df.empty:
            return AnomalyDetection(
                detected=False,
                anomaly_type=None,
                severity=AnomalySeverity.NORMAL,
                value=0,
                threshold=self.corr_break,
                description="Insufficient data for correlation analysis"
            )

        # Beregn returns
        gold_returns = gold_df['Close'].pct_change().dropna()
        dxy_returns = dxy_df['Close'].pct_change().dropna()

        # Synkroniser
        combined = pd.DataFrame({
            'gold': gold_returns,
            'dxy': dxy_returns
        }).dropna()

        if len(combined) < period:
            return AnomalyDetection(
                detected=False,
                anomaly_type=None,
                severity=AnomalySeverity.NORMAL,
                value=0,
                threshold=self.corr_break,
                description="Insufficient overlapping data"
            )

        # Seneste N dages korrelation
        recent_corr = combined['gold'].iloc[-period:].corr(combined['dxy'].iloc[-period:])

        # Normal korrelation er negativ (< -0.6)
        # Break = korrelation bliver positiv eller svagt negativ
        if recent_corr > self.corr_break:
            severity = AnomalySeverity.HIGH if recent_corr > 0 else AnomalySeverity.MEDIUM

            return AnomalyDetection(
                detected=True,
                anomaly_type=AnomalyType.CORRELATION_BREAK,
                severity=severity,
                value=recent_corr,
                threshold=self.corr_break,
                description=f"Correlation break: Gold-DXY at {recent_corr:.2f} (expected < -0.6)"
            )

        return AnomalyDetection(
            detected=False,
            anomaly_type=None,
            severity=AnomalySeverity.NORMAL,
            value=recent_corr,
            threshold=self.corr_break,
            description=f"Normal correlation: {recent_corr:.2f}"
        )

    def detect_vix_spike(self, vix_df: pd.DataFrame, period: int = 20) -> AnomalyDetection:
        """
        Detekterer VIX spike.

        Args:
            vix_df: DataFrame med VIX Close
            period: Periode til gennemsnitsberegning

        Returns:
            AnomalyDetection
        """
        if vix_df.empty or len(vix_df) < period:
            return AnomalyDetection(
                detected=False,
                anomaly_type=None,
                severity=AnomalySeverity.NORMAL,
                value=0,
                threshold=self.vix_mult,
                description="Insufficient VIX data"
            )

        current = vix_df['Close'].iloc[-1]
        avg = vix_df['Close'].iloc[-period:].mean()

        ratio = current / avg if avg > 0 else 1.0

        if ratio > 2.0:
            return AnomalyDetection(
                detected=True,
                anomaly_type=AnomalyType.VIX_SPIKE,
                severity=AnomalySeverity.CRITICAL,
                value=ratio,
                threshold=2.0,
                description=f"EXTREME VIX spike: {current:.1f} ({ratio:.1f}x average)"
            )
        elif ratio > self.vix_mult:
            return AnomalyDetection(
                detected=True,
                anomaly_type=AnomalyType.VIX_SPIKE,
                severity=AnomalySeverity.HIGH,
                value=ratio,
                threshold=self.vix_mult,
                description=f"VIX elevated: {current:.1f} ({ratio:.1f}x average)"
            )

        return AnomalyDetection(
            detected=False,
            anomaly_type=None,
            severity=AnomalySeverity.NORMAL,
            value=ratio,
            threshold=self.vix_mult,
            description=f"VIX normal: {current:.1f} ({ratio:.1f}x average)"
        )

    def run_full_scan(self, gold_df: pd.DataFrame,
                      dxy_df: pd.DataFrame = None,
                      vix_df: pd.DataFrame = None) -> AnomalyScan:
        """
        Kører komplet anomali scanning.

        Args:
            gold_df: DataFrame med guld OHLCV og ATR
            dxy_df: DataFrame med DXY data (optional)
            vix_df: DataFrame med VIX data (optional)

        Returns:
            AnomalyScan med alle resultater
        """
        # Flash crash
        flash_crash = self.detect_flash_crash(gold_df)

        # Volume
        volume = self.detect_volume_anomaly(gold_df)

        # Correlation (hvis DXY data)
        if dxy_df is not None and not dxy_df.empty:
            correlation = self.detect_correlation_break(gold_df, dxy_df)
        else:
            correlation = AnomalyDetection(
                detected=False,
                anomaly_type=None,
                severity=AnomalySeverity.NORMAL,
                value=0,
                threshold=self.corr_break,
                description="No DXY data available"
            )

        # VIX (hvis VIX data)
        if vix_df is not None and not vix_df.empty:
            vix = self.detect_vix_spike(vix_df)
        else:
            vix = AnomalyDetection(
                detected=False,
                anomaly_type=None,
                severity=AnomalySeverity.NORMAL,
                value=0,
                threshold=self.vix_mult,
                description="No VIX data available"
            )

        # Sammenfat
        all_detections = [flash_crash, volume, correlation, vix]

        any_critical = any(d.severity == AnomalySeverity.CRITICAL for d in all_detections)
        any_high = any(d.severity == AnomalySeverity.HIGH for d in all_detections)
        total_anomalies = sum(1 for d in all_detections if d.detected)

        # Generer recommendation
        if any_critical:
            recommendation = "⛔ CRITICAL ANOMALY DETECTED - Exit all positions immediately"
        elif any_high:
            recommendation = "⚠️ HIGH RISK anomaly detected - Reduce positions"
        elif total_anomalies > 0:
            recommendation = "📊 Minor anomalies detected - Monitor closely"
        else:
            recommendation = "✅ No anomalies - Normal market conditions"

        return AnomalyScan(
            flash_crash=flash_crash,
            volume=volume,
            correlation=correlation,
            vix=vix,
            any_critical=any_critical,
            any_high=any_high,
            total_anomalies=total_anomalies,
            recommendation=recommendation
        )
