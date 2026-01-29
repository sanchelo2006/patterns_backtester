import pandas as pd
import json
from pathlib import Path
from typing import Dict, Any
from src.config.settings import RESULTS_DIR
from src.utils.logger import get_logger

logger = get_logger('app')


class FileHandler:
    """Handle file operations for the application"""

    def __init__(self):
        RESULTS_DIR.mkdir(exist_ok=True)

    def save_to_excel(
        self,
        backtest_results: Dict[str, Any],
        filename: str
    ) -> bool:
        """Save backtest results to Excel file"""
        try:
            filepath = RESULTS_DIR / f"{filename}.xlsx"

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Save trades
                trades_df = pd.DataFrame([t.__dict__ for t in backtest_results['trades']])
                trades_df.to_excel(writer, sheet_name='Trades', index=False)

                # Save equity curve
                backtest_results['equity_curve'].to_excel(
                    writer,
                    sheet_name='Equity Curve',
                    index=False
                )

                # Save metrics
                metrics_df = pd.DataFrame([backtest_results['metrics']])
                metrics_df.to_excel(writer, sheet_name='Metrics', index=False)

                # Save pattern statistics if available
                if 'pattern_statistics' in backtest_results['metrics']:
                    pattern_stats = backtest_results['metrics']['pattern_statistics']
                    pattern_df = pd.DataFrame(pattern_stats)
                    pattern_df.to_excel(writer, sheet_name='Pattern Stats')

                logger.info(f"Results saved to {filepath}")
                return True

        except Exception as e:
            logger.error(f"Error saving to Excel: {str(e)}", exc_info=True)
            return False

    def save_chart_html(self, fig, filename: str) -> bool:
        """Save Plotly chart as HTML"""
        try:
            filepath = RESULTS_DIR / f"{filename}.html"
            fig.write_html(filepath)
            logger.info(f"Chart saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving chart: {str(e)}", exc_info=True)
            return False

    def save_config(self, config: Dict, filename: str) -> bool:
        """Save configuration to JSON"""
        try:
            filepath = RESULTS_DIR / f"{filename}.json"
            with open(filepath, 'w') as f:
                json.dump(config, f, indent=4)
            logger.info(f"Config saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving config: {str(e)}", exc_info=True)
            return False

    def load_config(self, filename: str) -> Dict:
        """Load configuration from JSON"""
        try:
            filepath = RESULTS_DIR / f"{filename}.json"
            with open(filepath, 'r') as f:
                config = json.load(f)
            logger.info(f"Config loaded from {filepath}")
            return config
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}", exc_info=True)
            return {}