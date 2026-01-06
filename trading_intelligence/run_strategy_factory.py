#!/usr/bin/env python3
"""
Quick Start Script for Strategy Factory

This script demonstrates the self-evolving trading system.
Run this to see The Loop in action!
"""

import sys
import os

# Add the trading_intelligence directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from learning.strategy_factory import StrategyFactory


def main():
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║   ⚡ STRATEGY FACTORY - SELF-EVOLVING TRADING INTELLIGENCE ⚡    ║
    ║                                                                  ║
    ║   The Loop:                                                      ║
    ║   Data → Analysis → Risk Check → Signal → Trade → Log →         ║
    ║     → Performance Review → Strategy Factory → New Rules →       ║
    ║       → Back to Analysis (with improved rules)                   ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # Initialize the factory
    print("Initializing Strategy Factory...")
    factory = StrategyFactory(data_dir="data")
    
    # Run The Loop
    print("\nStarting The Loop...")
    results = factory.run_the_loop(iterations=1)
    
    # Print final status
    print("\n" + "="*70)
    print("SYSTEM STATUS AFTER THE LOOP")
    print("="*70)
    factory.print_status()
    
    print("\n" + "="*70)
    print("FILES GENERATED")
    print("="*70)
    print("""
    data/
    ├── discovered_patterns.json   - Patterns found by Pattern Miner
    ├── discovered_rules.json      - Rules from patterns
    ├── evolved_rules.json         - Evolved trading rules
    ├── pine_rules.json           - Rules for Pine Script
    ├── optimized_config.json     - Optimized parameters
    ├── firebase_config.json      - Config for Firebase
    ├── production_config.json    - Complete production config
    ├── strategy_versions.json    - Version history
    └── loop_results.json         - Results from The Loop
    """)
    
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("""
    1. Review the generated rules in data/evolved_rules.json
    2. Update your Pine Script with data/pine_rules.json
    3. Push data/firebase_config.json to Firebase
    4. Monitor performance with the Feedback Loop
    5. Run The Loop again to continue evolving:
       
       python run_strategy_factory.py
       
       Or for continuous operation:
       
       python learning/run_the_loop.py --continuous
    """)
    
    return results


if __name__ == "__main__":
    main()
