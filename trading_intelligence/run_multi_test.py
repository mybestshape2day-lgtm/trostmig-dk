#!/usr/bin/env python3
"""
Multi-Config Tester

Kør flere Auto-Loggers med forskellige settings parallelt!
Sammenlign hvilke parametre der virker bedst.
"""

import subprocess
import sys
import os
import json
import time
from datetime import datetime

# Test konfigurationer
CONFIGS = [
    {"name": "conservative", "sl": 3, "tp": 6, "min_score": 70},
    {"name": "balanced", "sl": 4, "tp": 8, "min_score": 60},
    {"name": "aggressive", "sl": 5, "tp": 10, "min_score": 50},
    {"name": "tight", "sl": 2, "tp": 4, "min_score": 65},
    {"name": "wide", "sl": 6, "tp": 12, "min_score": 55},
]


def compare_results():
    """Sammenlign resultater fra alle configs"""
    print("\n" + "="*70)
    print("📊 SAMMENLIGNING AF ALLE KONFIGURATIONER")
    print("="*70)
    
    results = []
    
    for config in CONFIGS:
        db_path = f"data/auto_signals_{config['name']}.db"
        
        if not os.path.exists(db_path):
            continue
        
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM signals WHERE status IN ('WIN', 'LOSS')")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM signals WHERE status = 'WIN'")
        wins = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM signals WHERE status = 'LOSS'")
        losses = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(pnl) FROM signals WHERE status IN ('WIN', 'LOSS')")
        total_pnl = cursor.fetchone()[0] or 0
        
        conn.close()
        
        win_rate = (wins / total * 100) if total > 0 else 0
        
        results.append({
            "name": config['name'],
            "sl": config['sl'],
            "tp": config['tp'],
            "min_score": config['min_score'],
            "total": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "total_pnl": total_pnl
        })
    
    # Sort by total PnL
    results.sort(key=lambda x: x['total_pnl'], reverse=True)
    
    print(f"\n{'Config':<15} {'SL/TP':<10} {'Score':<8} {'Trades':<8} {'WinRate':<10} {'Total PnL':<12}")
    print("-"*70)
    
    for r in results:
        print(f"{r['name']:<15} {r['sl']}/{r['tp']:<7} {r['min_score']:<8} {r['total']:<8} {r['win_rate']:.1f}%{'':5} {r['total_pnl']:+.1f}")
    
    if results:
        best = results[0]
        print("\n" + "="*70)
        print(f"🏆 BEDSTE CONFIG: {best['name']}")
        print(f"   SL: {best['sl']} | TP: {best['tp']} | Min Score: {best['min_score']}")
        print(f"   Win Rate: {best['win_rate']:.1f}% | Total PnL: {best['total_pnl']:+.1f} points")
        print("="*70)
    
    return results


def show_instructions():
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║         🧪 MULTI-CONFIG TESTER 🧪                                ║
    ║                                                                  ║
    ║         Test flere parameter-kombinationer parallelt!            ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    
    Konfigurationer der testes:
    """)
    
    for c in CONFIGS:
        print(f"    • {c['name']}: SL={c['sl']}, TP={c['tp']}, MinScore={c['min_score']}")
    
    print("""
    
    BRUG:
    ─────────────────────────────────────────────────────────────────────
    
    Åbn 5 separate terminaler og kør:
    
    Terminal 1: python run_auto_logger.py --sl 3 --tp 6 --min-score 70 --db conservative
    Terminal 2: python run_auto_logger.py --sl 4 --tp 8 --min-score 60 --db balanced  
    Terminal 3: python run_auto_logger.py --sl 5 --tp 10 --min-score 50 --db aggressive
    Terminal 4: python run_auto_logger.py --sl 2 --tp 4 --min-score 65 --db tight
    Terminal 5: python run_auto_logger.py --sl 6 --tp 12 --min-score 55 --db wide
    
    ─────────────────────────────────────────────────────────────────────
    
    Sammenlign resultater:
    
    python run_multi_test.py --compare
    
    """)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Multi-Config Tester")
    parser.add_argument("--compare", action="store_true", help="Sammenlign resultater")
    
    args = parser.parse_args()
    
    if args.compare:
        compare_results()
    else:
        show_instructions()


if __name__ == "__main__":
    main()
