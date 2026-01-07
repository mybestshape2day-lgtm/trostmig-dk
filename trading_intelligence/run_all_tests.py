#!/usr/bin/env python3
"""
🧪 RUN ALL TESTS - Kør alle test-konfigurationer automatisk

Kører 10 forskellige konfigurationer og sammenligner resultater.
Alt i én terminal!
"""

import sys
import os
import time
import json
import sqlite3
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from learning.auto_logger import AutoLogger

# 10 smarte test-konfigurationer - "Sikker Profit" strategi
# Idé: Tag små sikre gevinster, bred stop loss
CONFIGS = [
    # Navn, SL, TP, MinScore, Beskrivelse
    ("safe_3_wide", 30, 3, 75, "Sikker $3 - bred SL, høj score"),
    ("safe_3_medium", 20, 3, 70, "Sikker $3 - medium SL"),
    ("safe_2_wide", 30, 2, 75, "Sikker $2 - meget bred SL"),
    ("safe_4_wide", 40, 4, 70, "Sikker $4 - bred SL"),
    ("safe_5_wide", 50, 5, 70, "Sikker $5 - meget bred SL"),
    ("safe_3_tight", 15, 3, 80, "Sikker $3 - tættere SL, meget høj score"),
    ("safe_2_tight", 10, 2, 80, "Sikker $2 - tæt SL, meget høj score"),
    ("safe_6_wide", 60, 6, 65, "Sikker $6 - meget bred SL"),
    ("safe_3_super", 100, 3, 75, "Sikker $3 - super bred SL"),
    ("safe_4_super", 100, 4, 70, "Sikker $4 - super bred SL"),
]


class MultiTester:
    def __init__(self):
        self.loggers = {}
        self.stats = {}
        self.running = False
        self.lock = threading.Lock()
        
    def init_loggers(self):
        """Initialiser alle loggers"""
        print("\n" + "="*70)
        print("🧪 INITIALISERER 10 TEST-KONFIGURATIONER")
        print("="*70)
        
        for name, sl, tp, min_score, desc in CONFIGS:
            db_path = f"data/test_{name}.db"
            logger = AutoLogger(db_path=db_path)
            logger.set_config(
                stop_loss_points=sl,
                take_profit_points=tp,
                min_score=min_score,
                check_interval_seconds=5,
                signal_expiry_minutes=120  # 2 timer - giv trades tid til at ramme TP
            )
            self.loggers[name] = logger
            print(f"  ✓ {name}: SL={sl}, TP={tp}, Score>={min_score} ({desc})")
        
        print("="*70 + "\n")
    
    def run_single_check(self, name, logger):
        """Kør én check for én logger"""
        try:
            logger.run_once()
            
            with self.lock:
                stats = logger.get_statistics()
                self.stats[name] = stats
        except Exception as e:
            pass
    
    def print_live_stats(self):
        """Print live statistik"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║         🧪 MULTI-CONFIG LIVE TEST 🧪                             ║
    ║         Tryk Ctrl+C for at stoppe                                ║
    ╚══════════════════════════════════════════════════════════════════╝
        """)
        
        print(f"    Tid: {datetime.now().strftime('%H:%M:%S')}")
        print()
        print(f"    {'Config':<15} {'SL/TP':<8} {'Score':<7} {'Signals':<9} {'Win':<5} {'Loss':<6} {'WinRate':<9} {'PnL':<10}")
        print("    " + "-"*75)
        
        # Sort by total PnL
        sorted_stats = sorted(
            [(name, self.stats.get(name, {})) for name in self.loggers.keys()],
            key=lambda x: x[1].get('total_pnl', 0),
            reverse=True
        )
        
        for name, stats in sorted_stats:
            cfg = next((c for c in CONFIGS if c[0] == name), None)
            if not cfg:
                continue
            
            sl, tp, min_score = cfg[1], cfg[2], cfg[3]
            total = stats.get('total_signals', 0)
            wins = stats.get('wins', 0)
            losses = stats.get('losses', 0)
            wr = stats.get('win_rate', 0)
            pnl = stats.get('total_pnl', 0)
            
            # Color coding (simple)
            pnl_str = f"{pnl:+.1f}" if pnl != 0 else "0.0"
            
            print(f"    {name:<15} {sl}/{tp:<5} {min_score:<7} {total:<9} {wins:<5} {losses:<6} {wr:.1f}%{'':5} {pnl_str:<10}")
        
        print()
        print("    " + "="*75)
        
        # Find best
        if sorted_stats and sorted_stats[0][1].get('total_pnl', 0) != 0:
            best_name = sorted_stats[0][0]
            best_pnl = sorted_stats[0][1].get('total_pnl', 0)
            print(f"    🏆 Bedste indtil nu: {best_name} ({best_pnl:+.1f} points)")
    
    def run_continuous(self):
        """Kør alle tests kontinuerligt"""
        self.init_loggers()
        self.running = True
        
        print("Starter live testing... (Ctrl+C for at stoppe)\n")
        time.sleep(2)
        
        try:
            while self.running:
                # Kør alle loggers
                for name, logger in self.loggers.items():
                    self.run_single_check(name, logger)
                
                # Print stats
                self.print_live_stats()
                
                # Vent
                time.sleep(10)
        
        except KeyboardInterrupt:
            print("\n\nStopper tests...")
            self.running = False
            self.print_final_results()
    
    def print_final_results(self):
        """Print endelige resultater"""
        print("\n" + "="*70)
        print("📊 ENDELIGE RESULTATER")
        print("="*70)
        
        results = []
        for name, logger in self.loggers.items():
            stats = logger.get_statistics()
            cfg = next((c for c in CONFIGS if c[0] == name), None)
            if cfg:
                results.append({
                    "name": name,
                    "sl": cfg[1],
                    "tp": cfg[2],
                    "min_score": cfg[3],
                    **stats
                })
        
        # Sort by PnL
        results.sort(key=lambda x: x['total_pnl'], reverse=True)
        
        print(f"\n{'Rank':<6} {'Config':<15} {'SL/TP':<8} {'Signals':<9} {'WinRate':<10} {'PnL':<12}")
        print("-"*60)
        
        for i, r in enumerate(results, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            print(f"{medal} {i:<4} {r['name']:<15} {r['sl']}/{r['tp']:<5} {r['total_signals']:<9} {r['win_rate']:.1f}%{'':5} {r['total_pnl']:+.1f}")
        
        if results and results[0]['total_pnl'] > 0:
            best = results[0]
            print(f"\n🏆 ANBEFALET CONFIG: {best['name']}")
            print(f"   Brug: python run_auto_logger.py --sl {best['sl']} --tp {best['tp']} --min-score {best['min_score']}")
        
        # Gem resultater
        with open("data/test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResultater gemt til: data/test_results.json")


def main():
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║         🧪 MULTI-CONFIG AUTO-TESTER 🧪                           ║
    ║                                                                  ║
    ║         Tester 10 forskellige konfigurationer samtidigt!         ║
    ║         Finder automatisk den bedste SL/TP/Score kombination     ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    
    tester = MultiTester()
    tester.run_continuous()


if __name__ == "__main__":
    main()
