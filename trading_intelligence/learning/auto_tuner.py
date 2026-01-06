"""
Auto-Tuner - Automatically optimizes trading parameters

This module:
1. Runs parameter sweeps to find optimal values
2. Adjusts thresholds based on market conditions
3. Optimizes per-regime and per-session parameters
4. Updates Pine Script / Firebase configurations
"""

import json
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import os
from itertools import product


@dataclass
class OptimizationResult:
    """Result of parameter optimization"""
    parameter_name: str
    optimal_value: float
    improvement: float  # % improvement over baseline
    win_rate: float
    profit_factor: float
    sample_size: int
    regime: str = "ALL"
    session: str = "ALL"


@dataclass
class TuningConfig:
    """Current tuning configuration"""
    stoch_oversold: int = 20
    stoch_overbought: int = 80
    rsi_oversold: int = 30
    rsi_overbought: int = 70
    min_score_long: int = 60
    min_score_short: int = 60
    atr_stop_mult: float = 2.0
    atr_tp_mult: float = 3.0
    adx_min_trend: int = 25
    
    # Per-regime adjustments
    regime_adjustments: Dict[str, Dict] = None
    
    # Per-session adjustments
    session_adjustments: Dict[str, Dict] = None
    
    def __post_init__(self):
        if self.regime_adjustments is None:
            self.regime_adjustments = {}
        if self.session_adjustments is None:
            self.session_adjustments = {}
    
    def to_dict(self) -> Dict:
        return asdict(self)


class AutoTuner:
    """
    Automatically tunes trading parameters based on historical performance.
    
    Optimization methods:
    1. Grid search for indicator thresholds
    2. Bayesian optimization for continuous params
    3. Regime-specific tuning
    4. Session-specific tuning
    """
    
    def __init__(self):
        self.current_config = TuningConfig()
        self.optimization_history: List[Dict] = []
        self.best_configs: Dict[str, TuningConfig] = {}
        
        # Parameter search spaces
        self.param_ranges = {
            "stoch_oversold": range(10, 35, 5),
            "stoch_overbought": range(65, 95, 5),
            "rsi_oversold": range(20, 40, 5),
            "rsi_overbought": range(60, 80, 5),
            "min_score_long": range(50, 80, 5),
            "min_score_short": range(50, 80, 5),
            "atr_stop_mult": [1.5, 2.0, 2.5, 3.0],
            "atr_tp_mult": [2.0, 2.5, 3.0, 3.5, 4.0],
            "adx_min_trend": range(15, 40, 5)
        }
        
        self.regimes = ["STRONG_UPTREND", "WEAK_UPTREND", "RANGING", 
                       "WEAK_DOWNTREND", "STRONG_DOWNTREND"]
        self.sessions = ["asia", "london", "newyork", "overlap"]
    
    def evaluate_config(self, config: Dict, data: List[Dict], 
                       direction: str = None,
                       regime: str = None,
                       session: str = None) -> Dict:
        """Evaluate a configuration on historical data"""
        filtered = data.copy()
        
        # Apply filters
        if regime:
            filtered = [d for d in filtered if d.get("regime") == regime]
        if session:
            filtered = [d for d in filtered if d.get("session") == session]
        if direction:
            filtered = [d for d in filtered if d.get("direction") == direction]
        
        if len(filtered) < 20:
            return {"win_rate": 0, "profit_factor": 0, "trades": 0, "fitness": 0}
        
        # Apply config filters
        min_score = config.get("min_score_long" if direction == "LONG" else "min_score_short", 60)
        
        # Simulate with config
        wins = 0
        losses = 0
        total_profit = 0
        total_loss = 0
        
        for d in filtered:
            # Check if trade would be taken with this config
            stoch = d.get("stoch_k", 50)
            rsi = d.get("rsi", 50)
            adx = d.get("adx", 25)
            
            # Check conditions
            if direction == "LONG":
                stoch_ok = stoch < config.get("stoch_oversold", 20)
                rsi_ok = rsi < config.get("rsi_overbought", 70)
            else:
                stoch_ok = stoch > config.get("stoch_overbought", 80)
                rsi_ok = rsi > config.get("rsi_oversold", 30)
            
            adx_ok = adx >= config.get("adx_min_trend", 25)
            
            # If conditions met, count the trade
            if stoch_ok or rsi_ok or adx_ok:
                if d["outcome"] == "WIN":
                    wins += 1
                    total_profit += abs(d["pnl"])
                else:
                    losses += 1
                    total_loss += abs(d["pnl"])
        
        total_trades = wins + losses
        if total_trades < 10:
            return {"win_rate": 0, "profit_factor": 0, "trades": 0, "fitness": 0}
        
        win_rate = wins / total_trades * 100
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        # Calculate fitness
        fitness = (win_rate - 50) * 2 + (profit_factor - 1) * 15 + min(total_trades / 5, 20)
        
        return {
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "trades": total_trades,
            "fitness": fitness
        }
    
    def optimize_parameter(self, param_name: str, data: List[Dict],
                          direction: str = None,
                          regime: str = None,
                          session: str = None) -> OptimizationResult:
        """Optimize a single parameter"""
        if param_name not in self.param_ranges:
            return None
        
        best_value = None
        best_fitness = -float('inf')
        best_result = None
        
        # Get current config as baseline
        base_config = self.current_config.to_dict()
        base_result = self.evaluate_config(base_config, data, direction, regime, session)
        base_fitness = base_result["fitness"]
        
        # Grid search
        for value in self.param_ranges[param_name]:
            test_config = base_config.copy()
            test_config[param_name] = value
            
            result = self.evaluate_config(test_config, data, direction, regime, session)
            
            if result["fitness"] > best_fitness:
                best_fitness = result["fitness"]
                best_value = value
                best_result = result
        
        if best_value is None:
            return None
        
        improvement = ((best_fitness - base_fitness) / base_fitness * 100) if base_fitness > 0 else 0
        
        return OptimizationResult(
            parameter_name=param_name,
            optimal_value=best_value,
            improvement=round(improvement, 2),
            win_rate=round(best_result["win_rate"], 2),
            profit_factor=round(best_result["profit_factor"], 2),
            sample_size=best_result["trades"],
            regime=regime or "ALL",
            session=session or "ALL"
        )
    
    def optimize_all_parameters(self, data: List[Dict]) -> Dict[str, OptimizationResult]:
        """Optimize all parameters"""
        print("\nOptimizing all parameters...")
        results = {}
        
        for param in self.param_ranges.keys():
            print(f"  Optimizing {param}...")
            
            # Optimize for LONG
            result_long = self.optimize_parameter(param, data, direction="LONG")
            if result_long and result_long.improvement > 0:
                results[f"{param}_long"] = result_long
            
            # Optimize for SHORT
            result_short = self.optimize_parameter(param, data, direction="SHORT")
            if result_short and result_short.improvement > 0:
                results[f"{param}_short"] = result_short
        
        return results
    
    def optimize_for_regime(self, regime: str, data: List[Dict]) -> TuningConfig:
        """Find optimal parameters for a specific regime"""
        print(f"\nOptimizing for regime: {regime}")
        
        regime_data = [d for d in data if d.get("regime") == regime]
        
        if len(regime_data) < 50:
            print(f"  Insufficient data for {regime}")
            return None
        
        config = TuningConfig()
        
        # Optimize key parameters
        for param in ["stoch_oversold", "stoch_overbought", "min_score_long", "adx_min_trend"]:
            result = self.optimize_parameter(param, regime_data)
            if result and result.improvement > 5:  # At least 5% improvement
                setattr(config, param, result.optimal_value)
                print(f"  {param}: {result.optimal_value} (+{result.improvement:.1f}%)")
        
        return config
    
    def optimize_for_session(self, session: str, data: List[Dict]) -> TuningConfig:
        """Find optimal parameters for a specific session"""
        print(f"\nOptimizing for session: {session}")
        
        session_data = [d for d in data if d.get("session") == session]
        
        if len(session_data) < 50:
            print(f"  Insufficient data for {session}")
            return None
        
        config = TuningConfig()
        
        # Optimize key parameters
        for param in ["stoch_oversold", "stoch_overbought", "min_score_long"]:
            result = self.optimize_parameter(param, session_data)
            if result and result.improvement > 5:
                setattr(config, param, result.optimal_value)
                print(f"  {param}: {result.optimal_value} (+{result.improvement:.1f}%)")
        
        return config
    
    def run_full_optimization(self, data: List[Dict]) -> TuningConfig:
        """Run complete optimization"""
        print("="*60)
        print("RUNNING FULL AUTO-TUNING")
        print("="*60)
        print(f"Data points: {len(data)}")
        
        # 1. Optimize global parameters
        print("\n1. Optimizing global parameters...")
        global_results = self.optimize_all_parameters(data)
        
        # Apply improvements to current config
        for key, result in global_results.items():
            param = key.replace("_long", "").replace("_short", "")
            if result.improvement > 10:  # Only apply significant improvements
                setattr(self.current_config, param, result.optimal_value)
        
        # 2. Optimize per-regime
        print("\n2. Optimizing per-regime parameters...")
        for regime in self.regimes:
            config = self.optimize_for_regime(regime, data)
            if config:
                self.current_config.regime_adjustments[regime] = config.to_dict()
        
        # 3. Optimize per-session
        print("\n3. Optimizing per-session parameters...")
        for session in self.sessions:
            config = self.optimize_for_session(session, data)
            if config:
                self.current_config.session_adjustments[session] = config.to_dict()
        
        # Record optimization
        self.optimization_history.append({
            "timestamp": datetime.now().isoformat(),
            "data_points": len(data),
            "global_improvements": len(global_results),
            "regime_optimizations": len(self.current_config.regime_adjustments),
            "session_optimizations": len(self.current_config.session_adjustments)
        })
        
        print("\n" + "="*60)
        print("OPTIMIZATION COMPLETE")
        print("="*60)
        
        return self.current_config
    
    def export_config(self, filepath: str = "data/optimized_config.json") -> str:
        """Export optimized configuration"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "config": self.current_config.to_dict(),
            "history": self.optimization_history
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"Exported config to {filepath}")
        return filepath
    
    def export_for_firebase(self, filepath: str = "data/firebase_config.json") -> str:
        """Export configuration for Firebase update"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        firebase_config = {
            "stochOversold": self.current_config.stoch_oversold,
            "stochOverbought": self.current_config.stoch_overbought,
            "rsiOversold": self.current_config.rsi_oversold,
            "rsiOverbought": self.current_config.rsi_overbought,
            "minScoreLong": self.current_config.min_score_long,
            "minScoreShort": self.current_config.min_score_short,
            "atrStopMult": self.current_config.atr_stop_mult,
            "atrTpMult": self.current_config.atr_tp_mult,
            "adxMinTrend": self.current_config.adx_min_trend,
            "lastUpdated": datetime.now().isoformat(),
            "version": len(self.optimization_history)
        }
        
        with open(filepath, 'w') as f:
            json.dump(firebase_config, f, indent=2)
        
        print(f"Exported Firebase config to {filepath}")
        return filepath
    
    def generate_pine_script_config(self) -> str:
        """Generate Pine Script configuration code"""
        config = self.current_config
        
        pine_code = f"""
// Auto-Tuned Configuration
// Generated: {datetime.now().isoformat()}
// Optimization runs: {len(self.optimization_history)}

// Stochastic Settings
stoch_oversold = input.int({config.stoch_oversold}, "Stoch Oversold", minval=5, maxval=40)
stoch_overbought = input.int({config.stoch_overbought}, "Stoch Overbought", minval=60, maxval=95)

// RSI Settings
rsi_oversold = input.int({config.rsi_oversold}, "RSI Oversold", minval=15, maxval=40)
rsi_overbought = input.int({config.rsi_overbought}, "RSI Overbought", minval=60, maxval=85)

// Score Thresholds
min_score_long = input.int({config.min_score_long}, "Min Score Long", minval=40, maxval=80)
min_score_short = input.int({config.min_score_short}, "Min Score Short", minval=40, maxval=80)

// Risk Management
atr_stop_mult = input.float({config.atr_stop_mult}, "ATR Stop Multiplier", minval=1.0, maxval=4.0, step=0.5)
atr_tp_mult = input.float({config.atr_tp_mult}, "ATR TP Multiplier", minval=1.5, maxval=5.0, step=0.5)

// Trend Filter
adx_min_trend = input.int({config.adx_min_trend}, "ADX Min Trend", minval=15, maxval=40)

// Regime-Specific Adjustments
// Apply these overrides based on detected regime
"""
        
        for regime, adj in config.regime_adjustments.items():
            if adj:
                pine_code += f"\n// {regime}: stoch_os={adj.get('stoch_oversold', config.stoch_oversold)}"
        
        return pine_code


if __name__ == "__main__":
    from pattern_miner import PatternMiner
    
    print("Loading data...")
    miner = PatternMiner()
    data = miner.load_historical_data()
    
    print("\nRunning auto-tuning...")
    tuner = AutoTuner()
    optimized_config = tuner.run_full_optimization(data)
    
    print("\n" + "="*60)
    print("OPTIMIZED CONFIGURATION")
    print("="*60)
    print(f"Stoch Oversold: {optimized_config.stoch_oversold}")
    print(f"Stoch Overbought: {optimized_config.stoch_overbought}")
    print(f"RSI Oversold: {optimized_config.rsi_oversold}")
    print(f"RSI Overbought: {optimized_config.rsi_overbought}")
    print(f"Min Score Long: {optimized_config.min_score_long}")
    print(f"Min Score Short: {optimized_config.min_score_short}")
    print(f"ATR Stop Mult: {optimized_config.atr_stop_mult}")
    print(f"ATR TP Mult: {optimized_config.atr_tp_mult}")
    print(f"ADX Min Trend: {optimized_config.adx_min_trend}")
    
    print("\nRegime Adjustments:")
    for regime, adj in optimized_config.regime_adjustments.items():
        print(f"  {regime}: {adj}")
    
    tuner.export_config()
    tuner.export_for_firebase()
    
    print("\n" + "-"*60)
    print("Pine Script Configuration:")
    print("-"*60)
    print(tuner.generate_pine_script_config())
