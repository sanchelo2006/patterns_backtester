import mplfinance as mpf
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pandas as pd
import numpy as np
import talib
from typing import List, Dict, Optional
from src.backtest.engine import Trade
from src.utils.logger import get_logger

logger = get_logger('app')


class InteractiveChartWindow(QMainWindow):
    """Interactive chart window using mplfinance"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Interactive Candlestick Chart")
        self.setGeometry(100, 100, 1400, 900)

        self.df = None
        self.trades = None
        self.title = ""

        # Indicator visibility
        self.show_volume = True
        self.show_macd = False
        self.show_rsi = False
        self.show_bollinger = False

        self.init_ui()

    def init_ui(self):
        """Initialize user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Control panel
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel)

        # Create matplotlib figure
        self.figure = Figure(figsize=(14, 10), dpi=100)
        self.canvas = FigureCanvas(self.figure)

        # Navigation toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)

        # Add canvas to layout
        layout.addWidget(self.canvas)

        # Add legend
        legend_panel = self.create_legend_panel()
        layout.addWidget(legend_panel)

    def create_control_panel(self) -> QWidget:
        """Create control panel for indicators"""
        panel = QGroupBox("Chart Controls")
        layout = QHBoxLayout()

        # Indicator toggles
        self.volume_check = QCheckBox("Volume")
        self.volume_check.setChecked(True)
        self.volume_check.toggled.connect(self.toggle_volume)
        layout.addWidget(self.volume_check)

        self.macd_check = QCheckBox("MACD")
        self.macd_check.toggled.connect(self.toggle_macd)
        layout.addWidget(self.macd_check)

        self.rsi_check = QCheckBox("RSI")
        self.rsi_check.toggled.connect(self.toggle_rsi)
        layout.addWidget(self.rsi_check)

        self.bb_check = QCheckBox("Bollinger Bands")
        self.bb_check.toggled.connect(self.toggle_bollinger)
        layout.addWidget(self.bb_check)

        layout.addStretch()

        # Style buttons
        style_label = QLabel("Chart Style:")
        layout.addWidget(style_label)

        self.style_combo = QComboBox()
        self.style_combo.addItems(['default', 'binance', 'blueskies', 'brasil',
                                  'charles', 'checkers', 'classic', 'yahoo'])
        self.style_combo.currentTextChanged.connect(self.change_style)
        layout.addWidget(self.style_combo)

        panel.setLayout(layout)
        return panel

    def create_legend_panel(self) -> QWidget:
        """Create legend panel for trade markers"""
        panel = QGroupBox("Trade Marker Legend")
        layout = QGridLayout()

        # Long positions
        layout.addWidget(QLabel("<b>Long Positions:</b>"), 0, 0, 1, 2)

        # Profit long
        profit_long_label = QLabel("▲ Green: Enter Profit Long")
        profit_long_label.setStyleSheet("color: green; font-weight: bold;")
        layout.addWidget(profit_long_label, 1, 0)

        exit_profit_long_label = QLabel("▲ Red: Exit Profit Long")
        exit_profit_long_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(exit_profit_long_label, 1, 1)

        # Loss long
        loss_long_label = QLabel("▼ Yellow: Enter Loss Long")
        loss_long_label.setStyleSheet("color: #FFD700; font-weight: bold;")
        layout.addWidget(loss_long_label, 2, 0)

        exit_loss_long_label = QLabel("▼ Blue: Exit Loss Long")
        exit_loss_long_label.setStyleSheet("color: blue; font-weight: bold;")
        layout.addWidget(exit_loss_long_label, 2, 1)

        # Short positions
        layout.addWidget(QLabel("<b>Short Positions:</b>"), 3, 0, 1, 2)

        # Profit short
        profit_short_label = QLabel("■ Red: Enter Profit Short")
        profit_short_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(profit_short_label, 4, 0)

        exit_profit_short_label = QLabel("■ Green: Exit Profit Short")
        exit_profit_short_label.setStyleSheet("color: green; font-weight: bold;")
        layout.addWidget(exit_profit_short_label, 4, 1)

        # Loss short
        loss_short_label = QLabel("■ Yellow: Enter Loss Short")
        loss_short_label.setStyleSheet("color: #FFD700; font-weight: bold;")
        layout.addWidget(loss_short_label, 5, 0)

        exit_loss_short_label = QLabel("■ Blue: Exit Loss Short")
        exit_loss_short_label.setStyleSheet("color: blue; font-weight: bold;")
        layout.addWidget(exit_loss_short_label, 5, 1)

        panel.setLayout(layout)
        return panel

    def set_data(self, df: pd.DataFrame, trades: List[Trade], title: str = ""):
        """Set chart data"""
        self.df = df.copy()
        self.trades = trades
        self.title = title
        self.update_chart()

    def update_chart(self):
        """Update the chart with current settings"""
        if self.df is None:
            return

        # Clear previous plot
        self.figure.clear()

        # Prepare data for mplfinance
        plot_df = self.df.copy()

        # Ensure index is datetime
        if not isinstance(plot_df.index, pd.DatetimeIndex):
            plot_df.index = pd.to_datetime(plot_df.index)

        # Add columns for mplfinance if missing
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_cols:
            if col not in plot_df.columns:
                if col == 'Volume':
                    plot_df['Volume'] = 0
                else:
                    plot_df[col] = plot_df['Close']

        # Prepare additional plots
        addplots = []

        # Add Bollinger Bands if selected
        if self.show_bollinger:
            bb_upper, bb_middle, bb_lower = talib.BBANDS(
                plot_df['Close'].values,
                timeperiod=20,
                nbdevup=2,
                nbdevdn=2,
                matype=0
            )

            bb_ap1 = mpf.make_addplot(bb_upper, color='blue', alpha=0.5)
            bb_ap2 = mpf.make_addplot(bb_middle, color='orange', alpha=0.5)
            bb_ap3 = mpf.make_addplot(bb_lower, color='blue', alpha=0.5)
            addplots.extend([bb_ap1, bb_ap2, bb_ap3])

        # Add trade markers
        trade_markers = self.create_trade_markers(plot_df)
        if trade_markers:
            addplots.extend(trade_markers)

        # Style selection
        style = self.style_combo.currentText()

        # Create subplot configuration based on selected indicators
        panel_ratios = None
        if self.show_volume:
            panel_ratios = (3, 1)

        # Plot candlestick chart
        mpf.plot(
            plot_df,
            type='candle',
            volume=self.show_volume,
            style=style,
            title=self.title,
            ylabel='Price',
            ylabel_lower='Volume',
            addplot=addplots if addplots else None,
            panel_ratios=panel_ratios,
            figratio=(14, 10),
            figscale=1.2,
            returnfig=True,
            warn_too_much_data=10000,
            datetime_format='%Y-%m-%d',
            xrotation=45,
            fig=self.figure
        )

        # Adjust layout
        self.figure.tight_layout()
        self.canvas.draw()

    def create_trade_markers(self, df) -> list:
        """Create trade markers for mplfinance"""
        if not self.trades:
            return []

        # Prepare series for entry and exit points
        entry_prices = pd.Series(index=df.index, dtype=float)
        exit_prices = pd.Series(index=df.index, dtype=float)
        entry_markers = pd.Series(index=df.index, dtype=str)
        exit_markers = pd.Series(index=df.index, dtype=str)

        for trade in self.trades:
            # Find closest index for entry and exit dates
            entry_idx = self.find_date_index(df, trade.entry_date)
            exit_idx = self.find_date_index(df, trade.exit_date)

            if entry_idx is not None and entry_idx < len(df):
                entry_prices.iloc[entry_idx] = trade.entry_price

                # Determine marker
                if trade.position_type == 'long':
                    if trade.success:
                        entry_markers.iloc[entry_idx] = '^'
                    else:
                        entry_markers.iloc[entry_idx] = 'v'
                else:  # short
                    entry_markers.iloc[entry_idx] = 's'

            if exit_idx is not None and exit_idx < len(df):
                exit_prices.iloc[exit_idx] = trade.exit_price

                # Determine marker
                if trade.position_type == 'long':
                    if trade.success:
                        exit_markers.iloc[exit_idx] = '^'
                    else:
                        exit_markers.iloc[exit_idx] = 'v'
                else:  # short
                    exit_markers.iloc[exit_idx] = 's'

        markers = []

        # Create entry markers addplot
        if not entry_prices.isna().all():
            entry_colors = []
            for idx in entry_prices.index:
                if pd.isna(entry_prices[idx]):
                    continue
                # Find trade for this entry
                trade = self.find_trade_by_entry_date(idx)
                if trade:
                    if trade.position_type == 'long':
                        if trade.success:
                            entry_colors.append('green')
                        else:
                            entry_colors.append('yellow')
                    else:  # short
                        if trade.success:
                            entry_colors.append('red')
                        else:
                            entry_colors.append('yellow')

            entry_ap = mpf.make_addplot(
                entry_prices,
                type='scatter',
                markersize=100,
                marker=entry_markers.replace('', np.nan),
                color=entry_colors if entry_colors else 'green',
                alpha=0.8
            )
            markers.append(entry_ap)

        # Create exit markers addplot
        if not exit_prices.isna().all():
            exit_colors = []
            for idx in exit_prices.index:
                if pd.isna(exit_prices[idx]):
                    continue
                # Find trade for this exit
                trade = self.find_trade_by_exit_date(idx)
                if trade:
                    if trade.position_type == 'long':
                        if trade.success:
                            exit_colors.append('red')
                        else:
                            exit_colors.append('blue')
                    else:  # short
                        if trade.success:
                            exit_colors.append('green')
                        else:
                            exit_colors.append('blue')

            exit_ap = mpf.make_addplot(
                exit_prices,
                type='scatter',
                markersize=80,
                marker=exit_markers.replace('', np.nan),
                color=exit_colors if exit_colors else 'red',
                alpha=0.8
            )
            markers.append(exit_ap)

        return markers

    def find_date_index(self, df, date):
        """Find the index of a date in the dataframe"""
        try:
            # Convert date to pandas Timestamp if needed
            if not isinstance(date, pd.Timestamp):
                date = pd.Timestamp(date)

            # Find exact match
            for i, idx in enumerate(df.index):
                if idx.date() == date.date():
                    return i

            # Find closest date
            time_diff = abs(df.index - date)
            if len(time_diff) > 0:
                return time_diff.argmin()

            return None

        except Exception as e:
            logger.error(f"Error finding date index: {str(e)}")
            return None

    def find_trade_by_entry_date(self, date):
        """Find trade by entry date"""
        for trade in self.trades:
            if trade.entry_date.date() == date.date():
                return trade
        return None

    def find_trade_by_exit_date(self, date):
        """Find trade by exit date"""
        for trade in self.trades:
            if trade.exit_date.date() == date.date():
                return trade
        return None

    def toggle_volume(self, checked: bool):
        """Toggle volume display"""
        self.show_volume = checked
        self.update_chart()

    def toggle_macd(self, checked: bool):
        """Toggle MACD display"""
        self.show_macd = checked
        # Note: MACD would need separate panel
        self.update_chart()

    def toggle_rsi(self, checked: bool):
        """Toggle RSI display"""
        self.show_rsi = checked
        # Note: RSI would need separate panel
        self.update_chart()

    def toggle_bollinger(self, checked: bool):
        """Toggle Bollinger Bands display"""
        self.show_bollinger = checked
        self.update_chart()

    def change_style(self, style_name: str):
        """Change chart style"""
        self.update_chart()