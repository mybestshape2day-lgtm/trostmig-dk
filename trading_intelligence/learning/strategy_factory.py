"""
Strategy Factory - The Main Orchestrator

This is the heart of the self-evolving system. It:
1. Orchestrates all learning components
2. Runs "The Loop" continuously
3. Manages strategy lifecycle
4. Pushes updates to production (Firebase/Pine Script)
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import time

from .pattern_miner import PatternMiner
from .rule_evolution import RuleEvolution
from .auto_tuner import AutoTuner
from .feedback_loop import FeedbackLoop


@dataclass
class StrategyVersion:
    """A version of the trading strategy"""
    version_id: str
    created_at: str
    rules_count: int
    win_rate: float
    profit_factor: float
    is_active: bool
    notes: str


class StrategyFactory:
    """
    The Strategy Factory - Orchestrates the self-evolving trading system.
    
    The Loop:
    1. Collect feedback data from signals
    2. Mine for new patterns
    3. Evolve trading rules
    4. Optimize parameters
    5. Test new strategy
    6. Deploy if improved
    7. Repeat
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize components
        self.pattern_miner = PatternMiner(db_path=f"{data_dir}/trading_history.db")
        self.rule_evolution = RuleEvolution(population_size=50)
        self.auto_tuner = AutoTuner()
        self.feedback_loop = FeedbackLoop(db_path=f"{data_dir}/feedback.db")
        
        # Strategy versions
        self.versions: List[StrategyVersion] = []
        self.current_version: Optional[StrategyVersion] = None
        
        # Configuration
        self.min_improvement = 5.0  # Minimum % improvement to deploy
        self.evolution_generations = 15
        self.optimization_interval = 24  # hours
        
        self._load_versions()
    
    def _load_versions(self):
        """Load strategy versions from disk"""
        versions_file = f"{self.data_dir}/strategy_versions.json"
        
        if os.path.exists(versions_file):
            with open(versions_file, 'r') as f:
                data = json.load(f)
                self.versions = [StrategyVersion(**v) for v in data.get("versions", [])]
                
                active = [v for v in self.versions if v.is_active]
                self.current_version = active[0] if active else None
    
    def _save_versions(self):
        """Save strategy versions to disk"""
        versions_file = f"{self.data_dir}/strategy_versions.json"
        
        with open(versions_file, 'w') as f:
            json.dump({
                "versions": [asdict(v) for v in self.versions],
                "current": self.current_version.version_id if self.current_version else None
            }, f, indent=2)
    
    def run_discovery(self) -> Dict:
        """Run pattern discovery"""
        print("\n" + "="*60)
        print("PHASE 1: PATTERN DISCOVERY")
        print("="*60)
        
        # Get feedback data if available
        feedback_data = self.feedback_loop.get_feedback_data()
        
        if feedback_data:
            print(f"Using {len(feedback_data)} signals from feedback loop")
        else:
            print("No feedback data - using synthetic data for discovery")
        
        # Mine patterns
        patterns = self.pattern_miner.mine_all_patterns()
        
        # Export patterns
        self.pattern_miner.export_patterns(f"{self.data_dir}/discovered_patterns.json")
        
        return {
            "patterns_found": len(patterns),
            "top_pattern": patterns[0].name if patterns else None,
            "top_confidence": patterns[0].confidence if patterns else 0
        }
    
    def run_evolution(self) -> Dict:
        """Run rule evolution"""
        print("\n" + "="*60)
        print("PHASE 2: RULE EVOLUTION")
        print("="*60)
        
        # Get patterns
        patterns = self.pattern_miner.get_top_patterns(30)
        
        if not patterns:
            print("No patterns to evolve - running discovery first")
            self.run_discovery()
            patterns = self.pattern_miner.get_top_patterns(30)
        
        # Initialize evolution with patterns
        self.rule_evolution.initialize_from_patterns([asdict(p) for p in patterns])
        
        # Get training data
        data = self.pattern_miner.load_historical_data()
        
        # Run evolution
        top_rules = self.rule_evolution.run_evolution(data, generations=self.evolution_generations)
        
        # Export rules
        self.rule_evolution.export_rules(f"{self.data_dir}/evolved_rules.json")
        self.rule_evolution.export_for_pine_script(f"{self.data_dir}/pine_rules.json")
        
        return {
            "rules_evolved": len(top_rules),
            "best_fitness": top_rules[0].fitness if top_rules else 0,
            "best_win_rate": top_rules[0].win_rate if top_rules else 0,
            "generations": self.rule_evolution.generation
        }
    
    def run_optimization(self) -> Dict:
        """Run parameter optimization"""
        print("\n" + "="*60)
        print("PHASE 3: PARAMETER OPTIMIZATION")
        print("="*60)
        
        # Get data
        data = self.pattern_miner.load_historical_data()
        
        # Run optimization
        optimized_config = self.auto_tuner.run_full_optimization(data)
        
        # Export config
        self.auto_tuner.export_config(f"{self.data_dir}/optimized_config.json")
        self.auto_tuner.export_for_firebase(f"{self.data_dir}/firebase_config.json")
        
        return {
            "stoch_oversold": optimized_config.stoch_oversold,
            "stoch_overbought": optimized_config.stoch_overbought,
            "min_score": optimized_config.min_score_long,
            "regime_adjustments": len(optimized_config.regime_adjustments),
            "session_adjustments": len(optimized_config.session_adjustments)
        }
    
    def evaluate_strategy(self, rules: List, config: Dict, data: List[Dict]) -> Dict:
        """Evaluate a strategy configuration"""
        wins = 0
        losses = 0
        total_profit = 0
        total_loss = 0
        
        for d in data:
            # Check if any rule triggers
            triggered = False
            direction = None
            
            for rule in rules:
                rule_matches = True
                for indicator, condition in rule.get("conditions", {}).items():
                    value = d.get(indicator, 50)
                    op = condition.get("operator", ">")
                    threshold = condition.get("value", 50)
                    
                    if op == "<" and value >= threshold:
                        rule_matches = False
                    elif op == ">" and value <= threshold:
                        rule_matches = False
                
                if rule_matches:
                    triggered = True
                    direction = rule.get("direction", "LONG")
                    break
            
            if triggered and d.get("direction") == direction:
                if d["outcome"] == "WIN":
                    wins += 1
                    total_profit += abs(d["pnl"])
                else:
                    losses += 1
                    total_loss += abs(d["pnl"])
        
        total = wins + losses
        win_rate = wins / total * 100 if total > 0 else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        return {
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_trades": total,
            "wins": wins,
            "losses": losses
        }
    
    def create_version(self, notes: str = "") -> StrategyVersion:
        """Create a new strategy version"""
        version_id = f"v{len(self.versions) + 1}.0_{datetime.now().strftime('%Y%m%d')}"
        
        # Get current metrics
        top_rules = self.rule_evolution.get_top_rules(10)
        avg_win_rate = sum(r.win_rate for r in top_rules) / len(top_rules) if top_rules else 0
        avg_pf = sum(r.profit_factor for r in top_rules) / len(top_rules) if top_rules else 0
        
        version = StrategyVersion(
            version_id=version_id,
            created_at=datetime.now().isoformat(),
            rules_count=len(top_rules),
            win_rate=round(avg_win_rate, 2),
            profit_factor=round(avg_pf, 2),
            is_active=False,
            notes=notes
        )
        
        self.versions.append(version)
        self._save_versions()
        
        return version
    
    def deploy_version(self, version_id: str) -> bool:
        """Deploy a strategy version to production"""
        version = next((v for v in self.versions if v.version_id == version_id), None)
        
        if not version:
            print(f"Version {version_id} not found")
            return False
        
        # Deactivate current version
        for v in self.versions:
            v.is_active = False
        
        # Activate new version
        version.is_active = True
        self.current_version = version
        
        self._save_versions()
        
        print(f"\n{'='*60}")
        print(f"DEPLOYED VERSION: {version_id}")
        print(f"{'='*60}")
        print(f"Rules: {version.rules_count}")
        print(f"Win Rate: {version.win_rate}%")
        print(f"Profit Factor: {version.profit_factor}")
        
        # Export for production
        self._export_production_files()
        
        return True
    
    def _export_production_files(self):
        """Export files for production use"""
        # Combine all outputs into a single production config
        production_config = {
            "version": self.current_version.version_id if self.current_version else "v0",
            "timestamp": datetime.now().isoformat(),
            "tuning": self.auto_tuner.current_config.to_dict(),
            "rules": [r.to_dict() for r in self.rule_evolution.get_top_rules(15)]
        }
        
        with open(f"{self.data_dir}/production_config.json", 'w') as f:
            json.dump(production_config, f, indent=2)
        
        print(f"Exported production config to {self.data_dir}/production_config.json")
    
    def run_the_loop(self, iterations: int = 1) -> List[Dict]:
        """Run the complete self-improvement loop"""
        print("\n" + "="*70)
        print("THE LOOP - SELF-EVOLVING TRADING INTELLIGENCE")
        print("="*70)
        print(f"Running {iterations} iteration(s)")
        print(f"Started at: {datetime.now().isoformat()}")
        
        results = []
        
        for i in range(iterations):
            print(f"\n{'#'*60}")
            print(f"ITERATION {i + 1}/{iterations}")
            print(f"{'#'*60}")
            
            iteration_result = {
                "iteration": i + 1,
                "started_at": datetime.now().isoformat()
            }
            
            try:
                # Phase 1: Discovery
                discovery_result = self.run_discovery()
                iteration_result["discovery"] = discovery_result
                
                # Phase 2: Evolution
                evolution_result = self.run_evolution()
                iteration_result["evolution"] = evolution_result
                
                # Phase 3: Optimization
                optimization_result = self.run_optimization()
                iteration_result["optimization"] = optimization_result
                
                # Phase 4: Create and evaluate new version
                version = self.create_version(f"Auto-generated iteration {i+1}")
                iteration_result["version"] = version.version_id
                
                # Phase 5: Deploy if improved
                should_deploy = False
                
                if self.current_version:
                    improvement = (version.win_rate - self.current_version.win_rate)
                    if improvement >= self.min_improvement:
                        should_deploy = True
                        print(f"\nImprovement: +{improvement:.1f}% - DEPLOYING")
                    else:
                        print(f"\nImprovement: {improvement:.1f}% - Below threshold, not deploying")
                else:
                    should_deploy = True
                    print("\nNo current version - DEPLOYING first version")
                
                if should_deploy:
                    self.deploy_version(version.version_id)
                    iteration_result["deployed"] = True
                else:
                    iteration_result["deployed"] = False
                
                iteration_result["completed_at"] = datetime.now().isoformat()
                iteration_result["status"] = "success"
                
            except Exception as e:
                iteration_result["status"] = "error"
                iteration_result["error"] = str(e)
                print(f"\nError in iteration: {e}")
            
            results.append(iteration_result)
        
        # Final summary
        print("\n" + "="*70)
        print("THE LOOP COMPLETE")
        print("="*70)
        
        successful = [r for r in results if r["status"] == "success"]
        print(f"Successful iterations: {len(successful)}/{iterations}")
        
        if self.current_version:
            print(f"\nActive Version: {self.current_version.version_id}")
            print(f"Win Rate: {self.current_version.win_rate}%")
            print(f"Profit Factor: {self.current_version.profit_factor}")
        
        # Save results
        with open(f"{self.data_dir}/loop_results.json", 'w') as f:
            json.dump(results, f, indent=2)
        
        return results
    
    def get_status(self) -> Dict:
        """Get current system status"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "current_version": asdict(self.current_version) if self.current_version else None,
            "total_versions": len(self.versions),
            "patterns_discovered": len(self.pattern_miner.discovered_patterns),
            "rules_evolved": len(self.rule_evolution.population),
            "optimization_runs": len(self.auto_tuner.optimization_history)
        }
        
        # Get feedback metrics
        metrics = self.feedback_loop.calculate_metrics(days=7)
        if metrics:
            status["recent_performance"] = {
                "signals": metrics.total_signals,
                "win_rate": metrics.win_rate,
                "profit_factor": metrics.profit_factor
            }
        
        return status
    
    def print_status(self):
        """Print system status"""
        status = self.get_status()
        
        print("\n" + "="*60)
        print("STRATEGY FACTORY STATUS")
        print("="*60)
        print(f"Timestamp: {status['timestamp']}")
        print(f"\nVersions: {status['total_versions']}")
        
        if status['current_version']:
            cv = status['current_version']
            print(f"\nActive Version: {cv['version_id']}")
            print(f"  Win Rate: {cv['win_rate']}%")
            print(f"  Profit Factor: {cv['profit_factor']}")
            print(f"  Rules: {cv['rules_count']}")
        
        print(f"\nPatterns Discovered: {status['patterns_discovered']}")
        print(f"Rules in Population: {status['rules_evolved']}")
        print(f"Optimization Runs: {status['optimization_runs']}")
        
        if "recent_performance" in status:
            perf = status["recent_performance"]
            print(f"\nRecent Performance (7 days):")
            print(f"  Signals: {perf['signals']}")
            print(f"  Win Rate: {perf['win_rate']}%")
            print(f"  Profit Factor: {perf['profit_factor']}")


if __name__ == "__main__":
    print("="*70)
    print("STRATEGY FACTORY - SELF-EVOLVING TRADING INTELLIGENCE")
    print("="*70)
    
    factory = StrategyFactory(data_dir="data")
    
    # Run The Loop once
    results = factory.run_the_loop(iterations=1)
    
    # Print status
    factory.print_status()
    
    print("\n" + "="*70)
    print("STRATEGY FACTORY INITIALIZED")
    print("="*70)
    print("\nThe system is now ready for continuous learning.")
    print("Run factory.run_the_loop(iterations=N) to continue evolution.")
