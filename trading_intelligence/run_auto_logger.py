#!/usr/bin/env python3
"""
🤖 AUTO-LOGGER - Start Script

Logger ALLE signals automatisk fra Firebase.
Ingen manuel logging - systemet lærer selv!

Brug:
    python run_auto_logger.py                    # Standard (SL=4, TP=8)
    python run_auto_logger.py --sl 5 --tp 10    # Custom SL/TP
    python run_auto_logger.py --stats            # Vis statistik
    python run_auto_logger.py --export           # Eksporter til Strategy Factory
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from learning.auto_logger import AutoLogger


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="🤖 Auto-Logger - Automatisk Signal Logging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Eksempler:
  python run_auto_logger.py                  # Start med standard settings
  python run_auto_logger.py --sl 5 --tp 10   # 5 point SL, 10 point TP
  python run_auto_logger.py --stats          # Vis statistik
  python run_auto_logger.py --export         # Eksporter til Strategy Factory
  python run_auto_logger.py --min-score 70   # Kun signals med score >= 70
        """
    )
    
    parser.add_argument("--sl", type=float, default=4.0, 
                       help="Stop Loss i points (default: 4)")
    parser.add_argument("--tp", type=float, default=8.0, 
                       help="Take Profit i points (default: 8)")
    parser.add_argument("--min-score", type=int, default=60, 
                       help="Minimum score for at logge signal (default: 60)")
    parser.add_argument("--interval", type=int, default=10, 
                       help="Check interval i sekunder (default: 10)")
    parser.add_argument("--expiry", type=int, default=60,
                       help="Signal udløber efter X minutter (default: 60)")
    parser.add_argument("--db", type=str, default=None,
                       help="Database navn for multi-test (f.eks. 'conservative', 'aggressive')")
    parser.add_argument("--stats", action="store_true",
                       help="Vis kun statistik")
    parser.add_argument("--export", action="store_true",
                       help="Eksporter data til Strategy Factory")

    args = parser.parse_args()
    
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║         🤖 AUTO-LOGGER - Automatisk Signal Logging 🤖            ║
    ║                                                                  ║
    ║         Logger ALLE signals fra Firebase automatisk              ║
    ║         Tracker WIN/LOSS uden manuel input                       ║
    ║         Fodrer data til Strategy Factory                         ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # Brug custom database hvis specificeret (til multi-testing)
    if args.db:
        db_path = f"data/auto_signals_{args.db}.db"
        print(f"    📁 Database: {db_path}")
    else:
        db_path = "data/auto_signals.db"

    logger = AutoLogger(db_path=db_path)

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
        print(f"Settings:")
        print(f"  Stop Loss: {args.sl} points")
        print(f"  Take Profit: {args.tp} points")
        print(f"  Min Score: {args.min_score}")
        print(f"  Check Interval: {args.interval} sekunder")
        print(f"  Signal Expiry: {args.expiry} minutter")
        print()
        
        logger.run_continuous()


if __name__ == "__main__":
    main()
