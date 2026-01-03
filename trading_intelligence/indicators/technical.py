"""
Trading Intelligence System - Tekniske Indikatorer
===================================================
Beregning af tekniske indikatorer for trading analyse.
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple

from config import INDICATORS


class TechnicalIndicators:
    """
    Beregner tekniske indikatorer fra OHLCV data.

    Understøtter:
    - EMA (Eksponentiel Glidende Gennemsnit)
    - Stokastisk Oscillator
    - RSI (Relative Strength Index)
    - MACD (Moving Average Convergence Divergence)
    - Bollinger Bands
    - ATR (Average True Range)
    - ADX (Average Directional Index)
    """

    def __init__(self, config: Optional[object] = None):
        self.config = config or INDICATORS

    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Beregner alle tekniske indikatorer og tilføjer til DataFrame.

        Args:
            df: DataFrame med OHLCV data

        Returns:
            DataFrame med alle indikatorer tilføjet
        """
        result = df.copy()

        # EMA
        for period in self.config.EMA_PERIODS:
            result[f'EMA_{period}'] = self.ema(df['Close'], period)

        # Stokastisk
        stoch_k, stoch_d = self.stochastic(df)
        result['Stoch_K'] = stoch_k
        result['Stoch_D'] = stoch_d

        # RSI
        result['RSI'] = self.rsi(df['Close'])

        # MACD
        macd, signal, hist = self.macd(df['Close'])
        result['MACD'] = macd
        result['MACD_Signal'] = signal
        result['MACD_Hist'] = hist

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = self.bollinger_bands(df['Close'])
        result['BB_Upper'] = bb_upper
        result['BB_Middle'] = bb_middle
        result['BB_Lower'] = bb_lower

        # ATR
        result['ATR'] = self.atr(df)

        # ADX
        adx, plus_di, minus_di = self.adx(df)
        result['ADX'] = adx
        result['Plus_DI'] = plus_di
        result['Minus_DI'] = minus_di

        return result

    def ema(self, series: pd.Series, period: int) -> pd.Series:
        """
        Beregner Eksponentiel Glidende Gennemsnit.

        Args:
            series: Prisdata (typisk Close)
            period: EMA periode

        Returns:
            Series med EMA værdier
        """
        return series.ewm(span=period, adjust=False).mean()

    def sma(self, series: pd.Series, period: int) -> pd.Series:
        """Beregner Simpel Glidende Gennemsnit"""
        return series.rolling(window=period).mean()

    def stochastic(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """
        Beregner Stokastisk Oscillator.

        Formler:
        %K = 100 * (Close - Lowest Low) / (Highest High - Lowest Low)
        %D = SMA(%K, d_period)

        Args:
            df: DataFrame med High, Low, Close

        Returns:
            Tuple af (Stoch_K, Stoch_D)
        """
        k_period = self.config.STOCH_K_PERIOD
        d_period = self.config.STOCH_D_PERIOD
        smooth_k = self.config.STOCH_SMOOTH_K

        low_min = df['Low'].rolling(window=k_period).min()
        high_max = df['High'].rolling(window=k_period).max()

        stoch_k = 100 * (df['Close'] - low_min) / (high_max - low_min)
        stoch_k = stoch_k.rolling(window=smooth_k).mean()  # Smooth %K
        stoch_d = stoch_k.rolling(window=d_period).mean()

        return stoch_k, stoch_d

    def rsi(self, series: pd.Series, period: int = None) -> pd.Series:
        """
        Beregner Relative Strength Index.

        Formel:
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss

        Args:
            series: Prisdata (typisk Close)
            period: RSI periode (default: 14)

        Returns:
            Series med RSI værdier (0-100)
        """
        period = period or self.config.RSI_PERIOD

        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def macd(self, series: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Beregner MACD (Moving Average Convergence Divergence).

        Formler:
        MACD Line = EMA(fast) - EMA(slow)
        Signal Line = EMA(MACD Line, signal_period)
        Histogram = MACD Line - Signal Line

        Args:
            series: Prisdata (typisk Close)

        Returns:
            Tuple af (MACD, Signal, Histogram)
        """
        fast_ema = self.ema(series, self.config.MACD_FAST)
        slow_ema = self.ema(series, self.config.MACD_SLOW)

        macd_line = fast_ema - slow_ema
        signal_line = self.ema(macd_line, self.config.MACD_SIGNAL)
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def bollinger_bands(self, series: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Beregner Bollinger Bands.

        Formler:
        Middle = SMA(period)
        Upper = Middle + (std * std_dev)
        Lower = Middle - (std * std_dev)

        Args:
            series: Prisdata (typisk Close)

        Returns:
            Tuple af (Upper, Middle, Lower)
        """
        period = self.config.BB_PERIOD
        std_dev = self.config.BB_STD

        middle = self.sma(series, period)
        std = series.rolling(window=period).std()

        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        return upper, middle, lower

    def atr(self, df: pd.DataFrame, period: int = None) -> pd.Series:
        """
        Beregner Average True Range.

        True Range = max(High-Low, |High-PrevClose|, |Low-PrevClose|)
        ATR = EMA(True Range, period)

        Args:
            df: DataFrame med High, Low, Close
            period: ATR periode

        Returns:
            Series med ATR værdier
        """
        period = period or self.config.ATR_PERIOD

        high = df['High']
        low = df['Low']
        close = df['Close'].shift(1)

        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.ewm(span=period, adjust=False).mean()

        return atr

    def adx(self, df: pd.DataFrame, period: int = None) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Beregner Average Directional Index.

        +DI = 100 * EMA(+DM) / ATR
        -DI = 100 * EMA(-DM) / ATR
        DX = 100 * |+DI - -DI| / (+DI + -DI)
        ADX = EMA(DX, period)

        Args:
            df: DataFrame med High, Low, Close
            period: ADX periode

        Returns:
            Tuple af (ADX, +DI, -DI)
        """
        period = period or self.config.ADX_PERIOD

        high = df['High']
        low = df['Low']

        # Directional Movement
        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        # ATR for normalisering
        atr = self.atr(df, period)

        # Smoothed DI
        plus_di = 100 * plus_dm.ewm(span=period, adjust=False).mean() / atr
        minus_di = 100 * minus_dm.ewm(span=period, adjust=False).mean() / atr

        # DX og ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.ewm(span=period, adjust=False).mean()

        return adx, plus_di, minus_di

    def get_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Genererer trading signaler baseret på indikatorer.

        Args:
            df: DataFrame med beregnede indikatorer

        Returns:
            DataFrame med signal kolonner
        """
        signals = pd.DataFrame(index=df.index)

        # RSI signaler
        if 'RSI' in df.columns:
            signals['RSI_Oversold'] = df['RSI'] < self.config.RSI_OVERSOLD
            signals['RSI_Overbought'] = df['RSI'] > self.config.RSI_OVERBOUGHT

        # MACD kryds
        if 'MACD' in df.columns and 'MACD_Signal' in df.columns:
            macd_cross = df['MACD'] - df['MACD_Signal']
            signals['MACD_Bullish_Cross'] = (macd_cross > 0) & (macd_cross.shift(1) <= 0)
            signals['MACD_Bearish_Cross'] = (macd_cross < 0) & (macd_cross.shift(1) >= 0)

        # Bollinger Band touch
        if all(col in df.columns for col in ['Close', 'BB_Upper', 'BB_Lower']):
            signals['BB_Lower_Touch'] = df['Close'] <= df['BB_Lower']
            signals['BB_Upper_Touch'] = df['Close'] >= df['BB_Upper']

        # Stokastisk kryds
        if 'Stoch_K' in df.columns and 'Stoch_D' in df.columns:
            stoch_cross = df['Stoch_K'] - df['Stoch_D']
            signals['Stoch_Bullish_Cross'] = (stoch_cross > 0) & (stoch_cross.shift(1) <= 0) & (df['Stoch_K'] < 20)
            signals['Stoch_Bearish_Cross'] = (stoch_cross < 0) & (stoch_cross.shift(1) >= 0) & (df['Stoch_K'] > 80)

        # Trend styrke (ADX)
        if 'ADX' in df.columns:
            signals['Strong_Trend'] = df['ADX'] > 25
            signals['Weak_Trend'] = df['ADX'] < 20

        return signals
