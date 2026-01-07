"""
Auto-Logger - Automatisk Signal Logging System

Logger ALLE signals fra Firebase automatisk.
Tracker pris og bestemmer WIN/LOSS uden manuel input.

Ingen manuel logging nødvendig!
"""

import json
import sqlite3
import os
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import threading


@dataclass
class AutoSignal:
    """En automatisk logget signal"""
    signal_id: str
    timestamp: str
    direction: str  # LONG eller SHORT
    entry_price: float
    stop_loss: float
    take_profit: float
    score_long: float
    score_short: float
    regime: str
    session: str
    stoch: float
    rsi: float
    atr: float
    
    # Outcome - udfyldes automatisk
    status: str = "OPEN"  # OPEN, WIN, LOSS, EXPIRED
    exit_price: Optional[float] = None
    exit_time: Optional[str] = None
    pnl: Optional[float] = None
    max_profit: float = 0  # Højeste profit under trade
    max_loss: float = 0    # Største drawdown under trade


class AutoLogger:
    """
    Automatisk Signal Logger
    
    - Henter signals fra Firebase
    - Logger alle potentielle trades
    - Tracker pris og bestemmer WIN/LOSS automatisk
    - Fodrer data til Strategy Factory
    """
    
    def __init__(self, 
                 firebase_url: str = "https://online-shopping-a7061.firebaseio.com/gold-live.json",
                 db_path: str = "data/auto_signals.db"):
        
        self.firebase_url = firebase_url
        self.db_path = db_path
        
        # Justerbare parametre
        self.config = {
            "stop_loss_points": 4.0,      # SL i points fra entry
            "take_profit_points": 8.0,    # TP i points fra entry
            "min_score": 60,              # Minimum score for at logge signal
            "signal_expiry_minutes": 60,  # Signal udløber efter X minutter
            "check_interval_seconds": 10  # Hvor ofte tjekkes prisen
        }
        
        # State
        self.open_signals: Dict[str, AutoSignal] = {}
        self.last_signal_hash: str = ""
        self.running: bool = False
        self.stats = {
            "total_signals": 0,
            "wins": 0,
            "losses": 0,
            "expired": 0,
            "open": 0
        }
        
        self._init_database()
        self._load_open_signals()
    
    def _init_database(self):
        """Initialiser database"""
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                signal_id TEXT PRIMARY KEY,
                timestamp TEXT,
                direction TEXT,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                score_long REAL,
                score_short REAL,
                regime TEXT,
                session TEXT,
                stoch REAL,
                rsi REAL,
                atr REAL,
                status TEXT,
                exit_price REAL,
                exit_time TEXT,
                pnl REAL,
                max_profit REAL,
                max_loss REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                price REAL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _load_open_signals(self):
        """Indlæs åbne signals fra database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM signals WHERE status = 'OPEN'")
        rows = cursor.fetchall()
        
        for row in rows:
            signal = AutoSignal(
                signal_id=row[0],
                timestamp=row[1],
                direction=row[2],
                entry_price=row[3],
                stop_loss=row[4],
                take_profit=row[5],
                score_long=row[6],
                score_short=row[7],
                regime=row[8],
                session=row[9],
                stoch=row[10],
                rsi=row[11],
                atr=row[12],
                status=row[13],
                exit_price=row[14],
                exit_time=row[15],
                pnl=row[16],
                max_profit=row[17],
                max_loss=row[18]
            )
            self.open_signals[signal.signal_id] = signal
        
        conn.close()
        print(f"Loaded {len(self.open_signals)} open signals")
    
    def set_config(self, **kwargs):
        """Opdater konfiguration"""
        for key, value in kwargs.items():
            if key in self.config:
                self.config[key] = value
                print(f"Config updated: {key} = {value}")
    
    def fetch_firebase_data(self) -> Optional[Dict]:
        """Hent seneste data fra Firebase"""
        try:
            response = requests.get(self.firebase_url, timeout=10)
            data = response.json()
            
            if data:
                keys = list(data.keys())
                latest = data[keys[-1]]
                return latest
            return None
        except Exception as e:
            print(f"Firebase fetch error: {e}")
            return None
    
    def check_for_new_signal(self, data: Dict) -> Optional[AutoSignal]:
        """Tjek om der er et nyt signal"""
        if not data or not data.get("price"):
            return None
        
        # Lav en hash af signalet for at undgå dubletter
        score_long = data.get("score_long", 0)
        score_short = data.get("score_short", 0)
        price = data.get("price", 0)
        
        signal_hash = f"{price}_{score_long}_{score_short}"
        
        # Tjek om det er samme signal
        if signal_hash == self.last_signal_hash:
            return None
        
        # Tjek om score er høj nok
        max_score = max(score_long, score_short)
        if max_score < self.config["min_score"]:
            return None
        
        # Bestem retning
        if score_long > score_short and score_long >= self.config["min_score"]:
            direction = "LONG"
            stop_loss = price - self.config["stop_loss_points"]
            take_profit = price + self.config["take_profit_points"]
        elif score_short > score_long and score_short >= self.config["min_score"]:
            direction = "SHORT"
            stop_loss = price + self.config["stop_loss_points"]
            take_profit = price - self.config["take_profit_points"]
        else:
            return None
        
        # Opret signal
        signal = AutoSignal(
            signal_id=f"AUTO_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            direction=direction,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            score_long=score_long,
            score_short=score_short,
            regime=data.get("trend", "UNKNOWN"),
            session=data.get("session", "unknown"),
            stoch=data.get("stoch", 50),
            rsi=data.get("rsi", 50),
            atr=data.get("atr", 0)
        )
        
        self.last_signal_hash = signal_hash
        return signal
    
    def log_signal(self, signal: AutoSignal):
        """Gem signal i database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO signals VALUES 
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal.signal_id, signal.timestamp, signal.direction,
            signal.entry_price, signal.stop_loss, signal.take_profit,
            signal.score_long, signal.score_short, signal.regime,
            signal.session, signal.stoch, signal.rsi, signal.atr,
            signal.status, signal.exit_price, signal.exit_time,
            signal.pnl, signal.max_profit, signal.max_loss
        ))
        
        conn.commit()
        conn.close()
        
        self.open_signals[signal.signal_id] = signal
        self.stats["total_signals"] += 1
        self.stats["open"] += 1
        
        print(f"\n{'='*50}")
        print(f"📝 NY SIGNAL LOGGET")
        print(f"{'='*50}")
        print(f"ID: {signal.signal_id}")
        print(f"Retning: {signal.direction}")
        print(f"Entry: {signal.entry_price}")
        print(f"Stop Loss: {signal.stop_loss}")
        print(f"Take Profit: {signal.take_profit}")
        print(f"Score: L={signal.score_long} S={signal.score_short}")
        print(f"{'='*50}\n")
    
    def check_signal_outcome(self, signal: AutoSignal, current_price: float) -> bool:
        """
        Tjek om signal har ramt SL eller TP
        Returns True hvis signal er afsluttet
        """
        if signal.status != "OPEN":
            return True
        
        # Beregn aktuel P/L
        if signal.direction == "LONG":
            current_pnl = current_price - signal.entry_price
            # Opdater max profit/loss
            signal.max_profit = max(signal.max_profit, current_pnl)
            signal.max_loss = min(signal.max_loss, current_pnl)
            
            # Tjek TP
            if current_price >= signal.take_profit:
                signal.status = "WIN"
                signal.exit_price = current_price
                signal.pnl = current_pnl
                signal.exit_time = datetime.now().isoformat()
                self._close_signal(signal)
                return True
            
            # Tjek SL
            if current_price <= signal.stop_loss:
                signal.status = "LOSS"
                signal.exit_price = current_price
                signal.pnl = current_pnl
                signal.exit_time = datetime.now().isoformat()
                self._close_signal(signal)
                return True
        
        else:  # SHORT
            current_pnl = signal.entry_price - current_price
            signal.max_profit = max(signal.max_profit, current_pnl)
            signal.max_loss = min(signal.max_loss, current_pnl)
            
            # Tjek TP
            if current_price <= signal.take_profit:
                signal.status = "WIN"
                signal.exit_price = current_price
                signal.pnl = current_pnl
                signal.exit_time = datetime.now().isoformat()
                self._close_signal(signal)
                return True
            
            # Tjek SL
            if current_price >= signal.stop_loss:
                signal.status = "LOSS"
                signal.exit_price = current_price
                signal.pnl = current_pnl
                signal.exit_time = datetime.now().isoformat()
                self._close_signal(signal)
                return True
        
        # Tjek om signal er udløbet
        signal_time = datetime.fromisoformat(signal.timestamp)
        if datetime.now() - signal_time > timedelta(minutes=self.config["signal_expiry_minutes"]):
            signal.status = "EXPIRED"
            signal.exit_price = current_price
            signal.pnl = current_pnl
            signal.exit_time = datetime.now().isoformat()
            self._close_signal(signal)
            return True
        
        return False
    
    def _close_signal(self, signal: AutoSignal):
        """Luk signal og opdater database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE signals SET 
                status = ?, exit_price = ?, exit_time = ?, 
                pnl = ?, max_profit = ?, max_loss = ?
            WHERE signal_id = ?
        """, (
            signal.status, signal.exit_price, signal.exit_time,
            signal.pnl, signal.max_profit, signal.max_loss,
            signal.signal_id
        ))
        
        conn.commit()
        conn.close()
        
        # Opdater stats
        self.stats["open"] -= 1
        if signal.status == "WIN":
            self.stats["wins"] += 1
        elif signal.status == "LOSS":
            self.stats["losses"] += 1
        else:
            self.stats["expired"] += 1
        
        # Fjern fra open signals
        if signal.signal_id in self.open_signals:
            del self.open_signals[signal.signal_id]
        
        icon = "✅" if signal.status == "WIN" else "❌" if signal.status == "LOSS" else "⏰"
        print(f"\n{icon} SIGNAL LUKKET: {signal.signal_id}")
        print(f"   Status: {signal.status}")
        print(f"   Entry: {signal.entry_price} → Exit: {signal.exit_price}")
        print(f"   P/L: {signal.pnl:+.1f} points")
        print(f"   Max Profit: {signal.max_profit:.1f} | Max Loss: {signal.max_loss:.1f}")
    
    def run_once(self):
        """Kør én iteration af auto-logging"""
        # Hent data fra Firebase
        data = self.fetch_firebase_data()
        
        if not data:
            return
        
        current_price = data.get("price", 0)
        
        # Log pris
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO price_history (timestamp, price) VALUES (?, ?)",
                      (datetime.now().isoformat(), current_price))
        conn.commit()
        conn.close()
        
        # Tjek for nyt signal
        new_signal = self.check_for_new_signal(data)
        if new_signal:
            self.log_signal(new_signal)
        
        # Tjek alle åbne signals
        for signal_id, signal in list(self.open_signals.items()):
            self.check_signal_outcome(signal, current_price)
    
    def run_continuous(self):
        """Kør kontinuerligt"""
        print("\n" + "="*60)
        print("🤖 AUTO-LOGGER STARTET")
        print("="*60)
        print(f"Firebase: {self.firebase_url}")
        print(f"Stop Loss: {self.config['stop_loss_points']} points")
        print(f"Take Profit: {self.config['take_profit_points']} points")
        print(f"Min Score: {self.config['min_score']}")
        print(f"Check interval: {self.config['check_interval_seconds']} sekunder")
        print("="*60)
        print("Tryk Ctrl+C for at stoppe\n")
        
        self.running = True
        
        try:
            while self.running:
                self.run_once()
                
                # Vis status
                print(f"\r📊 Signals: {self.stats['total_signals']} | "
                      f"✅ Wins: {self.stats['wins']} | "
                      f"❌ Losses: {self.stats['losses']} | "
                      f"📂 Open: {self.stats['open']}", end="", flush=True)
                
                time.sleep(self.config["check_interval_seconds"])
        
        except KeyboardInterrupt:
            print("\n\nAuto-Logger stoppet")
            self.running = False
    
    def get_statistics(self) -> Dict:
        """Hent statistik"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM signals")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM signals WHERE status = 'WIN'")
        wins = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM signals WHERE status = 'LOSS'")
        losses = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(pnl) FROM signals WHERE status = 'WIN'")
        avg_win = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT AVG(pnl) FROM signals WHERE status = 'LOSS'")
        avg_loss = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(pnl) FROM signals WHERE status IN ('WIN', 'LOSS')")
        total_pnl = cursor.fetchone()[0] or 0
        
        conn.close()
        
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        profit_factor = (abs(avg_win * wins) / abs(avg_loss * losses)) if losses > 0 and avg_loss != 0 else 0
        
        return {
            "total_signals": total,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "total_pnl": round(total_pnl, 2)
        }
    
    def export_for_strategy_factory(self, filepath: str = "data/auto_logged_data.json") -> str:
        """Eksporter data til Strategy Factory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM signals 
            WHERE status IN ('WIN', 'LOSS')
            ORDER BY timestamp DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        data = []
        for row in rows:
            data.append({
                "timestamp": row[1],
                "price": row[3],
                "rsi": row[11],
                "stoch_k": row[10],
                "stoch_d": row[10],
                "adx": 25,  # Default
                "atr": row[12],
                "regime": row[8],
                "session": row[9],
                "direction": row[2],
                "outcome": row[13],
                "pnl": row[16] or 0
            })
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump({
                "exported_at": datetime.now().isoformat(),
                "statistics": self.get_statistics(),
                "signals": data
            }, f, indent=2)
        
        print(f"Exported {len(data)} signals to {filepath}")
        return filepath
    
    def print_summary(self):
        """Print summary"""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("📊 AUTO-LOGGER STATISTIK")
        print("="*60)
        print(f"Total Signals: {stats['total_signals']}")
        print(f"Wins: {stats['wins']}")
        print(f"Losses: {stats['losses']}")
        print(f"Win Rate: {stats['win_rate']}%")
        print(f"Profit Factor: {stats['profit_factor']}")
        print(f"Avg Win: {stats['avg_win']} points")
        print(f"Avg Loss: {stats['avg_loss']} points")
        print(f"Total P/L: {stats['total_pnl']} points")
        print("="*60)


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto-Logger for Trading Signals")
    parser.add_argument("--sl", type=float, default=4.0, help="Stop Loss i points (default: 4)")
    parser.add_argument("--tp", type=float, default=8.0, help="Take Profit i points (default: 8)")
    parser.add_argument("--min-score", type=int, default=60, help="Minimum score (default: 60)")
    parser.add_argument("--interval", type=int, default=10, help="Check interval i sekunder (default: 10)")
    parser.add_argument("--expiry", type=int, default=60, help="Signal expiry i minutter (default: 60)")
    parser.add_argument("--stats", action="store_true", help="Vis kun statistik")
    parser.add_argument("--export", action="store_true", help="Eksporter data til Strategy Factory")
    
    args = parser.parse_args()
    
    logger = AutoLogger()
    
    # Opdater config
    logger.set_config(
        stop_loss_points=args.sl,
        take_profit_points=args.tp,
        min_score=args.min_score,
        check_interval_seconds=args.interval,
        signal_expiry_minutes=args.expiry
    )
    
    if args.stats:
        logger.print_summary()
    elif args.export:
        logger.export_for_strategy_factory()
        logger.print_summary()
    else:
        logger.run_continuous()
