import mplfinance as mpf
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
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


class SimpleChartWindow(QMainWindow):
    """Simple but reliable chart window"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Candlestick Chart")
        self.setGeometry(100, 100, 1400, 900)

        self.df = None
        self.trades = None
        self.title = ""

        # Indicator visibility
        self.show_volume = True
        self.show_macd = False
        self.show_rsi = False

        self.init_ui()

    def init_ui(self):
        """Initialize user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Control panel
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel)

        # Create matplotlib figure and canvas
        self.figure = Figure(figsize=(14, 9), dpi=100)
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

        layout.addStretch()

        # Style selection removed as requested

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
        self.debug_data_structure()
        self.update_chart()

    def debug_data_structure(self):
        """Debug method to check data structure"""
        if self.df is not None:
            print("\n=== DEBUG DATA STRUCTURE ===")
            print(f"Data shape: {self.df.shape}")
            print(f"Columns: {self.df.columns.tolist()}")
            print(f"Index type: {type(self.df.index)}")
            if len(self.df) > 0:
                print(f"Sample data (first 5 rows):")
                if all(col in self.df.columns for col in ['Open', 'High', 'Low', 'Close']):
                    print(self.df[['Open', 'High', 'Low', 'Close']].head())
                else:
                    print("Missing OHLC columns!")
            print("============================\n")

    def update_chart(self):
        """Update the chart with current settings"""
        if self.df is None:
            return

        # Clear previous plot
        self.figure.clear()

        # Prepare data for mplfinance
        plot_df = self.df.copy()

        # Ensure we have the required OHLCV columns
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']

        # Check if we have OHLC data
        if not all(col in plot_df.columns for col in ['Open', 'High', 'Low', 'Close']):
            # If we don't have proper OHLC data, create from Close price
            logger.warning("Creating OHLC data from Close price")
            if 'Close' in plot_df.columns:
                plot_df['Open'] = plot_df['Close'].shift(1).fillna(plot_df['Close'])
                plot_df['High'] = plot_df[['Open', 'Close']].max(axis=1)
                plot_df['Low'] = plot_df[['Open', 'Close']].min(axis=1)
            else:
                logger.error("No price data available")
                return

        # Add Volume if missing
        if 'Volume' not in plot_df.columns:
            plot_df['Volume'] = 0

        # Ensure index is datetime
        if not isinstance(plot_df.index, pd.DatetimeIndex):
            try:
                plot_df.index = pd.to_datetime(plot_df.index)
            except:
                # Create a dummy datetime index
                plot_df.index = pd.date_range(start='2020-01-01', periods=len(plot_df), freq='D')

        # Convert to float
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            plot_df[col] = pd.to_numeric(plot_df[col], errors='coerce')

        # Drop NaN values
        plot_df = plot_df.dropna(subset=['Open', 'High', 'Low', 'Close'])

        # Sort by index
        plot_df = plot_df.sort_index()

        # Calculate panel configuration
        panel_count = 1  # Always have price panel
        if self.show_volume:
            panel_count += 1
        if self.show_macd:
            panel_count += 1
        if self.show_rsi:
            panel_count += 1

        # Prepare addplots
        addplots = []

        # Calculate technical indicators
        if self.show_macd and len(plot_df) > 26:
            try:
                macd, macd_signal, macd_hist = talib.MACD(
                    plot_df['Close'].values,
                    fastperiod=12,
                    slowperiod=26,
                    signalperiod=9
                )

                # Determine panel index for MACD
                macd_panel = panel_count - 1
                if self.show_rsi:
                    macd_panel -= 1

                # Create MACD addplot with panel parameter in constructor
                macd_ap = mpf.make_addplot(macd, panel=macd_panel,
                                        color='blue', width=0.7, label='MACD')
                signal_ap = mpf.make_addplot(macd_signal, panel=macd_panel,
                                        color='red', width=0.7, label='Signal')
                hist_ap = mpf.make_addplot(macd_hist, type='bar', panel=macd_panel,
                                        color='gray', alpha=0.5, width=0.7, label='Histogram')
                addplots.extend([macd_ap, signal_ap, hist_ap])
            except Exception as e:
                logger.error(f"Error calculating MACD: {str(e)}")
                self.show_macd = False

        if self.show_rsi and len(plot_df) > 14:
            try:
                rsi = talib.RSI(plot_df['Close'].values, timeperiod=14)
                rsi_panel = panel_count - 1

                # Create RSI addplot with panel parameter in constructor
                rsi_ap = mpf.make_addplot(rsi, panel=rsi_panel, color='purple',
                                        width=0.7, label='RSI', ylabel='RSI')
                addplots.append(rsi_ap)

                # Add RSI levels
                rsi_30 = mpf.make_addplot([30] * len(plot_df), panel=rsi_panel,
                                        color='red', width=0.5, alpha=0.3)
                rsi_70 = mpf.make_addplot([70] * len(plot_df), panel=rsi_panel,
                                        color='green', width=0.5, alpha=0.3)
                addplots.extend([rsi_30, rsi_70])
            except Exception as e:
                logger.error(f"Error calculating RSI: {str(e)}")
                self.show_rsi = False

        # Create trade markers (they go in panel 0 - the main price chart)
        trade_markers_dicts = self.create_trade_markers(plot_df)
        if trade_markers_dicts:
            for marker_dict in trade_markers_dicts:
                # Convert dictionary to mplfinance addplot
                marker_ap = mpf.make_addplot(
                    marker_dict['data'],
                    type=marker_dict['type'],
                    markersize=marker_dict['markersize'],
                    marker=marker_dict['marker'],
                    color=marker_dict['color'],
                    alpha=marker_dict['alpha'],
                    panel=marker_dict['panel']
                )
                addplots.append(marker_ap)

        # Determine panel ratios
        panel_ratios = []
        if self.show_volume:
            panel_ratios.append(3)  # Price panel
            panel_ratios.append(1)  # Volume panel
        else:
            panel_ratios.append(3)  # Price panel only

        if self.show_macd:
            panel_ratios.append(1)  # MACD panel

        if self.show_rsi:
            panel_ratios.append(1)  # RSI panel

        try:
            # Create figure with mplfinance
            fig, axes = mpf.plot(
                plot_df,
                type='candle',
                volume=self.show_volume,
                style='yahoo',
                title=self.title,
                ylabel='Price',
                ylabel_lower='Volume' if self.show_volume else '',
                addplot=addplots if addplots else None,
                panel_ratios=tuple(panel_ratios),
                figratio=(14, 9),
                figscale=1.2,
                returnfig=True,
                warn_too_much_data=len(plot_df) > 1000,
                datetime_format='%Y-%m-%d',
                xrotation=45,
                tight_layout=True
            )

            # Clear our figure and copy everything from mplfinance figure
            self.figure.clear()

            # Get all axes from mplfinance figure
            mpl_axes = fig.get_axes()

            # Copy each axis to our figure
            for i, ax in enumerate(mpl_axes):
                if i == 0:
                    # Main price chart
                    new_ax = self.figure.add_subplot(len(mpl_axes), 1, i+1)
                else:
                    # Indicator charts (share x-axis with main chart)
                    new_ax = self.figure.add_subplot(len(mpl_axes), 1, i+1, sharex=self.figure.axes[0])

                # Copy all lines
                for line in ax.get_lines():
                    new_ax.add_line(line)

                # Copy collections (bars, scatter points, etc.)
                for collection in ax.collections:
                    new_ax.add_collection(collection)

                # Copy patches (rectangles for candlesticks)
                for patch in ax.patches:
                    new_ax.add_patch(patch)

                # Copy limits and labels
                new_ax.set_xlim(ax.get_xlim())
                new_ax.set_ylim(ax.get_ylim())
                new_ax.set_xlabel(ax.get_xlabel())
                new_ax.set_ylabel(ax.get_ylabel())
                if ax.get_title():
                    new_ax.set_title(ax.get_title())

                # Copy grid
                new_ax.grid(ax.get_grid())

                # Copy legend if exists
                if ax.get_legend():
                    handles, labels = ax.get_legend_handles_labels()
                    new_ax.legend(handles, labels)

            # Set overall figure title
            if self.title:
                self.figure.suptitle(self.title)

            # Close mplfinance figure
            plt.close(fig)

            # Adjust layout
            self.figure.tight_layout(rect=[0, 0.03, 1, 0.97])

            # Update canvas
            self.canvas.draw()

        except Exception as e:
            logger.error(f"Error plotting chart with mplfinance: {str(e)}")
            # Fallback to manual plotting
            self.manual_plot(plot_df)

    def create_trade_markers(self, plot_df) -> list:
        """Create trade markers for mplfinance"""
        if not self.trades:
            return []

        markers = []

        # Create separate series for different marker types
        entry_long_profit_prices = pd.Series(index=plot_df.index, dtype=float)
        entry_long_loss_prices = pd.Series(index=plot_df.index, dtype=float)
        exit_long_profit_prices = pd.Series(index=plot_df.index, dtype=float)
        exit_long_loss_prices = pd.Series(index=plot_df.index, dtype=float)

        entry_short_profit_prices = pd.Series(index=plot_df.index, dtype=float)
        entry_short_loss_prices = pd.Series(index=plot_df.index, dtype=float)
        exit_short_profit_prices = pd.Series(index=plot_df.index, dtype=float)
        exit_short_loss_prices = pd.Series(index=plot_df.index, dtype=float)

        for trade in self.trades:
            # Find indices
            entry_idx = self.find_date_index(plot_df, trade.entry_date)
            exit_idx = self.find_date_index(plot_df, trade.exit_date)

            if entry_idx is not None and entry_idx < len(plot_df):
                if trade.position_type == 'long':
                    if trade.success:
                        entry_long_profit_prices.iloc[entry_idx] = trade.entry_price
                    else:
                        entry_long_loss_prices.iloc[entry_idx] = trade.entry_price
                else:  # short
                    if trade.success:
                        entry_short_profit_prices.iloc[entry_idx] = trade.entry_price
                    else:
                        entry_short_loss_prices.iloc[entry_idx] = trade.entry_price

            if exit_idx is not None and exit_idx < len(plot_df):
                if trade.position_type == 'long':
                    if trade.success:
                        exit_long_profit_prices.iloc[exit_idx] = trade.exit_price
                    else:
                        exit_long_loss_prices.iloc[exit_idx] = trade.exit_price
                else:  # short
                    if trade.success:
                        exit_short_profit_prices.iloc[exit_idx] = trade.exit_price
                    else:
                        exit_short_loss_prices.iloc[exit_idx] = trade.exit_price

        # Create marker dictionaries with panel=0 (main price chart)
        if not entry_long_profit_prices.isna().all():
            markers.append({
                'data': entry_long_profit_prices,
                'type': 'scatter',
                'markersize': 100,
                'marker': '^',
                'color': 'green',
                'alpha': 0.8,
                'panel': 0
            })

        if not entry_long_loss_prices.isna().all():
            markers.append({
                'data': entry_long_loss_prices,
                'type': 'scatter',
                'markersize': 100,
                'marker': 'v',
                'color': 'yellow',
                'alpha': 0.8,
                'panel': 0
            })

        if not exit_long_profit_prices.isna().all():
            markers.append({
                'data': exit_long_profit_prices,
                'type': 'scatter',
                'markersize': 80,
                'marker': '^',
                'color': 'red',
                'alpha': 0.8,
                'panel': 0
            })

        if not exit_long_loss_prices.isna().all():
            markers.append({
                'data': exit_long_loss_prices,
                'type': 'scatter',
                'markersize': 80,
                'marker': 'v',
                'color': 'blue',
                'alpha': 0.8,
                'panel': 0
            })

        if not entry_short_profit_prices.isna().all():
            markers.append({
                'data': entry_short_profit_prices,
                'type': 'scatter',
                'markersize': 100,
                'marker': 's',
                'color': 'red',
                'alpha': 0.8,
                'panel': 0
            })

        if not entry_short_loss_prices.isna().all():
            markers.append({
                'data': entry_short_loss_prices,
                'type': 'scatter',
                'markersize': 100,
                'marker': 's',
                'color': 'yellow',
                'alpha': 0.8,
                'panel': 0
            })

        if not exit_short_profit_prices.isna().all():
            markers.append({
                'data': exit_short_profit_prices,
                'type': 'scatter',
                'markersize': 80,
                'marker': 's',
                'color': 'green',
                'alpha': 0.8,
                'panel': 0
            })

        if not exit_short_loss_prices.isna().all():
            markers.append({
                'data': exit_short_loss_prices,
                'type': 'scatter',
                'markersize': 80,
                'marker': 's',
                'color': 'blue',
                'alpha': 0.8,
                'panel': 0
            })

        return markers

    def manual_plot(self, plot_df):
        """Manual plotting when mplfinance fails"""
        # Calculate number of panels needed
        num_panels = 1  # Always have price chart
        if self.show_volume:
            num_panels += 1
        if self.show_macd:
            num_panels += 1
        if self.show_rsi:
            num_panels += 1

        current_panel = 1

        # Create price chart
        ax_price = self.figure.add_subplot(num_panels, 1, current_panel)
        current_panel += 1

        # Plot candlesticks manually
        for i, (idx, row) in enumerate(plot_df.iterrows()):
            # Plot the wick (high-low line)
            ax_price.plot([i, i], [row['Low'], row['High']], color='black', linewidth=1)

            # Plot the body
            if row['Close'] >= row['Open']:
                # Bullish candle - green
                color = 'green'
                bottom = row['Open']
                height = row['Close'] - row['Open']
            else:
                # Bearish candle - red
                color = 'red'
                bottom = row['Close']
                height = row['Open'] - row['Close']

            # Draw the body rectangle
            ax_price.bar(i, height, bottom=bottom, color=color, width=0.6, edgecolor='black')

        # Plot trade markers
        self.plot_trade_markers_manual(ax_price, plot_df)

        # Set labels and title
        ax_price.set_title(self.title)
        ax_price.set_ylabel('Price')
        ax_price.grid(True, alpha=0.3)

        # Plot volume if enabled
        if self.show_volume and 'Volume' in plot_df.columns:
            ax_volume = self.figure.add_subplot(num_panels, 1, current_panel, sharex=ax_price)
            current_panel += 1

            # Plot volume bars
            ax_volume.bar(range(len(plot_df)), plot_df['Volume'].values,
                         color=['green' if plot_df['Close'].iloc[i] >= plot_df['Open'].iloc[i] else 'red'
                                for i in range(len(plot_df))],
                         width=0.6, alpha=0.5)
            ax_volume.set_ylabel('Volume')
            ax_volume.grid(True, alpha=0.3)

        # Plot MACD if enabled
        if self.show_macd and len(plot_df) > 26:
            ax_macd = self.figure.add_subplot(num_panels, 1, current_panel, sharex=ax_price)
            current_panel += 1

            try:
                macd, macd_signal, macd_hist = talib.MACD(
                    plot_df['Close'].values,
                    fastperiod=12,
                    slowperiod=26,
                    signalperiod=9
                )

                ax_macd.plot(macd, label='MACD', color='blue', linewidth=1)
                ax_macd.plot(macd_signal, label='Signal', color='red', linewidth=1)

                # Plot histogram
                colors = ['green' if val >= 0 else 'red' for val in macd_hist]
                ax_macd.bar(range(len(macd_hist)), macd_hist, color=colors, alpha=0.5, width=0.6)

                ax_macd.set_ylabel('MACD')
                ax_macd.legend()
                ax_macd.grid(True, alpha=0.3)
            except Exception as e:
                logger.error(f"Error plotting MACD manually: {str(e)}")

        # Plot RSI if enabled
        if self.show_rsi and len(plot_df) > 14:
            ax_rsi = self.figure.add_subplot(num_panels, 1, current_panel, sharex=ax_price)

            try:
                rsi = talib.RSI(plot_df['Close'].values, timeperiod=14)
                ax_rsi.plot(rsi, label='RSI', color='purple', linewidth=1)
                ax_rsi.axhline(y=30, color='red', linestyle='--', alpha=0.5)
                ax_rsi.axhline(y=70, color='green', linestyle='--', alpha=0.5)
                ax_rsi.fill_between(range(len(rsi)), 30, 70, alpha=0.1, color='gray')
                ax_rsi.set_ylabel('RSI')
                ax_rsi.legend()
                ax_rsi.grid(True, alpha=0.3)
                ax_rsi.set_ylim([0, 100])
            except Exception as e:
                logger.error(f"Error plotting RSI manually: {str(e)}")

        # Set x-axis ticks (only on bottom panel)
        bottom_ax = self.figure.axes[-1]
        if len(plot_df) > 0:
            step = max(1, len(plot_df) // 10)
            indices = list(range(0, len(plot_df), step))
            if len(plot_df) - 1 not in indices:
                indices.append(len(plot_df) - 1)

            dates = [plot_df.index[i].strftime('%Y-%m-%d') for i in indices]
            bottom_ax.set_xticks(indices)
            bottom_ax.set_xticklabels(dates, rotation=45)
            bottom_ax.set_xlabel('Date')

        # Hide x-axis labels for all except bottom panel
        for ax in self.figure.axes[:-1]:
            plt.setp(ax.get_xticklabels(), visible=False)

        self.figure.tight_layout(rect=[0, 0.03, 1, 0.97])
        self.canvas.draw()

    def plot_trade_markers_manual(self, ax, plot_df):
        """Plot trade markers manually"""
        if not self.trades:
            return

        for trade in self.trades:
            # Find indices
            entry_idx = self.find_date_index(plot_df, trade.entry_date)
            exit_idx = self.find_date_index(plot_df, trade.exit_date)

            if entry_idx is not None:
                # Plot entry marker
                if trade.position_type == 'long':
                    marker = '^'
                    if trade.success:
                        color = 'green'
                    else:
                        color = 'yellow'
                else:  # short
                    marker = 's'
                    if trade.success:
                        color = 'red'
                    else:
                        color = 'yellow'

                ax.plot(entry_idx, trade.entry_price, marker=marker,
                       markersize=12, color=color, markeredgecolor='black',
                       markeredgewidth=1)

            if exit_idx is not None:
                # Plot exit marker
                if trade.position_type == 'long':
                    marker = '^'
                    if trade.success:
                        color = 'red'
                    else:
                        color = 'blue'
                else:  # short
                    marker = 's'
                    if trade.success:
                        color = 'green'
                    else:
                        color = 'blue'

                ax.plot(exit_idx, trade.exit_price, marker=marker,
                       markersize=10, color=color, markeredgecolor='black',
                       markeredgewidth=1)

    def find_date_index(self, df, date):
        """Find the index of a date in the dataframe"""
        try:
            # Convert date to pandas Timestamp if needed
            if not isinstance(date, pd.Timestamp):
                date = pd.Timestamp(date)

            # Try exact match
            for i, idx in enumerate(df.index):
                if idx.date() == date.date():
                    return i

            # Find closest date
            if len(df) > 0:
                time_diff = abs(df.index - date)
                return time_diff.argmin()

            return None

        except Exception as e:
            logger.error(f"Error finding date index: {str(e)}")
            return None

    def toggle_volume(self, checked: bool):
        """Toggle volume display"""
        self.show_volume = checked
        self.update_chart()

    def toggle_macd(self, checked: bool):
        """Toggle MACD display"""
        self.show_macd = checked
        self.update_chart()

    def toggle_rsi(self, checked: bool):
        """Toggle RSI display"""
        self.show_rsi = checked
        self.update_chart()