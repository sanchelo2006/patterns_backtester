import pandas as pd
from typing import Dict, List
from src.utils.logger import get_logger

logger = get_logger('app')


class MetricsCalculator:
    """Calculate comprehensive performance metrics"""

    @staticmethod
    def calculate_detailed_metrics(trades: List, equity_curve: pd.DataFrame) -> Dict:
        """Calculate detailed performance metrics"""

        trades_df = pd.DataFrame([t.__dict__ for t in trades])

        metrics = {}

        if len(trades_df) == 0:
            return metrics

        # Trade statistics
        metrics['total_trades'] = len(trades_df)
        metrics['long_trades'] = len(trades_df[trades_df['position_type'] == 'long'])
        metrics['short_trades'] = len(trades_df[trades_df['position_type'] == 'short'])

        metrics['winning_trades'] = len(trades_df[trades_df['success'] == True])
        metrics['losing_trades'] = len(trades_df[trades_df['success'] == False])
        metrics['win_rate'] = metrics['winning_trades'] / metrics['total_trades'] * 100

        # P&L statistics
        metrics['total_pnl'] = trades_df['pnl'].sum()
        metrics['avg_pnl'] = trades_df['pnl'].mean()
        metrics['median_pnl'] = trades_df['pnl'].median()

        winning_trades = trades_df[trades_df['success'] == True]
        losing_trades = trades_df[trades_df['success'] == False]

        metrics['avg_win'] = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        metrics['avg_loss'] = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
        metrics['largest_win'] = winning_trades['pnl'].max() if len(winning_trades) > 0 else 0
        metrics['largest_loss'] = losing_trades['pnl'].min() if len(losing_trades) > 0 else 0

        metrics['profit_factor'] = abs(winning_trades['pnl'].sum()) / abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else float('inf')

        # Risk metrics
        returns = trades_df['pnl_percent'] / 100
        metrics['sharpe_ratio'] = returns.mean() / returns.std() * (252 ** 0.5) if len(returns) > 1 and returns.std() != 0 else 0

        # Maximum consecutive wins/losses
        trades_df['result'] = trades_df['success'].apply(lambda x: 1 if x else -1)
        metrics['max_consecutive_wins'] = MetricsCalculator._max_consecutive(trades_df, 1)
        metrics['max_consecutive_losses'] = MetricsCalculator._max_consecutive(trades_df, -1)

        # Pattern effectiveness
        pattern_stats = trades_df.groupby('pattern').agg({
            'pnl': ['count', 'sum', 'mean'],
            'success': 'mean'
        }).round(2)

        metrics['pattern_statistics'] = pattern_stats.to_dict()

        return metrics

    @staticmethod
    def _max_consecutive(series: pd.DataFrame, value: int) -> int:
        """Calculate maximum consecutive occurrences"""
        max_count = 0
        current_count = 0

        for val in series['result']:
            if val == value:
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0

        return max_count

    @staticmethod
    def prepare_excel_report(backtest_results: Dict, filepath: str):
        """Save backtest results to Excel"""
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Save trades
                trades_df = pd.DataFrame([t.__dict__ for t in backtest_results['trades']])
                trades_df.to_excel(writer, sheet_name='Trades', index=False)

                # Save equity curve
                backtest_results['equity_curve'].to_excel(writer, sheet_name='Equity Curve', index=False)

                # Save metrics
                metrics_df = pd.DataFrame([backtest_results['metrics']])
                metrics_df.to_excel(writer, sheet_name='Metrics', index=False)

                # Save pattern statistics
                if 'pattern_statistics' in backtest_results['metrics']:
                    pattern_df = pd.DataFrame(backtest_results['metrics']['pattern_statistics'])
                    pattern_df.to_excel(writer, sheet_name='Pattern Stats')

                logger.info(f"Report saved to {filepath}")

        except Exception as e:
            logger.error(f"Error saving Excel report: {str(e)}", exc_info=True)
            raise