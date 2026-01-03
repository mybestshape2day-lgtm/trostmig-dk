"""
Trading Intelligence System - Database Manager
===============================================
SQLite database til lagring af OHLCV data, indikatorer og korrelationer.
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import pandas as pd
import json

from config import DB_PATH


class DatabaseManager:
    """
    Håndterer alle database operationer for trading systemet.

    Tabeller:
    - ohlcv_data: Pris og volumen data
    - technical_indicators: Beregnede indikatorer
    - correlations: Korrelationsdata mellem markeder
    - metadata: System metadata og logs
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Opretter database forbindelse med row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        """Initialiserer database med nødvendige tabeller"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # OHLCV Data tabel
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date)
            )
        """)

        # Tekniske indikatorer tabel
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS technical_indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                indicator_name TEXT NOT NULL,
                indicator_value REAL,
                parameters TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date, indicator_name)
            )
        """)

        # Korrelationer tabel
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS correlations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                base_symbol TEXT NOT NULL,
                correlated_symbol TEXT NOT NULL,
                period_start DATE NOT NULL,
                period_end DATE NOT NULL,
                correlation_value REAL,
                rolling_window INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Metadata tabel
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Indekser for hurtigere søgning
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_date ON ohlcv_data(symbol, date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_indicators_symbol_date ON technical_indicators(symbol, date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_correlations_symbols ON correlations(base_symbol, correlated_symbol)")

        conn.commit()
        conn.close()

    def save_ohlcv(self, symbol: str, df: pd.DataFrame) -> int:
        """
        Gemmer OHLCV data i databasen.

        Args:
            symbol: Ticker symbol (f.eks. "GC=F")
            df: DataFrame med OHLCV kolonner og DatetimeIndex

        Returns:
            Antal rækker indsat/opdateret
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        rows_affected = 0

        for date, row in df.iterrows():
            cursor.execute("""
                INSERT OR REPLACE INTO ohlcv_data
                (symbol, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                date.strftime('%Y-%m-%d'),
                float(row.get('Open', row.get('open', 0))),
                float(row.get('High', row.get('high', 0))),
                float(row.get('Low', row.get('low', 0))),
                float(row.get('Close', row.get('close', 0))),
                int(row.get('Volume', row.get('volume', 0)) or 0)
            ))
            rows_affected += 1

        conn.commit()
        conn.close()
        return rows_affected

    def get_ohlcv(self, symbol: str, start_date: Optional[str] = None,
                  end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Henter OHLCV data fra databasen.

        Args:
            symbol: Ticker symbol
            start_date: Start dato (YYYY-MM-DD)
            end_date: Slut dato (YYYY-MM-DD)

        Returns:
            DataFrame med OHLCV data
        """
        conn = self._get_connection()

        query = "SELECT date, open, high, low, close, volume FROM ohlcv_data WHERE symbol = ?"
        params = [symbol]

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date"

        df = pd.read_sql_query(query, conn, params=params, parse_dates=['date'])
        conn.close()

        if not df.empty:
            df.set_index('date', inplace=True)
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

        return df

    def save_indicators(self, symbol: str, date: str,
                        indicators: Dict[str, float]) -> None:
        """
        Gemmer tekniske indikatorer for en given dato.

        Args:
            symbol: Ticker symbol
            date: Dato (YYYY-MM-DD)
            indicators: Dict med indikator navn -> værdi
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        for name, value in indicators.items():
            if value is not None and not pd.isna(value):
                cursor.execute("""
                    INSERT OR REPLACE INTO technical_indicators
                    (symbol, date, indicator_name, indicator_value)
                    VALUES (?, ?, ?, ?)
                """, (symbol, date, name, float(value)))

        conn.commit()
        conn.close()

    def save_indicators_bulk(self, symbol: str, df: pd.DataFrame) -> int:
        """
        Gemmer alle indikatorer fra en DataFrame.

        Args:
            symbol: Ticker symbol
            df: DataFrame med indikatorer (kolonner) og DatetimeIndex

        Returns:
            Antal rækker indsat
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        rows_affected = 0

        # Ekskluder OHLCV kolonner
        ohlcv_cols = {'Open', 'High', 'Low', 'Close', 'Volume', 'open', 'high', 'low', 'close', 'volume'}
        indicator_cols = [col for col in df.columns if col not in ohlcv_cols]

        for date, row in df.iterrows():
            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
            for col in indicator_cols:
                value = row[col]
                if value is not None and not pd.isna(value):
                    cursor.execute("""
                        INSERT OR REPLACE INTO technical_indicators
                        (symbol, date, indicator_name, indicator_value)
                        VALUES (?, ?, ?, ?)
                    """, (symbol, date_str, col, float(value)))
                    rows_affected += 1

        conn.commit()
        conn.close()
        return rows_affected

    def get_indicators(self, symbol: str, indicator_names: Optional[List[str]] = None,
                       start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Henter tekniske indikatorer fra databasen.

        Args:
            symbol: Ticker symbol
            indicator_names: Liste af indikator navne (None = alle)
            start_date: Start dato
            end_date: Slut dato

        Returns:
            DataFrame med indikatorer som kolonner
        """
        conn = self._get_connection()

        query = """
            SELECT date, indicator_name, indicator_value
            FROM technical_indicators
            WHERE symbol = ?
        """
        params = [symbol]

        if indicator_names:
            placeholders = ','.join('?' * len(indicator_names))
            query += f" AND indicator_name IN ({placeholders})"
            params.extend(indicator_names)
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date"

        df = pd.read_sql_query(query, conn, params=params, parse_dates=['date'])
        conn.close()

        if df.empty:
            return pd.DataFrame()

        # Pivot til bredt format
        df_pivot = df.pivot(index='date', columns='indicator_name', values='indicator_value')
        return df_pivot

    def save_correlation(self, base_symbol: str, correlated_symbol: str,
                         period_start: str, period_end: str,
                         correlation_value: float, rolling_window: int = 30) -> None:
        """Gemmer korrelationsdata"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO correlations
            (base_symbol, correlated_symbol, period_start, period_end, correlation_value, rolling_window)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (base_symbol, correlated_symbol, period_start, period_end, correlation_value, rolling_window))

        conn.commit()
        conn.close()

    def get_correlations(self, base_symbol: str) -> pd.DataFrame:
        """Henter alle korrelationer for et symbol"""
        conn = self._get_connection()
        df = pd.read_sql_query("""
            SELECT * FROM correlations
            WHERE base_symbol = ?
            ORDER BY period_end DESC
        """, conn, params=[base_symbol])
        conn.close()
        return df

    def set_metadata(self, key: str, value: Any) -> None:
        """Gemmer metadata"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO metadata (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, json.dumps(value), datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def get_metadata(self, key: str) -> Any:
        """Henter metadata"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM metadata WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return json.loads(row['value']) if row else None

    def get_stats(self) -> Dict[str, int]:
        """Returnerer database statistik"""
        conn = self._get_connection()
        cursor = conn.cursor()

        stats = {}
        for table in ['ohlcv_data', 'technical_indicators', 'correlations']:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            stats[table] = cursor.fetchone()['count']

        # Unikke symboler
        cursor.execute("SELECT COUNT(DISTINCT symbol) as count FROM ohlcv_data")
        stats['unique_symbols'] = cursor.fetchone()['count']

        conn.close()
        return stats
