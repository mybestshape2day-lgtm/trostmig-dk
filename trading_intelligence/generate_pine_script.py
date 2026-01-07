#!/usr/bin/env python3
"""
Pine Script Generator

Læser evolved rules og genererer Pine Script kode automatisk.
Bare copy-paste ind i TradingView!
"""

import json
import os
from datetime import datetime


def generate_pine_script(rules_file: str = "data/pine_rules.json", 
                         config_file: str = "data/firebase_config.json") -> str:
    """Generer Pine Script kode fra evolved rules"""
    
    # Load rules
    rules = []
    if os.path.exists(rules_file):
        with open(rules_file, 'r') as f:
            rules = json.load(f)
    
    # Load config
    config = {}
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
    
    # Generate Pine Script
    pine = f"""
//@version=5
// ═══════════════════════════════════════════════════════════════════
// AUTO-GENERATED RULES FROM STRATEGY FACTORY
// Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
// Total Rules: {len(rules)}
// ═══════════════════════════════════════════════════════════════════

// ─────────────────────────────────────────────────────────────────────
// OPTIMIZED PARAMETERS (from Auto-Tuner)
// ─────────────────────────────────────────────────────────────────────
stoch_oversold = input.int({config.get('stochOversold', 20)}, "Stoch Oversold")
stoch_overbought = input.int({config.get('stochOverbought', 80)}, "Stoch Overbought")
rsi_oversold = input.int({config.get('rsiOversold', 30)}, "RSI Oversold")
rsi_overbought = input.int({config.get('rsiOverbought', 70)}, "RSI Overbought")
min_score_long = input.int({config.get('minScoreLong', 60)}, "Min Score Long")
min_score_short = input.int({config.get('minScoreShort', 60)}, "Min Score Short")

// ─────────────────────────────────────────────────────────────────────
// EVOLVED RULES - LONG
// ─────────────────────────────────────────────────────────────────────
"""
    
    long_rules = [r for r in rules if r.get('direction') == 'LONG']
    short_rules = [r for r in rules if r.get('direction') == 'SHORT']
    
    for i, rule in enumerate(long_rules[:15], 1):
        conditions = rule.get('conditions', {})
        weight = rule.get('weight', 5)
        name = rule.get('name', f'Rule {i}')
        regime = rule.get('regime')
        
        pine += f"\n// RULE L{i}: {name} (weight: {weight})\n"
        
        cond_parts = []
        for indicator, cond in conditions.items():
            if isinstance(cond, dict):
                op = cond.get('op', cond.get('operator', '>'))
                val = cond.get('val', cond.get('value', 50))
                cond_parts.append(f"{indicator} {op} {val}")
        
        if cond_parts:
            condition_str = " and ".join(cond_parts)
            if regime and regime != "ALL":
                condition_str += f' and regime == "{regime}"'
            pine += f"if {condition_str}\n"
            pine += f"    score_long := score_long + {weight}\n"
    
    pine += """
// ─────────────────────────────────────────────────────────────────────
// EVOLVED RULES - SHORT
// ─────────────────────────────────────────────────────────────────────
"""
    
    for i, rule in enumerate(short_rules[:15], 1):
        conditions = rule.get('conditions', {})
        weight = rule.get('weight', 5)
        name = rule.get('name', f'Rule {i}')
        regime = rule.get('regime')
        
        pine += f"\n// RULE S{i}: {name} (weight: {weight})\n"
        
        cond_parts = []
        for indicator, cond in conditions.items():
            if isinstance(cond, dict):
                op = cond.get('op', cond.get('operator', '>'))
                val = cond.get('val', cond.get('value', 50))
                cond_parts.append(f"{indicator} {op} {val}")
        
        if cond_parts:
            condition_str = " and ".join(cond_parts)
            if regime and regime != "ALL":
                condition_str += f' and regime == "{regime}"'
            pine += f"if {condition_str}\n"
            pine += f"    score_short := score_short + {weight}\n"
    
    pine += """
// ═══════════════════════════════════════════════════════════════════
// END OF AUTO-GENERATED RULES
// ═══════════════════════════════════════════════════════════════════
"""
    
    return pine


def main():
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║         🌲 PINE SCRIPT GENERATOR 🌲                              ║
    ║                                                                  ║
    ║         Genererer Pine Script fra Strategy Factory               ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    
    pine_code = generate_pine_script()
    
    # Save to file
    output_file = "data/generated_pine_script.txt"
    os.makedirs("data", exist_ok=True)
    
    with open(output_file, 'w') as f:
        f.write(pine_code)
    
    print(f"Pine Script gemt til: {output_file}")
    print("\n" + "="*60)
    print("GENERATED PINE SCRIPT:")
    print("="*60)
    print(pine_code)
    print("="*60)
    print(f"\nKopier koden ovenfor eller åbn: {output_file}")
    print("Indsæt i din TradingView Pine Script editor")


if __name__ == "__main__":
    main()
