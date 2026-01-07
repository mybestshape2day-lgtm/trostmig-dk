"""
Pattern Miner - Discovers profitable patterns in historical data

This module scans trading history to find:
1. Indicator combinations that precede profitable moves
2. Regime-specific patterns that work best
3. Session-based patterns (Asia, London, NY)
4. Time-of-day patterns
5. Multi-timeframe confirmations
"""

import json
import sqlite3
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import os


@dataclass
class DiscoveredPattern:
    """A pattern discovered by the miner"""
    pattern_id: str
    name: str
    description: str
    conditions: Dict
    direction: str  # LONG or SHORT
    win_rate: float
    profit_factor: float
    sample_size: int
    avg_profit: float
    max_drawdown: float
    best_regime: str
    best_session: str
    confidence: float  # 0-100
    discovered_at: str
    
    def to_rule(self) -> Dict:
        """Convert pattern to a trading rule format"""
        return {
            "id": self.pattern_id,
            "name": self.name,
            "conditions": self.conditions,
            "direction": self.direction,
            "weight": int(self.confidence / 10),  # 0-10 weight
            "regime_filter": self.best_regime if self.best_regime != "ALL" else None,
            "session_filter": self.best_session if self.best_session != "ALL" else None,
            "metadata": {
                "win_rate": self.win_rate,
                "profit_factor": self.profit_factor,
                "sample_size": self.sample_size,
                "discovered_at": self.discovered_at
            }
        }


class PatternMiner:
    """
    Mines historical data for profitable trading patterns.
    
    The miner looks for:
    - Indicator thresholds that precede profitable moves
    - Combinations of indicators that work together
    - Regime-specific patterns
    - Session-based patterns
    """
    
    def __init__(self, db_path: str = "data/trading_history.db"):
        self.db_path = db_path
        self.discovered_patterns: List[DiscoveredPattern] = []
        self.min_sample_size = 30  # Minimum trades to validate pattern
        self.min_win_rate = 55.0   # Minimum win rate to consider
        self.min_profit_factor = 1.3  # Minimum profit factor
        
        # Pattern search space
        self.indicator_thresholds = {
            "rsi": [20, 25, 30, 35, 40, 60, 65, 70, 75, 80],
            "stoch_k": [15, 20, 25, 30, 70, 75, 80, 85],
            "adx": [15, 20, 25, 30, 35, 40],
            "atr_percentile": [20, 30, 40, 60, 70, 80],
        }
        
        self.regimes = ["STRONG_UPTREND", "WEAK_UPTREND", "RANGING", 
                       "WEAK_DOWNTREND", "STRONG_DOWNTREND", "ALL"]
        self.sessions = ["asia", "london", "newyork", "overlap", "ALL"]
    
    def load_historical_data(self) -> List[Dict]:
        """Load historical trading data from database"""
        data = []

        # First try to load from auto_signals.db (Auto-Logger data)
        auto_db_path = "data/auto_signals.db"
        if os.path.exists(auto_db_path):
            try:
                conn = sqlite3.connect(auto_db_path)
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT timestamp, entry_price, rsi, stoch, stoch, 25, atr,
                           regime, session, direction, status, pnl
                    FROM signals
                    WHERE status IN ('WIN', 'LOSS')
                    ORDER BY timestamp
                """)

                rows = cursor.fetchall()
                conn.close()

                for row in rows:
                    data.append({
                        "timestamp": row[0],
                        "price": row[1],
                        "rsi": row[2],
                        "stoch_k": row[3],
                        "stoch_d": row[4],
                        "adx": row[5],
                        "atr": row[6],
                        "regime": row[7],
                        "session": row[8],
                        "direction": row[9],
                        "outcome": row[10],
                        "pnl": row[11]
                    })

                print(f"Loaded {len(data)} signals from Auto-Logger")
            except Exception as e:
                print(f"Could not load from auto_signals.db: {e}")

        # Also try the main trading_history.db
        if os.path.exists(self.db_path):
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT timestamp, price, rsi, stoch_k, stoch_d, adx, atr,
                           regime, session, signal_direction, outcome, pnl
                    FROM trading_signals
                    WHERE outcome IS NOT NULL
                    ORDER BY timestamp
                """)

                rows = cursor.fetchall()
                conn.close()

                for row in rows:
                    data.append({
                        "timestamp": row[0],
                        "price": row[1],
                        "rsi": row[2],
                        "stoch_k": row[3],
                        "stoch_d": row[4],
                        "adx": row[5],
                        "atr": row[6],
                        "regime": row[7],
                        "session": row[8],
                        "direction": row[9],
                        "outcome": row[10],
                        "pnl": row[11]
                    })

                print(f"Loaded additional {len(rows)} signals from trading_history.db")
            except Exception as e:
                print(f"Could not load from trading_history.db: {e}")

        # If no real data, generate synthetic for testing
        if not data:
            print("No real data found - generating synthetic data for testing")
            return self._generate_synthetic_data()

        return data
    
    def _generate_synthetic_data(self, n_samples: int = 1000) -> List[Dict]:
        """Generate synthetic trading data for pattern discovery"""
        np.random.seed(42)
        data = []
        
        base_time = datetime.now() - timedelta(days=100)
        price = 2650.0
        
        for i in range(n_samples):
            # Simulate market conditions
            rsi = np.random.normal(50, 15)
            rsi = max(10, min(90, rsi))
            
            stoch_k = np.random.normal(50, 20)
            stoch_k = max(5, min(95, stoch_k))
            
            adx = np.random.normal(25, 10)
            adx = max(10, min(60, adx))
            
            atr = np.random.normal(15, 5)
            atr = max(5, min(40, atr))
            
            # Determine regime based on indicators
            if rsi > 60 and adx > 25:
                regime = "STRONG_UPTREND"
            elif rsi > 50:
                regime = "WEAK_UPTREND"
            elif rsi < 40 and adx > 25:
                regime = "STRONG_DOWNTREND"
            elif rsi < 50:
                regime = "WEAK_DOWNTREND"
            else:
                regime = "RANGING"
            
            # Session
            hour = (i * 4) % 24
            if 0 <= hour < 8:
                session = "asia"
            elif 8 <= hour < 14:
                session = "london"
            elif 14 <= hour < 21:
                session = "newyork"
            else:
                session = "overlap"
            
            # Simulate trading outcome with realistic patterns
            # These are the "hidden" patterns we want the miner to discover
            
            # Pattern 1: Oversold stoch in uptrend = good long
            if stoch_k < 25 and regime in ["STRONG_UPTREND", "WEAK_UPTREND"]:
                win_prob = 0.70
                direction = "LONG"
            # Pattern 2: Overbought stoch in downtrend = good short
            elif stoch_k > 75 and regime in ["STRONG_DOWNTREND", "WEAK_DOWNTREND"]:
                win_prob = 0.68
                direction = "SHORT"
            # Pattern 3: High ADX breakout
            elif adx > 35 and abs(rsi - 50) > 15:
                win_prob = 0.65
                direction = "LONG" if rsi > 50 else "SHORT"
            # Pattern 4: London session momentum
            elif session == "london" and adx > 25:
                win_prob = 0.62
                direction = "LONG" if rsi > 50 else "SHORT"
            # Pattern 5: RSI extremes
            elif rsi < 25:
                win_prob = 0.60
                direction = "LONG"
            elif rsi > 75:
                win_prob = 0.58
                direction = "SHORT"
            else:
                win_prob = 0.48
                direction = "LONG" if np.random.random() > 0.5 else "SHORT"
            
            # Determine outcome
            is_win = np.random.random() < win_prob
            pnl = np.random.uniform(3, 8) if is_win else -np.random.uniform(2, 5)
            
            # Update price
            price += np.random.normal(0, 2)
            
            data.append({
                "timestamp": (base_time + timedelta(hours=i*4)).isoformat(),
                "price": round(price, 2),
                "rsi": round(rsi, 1),
                "stoch_k": round(stoch_k, 1),
                "stoch_d": round(stoch_k + np.random.normal(0, 3), 1),
                "adx": round(adx, 1),
                "atr": round(atr, 2),
                "regime": regime,
                "session": session,
                "direction": direction,
                "outcome": "WIN" if is_win else "LOSS",
                "pnl": round(pnl, 2)
            })
        
        return data
    
    def mine_single_indicator_patterns(self, data: List[Dict]) -> List[DiscoveredPattern]:
        """Find patterns based on single indicator thresholds"""
        patterns = []
        
        for indicator, thresholds in self.indicator_thresholds.items():
            for threshold in thresholds:
                for direction in ["LONG", "SHORT"]:
                    for comparison in ["<", ">"]:
                        # Filter data matching this condition
                        if comparison == "<":
                            filtered = [d for d in data 
                                       if d.get(indicator, 50) < threshold 
                                       and d["direction"] == direction]
                        else:
                            filtered = [d for d in data 
                                       if d.get(indicator, 50) > threshold 
                                       and d["direction"] == direction]
                        
                        if len(filtered) < self.min_sample_size:
                            continue
                        
                        # Calculate statistics
                        wins = [d for d in filtered if d["outcome"] == "WIN"]
                        losses = [d for d in filtered if d["outcome"] == "LOSS"]
                        
                        win_rate = len(wins) / len(filtered) * 100
                        
                        if win_rate < self.min_win_rate:
                            continue
                        
                        total_profit = sum(d["pnl"] for d in wins)
                        total_loss = abs(sum(d["pnl"] for d in losses)) or 0.01
                        profit_factor = total_profit / total_loss
                        
                        if profit_factor < self.min_profit_factor:
                            continue
                        
                        avg_profit = sum(d["pnl"] for d in filtered) / len(filtered)
                        
                        # Find best regime and session
                        regime_stats = defaultdict(list)
                        session_stats = defaultdict(list)
                        
                        for d in filtered:
                            regime_stats[d["regime"]].append(d["outcome"] == "WIN")
                            session_stats[d["session"]].append(d["outcome"] == "WIN")
                        
                        best_regime = max(regime_stats.keys(), 
                                         key=lambda r: np.mean(regime_stats[r]) if regime_stats[r] else 0,
                                         default="ALL")
                        best_session = max(session_stats.keys(),
                                          key=lambda s: np.mean(session_stats[s]) if session_stats[s] else 0,
                                          default="ALL")
                        
                        # Calculate confidence
                        confidence = min(100, (
                            (win_rate - 50) * 2 +
                            (profit_factor - 1) * 20 +
                            min(len(filtered) / 10, 30)
                        ))
                        
                        pattern = DiscoveredPattern(
                            pattern_id=f"P_{indicator}_{comparison}_{threshold}_{direction}",
                            name=f"{indicator.upper()} {comparison} {threshold} -> {direction}",
                            description=f"When {indicator} is {comparison} {threshold}, go {direction}",
                            conditions={
                                indicator: {"operator": comparison, "value": threshold}
                            },
                            direction=direction,
                            win_rate=round(win_rate, 2),
                            profit_factor=round(profit_factor, 2),
                            sample_size=len(filtered),
                            avg_profit=round(avg_profit, 2),
                            max_drawdown=round(min(d["pnl"] for d in filtered), 2),
                            best_regime=best_regime,
                            best_session=best_session,
                            confidence=round(confidence, 1),
                            discovered_at=datetime.now().isoformat()
                        )
                        
                        patterns.append(pattern)
        
        return patterns
    
    def mine_combo_patterns(self, data: List[Dict]) -> List[DiscoveredPattern]:
        """Find patterns based on indicator combinations"""
        patterns = []
        
        # Define combo searches
        combos = [
            # Oversold stoch + uptrend RSI
            {
                "name": "Oversold Stoch + Bullish RSI",
                "conditions": [
                    ("stoch_k", "<", 25),
                    ("rsi", ">", 45)
                ],
                "direction": "LONG"
            },
            # Overbought stoch + downtrend RSI
            {
                "name": "Overbought Stoch + Bearish RSI",
                "conditions": [
                    ("stoch_k", ">", 75),
                    ("rsi", "<", 55)
                ],
                "direction": "SHORT"
            },
            # High ADX + RSI momentum
            {
                "name": "Strong Trend + RSI Momentum Long",
                "conditions": [
                    ("adx", ">", 30),
                    ("rsi", ">", 55)
                ],
                "direction": "LONG"
            },
            {
                "name": "Strong Trend + RSI Momentum Short",
                "conditions": [
                    ("adx", ">", 30),
                    ("rsi", "<", 45)
                ],
                "direction": "SHORT"
            },
            # Extreme oversold
            {
                "name": "Extreme Oversold",
                "conditions": [
                    ("stoch_k", "<", 20),
                    ("rsi", "<", 30)
                ],
                "direction": "LONG"
            },
            # Extreme overbought
            {
                "name": "Extreme Overbought",
                "conditions": [
                    ("stoch_k", ">", 80),
                    ("rsi", ">", 70)
                ],
                "direction": "SHORT"
            }
        ]
        
        for combo in combos:
            # Filter data
            filtered = data.copy()
            
            for indicator, operator, value in combo["conditions"]:
                if operator == "<":
                    filtered = [d for d in filtered if d.get(indicator, 50) < value]
                else:
                    filtered = [d for d in filtered if d.get(indicator, 50) > value]
            
            # Only keep matching direction
            filtered = [d for d in filtered if d["direction"] == combo["direction"]]
            
            if len(filtered) < self.min_sample_size:
                continue
            
            # Calculate statistics
            wins = [d for d in filtered if d["outcome"] == "WIN"]
            losses = [d for d in filtered if d["outcome"] == "LOSS"]
            
            win_rate = len(wins) / len(filtered) * 100
            
            if win_rate < self.min_win_rate:
                continue
            
            total_profit = sum(d["pnl"] for d in wins)
            total_loss = abs(sum(d["pnl"] for d in losses)) or 0.01
            profit_factor = total_profit / total_loss
            
            if profit_factor < self.min_profit_factor:
                continue
            
            avg_profit = sum(d["pnl"] for d in filtered) / len(filtered)
            
            # Find best regime
            regime_stats = defaultdict(list)
            for d in filtered:
                regime_stats[d["regime"]].append(d["outcome"] == "WIN")
            
            best_regime = max(regime_stats.keys(),
                             key=lambda r: np.mean(regime_stats[r]) if regime_stats[r] else 0,
                             default="ALL")
            
            # Find best session
            session_stats = defaultdict(list)
            for d in filtered:
                session_stats[d["session"]].append(d["outcome"] == "WIN")
            
            best_session = max(session_stats.keys(),
                              key=lambda s: np.mean(session_stats[s]) if session_stats[s] else 0,
                              default="ALL")
            
            confidence = min(100, (
                (win_rate - 50) * 2 +
                (profit_factor - 1) * 20 +
                min(len(filtered) / 10, 30) +
                10  # Bonus for combo patterns
            ))
            
            conditions_dict = {}
            for indicator, operator, value in combo["conditions"]:
                conditions_dict[indicator] = {"operator": operator, "value": value}
            
            pattern = DiscoveredPattern(
                pattern_id=f"COMBO_{combo['name'].replace(' ', '_')}_{combo['direction']}",
                name=combo["name"],
                description=f"Combo pattern: {combo['name']} -> {combo['direction']}",
                conditions=conditions_dict,
                direction=combo["direction"],
                win_rate=round(win_rate, 2),
                profit_factor=round(profit_factor, 2),
                sample_size=len(filtered),
                avg_profit=round(avg_profit, 2),
                max_drawdown=round(min(d["pnl"] for d in filtered), 2),
                best_regime=best_regime,
                best_session=best_session,
                confidence=round(confidence, 1),
                discovered_at=datetime.now().isoformat()
            )
            
            patterns.append(pattern)
        
        return patterns
    
    def mine_regime_patterns(self, data: List[Dict]) -> List[DiscoveredPattern]:
        """Find regime-specific patterns"""
        patterns = []
        
        for regime in self.regimes:
            if regime == "ALL":
                continue
            
            regime_data = [d for d in data if d["regime"] == regime]
            
            if len(regime_data) < self.min_sample_size:
                continue
            
            # Analyze what works in this regime
            for direction in ["LONG", "SHORT"]:
                dir_data = [d for d in regime_data if d["direction"] == direction]
                
                if len(dir_data) < self.min_sample_size // 2:
                    continue
                
                wins = [d for d in dir_data if d["outcome"] == "WIN"]
                losses = [d for d in dir_data if d["outcome"] == "LOSS"]
                
                win_rate = len(wins) / len(dir_data) * 100
                
                if win_rate < self.min_win_rate:
                    continue
                
                total_profit = sum(d["pnl"] for d in wins)
                total_loss = abs(sum(d["pnl"] for d in losses)) or 0.01
                profit_factor = total_profit / total_loss
                
                if profit_factor < self.min_profit_factor:
                    continue
                
                # Find optimal indicator ranges for this regime
                avg_rsi = np.mean([d["rsi"] for d in wins])
                avg_stoch = np.mean([d["stoch_k"] for d in wins])
                avg_adx = np.mean([d["adx"] for d in wins])
                
                avg_profit = sum(d["pnl"] for d in dir_data) / len(dir_data)
                
                confidence = min(100, (
                    (win_rate - 50) * 2 +
                    (profit_factor - 1) * 20 +
                    min(len(dir_data) / 10, 30)
                ))
                
                pattern = DiscoveredPattern(
                    pattern_id=f"REGIME_{regime}_{direction}",
                    name=f"{regime} -> {direction}",
                    description=f"In {regime} regime, {direction} trades perform well",
                    conditions={
                        "regime": {"operator": "==", "value": regime},
                        "rsi_optimal": round(avg_rsi, 1),
                        "stoch_optimal": round(avg_stoch, 1),
                        "adx_optimal": round(avg_adx, 1)
                    },
                    direction=direction,
                    win_rate=round(win_rate, 2),
                    profit_factor=round(profit_factor, 2),
                    sample_size=len(dir_data),
                    avg_profit=round(avg_profit, 2),
                    max_drawdown=round(min(d["pnl"] for d in dir_data), 2),
                    best_regime=regime,
                    best_session="ALL",
                    confidence=round(confidence, 1),
                    discovered_at=datetime.now().isoformat()
                )
                
                patterns.append(pattern)
        
        return patterns
    
    def mine_session_patterns(self, data: List[Dict]) -> List[DiscoveredPattern]:
        """Find session-specific patterns"""
        patterns = []
        
        for session in self.sessions:
            if session == "ALL":
                continue
            
            session_data = [d for d in data if d["session"] == session]
            
            if len(session_data) < self.min_sample_size:
                continue
            
            for direction in ["LONG", "SHORT"]:
                dir_data = [d for d in session_data if d["direction"] == direction]
                
                if len(dir_data) < self.min_sample_size // 2:
                    continue
                
                wins = [d for d in dir_data if d["outcome"] == "WIN"]
                losses = [d for d in dir_data if d["outcome"] == "LOSS"]
                
                win_rate = len(wins) / len(dir_data) * 100
                
                if win_rate < self.min_win_rate:
                    continue
                
                total_profit = sum(d["pnl"] for d in wins)
                total_loss = abs(sum(d["pnl"] for d in losses)) or 0.01
                profit_factor = total_profit / total_loss
                
                if profit_factor < self.min_profit_factor:
                    continue
                
                avg_profit = sum(d["pnl"] for d in dir_data) / len(dir_data)
                
                # Find best conditions for this session
                avg_adx = np.mean([d["adx"] for d in wins])
                
                confidence = min(100, (
                    (win_rate - 50) * 2 +
                    (profit_factor - 1) * 20 +
                    min(len(dir_data) / 10, 30)
                ))
                
                pattern = DiscoveredPattern(
                    pattern_id=f"SESSION_{session}_{direction}",
                    name=f"{session.upper()} Session -> {direction}",
                    description=f"During {session} session, {direction} trades with ADX > {avg_adx:.0f}",
                    conditions={
                        "session": {"operator": "==", "value": session},
                        "adx_min": round(avg_adx - 5, 0)
                    },
                    direction=direction,
                    win_rate=round(win_rate, 2),
                    profit_factor=round(profit_factor, 2),
                    sample_size=len(dir_data),
                    avg_profit=round(avg_profit, 2),
                    max_drawdown=round(min(d["pnl"] for d in dir_data), 2),
                    best_regime="ALL",
                    best_session=session,
                    confidence=round(confidence, 1),
                    discovered_at=datetime.now().isoformat()
                )
                
                patterns.append(pattern)
        
        return patterns
    
    def mine_all_patterns(self) -> List[DiscoveredPattern]:
        """Run full pattern mining"""
        print("Loading historical data...")
        data = self.load_historical_data()
        print(f"Loaded {len(data)} data points")
        
        print("\nMining single indicator patterns...")
        single_patterns = self.mine_single_indicator_patterns(data)
        print(f"Found {len(single_patterns)} single indicator patterns")
        
        print("\nMining combo patterns...")
        combo_patterns = self.mine_combo_patterns(data)
        print(f"Found {len(combo_patterns)} combo patterns")
        
        print("\nMining regime patterns...")
        regime_patterns = self.mine_regime_patterns(data)
        print(f"Found {len(regime_patterns)} regime patterns")
        
        print("\nMining session patterns...")
        session_patterns = self.mine_session_patterns(data)
        print(f"Found {len(session_patterns)} session patterns")
        
        # Combine and sort by confidence
        all_patterns = single_patterns + combo_patterns + regime_patterns + session_patterns
        all_patterns.sort(key=lambda p: p.confidence, reverse=True)
        
        self.discovered_patterns = all_patterns
        
        print(f"\n{'='*50}")
        print(f"TOTAL PATTERNS DISCOVERED: {len(all_patterns)}")
        print(f"{'='*50}")
        
        return all_patterns
    
    def get_top_patterns(self, n: int = 10) -> List[DiscoveredPattern]:
        """Get top N patterns by confidence"""
        if not self.discovered_patterns:
            self.mine_all_patterns()
        
        return self.discovered_patterns[:n]
    
    def export_patterns(self, filepath: str = "data/discovered_patterns.json"):
        """Export discovered patterns to JSON"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        patterns_dict = [asdict(p) for p in self.discovered_patterns]
        
        with open(filepath, 'w') as f:
            json.dump(patterns_dict, f, indent=2)
        
        print(f"Exported {len(patterns_dict)} patterns to {filepath}")
        return filepath
    
    def export_as_rules(self, filepath: str = "data/discovered_rules.json") -> str:
        """Export patterns as trading rules"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        rules = [p.to_rule() for p in self.discovered_patterns]
        
        with open(filepath, 'w') as f:
            json.dump(rules, f, indent=2)
        
        print(f"Exported {len(rules)} rules to {filepath}")
        return filepath


if __name__ == "__main__":
    miner = PatternMiner()
    patterns = miner.mine_all_patterns()
    
    print("\n" + "="*60)
    print("TOP 10 DISCOVERED PATTERNS")
    print("="*60)
    
    for i, p in enumerate(patterns[:10], 1):
        print(f"\n{i}. {p.name}")
        print(f"   Direction: {p.direction}")
        print(f"   Win Rate: {p.win_rate}%")
        print(f"   Profit Factor: {p.profit_factor}")
        print(f"   Sample Size: {p.sample_size}")
        print(f"   Confidence: {p.confidence}")
        print(f"   Best Regime: {p.best_regime}")
        print(f"   Best Session: {p.best_session}")
    
    # Export
    miner.export_patterns()
    miner.export_as_rules()
