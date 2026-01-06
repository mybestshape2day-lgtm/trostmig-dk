"""
THE LOOP - Continuous Self-Improvement Runner

This script runs the complete self-evolving trading intelligence system.
It can run as a continuous service or as scheduled jobs.

Usage:
    python run_the_loop.py                  # Run once
    python run_the_loop.py --continuous     # Run continuously (every 24h)
    python run_the_loop.py --iterations 5   # Run 5 iterations
"""

import sys
import os
import time
import argparse
import json
from datetime import datetime, timedelta
import schedule

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from learning.strategy_factory import StrategyFactory


def run_once(data_dir: str = "data") -> dict:
    """Run a single iteration of The Loop"""
    print("\n" + "#"*70)
    print(f"THE LOOP - Single Run - {datetime.now().isoformat()}")
    print("#"*70)
    
    factory = StrategyFactory(data_dir=data_dir)
    results = factory.run_the_loop(iterations=1)
    
    return results[0] if results else {}


def run_continuous(data_dir: str = "data", interval_hours: int = 24):
    """Run The Loop continuously at specified interval"""
    print("\n" + "="*70)
    print("THE LOOP - CONTINUOUS MODE")
    print("="*70)
    print(f"Interval: Every {interval_hours} hours")
    print(f"Started: {datetime.now().isoformat()}")
    print("Press Ctrl+C to stop")
    print("="*70)
    
    factory = StrategyFactory(data_dir=data_dir)
    run_count = 0
    
    def job():
        nonlocal run_count
        run_count += 1
        print(f"\n{'*'*70}")
        print(f"SCHEDULED RUN #{run_count}")
        print(f"{'*'*70}")
        
        try:
            results = factory.run_the_loop(iterations=1)
            
            # Log result
            log_entry = {
                "run": run_count,
                "timestamp": datetime.now().isoformat(),
                "result": results[0] if results else "no results"
            }
            
            log_file = f"{data_dir}/continuous_log.json"
            
            try:
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            except:
                logs = []
            
            logs.append(log_entry)
            
            with open(log_file, 'w') as f:
                json.dump(logs[-100:], f, indent=2)  # Keep last 100 runs
            
        except Exception as e:
            print(f"Error in scheduled run: {e}")
    
    # Run immediately
    job()
    
    # Schedule future runs
    schedule.every(interval_hours).hours.do(job)
    
    # Keep running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\nContinuous mode stopped by user")
        print(f"Total runs: {run_count}")


def run_multiple(data_dir: str = "data", iterations: int = 5):
    """Run multiple iterations of The Loop"""
    print("\n" + "="*70)
    print(f"THE LOOP - {iterations} ITERATIONS")
    print("="*70)
    
    factory = StrategyFactory(data_dir=data_dir)
    results = factory.run_the_loop(iterations=iterations)
    
    # Summary
    print("\n" + "="*70)
    print("MULTI-ITERATION SUMMARY")
    print("="*70)
    
    successful = [r for r in results if r.get("status") == "success"]
    deployed = [r for r in results if r.get("deployed")]
    
    print(f"Total iterations: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Deployments: {len(deployed)}")
    
    factory.print_status()
    
    return results


def generate_report(data_dir: str = "data"):
    """Generate a report of the current system state"""
    print("\n" + "="*70)
    print("STRATEGY FACTORY REPORT")
    print("="*70)
    print(f"Generated: {datetime.now().isoformat()}")
    
    factory = StrategyFactory(data_dir=data_dir)
    
    # Current status
    factory.print_status()
    
    # Version history
    print("\n" + "-"*60)
    print("VERSION HISTORY")
    print("-"*60)
    
    for v in factory.versions[-10:]:  # Last 10 versions
        status = "ACTIVE" if v.is_active else ""
        print(f"  {v.version_id}: WR={v.win_rate}% PF={v.profit_factor} {status}")
    
    # Pattern summary
    print("\n" + "-"*60)
    print("TOP PATTERNS")
    print("-"*60)
    
    for p in factory.pattern_miner.get_top_patterns(5):
        print(f"  {p.name}")
        print(f"    Confidence: {p.confidence}, WR: {p.win_rate}%")
    
    # Rule summary
    print("\n" + "-"*60)
    print("TOP RULES")
    print("-"*60)
    
    for r in factory.rule_evolution.get_top_rules(5):
        print(f"  {r.rule_id}: {r.name}")
        print(f"    Fitness: {r.fitness:.1f}, WR: {r.win_rate:.1f}%")
    
    # Export report
    report = {
        "timestamp": datetime.now().isoformat(),
        "status": factory.get_status(),
        "versions": [v.__dict__ for v in factory.versions[-10:]],
        "top_patterns": [p.__dict__ for p in factory.pattern_miner.get_top_patterns(10)],
        "top_rules": [r.to_dict() for r in factory.rule_evolution.get_top_rules(10)]
    }
    
    report_file = f"{data_dir}/system_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\nReport saved to: {report_file}")


def main():
    parser = argparse.ArgumentParser(
        description="THE LOOP - Self-Evolving Trading Intelligence"
    )
    
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuously (default: every 24 hours)"
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=24,
        help="Interval in hours for continuous mode (default: 24)"
    )
    
    parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="Number of iterations to run (default: 1)"
    )
    
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data",
        help="Data directory (default: data)"
    )
    
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate system report"
    )
    
    args = parser.parse_args()
    
    # Ensure data directory exists
    os.makedirs(args.data_dir, exist_ok=True)
    
    if args.report:
        generate_report(args.data_dir)
    elif args.continuous:
        run_continuous(args.data_dir, args.interval)
    elif args.iterations > 1:
        run_multiple(args.data_dir, args.iterations)
    else:
        run_once(args.data_dir)


if __name__ == "__main__":
    main()
