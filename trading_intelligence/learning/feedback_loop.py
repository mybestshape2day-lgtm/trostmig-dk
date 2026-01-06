"""
Feedback Loop - Connects signals to outcomes for continuous learning

This module:
1. Tracks all generated signals
2. Monitors trade outcomes
3. Updates performance metrics
4. Feeds data back to Pattern Miner and Rule Evolution
5. Triggers re-optimization when performance degrades
"""

import json
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import numpy as np


@dataclass
class Signal:
    """A trading signal"""
    signal_id: str
    timestamp: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    score: float
    regime: str
    session: str
    indicators: Dict
    rules_triggered: List[str]
    
    # Outcome (filled later)
    exit_price: Optional[float] = None
    exit_time: Optional[str] = None
    outcome: Optional[str] = None  # WIN, LOSS, BREAKEVEN
    pnl: Optional[float] = None
    hold_time: Optional[float] = None  # in minutes


@dataclass 
class PerformanceMetrics:
    """Performance metrics for a period"""
    period: str
    total_signals: int
    wins: int
    losses: int
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    avg_hold_time: float
    best_regime: str
    best_session: str
    worst_regime: str
    worst_session: str


class FeedbackLoop:
    """
    Manages the feedback loop between signals and outcomes.
    
    The loop:
    1. Log signal -> 2. Monitor outcome -> 3. Update metrics ->
    4. Analyze performance -> 5. Trigger re-optimization -> 
    6. Update rules -> Back to 1
    """
    
    def __init__(self, db_path: str = "data/feedback.db"):
        self.db_path = db_path
        self.signals: List[Signal] = []
        self.metrics_history: List[PerformanceMetrics] = []
        
        # Performance thresholds for triggering re-optimization
        self.min_win_rate = 50.0
        self.min_profit_factor = 1.2
        self.degradation_threshold = 10  # % drop triggers re-optimization
        
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database"""
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
                score REAL,
                regime TEXT,
                session TEXT,
                indicators TEXT,
                rules_triggered TEXT,
                exit_price REAL,
                exit_time TEXT,
                outcome TEXT,
                pnl REAL,
                hold_time REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                period TEXT,
                total_signals INTEGER,
                wins INTEGER,
                losses INTEGER,
                win_rate REAL,
                profit_factor REAL,
                avg_win REAL,
                avg_loss REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimization_triggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                reason TEXT,
                metrics TEXT,
                action_taken TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def log_signal(self, signal: Signal) -> str:
        """Log a new signal"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO signals 
            (signal_id, timestamp, direction, entry_price, stop_loss, take_profit,
             score, regime, session, indicators, rules_triggered)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal.signal_id,
            signal.timestamp,
            signal.direction,
            signal.entry_price,
            signal.stop_loss,
            signal.take_profit,
            signal.score,
            signal.regime,
            signal.session,
            json.dumps(signal.indicators),
            json.dumps(signal.rules_triggered)
        ))
        
        conn.commit()
        conn.close()
        
        self.signals.append(signal)
        print(f"Logged signal: {signal.signal_id} - {signal.direction} @ {signal.entry_price}")
        
        return signal.signal_id
    
    def update_outcome(self, signal_id: str, exit_price: float, 
                      outcome: str, exit_time: str = None) -> bool:
        """Update signal with outcome"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get original signal
        cursor.execute("SELECT * FROM signals WHERE signal_id = ?", (signal_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return False
        
        entry_price = row[3]
        direction = row[2]
        timestamp = row[1]
        
        # Calculate PnL
        if direction == "LONG":
            pnl = exit_price - entry_price
        else:
            pnl = entry_price - exit_price
        
        # Calculate hold time
        exit_time = exit_time or datetime.now().isoformat()
        try:
            entry_dt = datetime.fromisoformat(timestamp)
            exit_dt = datetime.fromisoformat(exit_time)
            hold_time = (exit_dt - entry_dt).total_seconds() / 60
        except:
            hold_time = 0
        
        cursor.execute("""
            UPDATE signals 
            SET exit_price = ?, exit_time = ?, outcome = ?, pnl = ?, hold_time = ?
            WHERE signal_id = ?
        """, (exit_price, exit_time, outcome, pnl, hold_time, signal_id))
        
        conn.commit()
        conn.close()
        
        print(f"Updated outcome: {signal_id} - {outcome} (PnL: {pnl:.2f})")
        
        # Check if we need to trigger re-optimization
        self._check_performance()
        
        return True
    
    def get_signals(self, days: int = 30, with_outcome: bool = True) -> List[Signal]:
        """Get recent signals"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        if with_outcome:
            cursor.execute("""
                SELECT * FROM signals 
                WHERE timestamp > ? AND outcome IS NOT NULL
                ORDER BY timestamp DESC
            """, (cutoff,))
        else:
            cursor.execute("""
                SELECT * FROM signals 
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            """, (cutoff,))
        
        rows = cursor.fetchall()
        conn.close()
        
        signals = []
        for row in rows:
            signals.append(Signal(
                signal_id=row[0],
                timestamp=row[1],
                direction=row[2],
                entry_price=row[3],
                stop_loss=row[4],
                take_profit=row[5],
                score=row[6],
                regime=row[7],
                session=row[8],
                indicators=json.loads(row[9]) if row[9] else {},
                rules_triggered=json.loads(row[10]) if row[10] else [],
                exit_price=row[11],
                exit_time=row[12],
                outcome=row[13],
                pnl=row[14],
                hold_time=row[15]
            ))
        
        return signals
    
    def calculate_metrics(self, days: int = 30) -> PerformanceMetrics:
        """Calculate performance metrics for a period"""
        signals = self.get_signals(days=days, with_outcome=True)
        
        if not signals:
            return None
        
        wins = [s for s in signals if s.outcome == "WIN"]
        losses = [s for s in signals if s.outcome == "LOSS"]
        
        total = len(signals)
        n_wins = len(wins)
        n_losses = len(losses)
        
        win_rate = n_wins / total * 100 if total > 0 else 0
        
        total_profit = sum(s.pnl for s in wins) if wins else 0
        total_loss = abs(sum(s.pnl for s in losses)) if losses else 0.01
        profit_factor = total_profit / total_loss
        
        avg_win = np.mean([s.pnl for s in wins]) if wins else 0
        avg_loss = abs(np.mean([s.pnl for s in losses])) if losses else 0
        
        largest_win = max([s.pnl for s in wins]) if wins else 0
        largest_loss = abs(min([s.pnl for s in losses])) if losses else 0
        
        avg_hold = np.mean([s.hold_time for s in signals if s.hold_time]) if signals else 0
        
        # Find best/worst regime and session
        regime_stats = defaultdict(lambda: {"wins": 0, "total": 0})
        session_stats = defaultdict(lambda: {"wins": 0, "total": 0})
        
        for s in signals:
            regime_stats[s.regime]["total"] += 1
            session_stats[s.session]["total"] += 1
            if s.outcome == "WIN":
                regime_stats[s.regime]["wins"] += 1
                session_stats[s.session]["wins"] += 1
        
        def calc_wr(stats):
            return {k: v["wins"]/v["total"]*100 if v["total"] > 0 else 0 
                   for k, v in stats.items()}
        
        regime_wr = calc_wr(regime_stats)
        session_wr = calc_wr(session_stats)
        
        best_regime = max(regime_wr, key=regime_wr.get) if regime_wr else "N/A"
        worst_regime = min(regime_wr, key=regime_wr.get) if regime_wr else "N/A"
        best_session = max(session_wr, key=session_wr.get) if session_wr else "N/A"
        worst_session = min(session_wr, key=session_wr.get) if session_wr else "N/A"
        
        metrics = PerformanceMetrics(
            period=f"Last {days} days",
            total_signals=total,
            wins=n_wins,
            losses=n_losses,
            win_rate=round(win_rate, 2),
            profit_factor=round(profit_factor, 2),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            largest_win=round(largest_win, 2),
            largest_loss=round(largest_loss, 2),
            avg_hold_time=round(avg_hold, 1),
            best_regime=best_regime,
            best_session=best_session,
            worst_regime=worst_regime,
            worst_session=worst_session
        )
        
        self.metrics_history.append(metrics)
        self._save_metrics(metrics)
        
        return metrics
    
    def _save_metrics(self, metrics: PerformanceMetrics):
        """Save metrics to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO metrics 
            (timestamp, period, total_signals, wins, losses, win_rate, profit_factor, avg_win, avg_loss)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            metrics.period,
            metrics.total_signals,
            metrics.wins,
            metrics.losses,
            metrics.win_rate,
            metrics.profit_factor,
            metrics.avg_win,
            metrics.avg_loss
        ))
        
        conn.commit()
        conn.close()
    
    def _check_performance(self) -> bool:
        """Check if performance has degraded and trigger re-optimization"""
        # Get recent vs historical metrics
        recent = self.calculate_metrics(days=7)
        historical = self.calculate_metrics(days=30)
        
        if not recent or not historical:
            return False
        
        triggers = []
        
        # Check win rate degradation
        if recent.win_rate < historical.win_rate - self.degradation_threshold:
            triggers.append(f"Win rate dropped: {historical.win_rate:.1f}% -> {recent.win_rate:.1f}%")
        
        # Check profit factor degradation
        if recent.profit_factor < self.min_profit_factor:
            triggers.append(f"Profit factor below minimum: {recent.profit_factor:.2f}")
        
        # Check win rate below minimum
        if recent.win_rate < self.min_win_rate:
            triggers.append(f"Win rate below minimum: {recent.win_rate:.1f}%")
        
        if triggers:
            self._log_optimization_trigger(triggers, recent)
            return True
        
        return False
    
    def _log_optimization_trigger(self, reasons: List[str], metrics: PerformanceMetrics):
        """Log optimization trigger"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO optimization_triggers 
            (timestamp, reason, metrics, action_taken)
            VALUES (?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            json.dumps(reasons),
            json.dumps(asdict(metrics)),
            "PENDING"
        ))
        
        conn.commit()
        conn.close()
        
        print("\n" + "!"*60)
        print("OPTIMIZATION TRIGGERED")
        print("!"*60)
        for reason in reasons:
            print(f"  - {reason}")
    
    def get_feedback_data(self) -> List[Dict]:
        """Get data formatted for pattern mining and rule evolution"""
        signals = self.get_signals(days=90, with_outcome=True)
        
        data = []
        for s in signals:
            data.append({
                "timestamp": s.timestamp,
                "price": s.entry_price,
                "rsi": s.indicators.get("rsi", 50),
                "stoch_k": s.indicators.get("stoch_k", 50),
                "stoch_d": s.indicators.get("stoch_d", 50),
                "adx": s.indicators.get("adx", 25),
                "atr": s.indicators.get("atr", 10),
                "regime": s.regime,
                "session": s.session,
                "direction": s.direction,
                "outcome": s.outcome,
                "pnl": s.pnl or 0
            })
        
        return data
    
    def get_rule_performance(self) -> Dict[str, Dict]:
        """Analyze performance of individual rules"""
        signals = self.get_signals(days=30, with_outcome=True)
        
        rule_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0})
        
        for s in signals:
            for rule in s.rules_triggered:
                rule_stats[rule]["pnl"] += s.pnl or 0
                if s.outcome == "WIN":
                    rule_stats[rule]["wins"] += 1
                else:
                    rule_stats[rule]["losses"] += 1
        
        # Calculate metrics
        for rule, stats in rule_stats.items():
            total = stats["wins"] + stats["losses"]
            stats["win_rate"] = stats["wins"] / total * 100 if total > 0 else 0
            stats["total_trades"] = total
        
        return dict(rule_stats)
    
    def print_summary(self):
        """Print performance summary"""
        metrics = self.calculate_metrics(days=30)
        
        if not metrics:
            print("No signals recorded yet")
            return
        
        print("\n" + "="*60)
        print("PERFORMANCE SUMMARY - Last 30 Days")
        print("="*60)
        print(f"Total Signals: {metrics.total_signals}")
        print(f"Wins/Losses: {metrics.wins}/{metrics.losses}")
        print(f"Win Rate: {metrics.win_rate}%")
        print(f"Profit Factor: {metrics.profit_factor}")
        print(f"Avg Win: ${metrics.avg_win}")
        print(f"Avg Loss: ${metrics.avg_loss}")
        print(f"Largest Win: ${metrics.largest_win}")
        print(f"Largest Loss: ${metrics.largest_loss}")
        print(f"Avg Hold Time: {metrics.avg_hold_time} min")
        print(f"\nBest Regime: {metrics.best_regime}")
        print(f"Worst Regime: {metrics.worst_regime}")
        print(f"Best Session: {metrics.best_session}")
        print(f"Worst Session: {metrics.worst_session}")
        
        # Rule performance
        print("\n" + "-"*60)
        print("RULE PERFORMANCE")
        print("-"*60)
        
        rule_perf = self.get_rule_performance()
        sorted_rules = sorted(rule_perf.items(), 
                            key=lambda x: x[1]["win_rate"], 
                            reverse=True)
        
        for rule, stats in sorted_rules[:10]:
            print(f"{rule}: {stats['win_rate']:.1f}% WR ({stats['total_trades']} trades)")
    
    def export_for_learning(self, filepath: str = "data/feedback_data.json") -> str:
        """Export feedback data for learning modules"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "signals": self.get_feedback_data(),
            "metrics": asdict(self.calculate_metrics(days=30)) if self.calculate_metrics(days=30) else {},
            "rule_performance": self.get_rule_performance()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Exported feedback data to {filepath}")
        return filepath


if __name__ == "__main__":
    # Test feedback loop
    loop = FeedbackLoop()
    
    # Create some test signals
    import random
    
    for i in range(20):
        signal = Signal(
            signal_id=f"TEST_{i:04d}",
            timestamp=(datetime.now() - timedelta(hours=i*4)).isoformat(),
            direction=random.choice(["LONG", "SHORT"]),
            entry_price=2650 + random.uniform(-20, 20),
            stop_loss=2645,
            take_profit=2660,
            score=random.uniform(50, 90),
            regime=random.choice(["STRONG_UPTREND", "WEAK_UPTREND", "RANGING"]),
            session=random.choice(["london", "newyork", "asia"]),
            indicators={"rsi": random.uniform(30, 70), "stoch_k": random.uniform(20, 80)},
            rules_triggered=[f"RULE_{random.randint(1,10):02d}"]
        )
        
        loop.log_signal(signal)
        
        # Update with random outcome
        exit_price = signal.entry_price + random.uniform(-5, 8)
        outcome = "WIN" if (exit_price > signal.entry_price and signal.direction == "LONG") or \
                          (exit_price < signal.entry_price and signal.direction == "SHORT") else "LOSS"
        
        loop.update_outcome(signal.signal_id, exit_price, outcome)
    
    # Print summary
    loop.print_summary()
    
    # Export
    loop.export_for_learning()
