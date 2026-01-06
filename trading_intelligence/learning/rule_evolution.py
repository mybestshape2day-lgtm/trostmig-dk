"""
Rule Evolution - Generates and evolves trading rules using genetic algorithms

This module:
1. Takes discovered patterns and creates rule "DNA"
2. Mutates rules to find improvements
3. Crossbreeds successful rules
4. Eliminates underperforming rules
5. Promotes top performers to production
"""

import json
import random
import copy
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict, field
import os


@dataclass
class TradingRule:
    """A trading rule with evolvable parameters"""
    rule_id: str
    name: str
    generation: int
    
    # Conditions
    conditions: Dict[str, Dict]  # {indicator: {operator, value}}
    
    # Filters
    regime_filter: Optional[str] = None
    session_filter: Optional[str] = None
    
    # Output
    direction: str = "LONG"  # LONG or SHORT
    weight: int = 5  # 1-10 contribution to score
    
    # Performance metrics
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    fitness: float = 0.0
    
    # Lineage
    parent_ids: List[str] = field(default_factory=list)
    mutations: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TradingRule':
        return cls(**data)


class RuleEvolution:
    """
    Evolves trading rules using genetic algorithms.
    
    The evolution process:
    1. Initialize population from discovered patterns
    2. Evaluate fitness on historical data
    3. Select top performers
    4. Crossbreed and mutate
    5. Replace weak rules
    6. Repeat
    """
    
    def __init__(self, population_size: int = 50):
        self.population_size = population_size
        self.population: List[TradingRule] = []
        self.generation = 0
        self.elite_count = 5  # Top rules preserved each generation
        self.mutation_rate = 0.2
        self.crossover_rate = 0.3
        
        # Evolution parameters
        self.indicator_ranges = {
            "rsi": (10, 90),
            "stoch_k": (5, 95),
            "adx": (10, 60),
            "atr_percentile": (10, 90)
        }
        
        self.regimes = ["STRONG_UPTREND", "WEAK_UPTREND", "RANGING", 
                       "WEAK_DOWNTREND", "STRONG_DOWNTREND", None]
        self.sessions = ["asia", "london", "newyork", "overlap", None]
        
        # History
        self.evolution_history: List[Dict] = []
    
    def initialize_from_patterns(self, patterns: List[Dict]) -> None:
        """Initialize population from discovered patterns"""
        self.population = []
        
        for i, pattern in enumerate(patterns[:self.population_size]):
            rule = TradingRule(
                rule_id=f"GEN0_R{i:03d}",
                name=pattern.get("name", f"Rule {i}"),
                generation=0,
                conditions=pattern.get("conditions", {}),
                regime_filter=pattern.get("best_regime") if pattern.get("best_regime") != "ALL" else None,
                session_filter=pattern.get("best_session") if pattern.get("best_session") != "ALL" else None,
                direction=pattern.get("direction", "LONG"),
                weight=min(10, max(1, int(pattern.get("confidence", 50) / 10))),
                win_rate=pattern.get("win_rate", 0),
                profit_factor=pattern.get("profit_factor", 0),
                total_trades=pattern.get("sample_size", 0),
                fitness=pattern.get("confidence", 0)
            )
            self.population.append(rule)
        
        # Fill remaining with random rules if needed
        while len(self.population) < self.population_size:
            self.population.append(self._create_random_rule())
        
        print(f"Initialized population with {len(self.population)} rules")
    
    def _create_random_rule(self) -> TradingRule:
        """Create a random rule"""
        rule_id = f"GEN{self.generation}_R{random.randint(100, 999)}"
        
        # Random conditions
        conditions = {}
        n_conditions = random.randint(1, 3)
        indicators = random.sample(list(self.indicator_ranges.keys()), n_conditions)
        
        for ind in indicators:
            low, high = self.indicator_ranges[ind]
            operator = random.choice(["<", ">"])
            value = random.randint(low, high)
            conditions[ind] = {"operator": operator, "value": value}
        
        return TradingRule(
            rule_id=rule_id,
            name=f"Random Rule {rule_id}",
            generation=self.generation,
            conditions=conditions,
            regime_filter=random.choice(self.regimes),
            session_filter=random.choice(self.sessions),
            direction=random.choice(["LONG", "SHORT"]),
            weight=random.randint(1, 10)
        )
    
    def evaluate_fitness(self, rule: TradingRule, data: List[Dict]) -> float:
        """Evaluate rule fitness on historical data"""
        # Filter data matching rule conditions
        filtered = data.copy()
        
        # Apply regime filter
        if rule.regime_filter:
            filtered = [d for d in filtered if d.get("regime") == rule.regime_filter]
        
        # Apply session filter
        if rule.session_filter:
            filtered = [d for d in filtered if d.get("session") == rule.session_filter]
        
        # Apply indicator conditions
        for indicator, condition in rule.conditions.items():
            operator = condition.get("operator", ">")
            value = condition.get("value", 50)
            
            if operator == "<":
                filtered = [d for d in filtered if d.get(indicator, 50) < value]
            elif operator == ">":
                filtered = [d for d in filtered if d.get(indicator, 50) > value]
            elif operator == "==":
                filtered = [d for d in filtered if d.get(indicator) == value]
        
        # Only consider matching direction
        filtered = [d for d in filtered if d.get("direction") == rule.direction]
        
        if len(filtered) < 10:
            return 0.0
        
        # Calculate metrics
        wins = [d for d in filtered if d["outcome"] == "WIN"]
        losses = [d for d in filtered if d["outcome"] == "LOSS"]
        
        win_rate = len(wins) / len(filtered) * 100
        
        total_profit = sum(d["pnl"] for d in wins) if wins else 0
        total_loss = abs(sum(d["pnl"] for d in losses)) if losses else 0.01
        profit_factor = total_profit / total_loss
        
        # Update rule metrics
        rule.win_rate = win_rate
        rule.profit_factor = profit_factor
        rule.total_trades = len(filtered)
        
        # Calculate fitness
        # Fitness = win_rate bonus + profit_factor bonus + sample size bonus
        fitness = (
            (win_rate - 50) * 2 +  # Win rate contribution
            (profit_factor - 1) * 20 +  # Profit factor contribution
            min(len(filtered) / 5, 20)  # Sample size contribution (max 20)
        )
        
        # Penalize very few trades
        if len(filtered) < 20:
            fitness *= 0.5
        
        rule.fitness = max(0, fitness)
        return rule.fitness
    
    def evaluate_population(self, data: List[Dict]) -> None:
        """Evaluate fitness of all rules"""
        for rule in self.population:
            self.evaluate_fitness(rule, data)
        
        # Sort by fitness
        self.population.sort(key=lambda r: r.fitness, reverse=True)
    
    def select_parents(self) -> Tuple[TradingRule, TradingRule]:
        """Select two parents using tournament selection"""
        tournament_size = 5
        
        def tournament():
            candidates = random.sample(self.population, tournament_size)
            return max(candidates, key=lambda r: r.fitness)
        
        return tournament(), tournament()
    
    def crossover(self, parent1: TradingRule, parent2: TradingRule) -> TradingRule:
        """Create child by combining two parents"""
        child_id = f"GEN{self.generation}_R{random.randint(100, 999)}"
        
        # Combine conditions from both parents
        conditions = {}
        all_indicators = set(parent1.conditions.keys()) | set(parent2.conditions.keys())
        
        for ind in all_indicators:
            if ind in parent1.conditions and ind in parent2.conditions:
                # Average the values
                v1 = parent1.conditions[ind]["value"]
                v2 = parent2.conditions[ind]["value"]
                conditions[ind] = {
                    "operator": random.choice([parent1.conditions[ind]["operator"],
                                               parent2.conditions[ind]["operator"]]),
                    "value": int((v1 + v2) / 2)
                }
            elif ind in parent1.conditions:
                conditions[ind] = copy.deepcopy(parent1.conditions[ind])
            else:
                conditions[ind] = copy.deepcopy(parent2.conditions[ind])
        
        # Inherit filters
        regime_filter = random.choice([parent1.regime_filter, parent2.regime_filter])
        session_filter = random.choice([parent1.session_filter, parent2.session_filter])
        
        # Inherit direction from fitter parent
        direction = parent1.direction if parent1.fitness > parent2.fitness else parent2.direction
        
        # Average weight
        weight = int((parent1.weight + parent2.weight) / 2)
        
        return TradingRule(
            rule_id=child_id,
            name=f"Crossover {parent1.rule_id} x {parent2.rule_id}",
            generation=self.generation,
            conditions=conditions,
            regime_filter=regime_filter,
            session_filter=session_filter,
            direction=direction,
            weight=weight,
            parent_ids=[parent1.rule_id, parent2.rule_id]
        )
    
    def mutate(self, rule: TradingRule) -> TradingRule:
        """Mutate a rule"""
        mutated = copy.deepcopy(rule)
        mutated.rule_id = f"GEN{self.generation}_M{random.randint(100, 999)}"
        mutated.generation = self.generation
        mutated.parent_ids = [rule.rule_id]
        mutated.mutations = []
        
        # Mutate conditions
        for indicator, condition in mutated.conditions.items():
            if random.random() < 0.3:
                # Mutate value
                low, high = self.indicator_ranges.get(indicator, (0, 100))
                delta = random.randint(-10, 10)
                new_value = max(low, min(high, condition["value"] + delta))
                mutated.mutations.append(f"{indicator}: {condition['value']} -> {new_value}")
                condition["value"] = new_value
            
            if random.random() < 0.1:
                # Flip operator
                condition["operator"] = ">" if condition["operator"] == "<" else "<"
                mutated.mutations.append(f"{indicator} operator flipped")
        
        # Mutate filters
        if random.random() < 0.15:
            mutated.regime_filter = random.choice(self.regimes)
            mutated.mutations.append(f"regime_filter -> {mutated.regime_filter}")
        
        if random.random() < 0.15:
            mutated.session_filter = random.choice(self.sessions)
            mutated.mutations.append(f"session_filter -> {mutated.session_filter}")
        
        # Mutate weight
        if random.random() < 0.2:
            delta = random.choice([-1, 1])
            mutated.weight = max(1, min(10, mutated.weight + delta))
            mutated.mutations.append(f"weight -> {mutated.weight}")
        
        mutated.name = f"Mutated {rule.rule_id}"
        return mutated
    
    def evolve_generation(self, data: List[Dict]) -> Dict:
        """Run one generation of evolution"""
        self.generation += 1
        print(f"\n{'='*50}")
        print(f"GENERATION {self.generation}")
        print(f"{'='*50}")
        
        # Evaluate current population
        self.evaluate_population(data)
        
        # Record stats
        avg_fitness = np.mean([r.fitness for r in self.population])
        max_fitness = max(r.fitness for r in self.population)
        avg_win_rate = np.mean([r.win_rate for r in self.population])
        
        stats = {
            "generation": self.generation,
            "avg_fitness": round(avg_fitness, 2),
            "max_fitness": round(max_fitness, 2),
            "avg_win_rate": round(avg_win_rate, 2),
            "best_rule": self.population[0].rule_id
        }
        self.evolution_history.append(stats)
        
        print(f"Avg Fitness: {avg_fitness:.2f}")
        print(f"Max Fitness: {max_fitness:.2f}")
        print(f"Best Rule: {self.population[0].name}")
        
        # Keep elite rules
        new_population = self.population[:self.elite_count]
        
        # Generate new rules through crossover and mutation
        while len(new_population) < self.population_size:
            if random.random() < self.crossover_rate:
                # Crossover
                parent1, parent2 = self.select_parents()
                child = self.crossover(parent1, parent2)
                new_population.append(child)
            elif random.random() < self.mutation_rate:
                # Mutation
                parent = random.choice(self.population[:self.population_size // 2])
                mutant = self.mutate(parent)
                new_population.append(mutant)
            else:
                # Random new rule
                new_population.append(self._create_random_rule())
        
        self.population = new_population[:self.population_size]
        
        return stats
    
    def run_evolution(self, data: List[Dict], generations: int = 20) -> List[TradingRule]:
        """Run full evolution process"""
        print(f"\nStarting evolution for {generations} generations")
        print(f"Population size: {self.population_size}")
        print(f"Data points: {len(data)}")
        
        for _ in range(generations):
            self.evolve_generation(data)
        
        # Final evaluation
        self.evaluate_population(data)
        
        print(f"\n{'='*60}")
        print("EVOLUTION COMPLETE")
        print(f"{'='*60}")
        print(f"Generations: {self.generation}")
        print(f"Best fitness: {self.population[0].fitness:.2f}")
        print(f"Best win rate: {self.population[0].win_rate:.2f}%")
        print(f"Best profit factor: {self.population[0].profit_factor:.2f}")
        
        return self.get_top_rules()
    
    def get_top_rules(self, n: int = 10) -> List[TradingRule]:
        """Get top N rules"""
        self.population.sort(key=lambda r: r.fitness, reverse=True)
        return self.population[:n]
    
    def export_rules(self, filepath: str = "data/evolved_rules.json") -> str:
        """Export top rules to JSON"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        rules_dict = [r.to_dict() for r in self.get_top_rules(20)]
        
        with open(filepath, 'w') as f:
            json.dump({
                "generation": self.generation,
                "timestamp": datetime.now().isoformat(),
                "rules": rules_dict,
                "evolution_history": self.evolution_history
            }, f, indent=2)
        
        print(f"Exported rules to {filepath}")
        return filepath
    
    def export_for_pine_script(self, filepath: str = "data/pine_rules.json") -> str:
        """Export rules in Pine Script compatible format"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        pine_rules = []
        for rule in self.get_top_rules(15):
            pine_rule = {
                "id": rule.rule_id,
                "name": rule.name,
                "direction": rule.direction,
                "weight": rule.weight,
                "conditions": {}
            }
            
            for indicator, cond in rule.conditions.items():
                pine_rule["conditions"][indicator] = {
                    "op": cond["operator"],
                    "val": cond["value"]
                }
            
            if rule.regime_filter:
                pine_rule["regime"] = rule.regime_filter
            if rule.session_filter:
                pine_rule["session"] = rule.session_filter
            
            pine_rules.append(pine_rule)
        
        with open(filepath, 'w') as f:
            json.dump(pine_rules, f, indent=2)
        
        print(f"Exported Pine Script rules to {filepath}")
        return filepath


if __name__ == "__main__":
    # Test evolution
    from pattern_miner import PatternMiner
    
    print("Mining patterns...")
    miner = PatternMiner()
    patterns = miner.mine_all_patterns()
    
    print("\nInitializing evolution...")
    evolution = RuleEvolution(population_size=50)
    evolution.initialize_from_patterns([p.__dict__ for p in patterns])
    
    print("\nRunning evolution...")
    data = miner.load_historical_data()
    top_rules = evolution.run_evolution(data, generations=10)
    
    print("\n" + "="*60)
    print("TOP EVOLVED RULES")
    print("="*60)
    
    for i, rule in enumerate(top_rules[:5], 1):
        print(f"\n{i}. {rule.name}")
        print(f"   Fitness: {rule.fitness:.2f}")
        print(f"   Win Rate: {rule.win_rate:.2f}%")
        print(f"   Profit Factor: {rule.profit_factor:.2f}")
        print(f"   Conditions: {rule.conditions}")
        print(f"   Direction: {rule.direction}")
        print(f"   Weight: {rule.weight}")
    
    evolution.export_rules()
    evolution.export_for_pine_script()
