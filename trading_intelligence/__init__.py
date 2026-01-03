"""
Trading Intelligence System
============================
AI-drevet trading intelligence for guld futures (GC).

Moduler:
- config: Konfigurationsindstillinger
- data: Data-indsamling og korrelationer
- indicators: Tekniske indikatorer
- database: SQLite data lagring
- visualization: Charts og plots

Brug:
    from trading_intelligence import TradingSystem
    system = TradingSystem()
    system.run_analysis()
"""

from .config import SYMBOLS, INDICATORS, DATA, DB_PATH
from .data import DataFetcher, CorrelationTracker
from .indicators import TechnicalIndicators
from .database import DatabaseManager
from .visualization import ChartGenerator


class TradingSystem:
    """
    Hovedklasse der koordinerer alle moduler.

    Eksempel:
        system = TradingSystem()
        report = system.run_analysis(period_days=90)
        print(report)
    """

    def __init__(self):
        self.fetcher = DataFetcher()
        self.indicators = TechnicalIndicators()
        self.correlations = CorrelationTracker()
        self.db = DatabaseManager()
        self.charts = ChartGenerator()

    def run_analysis(self, period_days: int = 90, save_to_db: bool = True,
                     generate_charts: bool = True) -> dict:
        """
        Udfører komplet analyse af guld futures.

        Args:
            period_days: Antal dage at analysere
            save_to_db: Gem data i database
            generate_charts: Generer visualiseringer

        Returns:
            Dict med analyse resultater
        """
        results = {
            'status': 'running',
            'gold_data': None,
            'indicators': None,
            'correlations': None,
            'charts': [],
            'report': None
        }

        # 1. Hent data
        print("Henter markedsdata...")
        all_data = self.fetcher.fetch_all_markets(period_days)

        if SYMBOLS.PRIMARY_SYMBOL not in all_data:
            results['status'] = 'error'
            results['error'] = 'Kunne ikke hente guld data'
            return results

        gold_df = all_data[SYMBOLS.PRIMARY_SYMBOL]
        results['gold_data'] = gold_df

        # 2. Beregn indikatorer
        print("Beregner tekniske indikatorer...")
        gold_with_indicators = self.indicators.calculate_all(gold_df)
        results['indicators'] = gold_with_indicators

        # 3. Korrelationsanalyse
        print("Analyserer korrelationer...")
        corr_analysis = self.correlations.analyze_correlations(all_data)
        results['correlations'] = corr_analysis

        # 4. Gem i database
        if save_to_db:
            print("Gemmer i database...")
            for symbol, df in all_data.items():
                self.db.save_ohlcv(symbol, df)

            self.db.save_indicators_bulk(SYMBOLS.PRIMARY_SYMBOL, gold_with_indicators)
            self.db.set_metadata('last_analysis', {
                'date': str(gold_df.index[-1]),
                'period_days': period_days
            })

        # 5. Generer charts
        if generate_charts:
            print("Genererer visualiseringer...")

            # Teknisk analyse chart
            chart1 = self.charts.plot_price_with_indicators(
                gold_with_indicators, SYMBOLS.PRIMARY_SYMBOL
            )
            if chart1:
                results['charts'].append(str(chart1))

            # Korrelationsmatrix
            corr_matrix = self.correlations.calculate_correlation_matrix(all_data)
            if not corr_matrix.empty:
                chart2 = self.charts.plot_correlation_matrix(corr_matrix)
                if chart2:
                    results['charts'].append(str(chart2))

            # Multi-asset sammenligning
            chart3 = self.charts.plot_multi_asset(all_data)
            if chart3:
                results['charts'].append(str(chart3))

        # 6. Generer rapport
        results['report'] = self.charts.generate_summary_report(
            gold_with_indicators, SYMBOLS.PRIMARY_SYMBOL
        )

        results['status'] = 'completed'
        print("\nAnalyse færdig!")

        return results

    def get_latest_signals(self) -> dict:
        """Henter seneste trading signaler"""
        gold_df = self.fetcher.fetch_gold_futures(period_days=30)
        if gold_df.empty:
            return {'error': 'Ingen data'}

        gold_with_indicators = self.indicators.calculate_all(gold_df)
        signals = self.indicators.get_signals(gold_with_indicators)

        return {
            'date': str(gold_df.index[-1]),
            'price': float(gold_df['Close'].iloc[-1]),
            'signals': signals.iloc[-1].to_dict() if not signals.empty else {}
        }

    def get_db_stats(self) -> dict:
        """Returnerer database statistik"""
        return self.db.get_stats()
