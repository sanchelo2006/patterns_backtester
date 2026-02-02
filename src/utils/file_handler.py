import pandas as pd
import json
from pathlib import Path
from typing import Dict, Any, Optional
import plotly.graph_objects as go
from plotly.io import to_image
import base64
from io import BytesIO
from src.config.settings import RESULTS_DIR
from src.utils.logger import get_logger

logger = get_logger('app')


class FileHandler:
    """Handle file operations for the application"""

    def __init__(self):
        RESULTS_DIR.mkdir(exist_ok=True)

    def save_to_excel_with_chart(
        self,
        backtest_results: Dict[str, Any],
        strategy_info: Dict[str, Any],
        filename: str
    ) -> bool:
        """Save backtest results to Excel file with embedded chart"""
        try:
            filepath = RESULTS_DIR / f"{filename}.xlsx"

            # Create Excel writer with XlsxWriter engine for chart support
            with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
                workbook = writer.book

                # Save trades
                trades_df = pd.DataFrame([t.to_dict() for t in backtest_results['trades']])
                trades_df.to_excel(writer, sheet_name='Trades', index=False)

                # Save equity curve
                equity_df = backtest_results['equity_curve']
                equity_df.to_excel(writer, sheet_name='Equity Curve', index=False)

                # Save metrics
                metrics_df = pd.DataFrame([backtest_results['metrics']])
                metrics_df.to_excel(writer, sheet_name='Metrics', index=False)

                # Save summary
                summary_data = {
                    'Parameter': [],
                    'Value': []
                }

                for key, value in strategy_info.items():
                    summary_data['Parameter'].append(key)
                    summary_data['Value'].append(str(value))

                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)

                # Create chart sheet
                chart_sheet = workbook.add_worksheet('Chart')

                # Add some text about the chart
                chart_sheet.write('A1', 'Backtest Chart')
                chart_sheet.write('A2', 'Note: For interactive chart, please use the application.')
                chart_sheet.write('A3', 'This sheet contains trade markers information.')

                # Add trade markers table
                if backtest_results['trades']:
                    chart_sheet.write('A5', 'Trade Entry/Exit Points:')
                    headers = ['Type', 'Date', 'Price', 'Pattern', 'P&L', 'Result']
                    for col, header in enumerate(headers):
                        chart_sheet.write(5, col, header)

                    for row, trade in enumerate(backtest_results['trades'], start=6):
                        chart_sheet.write(row, 0, trade.position_type.upper())
                        chart_sheet.write(row, 1, trade.entry_date.strftime('%Y-%m-%d'))
                        chart_sheet.write(row, 2, trade.entry_price)
                        chart_sheet.write(row, 3, trade.pattern)
                        chart_sheet.write(row, 4, f"{trade.pnl:.2f}")
                        chart_sheet.write(row, 5, 'PROFIT' if trade.success else 'LOSS')

                # Create a simple chart using equity curve
                equity_chart = workbook.add_chart({'type': 'line'})
                equity_chart.add_series({
                    'name': 'Equity',
                    'categories': ['Equity Curve', 1, 0, len(equity_df), 0],
                    'values': ['Equity Curve', 1, 1, len(equity_df), 1],
                })
                equity_chart.set_title({'name': 'Equity Curve'})
                equity_chart.set_x_axis({'name': 'Date'})
                equity_chart.set_y_axis({'name': 'Equity'})
                chart_sheet.insert_chart('A20', equity_chart)

                logger.info(f"Excel report saved to {filepath}")
                return True

        except Exception as e:
            logger.error(f"Error saving to Excel: {str(e)}", exc_info=True)
            return False

    def save_chart_image(self, fig: go.Figure, filename: str) -> Optional[str]:
        """Save chart as image and return filepath"""
        try:
            filepath = RESULTS_DIR / f"{filename}.png"

            # Convert to image
            img_bytes = to_image(fig, format='png', width=1200, height=800)

            # Save to file
            with open(filepath, 'wb') as f:
                f.write(img_bytes)

            logger.info(f"Chart image saved to {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error saving chart image: {str(e)}", exc_info=True)
            return None