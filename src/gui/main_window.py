import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import plot
import webbrowser
from pathlib import Path
import sqlite3
import json
from datetime import datetime

from src.config.settings import CANDLE_PATTERNS, DEFAULT_CAPITAL, DEFAULT_POSITION_SIZE, DEFAULT_THRESHOLD
from src.data.moex_client import MOEXClient
from src.data.crypto_client import CryptoClient
from src.patterns.pattern_detector import PatternDetector
from src.backtest.engine import BacktestEngine
from src.gui.database_viewer import DatabaseViewer
from src.gui.help_window import HelpWindow
import threading
from src.visualization.tradingview_chart import create_plotly_chart
from src.strategies.strategy_builder import Strategy, StrategyBuilder, TimeFrame, EntryRule, ExitRule
from src.strategies.entry_rules import EntryRuleExecutor
from src.strategies.exit_rules import ExitRuleExecutor
from src.config.database import Database
from src.utils.logger import log_user_action, log_error, log_app_info



class StrategyDialog(QDialog):
    """Dialog for creating/editing strategies"""

    def __init__(self, parent=None, strategy=None):
        super().__init__(parent)
        self.strategy = strategy
        self.setWindowTitle("Strategy Editor" if strategy else "New Strategy")
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)

        # Strategy name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Strategy Name:"))
        self.name_edit = QLineEdit()
        if self.strategy:
            self.name_edit.setText(self.strategy.name)
            self.name_edit.setEnabled(False)  # Can't rename existing strategy
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # Timeframe
        timeframe_layout = QHBoxLayout()
        timeframe_layout.addWidget(QLabel("Timeframe:"))
        self.timeframe_combo = QComboBox()
        for tf in TimeFrame:
            self.timeframe_combo.addItem(tf.value, tf)
        if self.strategy:
            index = self.timeframe_combo.findText(self.strategy.timeframe.value)
            if index >= 0:
                self.timeframe_combo.setCurrentIndex(index)
        timeframe_layout.addWidget(self.timeframe_combo)
        layout.addLayout(timeframe_layout)

        # Pattern selection
        layout.addWidget(QLabel("Select Patterns:"))
        self.pattern_list = QListWidget()
        self.pattern_list.addItems(CANDLE_PATTERNS)
        self.pattern_list.setSelectionMode(QListWidget.MultiSelection)

        # Select patterns if editing
        if self.strategy:
            for i in range(self.pattern_list.count()):
                item = self.pattern_list.item(i)
                if item.text() in self.strategy.patterns:
                    item.setSelected(True)

        layout.addWidget(self.pattern_list)

        # Entry rule
        entry_layout = QHBoxLayout()
        entry_layout.addWidget(QLabel("Entry Rule:"))
        self.entry_combo = QComboBox()
        for rule in EntryRule:
            self.entry_combo.addItem(
                f"{rule.value} - {EntryRuleExecutor.get_description(rule)}",
                rule
            )
        if self.strategy:
            index = self.entry_combo.findData(self.strategy.entry_rule)
            if index >= 0:
                self.entry_combo.setCurrentIndex(index)
        entry_layout.addWidget(self.entry_combo)
        layout.addLayout(entry_layout)

        # Exit rule
        exit_layout = QHBoxLayout()
        exit_layout.addWidget(QLabel("Exit Rule:"))
        self.exit_combo = QComboBox()
        for rule in ExitRule:
            self.exit_combo.addItem(
                f"{rule.value} - {ExitRuleExecutor.get_description(rule)}",
                rule
            )
        if self.strategy:
            index = self.exit_combo.findData(self.strategy.exit_rule)
            if index >= 0:
                self.exit_combo.setCurrentIndex(index)
        exit_layout.addWidget(self.exit_combo)
        layout.addLayout(exit_layout)

        # Risk parameters
        risk_group = QGroupBox("Risk Parameters")
        risk_layout = QGridLayout()

        risk_layout.addWidget(QLabel("Position Size (%):"), 0, 0)
        self.position_spin = QDoubleSpinBox()
        self.position_spin.setRange(1, 100)
        self.position_spin.setValue(self.strategy.position_size_pct if self.strategy else 10.0)
        risk_layout.addWidget(self.position_spin, 0, 1)

        risk_layout.addWidget(QLabel("Stop Loss (%):"), 1, 0)
        self.stop_loss_spin = QDoubleSpinBox()
        self.stop_loss_spin.setRange(0.1, 50)
        self.stop_loss_spin.setValue(self.strategy.stop_loss_pct if self.strategy else 2.0)
        self.stop_loss_spin.setSingleStep(0.5)
        risk_layout.addWidget(self.stop_loss_spin, 1, 1)

        risk_layout.addWidget(QLabel("Take Profit (%):"), 2, 0)
        self.take_profit_spin = QDoubleSpinBox()
        self.take_profit_spin.setRange(0.1, 100)
        self.take_profit_spin.setValue(self.strategy.take_profit_pct if self.strategy else 4.0)
        self.take_profit_spin.setSingleStep(0.5)
        risk_layout.addWidget(self.take_profit_spin, 2, 1)

        risk_layout.addWidget(QLabel("Max Bars to Hold:"), 3, 0)
        self.max_bars_spin = QSpinBox()
        self.max_bars_spin.setRange(1, 1000)
        self.max_bars_spin.setValue(self.strategy.max_bars_hold if self.strategy else 20)
        risk_layout.addWidget(self.max_bars_spin, 3, 1)

        risk_group.setLayout(risk_layout)
        layout.addWidget(risk_group)

        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def get_strategy_data(self) -> dict:
        """Get strategy data from form"""
        return {
            'name': self.name_edit.text(),
            'patterns': [item.text() for item in self.pattern_list.selectedItems()],
            'entry_rule': self.entry_combo.currentData(),
            'exit_rule': self.exit_combo.currentData(),
            'timeframe': self.timeframe_combo.currentData(),
            'position_size_pct': self.position_spin.value(),
            'stop_loss_pct': self.stop_loss_spin.value(),
            'take_profit_pct': self.take_profit_spin.value(),
            'max_bars_hold': self.max_bars_spin.value()
        }


class BacktestApp(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MOEX & Crypto Backtest System")
        self.setGeometry(100, 100, 1600, 900)

        self.data_client = None
        self.current_data = None
        self.backtest_results = None
        self.current_strategy = None
        self.database = Database()
        self.strategy_builder = StrategyBuilder()

        self.chart_window = None

        self.init_ui()
        self.load_strategies()
        log_app_info("Application started")

    def init_ui(self):
        """Initialize user interface"""
        # Central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left panel for controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Menu bar
        self.create_menu_bar()

        # Strategy management
        strategy_group = self.create_strategy_group()
        left_layout.addWidget(strategy_group)

        # Data fetching controls
        data_group = self.create_data_group()
        left_layout.addWidget(data_group)

        # Backtest controls
        backtest_group = self.create_backtest_group()
        left_layout.addWidget(backtest_group)

        # Action buttons panel
        action_group = self.create_action_buttons()
        left_layout.addWidget(action_group)

        left_layout.addStretch()

        # Right panel for results
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Results text area
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Courier", 10))
        right_layout.addWidget(self.results_text)

        # Add panels to splitter
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 2)

        # Status bar
        self.statusBar().showMessage("Ready")

    def create_action_buttons(self) -> QWidget:
        """Create panel with action buttons"""
        panel = QGroupBox("Actions")
        layout = QVBoxLayout()

        # Row 1
        row1 = QHBoxLayout()

        self.save_excel_btn = QPushButton("Save to Excel")
        self.save_excel_btn.clicked.connect(self.save_to_excel)
        self.save_excel_btn.setEnabled(False)
        row1.addWidget(self.save_excel_btn)

        self.save_db_btn = QPushButton("Save to Database")
        self.save_db_btn.clicked.connect(self.save_to_database)
        self.save_db_btn.setEnabled(False)
        row1.addWidget(self.save_db_btn)

        self.view_db_btn = QPushButton("View Database")
        self.view_db_btn.clicked.connect(self.view_database)
        row1.addWidget(self.view_db_btn)

        layout.addLayout(row1)

        # Row 2
        row2 = QHBoxLayout()

        self.chart_btn = QPushButton("Show Chart")
        self.chart_btn.clicked.connect(self.show_interactive_chart)
        self.chart_btn.setEnabled(False)
        row2.addWidget(self.chart_btn)

        self.help_btn = QPushButton("Help")
        self.help_btn.clicked.connect(self.show_help)
        row2.addWidget(self.help_btn)

        self.debug_btn = QPushButton("Debug Mode")
        self.debug_btn.clicked.connect(self.toggle_debug_mode)
        row2.addWidget(self.debug_btn)

        layout.addLayout(row2)

        panel.setLayout(layout)
        return panel

    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('File')

        save_excel_action = QAction('Save to Excel', self)
        save_excel_action.triggered.connect(self.save_to_excel)
        file_menu.addAction(save_excel_action)

        save_db_action = QAction('Save to Database', self)
        save_db_action.triggered.connect(self.save_to_database)
        file_menu.addAction(save_db_action)

        file_menu.addSeparator()

        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu('Tools')

        chart_action = QAction('Show Interactive Chart', self)
        chart_action.triggered.connect(self.show_interactive_chart)
        tools_menu.addAction(chart_action)

    def create_strategy_group(self) -> QWidget:
        """Create strategy management group"""
        group = QGroupBox("Strategy Management")
        layout = QVBoxLayout()

        # Strategy selection
        strategy_layout = QHBoxLayout()
        strategy_layout.addWidget(QLabel("Strategy:"))
        self.strategy_combo = QComboBox()
        self.strategy_combo.currentIndexChanged.connect(self.on_strategy_changed)
        strategy_layout.addWidget(self.strategy_combo)

        # Strategy buttons
        new_btn = QPushButton("New")
        new_btn.clicked.connect(self.create_strategy)
        strategy_layout.addWidget(new_btn)

        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self.edit_strategy)
        strategy_layout.addWidget(edit_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self.delete_strategy)
        strategy_layout.addWidget(delete_btn)

        layout.addLayout(strategy_layout)

        # Strategy info
        self.strategy_info = QTextEdit()
        self.strategy_info.setReadOnly(True)
        self.strategy_info.setMaximumHeight(150)
        layout.addWidget(self.strategy_info)

        group.setLayout(layout)
        return group

    def create_data_group(self) -> QWidget:
        """Create data fetching group"""
        group = QGroupBox("Data Settings")
        layout = QGridLayout()

        # Market selection
        layout.addWidget(QLabel("Market:"), 0, 0)
        self.market_combo = QComboBox()
        self.market_combo.addItems(["MOEX", "Cryptocurrency"])
        self.market_combo.currentTextChanged.connect(self.on_market_changed)
        layout.addWidget(self.market_combo, 0, 1)

        # Ticker/Symbol
        layout.addWidget(QLabel("Ticker/Symbol:"), 1, 0)
        self.ticker_edit = QLineEdit()
        self.ticker_edit.setText("SBER")
        layout.addWidget(self.ticker_edit, 1, 1)

        # Timeframe
        layout.addWidget(QLabel("Timeframe:"), 2, 0)
        self.timeframe_combo = QComboBox()
        for tf in TimeFrame:
            self.timeframe_combo.addItem(tf.value, tf)
        layout.addWidget(self.timeframe_combo, 2, 1)

        # Date range
        layout.addWidget(QLabel("Start Date:"), 3, 0)
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addYears(-1))
        self.start_date.setCalendarPopup(True)
        layout.addWidget(self.start_date, 3, 1)

        layout.addWidget(QLabel("End Date:"), 4, 0)
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        layout.addWidget(self.end_date, 4, 1)

        # Pattern threshold
        layout.addWidget(QLabel("Pattern Threshold:"), 5, 0)
        threshold_layout = QHBoxLayout()
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setValue(int(DEFAULT_THRESHOLD * 100))
        threshold_layout.addWidget(self.threshold_slider)

        self.threshold_label = QLabel(f"{DEFAULT_THRESHOLD:.2f}")
        threshold_layout.addWidget(self.threshold_label)
        self.threshold_slider.valueChanged.connect(
            lambda v: self.threshold_label.setText(f"{v/100:.2f}")
        )
        layout.addLayout(threshold_layout, 5, 1)

        # Fetch button
        self.fetch_button = QPushButton("Fetch Data")
        self.fetch_button.clicked.connect(self.fetch_data)
        layout.addWidget(self.fetch_button, 6, 0, 1, 2)

        group.setLayout(layout)
        return group

    def create_backtest_group(self) -> QWidget:
        """Create backtest controls group"""
        group = QGroupBox("Backtest Parameters")
        layout = QGridLayout()

        # Capital
        layout.addWidget(QLabel("Initial Capital:"), 0, 0)
        self.capital_spin = QDoubleSpinBox()
        self.capital_spin.setRange(1000, 100000000)
        self.capital_spin.setValue(DEFAULT_CAPITAL)
        self.capital_spin.setSuffix(" RUB")
        layout.addWidget(self.capital_spin, 0, 1)

        # Commission
        layout.addWidget(QLabel("Commission (%):"), 1, 0)
        self.commission_spin = QDoubleSpinBox()
        self.commission_spin.setRange(0, 5)
        self.commission_spin.setValue(0.1)
        self.commission_spin.setSingleStep(0.01)
        layout.addWidget(self.commission_spin, 1, 1)

        # Slippage
        layout.addWidget(QLabel("Slippage (%):"), 2, 0)
        self.slippage_spin = QDoubleSpinBox()
        self.slippage_spin.setRange(0, 5)
        self.slippage_spin.setValue(0.1)
        self.slippage_spin.setSingleStep(0.01)
        layout.addWidget(self.slippage_spin, 2, 1)

        # Run button
        self.run_button = QPushButton("Run Backtest")
        self.run_button.clicked.connect(self.run_backtest)
        self.run_button.setEnabled(False)
        layout.addWidget(self.run_button, 3, 0, 1, 2)

        # Chart button
        self.chart_button = QPushButton("Show Chart")
        self.chart_button.clicked.connect(self.show_interactive_chart)
        self.chart_button.setEnabled(False)
        layout.addWidget(self.chart_button, 4, 0, 1, 2)

        group.setLayout(layout)
        return group

    def load_strategies(self):
        """Load strategies from database"""
        try:
            strategies = self.strategy_builder.get_all_strategies(self.database)
            self.strategy_combo.clear()
            for strategy in strategies:
                self.strategy_combo.addItem(strategy.name, strategy)

            if strategies:
                self.on_strategy_changed(0)

        except Exception as e:
            log_error(e, "load_strategies")

    def on_strategy_changed(self, index: int):
        """Handle strategy selection change"""
        if index >= 0:
            self.current_strategy = self.strategy_combo.itemData(index)
            self.update_strategy_info()

    def update_strategy_info(self):
        """Update strategy information display"""
        if not self.current_strategy:
            self.strategy_info.clear()
            return

        info = f"<b>{self.current_strategy.name}</b><br>"
        info += f"Timeframe: {self.current_strategy.timeframe.value}<br>"
        info += f"Patterns: {', '.join(self.current_strategy.patterns[:5])}"
        if len(self.current_strategy.patterns) > 5:
            info += f"... (+{len(self.current_strategy.patterns) - 5} more)"
        info += "<br>"
        info += f"Entry: {self.current_strategy.entry_rule.value}<br>"
        info += f"Exit: {self.current_strategy.exit_rule.value}<br>"
        info += f"Position Size: {self.current_strategy.position_size_pct}%<br>"
        info += f"Stop Loss: {self.current_strategy.stop_loss_pct}%<br>"
        info += f"Take Profit: {self.current_strategy.take_profit_pct}%"

        self.strategy_info.setHtml(info)

    def create_strategy(self):
        """Create new strategy"""
        dialog = StrategyDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                data = dialog.get_strategy_data()

                # Validate
                if not data['name']:
                    QMessageBox.warning(self, "Warning", "Strategy name is required")
                    return

                if not data['patterns']:
                    QMessageBox.warning(self, "Warning", "Select at least one pattern")
                    return

                # Create strategy
                strategy = self.strategy_builder.create_strategy(
                    name=data['name'],
                    patterns=data['patterns'],
                    entry_rule=data['entry_rule'],
                    exit_rule=data['exit_rule'],
                    timeframe=data['timeframe'],
                    position_size_pct=data['position_size_pct'],
                    stop_loss_pct=data['stop_loss_pct'],
                    take_profit_pct=data['take_profit_pct'],
                    max_bars_hold=data['max_bars_hold']
                )

                # Save to database
                self.strategy_builder.save_strategy_to_db(strategy, self.database)

                # Reload strategies
                self.load_strategies()

                log_user_action("Create strategy", {'name': data['name']})

            except Exception as e:
                log_error(e, "create_strategy")
                QMessageBox.critical(self, "Error", f"Failed to create strategy: {str(e)}")

    def edit_strategy(self):
        """Edit selected strategy"""
        if not self.current_strategy:
            QMessageBox.warning(self, "Warning", "No strategy selected")
            return

        dialog = StrategyDialog(self, self.current_strategy)
        if dialog.exec_() == QDialog.Accepted:
            try:
                data = dialog.get_strategy_data()

                # Update strategy
                updated_strategy = Strategy(
                    name=data['name'],
                    patterns=data['patterns'],
                    entry_rule=data['entry_rule'],
                    entry_params=self.current_strategy.entry_params,
                    exit_rule=data['exit_rule'],
                    exit_params=self.current_strategy.exit_params,
                    timeframe=data['timeframe'],
                    position_size_pct=data['position_size_pct'],
                    stop_loss_pct=data['stop_loss_pct'],
                    take_profit_pct=data['take_profit_pct'],
                    max_bars_hold=data['max_bars_hold']
                )

                # Save to database
                self.strategy_builder.save_strategy_to_db(updated_strategy, self.database)

                # Reload strategies
                self.load_strategies()

                log_user_action("Edit strategy", {'name': data['name']})

            except Exception as e:
                log_error(e, "edit_strategy")
                QMessageBox.critical(self, "Error", f"Failed to edit strategy: {str(e)}")

    def delete_strategy(self):
        """Delete selected strategy"""
        if not self.current_strategy:
            QMessageBox.warning(self, "Warning", "No strategy selected")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete strategy '{self.current_strategy.name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.strategy_builder.delete_strategy(self.current_strategy.name, self.database)
                self.load_strategies()
                self.current_strategy = None
                self.strategy_info.clear()

                log_user_action("Delete strategy", {'name': self.current_strategy.name})

            except Exception as e:
                log_error(e, "delete_strategy")
                QMessageBox.critical(self, "Error", f"Failed to delete strategy: {str(e)}")

    def on_market_changed(self, market: str):
        """Handle market selection change"""
        log_user_action(f"Market changed to {market}")

        if market == "MOEX":
            self.ticker_edit.setText("SBER")
        else:
            self.ticker_edit.setText("BTCUSDT")

    def fetch_data(self):
        """Fetch data from selected market"""
        try:
            market = self.market_combo.currentText()
            ticker = self.ticker_edit.text().strip()
            start_date = self.start_date.date().toString("yyyy-MM-dd")
            end_date = self.end_date.date().toString("yyyy-MM-dd")
            timeframe = self.timeframe_combo.currentData()

            if not ticker:
                QMessageBox.warning(self, "Warning", "Please enter a ticker/symbol")
                return

            log_user_action("Fetch data", {
                "market": market,
                "ticker": ticker,
                "timeframe": timeframe.value,
                "start_date": start_date,
                "end_date": end_date
            })

            self.statusBar().showMessage(f"Fetching {market} data for {ticker}...")
            QApplication.processEvents()

            if market == "MOEX":
                self.data_client = MOEXClient()
                # Pass timeframe string directly
                data = self.data_client.get_data(ticker, start_date, end_date, timeframe.value)
            else:
                self.data_client = CryptoClient()
                # Convert timeframe for Bybit
                interval_map = {
                    TimeFrame.MINUTE_1: '1',
                    TimeFrame.MINUTE_5: '5',
                    TimeFrame.MINUTE_15: '15',
                    TimeFrame.MINUTE_30: '30',
                    TimeFrame.HOUR_1: '60',
                    TimeFrame.HOUR_4: '240',
                    TimeFrame.DAILY: 'D',
                    TimeFrame.WEEKLY: 'W',
                    TimeFrame.MONTHLY: 'M'
                }
                interval = interval_map.get(timeframe, 'D')
                data = self.data_client.get_data(ticker, start_date, end_date, interval)

            if data is not None and not data.empty:
                self.current_data = data
                self.run_button.setEnabled(True)

                # Display data info
                info_text = f"Fetched {len(data)} bars for {ticker}\n"
                info_text += f"Date range: {data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}\n"
                info_text += f"Columns: {', '.join(data.columns.tolist())}"

                self.statusBar().showMessage(info_text)
                log_app_info(f"Data fetched successfully: {len(data)} bars")

                # Debug: print data info
                print(f"Data shape: {data.shape}")
                print(f"Data columns: {data.columns.tolist()}")
                print(f"First few rows:\n{data.head()}")

            else:
                QMessageBox.warning(self, "Warning", "No data found for the given parameters")
                self.statusBar().showMessage("Failed to fetch data")

        except Exception as e:
            log_error(e, "fetch_data")
            QMessageBox.critical(self, "Error", f"Failed to fetch data: {str(e)}")
            self.statusBar().showMessage("Error fetching data")

    def run_backtest(self):
        """Run backtest with selected parameters"""
        try:
            if not self.current_strategy:
                QMessageBox.warning(self, "Warning", "Please select a strategy first")
                return

            if self.current_data is None or self.current_data.empty:
                QMessageBox.warning(self, "Warning", "Please fetch data first")
                return

            # Get parameters
            threshold = self.threshold_slider.value() / 100
            initial_capital = self.capital_spin.value()
            commission = self.commission_spin.value() / 100
            slippage = self.slippage_spin.value() / 100

            log_user_action("Run backtest", {
                "strategy": self.current_strategy.name,
                "threshold": threshold,
                "initial_capital": initial_capital,
                "commission": commission,
                "slippage": slippage
            })

            self.statusBar().showMessage("Running backtest...")
            QApplication.processEvents()

            # Detect patterns
            detector = PatternDetector(threshold=threshold)
            data_with_patterns = detector.detect_all_patterns(self.current_data.copy())

            # Run backtest
            engine = BacktestEngine(
                initial_capital=initial_capital,
                position_size_pct=self.current_strategy.position_size_pct,
                commission=commission,
                slippage=slippage
            )

            self.backtest_results = engine.run(
                data_with_patterns,
                self.current_strategy.patterns,
                self.current_strategy.entry_rule,
                self.current_strategy.exit_rule,
                self.current_strategy.entry_params,
                self.current_strategy.exit_params
            )

            # Display results
            self.display_results()

            self.chart_button.setEnabled(True)
            self.statusBar().showMessage("Backtest completed successfully")
            log_app_info(f"Backtest completed: {len(self.backtest_results['trades'])} trades")

        except Exception as e:
            log_error(e, "run_backtest")
            QMessageBox.critical(self, "Error", f"Backtest failed: {str(e)}")
            self.statusBar().showMessage("Backtest failed")

    def display_results(self):
        """Display backtest results in text area"""
        if not self.backtest_results:
            return

        metrics = self.backtest_results['metrics']
        trades = self.backtest_results['trades']

        text = "=" * 80 + "\n"
        text += f"BACKTEST RESULTS - {self.current_strategy.name if self.current_strategy else 'Unknown'}\n"
        text += "=" * 80 + "\n\n"

        # Capital tracking
        text += f"Initial Capital: {metrics.get('initial_capital', 0):,.2f}\n"
        text += f"Final Capital: {metrics.get('final_capital', 0):,.2f}\n"
        text += f"Total Return: {metrics.get('total_return_pct', 0):.2f}%\n"
        text += f"Total P&L: {metrics.get('total_pnl', 0):,.2f}\n"
        text += f"Average Invested per Trade: {metrics.get('avg_invested_per_trade', 0):,.2f}\n"
        text += f"Total Invested: {metrics.get('total_invested', 0):,.2f}\n\n"

        text += f"Total Trades: {metrics.get('total_trades', 0)}\n"
        text += f"Winning Trades: {metrics.get('winning_trades', 0)}\n"
        text += f"Losing Trades: {metrics.get('losing_trades', 0)}\n"
        text += f"Win Rate: {metrics.get('win_rate', 0):.2f}%\n\n"

        text += f"Average Win: {metrics.get('avg_win', 0):,.2f}\n"
        text += f"Average Loss: {metrics.get('avg_loss', 0):,.2f}\n"
        text += f"Profit Factor: {metrics.get('profit_factor', 0):.2f}\n"
        text += f"Average ROI per Trade: {metrics.get('avg_roi_per_trade', 0):.2f}%\n"
        text += f"Max Consecutive Wins: {metrics.get('consecutive_wins', 0)}\n"
        text += f"Max Consecutive Losses: {metrics.get('consecutive_losses', 0)}\n\n"

        text += f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}\n"
        text += f"Maximum Drawdown: {metrics.get('max_drawdown', 0):.2f}%\n"
        text += f"Average Trade Duration: {metrics.get('avg_trade_duration', pd.Timedelta(0))}\n\n"

        # Debug info if available
        if 'debug_info' in self.backtest_results:
            debug = self.backtest_results['debug_info']
            text += "DEBUG INFO:\n"
            text += f"Expected Final Capital: {debug['expected_final_capital']:,.2f}\n"
            text += f"Engine Final Capital: {debug['engine_final_capital']:,.2f}\n\n"

        text += "=" * 80 + "\n"
        text += "TRADE LIST\n"
        text += "=" * 80 + "\n\n"

        for i, trade in enumerate(trades, 1):
            text += f"Trade #{i}:\n"
            text += f"  Type: {trade.position_type.upper()}\n"
            text += f"  Entry: {trade.entry_date.strftime('%Y-%m-%d')} at {trade.entry_price:.2f}\n"
            text += f"  Exit: {trade.exit_date.strftime('%Y-%m-%d')} at {trade.exit_price:.2f}\n"
            text += f"  Invested: {trade.invested_capital:,.2f}\n"
            text += f"  P&L: {trade.pnl:,.2f} ({trade.pnl_percent:.2f}%)\n"
            text += f"  Pattern: {trade.pattern}\n"
            text += f"  Exit Reason: {trade.exit_reason}\n"
            text += f"  Result: {'PROFIT' if trade.success else 'LOSS'}\n"
            text += "-" * 40 + "\n"

        self.results_text.setText(text)

    def show_interactive_chart(self):
        """Show interactive Plotly chart"""
        try:
            if not self.backtest_results:
                QMessageBox.warning(self, "Warning", "Please run backtest first")
                return

            log_user_action("Show interactive Plotly chart")

            title = f"{self.ticker_edit.text()} - {self.current_strategy.name if self.current_strategy else 'Backtest'}"

            # Run Plotly chart in separate thread
            import threading

            def create_chart():
                try:
                    create_plotly_chart(
                        self.backtest_results['df'],
                        self.backtest_results['trades'],
                        title
                    )
                except Exception as e:
                    print(f"Plotly chart error: {e}")
                    import traceback
                    traceback.print_exc()

            thread = threading.Thread(target=create_chart, daemon=True)
            thread.start()

        except Exception as e:
            log_error(e, "show_interactive_chart")
            QMessageBox.critical(self, "Error", f"Failed to show chart: {str(e)}")

    def save_to_excel(self):
        """Save backtest results to Excel"""
        try:
            if not self.backtest_results:
                QMessageBox.warning(self, "Warning", "No results to save")
                return

            log_user_action("Save to Excel")

            # Get filename
            default_name = f"backtest_{self.ticker_edit.text()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            filename, ok = QFileDialog.getSaveFileName(
                self,
                "Save to Excel",
                f"results/{default_name}.xlsx",
                "Excel Files (*.xlsx)"
            )

            if ok and filename:
                # Ensure directory exists
                Path(filename).parent.mkdir(parents=True, exist_ok=True)

                # Prepare data for export
                trades_df = pd.DataFrame([t.to_dict() for t in self.backtest_results['trades']])
                equity_df = self.backtest_results['equity_curve']
                metrics = self.backtest_results['metrics']

                # Create Excel writer
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    # Summary sheet
                    summary_data = {
                        'Parameter': [
                            'Strategy', 'Symbol', 'Timeframe', 'Start Date', 'End Date',
                            'Initial Capital', 'Final Capital', 'Total Return %',
                            'Total Trades', 'Win Rate %', 'Profit Factor',
                            'Sharpe Ratio', 'Max Drawdown %'
                        ],
                        'Value': [
                            self.current_strategy.name if self.current_strategy else 'N/A',
                            self.ticker_edit.text(),
                            self.timeframe_combo.currentText(),
                            self.start_date.date().toString("yyyy-MM-dd"),
                            self.end_date.date().toString("yyyy-MM-dd"),
                            f"{metrics.get('initial_capital', 0):,.2f}",
                            f"{metrics.get('final_capital', 0):,.2f}",
                            f"{metrics.get('total_return_pct', 0):.2f}",
                            metrics.get('total_trades', 0),
                            f"{metrics.get('win_rate', 0):.2f}",
                            f"{metrics.get('profit_factor', 0):.2f}",
                            f"{metrics.get('sharpe_ratio', 0):.2f}",
                            f"{metrics.get('max_drawdown', 0):.2f}"
                        ]
                    }
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)

                    # Trades sheet
                    trades_df.to_excel(writer, sheet_name='Trades', index=False)

                    # Equity curve sheet
                    equity_df.to_excel(writer, sheet_name='Equity Curve', index=False)

                    # Metrics sheet
                    metrics_df = pd.DataFrame([{k: v for k, v in metrics.items()
                                            if not isinstance(v, (dict, pd.Timedelta))}])
                    metrics_df.to_excel(writer, sheet_name='Metrics', index=False)

                    # Pattern statistics sheet
                    if 'pattern_statistics' in metrics:
                        pattern_data = []
                        pattern_stats = metrics['pattern_statistics']
                        if 'count' in pattern_stats:
                            for pattern in pattern_stats['count']:
                                pattern_data.append({
                                    'Pattern': pattern,
                                    'Count': pattern_stats['count'][pattern],
                                    'Total P&L': pattern_stats['sum']['pnl'][pattern],
                                    'Avg P&L': pattern_stats['mean']['pnl'][pattern],
                                    'Win Rate': pattern_stats['mean']['success'][pattern] * 100
                                })
                            pattern_df = pd.DataFrame(pattern_data)
                            pattern_df.to_excel(writer, sheet_name='Pattern Stats', index=False)

                QMessageBox.information(self, "Success", f"Results saved to {filename}")
                log_app_info(f"Results saved to Excel: {filename}")

        except Exception as e:
            log_error(e, "save_to_excel")
            QMessageBox.critical(self, "Error", f"Failed to save to Excel: {str(e)}")

    def save_to_database(self):
        """Save backtest results to database"""
        try:
            if not self.backtest_results:
                QMessageBox.warning(self, "Warning", "No results to save")
                return

            if not self.current_strategy:
                QMessageBox.warning(self, "Warning", "No strategy selected")
                return

            log_user_action("Save to database")

            # Prepare result data
            result_data = {
                'strategy_id': None,  # Would need strategy ID from DB
                'symbol': self.ticker_edit.text(),
                'timeframe': self.timeframe_combo.currentText(),
                'start_date': self.start_date.date().toString("yyyy-MM-dd"),
                'end_date': self.end_date.date().toString("yyyy-MM-dd"),
                'initial_capital': self.capital_spin.value(),
                'final_capital': self.backtest_results['metrics']['final_capital'],
                'total_return': self.backtest_results['metrics']['total_return_pct'],
                'total_trades': self.backtest_results['metrics']['total_trades'],
                'win_rate': self.backtest_results['metrics']['win_rate'],
                'profit_factor': self.backtest_results['metrics']['profit_factor'],
                'sharpe_ratio': self.backtest_results['metrics'].get('sharpe_ratio'),
                'max_drawdown': self.backtest_results['metrics']['max_drawdown'],
                'metrics': self.backtest_results['metrics'],
                'trades': [t.to_dict() for t in self.backtest_results['trades']]
            }

            # Get strategy ID
            strategies = self.strategy_builder.get_all_strategies(self.database)
            for strat in strategies:
                if strat.name == self.current_strategy.name:
                    result_data['strategy_id'] = strat.id
                    break

            # Save to database
            result_id = self.database.save_backtest_result(result_data)

            QMessageBox.information(self, "Success", f"Results saved to database (ID: {result_id})")
            log_app_info(f"Results saved to database: ID {result_id}")

        except Exception as e:
            log_error(e, "save_to_database")
            QMessageBox.critical(self, "Error", f"Failed to save to database: {str(e)}")

    def view_database(self):
        """View database contents"""
        try:
            # Create database viewer window
            self.db_viewer = DatabaseViewer(self, self.database)
            self.db_viewer.show()

            log_user_action("View database")

        except Exception as e:
            log_error(e, "view_database")
            QMessageBox.critical(self, "Error", f"Failed to view database: {str(e)}")

    def show_help(self):
        """Show help window"""
        try:
            self.help_window = HelpWindow(self)
            self.help_window.show()

            log_user_action("Show help")

        except Exception as e:
            log_error(e, "show_help")
            QMessageBox.critical(self, "Error", f"Failed to show help: {str(e)}")

    def toggle_debug_mode(self):
        """Toggle debug mode"""
        from src.utils.logger import get_logger
        logger = get_logger('app')

        current_level = logger.level
        if current_level == 20:  # INFO
            logger.setLevel(10)  # DEBUG
            self.debug_btn.setText("Debug: ON")
            self.statusBar().showMessage("Debug mode enabled")
            log_app_info("Debug mode enabled")
        else:
            logger.setLevel(20)  # INFO
            self.debug_btn.setText("Debug Mode")
            self.statusBar().showMessage("Debug mode disabled")
            log_app_info("Debug mode disabled")

    def run_backtest_with_debug(self):
        """Run backtest with debug information"""
        try:
            if not self.current_strategy:
                QMessageBox.warning(self, "Warning", "Please select a strategy first")
                return

            if self.current_data is None or self.current_data.empty:
                QMessageBox.warning(self, "Warning", "Please fetch data first")
                return

            # Get parameters
            threshold = self.threshold_slider.value() / 100
            initial_capital = self.capital_spin.value()
            commission = self.commission_spin.value() / 100
            slippage = self.slippage_spin.value() / 100

            log_user_action("Run backtest", {
                "strategy": self.current_strategy.name,
                "threshold": threshold,
                "initial_capital": initial_capital,
                "commission": commission,
                "slippage": slippage
            })

            self.statusBar().showMessage("Running backtest with debug...")
            QApplication.processEvents()

            # Detect patterns
            detector = PatternDetector(threshold=threshold)
            data_with_patterns = detector.detect_all_patterns(self.current_data.copy())

            # Run backtest
            engine = BacktestEngine(
                initial_capital=initial_capital,
                position_size_pct=self.current_strategy.position_size_pct,
                commission=commission,
                slippage=slippage
            )

            # Run with debug logging
            import logging
            logging.getLogger('app').setLevel(logging.DEBUG)

            self.backtest_results = engine.run(
                data_with_patterns,
                self.current_strategy.patterns,
                self.current_strategy.entry_rule,
                self.current_strategy.exit_rule,
                self.current_strategy.entry_params,
                self.current_strategy.exit_params
            )

            # Add debug information
            self.add_debug_info(engine)

            # Display results
            self.display_results()

            self.chart_button.setEnabled(True)
            self.save_excel_btn.setEnabled(True)
            self.save_db_btn.setEnabled(True)
            self.statusBar().showMessage("Backtest completed successfully")
            log_app_info(f"Backtest completed: {len(self.backtest_results['trades'])} trades")

        except Exception as e:
            log_error(e, "run_backtest")
            QMessageBox.critical(self, "Error", f"Backtest failed: {str(e)}")
            self.statusBar().showMessage("Backtest failed")

    def add_debug_info(self, engine):
        """Add debug information to results"""
        if not self.backtest_results:
            return

        # Calculate cumulative capital
        capital_tracking = []
        current_capital = engine.initial_capital

        for trade in self.backtest_results['trades']:
            # Entry: deduct invested capital
            invested = trade.invested_capital
            current_capital -= invested

            # Exit: add back invested capital + P&L
            current_capital += invested + trade.pnl

            capital_tracking.append({
                'trade': len(capital_tracking) + 1,
                'capital_before': current_capital + invested - trade.pnl,  # Before exit
                'invested': invested,
                'pnl': trade.pnl,
                'capital_after': current_capital
            })

        # Add debug info to results
        self.backtest_results['debug_info'] = {
            'capital_tracking': capital_tracking,
            'expected_final_capital': current_capital,
            'engine_final_capital': engine.capital
        }

        # Log discrepancies
        if abs(current_capital - engine.capital) > 0.01:
            logger.warning(f"Capital mismatch: expected={current_capital:.2f}, actual={engine.capital:.2f}")