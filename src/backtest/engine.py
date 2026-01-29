import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from src.utils.logger import get_logger

logger = get_logger('app')


@dataclass
class Trade:
    """Trade data class"""
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_price: float
    exit_price: float
    position_type: str  # 'long' or 'short'
    quantity: float
    pnl: float
    pnl_percent: float
    pattern: str
    success: bool


class BacktestEngine:
    """Backtesting engine for trading strategies"""

    def __init__(
        self,
        initial_capital: float = 1000000,
        position_size_pct: float = 10,
        commission: float = 0.001
    ):
        self.initial_capital = initial_capital
        self.position_size_pct = position_size_pct
        self.commission = commission
        self.capital = initial_capital
        self.trades: List[Trade] = []
        self.equity_curve = []
        self.position = None

    def run(
        self,
        df: pd.DataFrame,
        patterns_to_use: List[str]
    ) -> Dict:
        """Run backtest on the provided data"""
        logger.info(f"Starting backtest with {len(df)} bars")

        self.capital = self.initial_capital
        self.trades = []
        self.equity_curve = []
        self.position = None

        # Add required columns if they don't exist
        for col in ['signal', 'pattern_name']:
            if col not in df.columns:
                df[col] = 0 if col == 'signal' else ''

        # Detect patterns and generate signals
        for i in range(1, len(df)):
            current_bar = df.iloc[i]
            prev_bar = df.iloc[i-1]

            # Get signal from pattern detector
            signal, pattern_name = self._get_signal(prev_bar, patterns_to_use)

            df.at[df.index[i], 'signal'] = signal
            df.at[df.index[i], 'pattern_name'] = pattern_name

            # Check for exit conditions
            if self.position:
                self._check_exit(current_bar, df.index[i])

            # Check for entry conditions
            if signal != 0 and not self.position:
                self._enter_trade(
                    df.index[i],
                    current_bar['Close'],
                    signal,
                    pattern_name
                )

            # Update equity curve
            self.equity_curve.append({
                'date': df.index[i],
                'equity': self._calculate_equity(current_bar['Close'])
            })

        # Close any open position at the end
        if self.position:
            self._exit_trade(
                df.index[-1],
                df.iloc[-1]['Close'],
                'end_of_data'
            )

        # Calculate metrics
        metrics = self._calculate_metrics(df)

        logger.info(f"Backtest completed. {len(self.trades)} trades executed")
        return {
            'trades': self.trades,
            'equity_curve': pd.DataFrame(self.equity_curve),
            'metrics': metrics,
            'df': df
        }

    def _get_signal(self, row: pd.Series, patterns_to_use: List[str]) -> Tuple[int, str]:
        """Get trading signal from row"""
        for pattern in patterns_to_use:
            if pattern in row and row[pattern] != 0:
                if row[pattern] > 0:
                    return 1, pattern  # Buy signal
                elif row[pattern] < 0:
                    return -1, pattern  # Sell signal
        return 0, ''

    def _enter_trade(
        self,
        date: pd.Timestamp,
        price: float,
        signal: int,
        pattern: str
    ):
        """Enter a new trade"""
        position_type = 'long' if signal > 0 else 'short'

        # Calculate position size
        position_value = self.capital * (self.position_size_pct / 100)
        quantity = position_value / price

        self.position = {
            'entry_date': date,
            'entry_price': price,
            'position_type': position_type,
            'quantity': quantity,
            'pattern': pattern
        }

        # Apply commission
        self.capital -= position_value * self.commission

        logger.debug(f"Entered {position_type} trade at {price} on {date}")

    def _check_exit(self, current_bar: pd.Series, date: pd.Timestamp):
        """Check exit conditions"""
        if not self.position:
            return

        current_price = current_bar['Close']
        entry_price = self.position['entry_price']

        # Calculate profit/loss
        if self.position['position_type'] == 'long':
            pl = (current_price - entry_price) * self.position['quantity']
        else:  # short
            pl = (entry_price - current_price) * self.position['quantity']

        pl_pct = pl / (entry_price * self.position['quantity']) * 100

        # Exit conditions (simplified - could add stop loss/take profit)
        # For now, exit on opposite signal or after 20 bars
        days_in_trade = (date - self.position['entry_date']).days

        if days_in_trade >= 20:
            self._exit_trade(date, current_price, 'time_exit', pl, pl_pct)

    def _exit_trade(
        self,
        date: pd.Timestamp,
        price: float,
        exit_reason: str,
        pl: Optional[float] = None,
        pl_pct: Optional[float] = None
    ):
        """Exit current trade"""
        if not self.position:
            return

        # Calculate P&L if not provided
        if pl is None:
            entry_price = self.position['entry_price']
            quantity = self.position['quantity']

            if self.position['position_type'] == 'long':
                pl = (price - entry_price) * quantity
            else:  # short
                pl = (entry_price - price) * quantity

            pl_pct = pl / (entry_price * quantity) * 100

        # Create trade record
        trade = Trade(
            entry_date=self.position['entry_date'],
            exit_date=date,
            entry_price=self.position['entry_price'],
            exit_price=price,
            position_type=self.position['position_type'],
            quantity=self.position['quantity'],
            pnl=pl,
            pnl_percent=pl_pct,
            pattern=self.position['pattern'],
            success=pl > 0
        )

        self.trades.append(trade)

        # Update capital
        self.capital += self.position['entry_price'] * self.position['quantity'] + pl
        self.capital -= self.position['entry_price'] * self.position['quantity'] * self.commission

        logger.debug(f"Exited {self.position['position_type']} trade. P&L: {pl:.2f}")
        self.position = None

    def _calculate_equity(self, current_price: float) -> float:
        """Calculate current equity"""
        if not self.position:
            return self.capital

        entry_price = self.position['entry_price']
        quantity = self.position['quantity']

        if self.position['position_type'] == 'long':
            position_value = current_price * quantity
        else:  # short
            # For short, value decreases as price goes down
            price_diff = entry_price - current_price
            position_value = entry_price * quantity + price_diff * quantity

        return self.capital + position_value - (entry_price * quantity)

    def _calculate_metrics(self, df: pd.DataFrame) -> Dict:
        """Calculate performance metrics"""
        if not self.trades:
            return {}

        trades_df = pd.DataFrame([t.__dict__ for t in self.trades])

        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = len(trades_df[trades_df['success'] == True])
        losing_trades = len(trades_df[trades_df['success'] == False])

        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        total_pnl = trades_df['pnl'].sum()
        total_return_pct = (self.capital - self.initial_capital) / self.initial_capital * 100

        avg_win = trades_df[trades_df['success'] == True]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['success'] == False]['pnl'].mean() if losing_trades > 0 else 0

        profit_factor = abs(avg_win * winning_trades) / abs(avg_loss * losing_trades) if losing_trades > 0 else float('inf')

        # Sharpe ratio (simplified)
        equity_series = pd.Series([e['equity'] for e in self.equity_curve])
        returns = equity_series.pct_change().dropna()
        sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if len(returns) > 1 and returns.std() != 0 else 0

        # Maximum drawdown
        equity_df = pd.DataFrame(self.equity_curve)
        equity_df['peak'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak'] * 100
        max_drawdown = equity_df['drawdown'].min()

        metrics = {
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'total_return_pct': total_return_pct,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'avg_trade_duration': trades_df['exit_date'] - trades_df['entry_date']
        }

        return metrics