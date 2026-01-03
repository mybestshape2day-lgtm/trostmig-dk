# Trading Intelligence System

AI-drevet trading intelligence for guld futures (GC).

## Arkitektur

```
trading_intelligence/
├── config/           # Konfiguration og indstillinger
│   └── settings.py   # Symboler, indikator parametre
├── data/             # Data-indsamling
│   ├── fetcher.py    # Yahoo Finance API wrapper
│   └── correlations.py # Korrelationsanalyse
├── indicators/       # Tekniske indikatorer
│   └── technical.py  # EMA, RSI, MACD, Bollinger, ATR, ADX
├── database/         # Data lagring
│   └── db_manager.py # SQLite database manager
├── visualization/    # Charts og plots
│   └── charts.py     # Matplotlib visualiseringer
└── run_analysis.py   # Hovedscript
```

## Installation

```bash
pip install -r requirements.txt
```

## Brug

```bash
# Kør komplet analyse (90 dage)
python run_analysis.py

# Specificer periode
python run_analysis.py --days 180

# Uden visualiseringer
python run_analysis.py --no-charts
```

## Moduler

### DataFetcher
Henter OHLCV data fra Yahoo Finance.
- `fetch_gold_futures()` - Hent guld futures (GC=F)
- `fetch_correlated_markets()` - Hent DXY, Treasury, S&P, Sølv, Oil

### TechnicalIndicators
Beregner tekniske indikatorer.
- EMA (9, 21, 50, 200)
- Stokastisk Oscillator
- RSI (14)
- MACD (12, 26, 9)
- Bollinger Bands (20, 2)
- ATR (14)
- ADX (14)

### CorrelationTracker
Analyserer korrelationer mellem guld og relaterede markeder.

### DatabaseManager
SQLite database til persistent lagring af data og indikatorer.

### ChartGenerator
Genererer visualiseringer med matplotlib.

## Udvidelse

Systemet er designet til at være modulært og let at udvide:

1. **Nye indikatorer**: Tilføj metoder til `TechnicalIndicators` klassen
2. **Nye datakilder**: Implementer nye metoder i `DataFetcher`
3. **Nye markeder**: Tilføj symboler i `config/settings.py`
4. **AI modeller**: Tilføj nyt `models/` modul
