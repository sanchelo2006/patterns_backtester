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
import numpy as np

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
        # FIX: Get stop_loss from exit_params if exists
        if self.strategy:
            stop_loss_value = self.strategy.exit_params.get('stop_loss_pct',
                                    self.strategy.exit_params.get('trailing_stop_pct', 2.0))
        else:
            stop_loss_value = 2.0
        self.stop_loss_spin.setValue(stop_loss_value)
        self.stop_loss_spin.setSingleStep(0.5)
        risk_layout.addWidget(self.stop_loss_spin, 1, 1)

        risk_layout.addWidget(QLabel("Take Profit (%):"), 2, 0)
        self.take_profit_spin = QDoubleSpinBox()
        self.take_profit_spin.setRange(0.1, 100)
        # FIX: Get take_profit from exit_params if exists
        if self.strategy:
            take_profit_value = self.strategy.exit_params.get('take_profit_pct', 4.0)
        else:
            take_profit_value = 4.0
        self.take_profit_spin.setValue(take_profit_value)
        self.take_profit_spin.setSingleStep(0.5)
        risk_layout.addWidget(self.take_profit_spin, 2, 1)

        risk_layout.addWidget(QLabel("Max Bars to Hold:"), 3, 0)
        self.max_bars_spin = QSpinBox()
        self.max_bars_spin.setRange(1, 1000)
        # FIX: Get max_bars from exit_params if exists
        if self.strategy:
            max_bars_value = self.strategy.exit_params.get('max_bars',
                                self.strategy.max_bars_hold if hasattr(self.strategy, 'max_bars_hold') else 20)
        else:
            max_bars_value = 20
        self.max_bars_spin.setValue(max_bars_value)
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
        info += f"Patterns: {', '.join(self.current_strategy.patterns[:5])}"
        if len(self.current_strategy.patterns) > 5:
            info += f"... (+{len(self.current_strategy.patterns) - 5} more)"
        info += "<br>"
        info += f"Entry: {self.current_strategy.entry_rule.value}<br>"
        info += f"Exit: {self.current_strategy.exit_rule.value}<br>"
        info += f"Position Size: {self.current_strategy.position_size_pct}%<br>"
        info += f"Stop Loss: {self.current_strategy.stop_loss_pct}%<br>"
        info += f"Take Profit: {self.current_strategy.take_profit_pct}%<br>"
        info += f"Max Bars: {self.current_strategy.max_bars_hold}"

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

                # Create exit_params based on exit rule
                exit_params = {}

                if data['exit_rule'] == ExitRule.STOP_LOSS_TAKE_PROFIT:
                    exit_params = {
                        'stop_loss_pct': data['stop_loss_pct'],
                        'take_profit_pct': data['take_profit_pct']
                    }
                elif data['exit_rule'] == ExitRule.TAKE_PROFIT_ONLY:
                    exit_params = {
                        'take_profit_pct': data['take_profit_pct']
                    }
                elif data['exit_rule'] == ExitRule.TIMEBASED_EXIT:
                    exit_params = {
                        'max_bars': data['max_bars_hold']
                    }
                elif data['exit_rule'] == ExitRule.TRAILING_STOP:
                    exit_params = {
                        'trailing_stop_pct': data['stop_loss_pct']
                    }

                # Create strategy - ID will be None initially
                strategy = Strategy(
                    id=None,  # Will be set when saved to database
                    name=data['name'],
                    patterns=data['patterns'],
                    entry_rule=data['entry_rule'],
                    entry_params={},
                    exit_rule=data['exit_rule'],
                    exit_params=exit_params,
                    position_size_pct=data['position_size_pct'],
                    stop_loss_pct=data['stop_loss_pct'],
                    take_profit_pct=data['take_profit_pct'],
                    max_bars_hold=data['max_bars_hold']
                )

                # Save to database - this will set the strategy.id
                self.strategy_builder.save_strategy_to_db(strategy, self.database)

                # Reload strategies
                self.load_strategies()

                # Select the new strategy
                index = self.strategy_combo.findText(data['name'])
                if index >= 0:
                    self.strategy_combo.setCurrentIndex(index)

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

                # Create proper exit_params based on exit rule
                exit_params = {}

                if data['exit_rule'] == ExitRule.STOP_LOSS_TAKE_PROFIT:
                    exit_params = {
                        'stop_loss_pct': data['stop_loss_pct'],
                        'take_profit_pct': data['take_profit_pct']
                    }
                elif data['exit_rule'] == ExitRule.TAKE_PROFIT_ONLY:
                    exit_params = {
                        'take_profit_pct': data['take_profit_pct']
                    }
                elif data['exit_rule'] == ExitRule.TIMEBASED_EXIT:
                    exit_params = {
                        'max_bars': data['max_bars_hold']
                    }
                elif data['exit_rule'] == ExitRule.TRAILING_STOP:
                    exit_params = {
                        'trailing_stop_pct': data['stop_loss_pct']
                    }

                # Create updated strategy - PRESERVE THE ID
                updated_strategy = Strategy(
                    id=self.current_strategy.id if hasattr(self.current_strategy, 'id') else None,
                    name=data['name'],
                    patterns=data['patterns'],
                    entry_rule=data['entry_rule'],
                    entry_params=self.current_strategy.entry_params,
                    exit_rule=data['exit_rule'],
                    exit_params=exit_params,
                    position_size_pct=data['position_size_pct'],
                    stop_loss_pct=data['stop_loss_pct'],
                    take_profit_pct=data['take_profit_pct'],
                    max_bars_hold=data['max_bars_hold']
                )

                # Save to database
                self.strategy_builder.save_strategy_to_db(updated_strategy, self.database)

                # Reload strategies
                self.load_strategies()

                # Update current strategy
                self.current_strategy = updated_strategy
                self.update_strategy_info()

                log_user_action("Edit strategy", {
                    'name': data['name'],
                    'position_size': data['position_size_pct'],
                    'stop_loss': data['stop_loss_pct'],
                    'take_profit': data['take_profit_pct'],
                    'max_bars': data['max_bars_hold']
                })

                QMessageBox.information(self, "Success", "Strategy updated successfully!")

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
                self.chart_button.setEnabled(False)  # Disable chart until backtest runs

                # Display fetched data in results area
                self.display_fetched_data(data)

                log_app_info(f"Data fetched successfully: {len(data)} bars")

            else:
                QMessageBox.warning(self, "Warning", "No data found for the given parameters")
                self.statusBar().showMessage("Failed to fetch data")
                self.results_text.setText("No data available. Please check your parameters.")

        except Exception as e:
            log_error(e, "fetch_data")
            QMessageBox.critical(self, "Error", f"Failed to fetch data: {str(e)}")
            self.statusBar().showMessage("Error fetching data")
            self.results_text.setText(f"Error fetching data: {str(e)}")

    def run_backtest(self):
        """Run backtest with selected parameters"""
        try:
            if not self.current_strategy:
                QMessageBox.warning(self, "Warning", "Please select a strategy first")
                return

            if self.current_data is None or self.current_data.empty:
                QMessageBox.warning(self, "Warning", "Please fetch data first")
                return

            # Clear results area and show "Running backtest..." message
            self.results_text.setText("Running backtest... Please wait.")
            QApplication.processEvents()

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
            self.save_excel_btn.setEnabled(True)
            self.save_db_btn.setEnabled(True)
            self.statusBar().showMessage("Backtest completed successfully")
            log_app_info(f"Backtest completed: {len(self.backtest_results['trades'])} trades")

        except Exception as e:
            log_error(e, "run_backtest")
            QMessageBox.critical(self, "Error", f"Backtest failed: {str(e)}")
            self.statusBar().showMessage("Backtest failed")
            self.results_text.setText(f"Backtest failed with error: {str(e)}\n\nPlease check the logs for details.")

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
        """Show interactive Plotly chart with toggle options"""
        try:
            if not self.backtest_results:
                QMessageBox.warning(self, "Warning", "Please run backtest first")
                return

            # Create dialog for indicator selection
            dialog = IndicatorSelectionDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                show_volume, show_macd, show_rsi = dialog.get_selections()

                log_user_action("Show interactive Plotly chart", {
                    "volume": show_volume,
                    "macd": show_macd,
                    "rsi": show_rsi
                })

                title = f"{self.ticker_edit.text()} - {self.current_strategy.name if self.current_strategy else 'Backtest'}"

                # Run Plotly chart in separate thread
                import threading

                def create_chart():
                    try:
                        from src.visualization.tradingview_chart import create_plotly_chart
                        create_plotly_chart(
                            self.backtest_results['df'],
                            self.backtest_results['trades'],
                            title,
                            show_volume=show_volume,
                            show_macd=show_macd,
                            show_rsi=show_rsi
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
        """Save backtest results to database - SIMPLIFIED VERSION"""
        try:
            if not self.backtest_results:
                QMessageBox.warning(self, "Warning", "No results to save")
                return

            if not self.current_strategy:
                QMessageBox.warning(self, "Warning", "No strategy selected")
                return

            log_user_action("Save to database")

            # Get metrics and clean them
            source_metrics = self.backtest_results['metrics'].copy()

            # Debug the metrics structure
            print("\n=== DEBUG METRICS STRUCTURE ===")
            self.debug_metrics_structure(source_metrics)
            print("================================\n")

            # Create a SIMPLE metrics dictionary without complex structures
            clean_metrics = self._create_clean_metrics(source_metrics)

            # Verify it's JSON serializable
            try:
                json.dumps(clean_metrics)
            except TypeError as e:
                print(f"WARNING: Metrics still not serializable: {e}")
                # Create even simpler metrics
                clean_metrics = self._create_minimal_metrics(source_metrics)

            # Prepare result data
            result_data = {
                'strategy_id': self.current_strategy.id if hasattr(self.current_strategy, 'id') else None,
                'symbol': self.ticker_edit.text(),
                'timeframe': self.timeframe_combo.currentText(),
                'start_date': self.start_date.date().toString("yyyy-MM-dd"),
                'end_date': self.end_date.date().toString("yyyy-MM-dd"),
                'initial_capital': self.capital_spin.value(),
                'final_capital': source_metrics.get('final_capital', 0),
                'total_return': source_metrics.get('total_return_pct', 0),
                'total_trades': source_metrics.get('total_trades', 0),
                'win_rate': source_metrics.get('win_rate', 0),
                'profit_factor': source_metrics.get('profit_factor', 0),
                'sharpe_ratio': source_metrics.get('sharpe_ratio'),
                'max_drawdown': source_metrics.get('max_drawdown', 0),
                'metrics': clean_metrics,
                'trades': [t.to_dict() for t in self.backtest_results['trades']]
            }

            # Get strategy ID
            if result_data['strategy_id'] is None:
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

    def display_fetched_data(self, df: pd.DataFrame):
        """Display fetched data sample in results area"""
        if df is None or df.empty:
            self.results_text.setText("No data available")
            return

        # Display basic info
        text = "=" * 80 + "\n"
        text += "FETCHED DATA SAMPLE\n"
        text += "=" * 80 + "\n\n"

        # Basic info
        text += f"Total bars: {len(df):,}\n"
        text += f"Date range: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}\n"
        text += f"Columns: {', '.join(df.columns.tolist())}\n\n"

        # Data sample (first 50 rows or available)
        sample_size = min(50, len(df))
        text += f"First {sample_size} rows:\n"
        text += "-" * 80 + "\n"

        # Create a formatted table
        if 'Open' in df.columns and 'High' in df.columns and 'Low' in df.columns and 'Close' in df.columns:
            # Format as OHLC table
            text += f"{'Date':<12} {'Open':>8} {'High':>8} {'Low':>8} {'Close':>8} {'Volume':>12}\n"
            text += "-" * 80 + "\n"

            for i in range(sample_size):
                if i < len(df):
                    row = df.iloc[i]
                    date_str = df.index[i].strftime('%Y-%m-%d')
                    open_price = f"{row['Open']:.2f}" if 'Open' in df.columns else "N/A"
                    high_price = f"{row['High']:.2f}" if 'High' in df.columns else "N/A"
                    low_price = f"{row['Low']:.2f}" if 'Low' in df.columns else "N/A"
                    close_price = f"{row['Close']:.2f}" if 'Close' in df.columns else "N/A"

                    # Format volume with thousands separator
                    if 'Volume' in df.columns and not pd.isna(row['Volume']):
                        volume_str = f"{int(row['Volume']):,}"
                    else:
                        volume_str = "N/A"

                    text += f"{date_str:<12} {open_price:>8} {high_price:>8} {low_price:>8} {close_price:>8} {volume_str:>12}\n"
        else:
            # Generic display
            for i in range(sample_size):
                if i < len(df):
                    date_str = df.index[i].strftime('%Y-%m-%d')
                    text += f"{date_str}: "
                    for col in df.columns:
                        if col != 'Volume':
                            text += f"{col}={df.iloc[i][col]:.2f} "
                        else:
                            text += f"{col}={int(df.iloc[i][col]):,} "
                    text += "\n"

        # Add statistics
        text += "\n" + "=" * 80 + "\n"
        text += "DATA STATISTICS\n"
        text += "=" * 80 + "\n\n"

        if 'Close' in df.columns:
            close_series = df['Close']
            text += f"Close Price Statistics:\n"
            text += f"  Min: {close_series.min():.2f}\n"
            text += f"  Max: {close_series.max():.2f}\n"
            text += f"  Mean: {close_series.mean():.2f}\n"
            text += f"  Std Dev: {close_series.std():.2f}\n"
            text += f"  Last Price: {close_series.iloc[-1]:.2f}\n\n"

        if 'Volume' in df.columns and df['Volume'].sum() > 0:
            volume_series = df['Volume']
            text += f"Volume Statistics:\n"
            text += f"  Avg Volume: {volume_series.mean():,.0f}\n"
            text += f"  Max Volume: {volume_series.max():,.0f}\n"
            text += f"  Total Volume: {volume_series.sum():,.0f}\n"

        self.results_text.setText(text)

        # Also update status bar
        self.statusBar().showMessage(f"Fetched {len(df)} bars. Showing first {sample_size} rows.")

    def _create_clean_metrics(self, source_metrics):
        """Create clean, JSON-serializable metrics"""
        clean_metrics = {}

        # Basic metrics that are always safe
        basic_keys = [
            'initial_capital', 'final_capital', 'total_return_pct',
            'total_trades', 'winning_trades', 'losing_trades', 'win_rate',
            'total_pnl', 'avg_win', 'avg_loss', 'profit_factor',
            'sharpe_ratio', 'max_drawdown', 'max_win', 'max_loss',
            'consecutive_wins', 'consecutive_losses', 'long_trades',
            'short_trades', 'avg_pnl_per_trade', 'std_pnl',
            'total_invested', 'avg_invested_per_trade', 'avg_roi_per_trade'
        ]

        for key in basic_keys:
            if key in source_metrics:
                value = source_metrics[key]
                clean_metrics[key] = self._convert_to_json_serializable(value)

        # Handle timedelta
        if 'avg_trade_duration' in source_metrics:
            dur = source_metrics['avg_trade_duration']
            clean_metrics['avg_trade_duration'] = str(dur) if isinstance(dur, pd.Timedelta) else dur

        # Handle pattern statistics SIMPLY - just store counts
        if 'pattern_statistics' in source_metrics:
            pattern_stats = source_metrics['pattern_statistics']
            if isinstance(pattern_stats, dict):
                # Create a simple version with just pattern names and counts
                simple_pattern_stats = {}
                try:
                    # Try to extract pattern counts
                    if 'count' in pattern_stats and isinstance(pattern_stats['count'], dict):
                        for pattern, count in pattern_stats['count'].items():
                            if isinstance(pattern, (str, int, float)):
                                simple_pattern_stats[str(pattern)] = {'count': count}

                    clean_metrics['pattern_statistics'] = simple_pattern_stats
                except:
                    # If we can't parse it, skip it
                    pass

        return clean_metrics

    def _create_minimal_metrics(self, source_metrics):
        """Create absolutely minimal metrics if cleaning fails"""
        return {
            'initial_capital': float(source_metrics.get('initial_capital', 0)),
            'final_capital': float(source_metrics.get('final_capital', 0)),
            'total_return_pct': float(source_metrics.get('total_return_pct', 0)),
            'total_trades': int(source_metrics.get('total_trades', 0)),
            'win_rate': float(source_metrics.get('win_rate', 0)),
            'profit_factor': float(source_metrics.get('profit_factor', 0)),
            'max_drawdown': float(source_metrics.get('max_drawdown', 0))
        }

    def _convert_to_json_serializable(self, value):
        """Convert any value to JSON-serializable format"""
        if isinstance(value, (int, float, str, bool, type(None))):
            return value
        elif isinstance(value, pd.Timestamp):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(value, pd.Timedelta):
            return str(value)
        elif isinstance(value, (np.integer, np.int64, np.int32)):
            return int(value)
        elif isinstance(value, (np.floating, np.float64, np.float32)):
            return float(value)
        elif isinstance(value, np.ndarray):
            return value.tolist()
        else:
            try:
                return str(value)
            except:
                return None

    def debug_metrics_structure(self, metrics, indent=0):
        """Debug: Print metrics structure to find tuple keys"""
        prefix = "  " * indent
        for key, value in metrics.items():
            print(f"{prefix}Key: {key} (type: {type(key)})")
            if isinstance(key, tuple):
                print(f"{prefix}  WARNING: TUPLE KEY FOUND: {key}")

            if isinstance(value, dict):
                print(f"{prefix}  Value is dict:")
                self.debug_metrics_structure(value, indent + 2)
            elif isinstance(value, (list, tuple)):
                print(f"{prefix}  Value is list/tuple with {len(value)} items")
                if value and isinstance(value[0], dict):
                    for i, item in enumerate(value[:2]):  # Just first 2
                        print(f"{prefix}    Item {i}:")
                        self.debug_metrics_structure(item, indent + 3)
            else:
                print(f"{prefix}  Value: {value} (type: {type(value)})")

class IndicatorSelectionDialog(QDialog):
    """Dialog for selecting which indicators to show"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Indicators")
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)

        # Volume checkbox
        self.volume_check = QCheckBox("Show Volume")
        self.volume_check.setChecked(True)
        layout.addWidget(self.volume_check)

        # MACD checkbox
        self.macd_check = QCheckBox("Show MACD")
        self.macd_check.setChecked(True)
        layout.addWidget(self.macd_check)

        # RSI checkbox
        self.rsi_check = QCheckBox("Show RSI")
        self.rsi_check.setChecked(True)
        layout.addWidget(self.rsi_check)

        # Buttons
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def get_selections(self):
        """Get selected indicators"""
        return (
            self.volume_check.isChecked(),
            self.macd_check.isChecked(),
            self.rsi_check.isChecked()
        )