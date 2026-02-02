import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from src.strategies.entry_rules import EntryRule, EntryRuleExecutor
from src.strategies.exit_rules import ExitRule, ExitRuleExecutor, ExitSignal
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
    exit_reason: str
    success: bool
    invested_capital: float  # How much capital was used for this trade

    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            'entry_date': self.entry_date.strftime('%Y-%m-%d %H:%M:%S'),
            'exit_date': self.exit_date.strftime('%Y-%m-%d %H:%M:%S'),
            'entry_price': float(self.entry_price),
            'exit_price': float(self.exit_price),
            'position_type': self.position_type,
            'quantity': float(self.quantity),
            'pnl': float(self.pnl),
            'pnl_percent': float(self.pnl_percent),
            'pattern': self.pattern,
            'exit_reason': self.exit_reason,
            'success': bool(self.success),
            'invested_capital': float(self.invested_capital)
        }


class BacktestEngine:
    """Backtesting engine for trading strategies"""

    def __init__(
        self,
        initial_capital: float = 1000000,
        position_size_pct: float = 10,
        commission: float = 0.001,
        slippage: float = 0.001
    ):
        self.initial_capital = initial_capital
        self.position_size_pct = position_size_pct
        self.commission = commission
        self.slippage = slippage
        self.reset()

    def reset(self):
        """Reset engine state"""
        self.capital = self.initial_capital  # Available capital
        self.trades: List[Trade] = []
        self.equity_curve = []
        self.position = None
        self.max_drawdown = 0
        self.peak_equity = self.initial_capital
        self.current_equity = self.initial_capital
        self.invested_capital = 0  # Capital currently invested in open position

    def run(
        self,
        df: pd.DataFrame,
        patterns_to_use: List[str],
        entry_rule: EntryRule,
        exit_rule: ExitRule,
        entry_params: Dict = None,
        exit_params: Dict = None
    ) -> Dict:
        """Run backtest on the provided data"""
        logger.info(f"Starting backtest with {len(df)} bars")

        self.reset()
        entry_executor = EntryRuleExecutor()
        exit_executor = ExitRuleExecutor(exit_rule, exit_params)

        # Add required columns
        df = df.copy()
        if 'signal' not in df.columns:
            df['signal'] = 0
        if 'pattern_name' not in df.columns:
            df['pattern_name'] = ''

        for i in range(1, len(df)):
            current_bar = df.iloc[i]
            current_date = df.index[i]

            # Get signal from pattern
            signal, pattern_name = self._get_signal(df.iloc[i-1], patterns_to_use)
            df.at[current_date, 'signal'] = signal
            df.at[current_date, 'pattern_name'] = pattern_name

            # Check for exit conditions
            if self.position:
                bars_since_entry = (current_date - self.position['entry_date']).days

                exit_signal = exit_executor.check_exit(
                    entry_price=self.position['entry_price'],
                    current_price=current_bar['Close'],
                    position_type=self.position['position_type'],
                    bars_since_entry=bars_since_entry,
                    pattern_data={'pattern_name': pattern_name, 'has_opposite_pattern': signal != 0},
                    current_bar=current_bar.to_dict()
                )

                if exit_signal.should_exit:
                    self._exit_trade(
                        date=current_date,
                        price=exit_signal.exit_price or current_bar['Close'],
                        exit_reason=exit_signal.reason
                    )

            # Check for entry conditions
            if signal != 0 and not self.position:
                pattern_data = {
                    'pattern_name': pattern_name,
                    'pattern_high': df.iloc[i-1]['High'],
                    'pattern_low': df.iloc[i-1]['Low'],
                    'pattern_close': df.iloc[i-1]['Close']
                }

                entry_price = entry_executor.execute(
                    rule=entry_rule,
                    pattern_data=pattern_data,
                    current_price=current_bar['Open'],
                    params=entry_params
                )

                self._enter_trade(
                    date=current_date,
                    price=entry_price,
                    signal=signal,
                    pattern_name=pattern_name
                )

            # Update equity curve
            self._update_equity(current_bar['Close'])
            self.equity_curve.append({
                'date': current_date,
                'equity': self.current_equity,
                'drawdown': self.max_drawdown,
                'available_capital': self.capital,
                'invested_capital': self.invested_capital
            })

        # Close any open position at the end
        if self.position:
            self._exit_trade(
                date=df.index[-1],
                price=df.iloc[-1]['Close'],
                exit_reason='end_of_data'
            )

        # Calculate metrics
        metrics = self._calculate_metrics()

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
        pattern_name: str
    ):
        """Enter a new trade"""
        position_type = 'long' if signal > 0 else 'short'

        # Apply slippage
        if position_type == 'long':
            entry_price = price * (1 + self.slippage)
        else:  # short
            entry_price = price * (1 - self.slippage)

        # Calculate position size (based on available capital)
        position_value = self.capital * (self.position_size_pct / 100)
        quantity = position_value / entry_price

        # Check if we have enough capital
        if position_value > self.capital:
            logger.warning(f"Insufficient capital for trade. Need: {position_value}, Have: {self.capital}")
            return

        self.position = {
            'entry_date': date,
            'entry_price': entry_price,
            'position_type': position_type,
            'quantity': quantity,
            'pattern': pattern_name,
            'invested_capital': position_value  # Store invested capital
        }

        # Deduct position value from available capital
        self.capital -= position_value
        self.invested_capital = position_value

        # Apply commission (on the position value)
        commission_cost = position_value * self.commission
        self.capital -= commission_cost

        logger.debug(f"Entered {position_type} trade at {entry_price:.2f} on {date}, Invested: {position_value:.2f}")

    def _exit_trade(self, date: pd.Timestamp, price: float, exit_reason: str):
        """Exit current trade"""
        if not self.position:
            return

        entry_price = self.position['entry_price']
        quantity = self.position['quantity']
        position_type = self.position['position_type']
        invested_capital = self.position['invested_capital']

        # Apply slippage
        if position_type == 'long':
            exit_price = price * (1 - self.slippage)
        else:  # short
            exit_price = price * (1 + self.slippage)

        # Calculate P&L
        if position_type == 'long':
            pl = (exit_price - entry_price) * quantity
        else:  # short
            pl = (entry_price - exit_price) * quantity

        pl_pct = (pl / invested_capital) * 100 if invested_capital > 0 else 0

        # Create trade record
        trade = Trade(
            entry_date=self.position['entry_date'],
            exit_date=date,
            entry_price=entry_price,
            exit_price=exit_price,
            position_type=position_type,
            quantity=quantity,
            pnl=pl,
            pnl_percent=pl_pct,
            pattern=self.position['pattern'],
            exit_reason=exit_reason,
            success=pl > 0,
            invested_capital=invested_capital
        )

        self.trades.append(trade)

        # Return invested capital + P&L to available capital
        self.capital += invested_capital + pl

        # Apply exit commission (on the exit value)
        exit_value = exit_price * quantity
        commission_cost = exit_value * self.commission
        self.capital -= commission_cost

        # Reset position tracking
        self.position = None
        self.invested_capital = 0

        logger.debug(f"Exited {position_type} trade. P&L: {pl:.2f} ({pl_pct:.2f}%), Reason: {exit_reason}")

    def _update_equity(self, current_price: float):
        """Update current equity value"""
        if not self.position:
            # No position, equity = available capital
            self.current_equity = self.capital
        else:
            entry_price = self.position['entry_price']
            quantity = self.position['quantity']
            position_type = self.position['position_type']
            invested_capital = self.position['invested_capital']

            # Calculate unrealized P&L
            if position_type == 'long':
                unrealized_pl = (current_price - entry_price) * quantity
            else:  # short
                unrealized_pl = (entry_price - current_price) * quantity

            # Equity = available capital + invested capital + unrealized P&L
            self.current_equity = self.capital + invested_capital + unrealized_pl

        # Update max drawdown
        if self.current_equity > self.peak_equity:
            self.peak_equity = self.current_equity

        drawdown = (self.peak_equity - self.current_equity) / self.peak_equity * 100
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown

    def _calculate_metrics(self) -> Dict:
        """Calculate comprehensive performance metrics"""
        if not self.trades:
            return {
                'initial_capital': self.initial_capital,
                'final_capital': self.capital,
                'total_return_pct': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'sharpe_ratio': 0,
                'max_drawdown': self.max_drawdown,
                'avg_trade_duration': pd.Timedelta(0),
                'total_invested': 0
            }

        trades_df = pd.DataFrame([t.to_dict() for t in self.trades])

        # Convert string dates back to datetime for calculations
        trades_df['entry_date'] = pd.to_datetime(trades_df['entry_date'])
        trades_df['exit_date'] = pd.to_datetime(trades_df['exit_date'])

        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = len(trades_df[trades_df['success'] == True])
        losing_trades = len(trades_df[trades_df['success'] == False])

        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0

        total_pnl = trades_df['pnl'].sum()
        total_return_pct = ((self.capital - self.initial_capital) / self.initial_capital) * 100

        # Calculate average invested capital per trade
        avg_invested = trades_df['invested_capital'].mean()
        total_invested = trades_df['invested_capital'].sum()

        avg_win = trades_df[trades_df['success'] == True]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['success'] == False]['pnl'].mean() if losing_trades > 0 else 0

        total_win = trades_df[trades_df['success'] == True]['pnl'].sum()
        total_loss = abs(trades_df[trades_df['success'] == False]['pnl'].sum())
        profit_factor = total_win / total_loss if total_loss > 0 else float('inf')

        # Sharpe ratio
        equity_series = pd.Series([e['equity'] for e in self.equity_curve])
        if len(equity_series) > 1:
            returns = equity_series.pct_change().dropna()
            if returns.std() > 0:
                sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0

        # Trade duration
        avg_duration = (trades_df['exit_date'] - trades_df['entry_date']).mean()

        # Additional metrics
        max_win = trades_df[trades_df['success'] == True]['pnl'].max() if winning_trades > 0 else 0
        max_loss = trades_df[trades_df['success'] == False]['pnl'].min() if losing_trades > 0 else 0

        # Calculate consecutive wins/losses
        trades_df['result_seq'] = trades_df['success'].astype(int).diff().fillna(0).cumsum()
        consecutive_wins = trades_df.groupby('result_seq')['success'].sum().max()
        consecutive_losses = (-trades_df.groupby('result_seq')['success'].sum().min()) if losing_trades > 0 else 0

        # Calculate return on invested capital
        avg_roi_per_trade = (trades_df['pnl'] / trades_df['invested_capital'] * 100).mean()

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
            'max_drawdown': self.max_drawdown,
            'avg_trade_duration': avg_duration,
            'max_win': max_win,
            'max_loss': max_loss,
            'consecutive_wins': consecutive_wins,
            'consecutive_losses': consecutive_losses,
            'long_trades': len(trades_df[trades_df['position_type'] == 'long']),
            'short_trades': len(trades_df[trades_df['position_type'] == 'short']),
            'avg_pnl_per_trade': trades_df['pnl'].mean(),
            'std_pnl': trades_df['pnl'].std(),
            'total_invested': total_invested,
            'avg_invested_per_trade': avg_invested,
            'avg_roi_per_trade': avg_roi_per_trade
        }

        # Add pattern statistics
        pattern_stats = trades_df.groupby('pattern').agg({
            'pnl': ['count', 'sum', 'mean'],
            'pnl_percent': 'mean',
            'success': 'mean',
            'invested_capital': 'mean'
        }).round(2)

        metrics['pattern_statistics'] = pattern_stats.to_dict()

        return metrics