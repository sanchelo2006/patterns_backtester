import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import plot
import webbrowser
from pathlib import Path

from src.config.settings import CANDLE_PATTERNS, DEFAULT_CAPITAL, DEFAULT_POSITION_SIZE, DEFAULT_THRESHOLD
from src.data.moex_client import MOEXClient
from src.data.crypto_client import CryptoClient
from src.patterns.pattern_detector import PatternDetector
from src.backtest.engine import BacktestEngine
from src.backtest.metrics import MetricsCalculator
from src.visualization.chart_builder import ChartBuilder
from src.utils.logger import log_user_action, log_error, log_app_info
from src.utils.file_handler import FileHandler


class BacktestApp(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MOEX & Crypto Backtest System")
        self.setGeometry(100, 100, 1400, 900)

        self.data_client = None
        self.current_data = None
        self.backtest_results = None
        self.file_handler = FileHandler()

        self.init_ui()
        log_app_info("Application started")

    def init_ui(self):
        """Initialize user interface"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)

        # Menu bar
        self.create_menu_bar()

        # Control panel
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)

        # Results area
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        main_layout.addWidget(self.results_text)

        # Status bar
        self.statusBar().showMessage("Ready")

    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('File')

        save_action = QAction('Save Results', self)
        save_action.triggered.connect(self.save_results)
        file_menu.addAction(save_action)

        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu('Tools')

        chart_action = QAction('Create Chart', self)
        chart_action.triggered.connect(self.create_chart)
        tools_menu.addAction(chart_action)

    def create_control_panel(self) -> QWidget:
        """Create control panel with all inputs"""
        panel = QGroupBox("Backtest Parameters")
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

        # Date range
        layout.addWidget(QLabel("Start Date:"), 2, 0)
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addYears(-1))
        self.start_date.setCalendarPopup(True)
        layout.addWidget(self.start_date, 2, 1)

        layout.addWidget(QLabel("End Date:"), 2, 2)
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        layout.addWidget(self.end_date, 2, 3)

        # Capital and position size
        layout.addWidget(QLabel("Initial Capital:"), 3, 0)
        self.capital_spin = QDoubleSpinBox()
        self.capital_spin.setRange(1000, 100000000)
        self.capital_spin.setValue(DEFAULT_CAPITAL)
        self.capital_spin.setSuffix(" RUB")
        layout.addWidget(self.capital_spin, 3, 1)

        layout.addWidget(QLabel("Position Size:"), 3, 2)
        self.position_spin = QDoubleSpinBox()
        self.position_spin.setRange(1, 100)
        self.position_spin.setValue(DEFAULT_POSITION_SIZE)
        self.position_spin.setSuffix(" %")
        layout.addWidget(self.position_spin, 3, 3)

        # Pattern threshold
        layout.addWidget(QLabel("Pattern Threshold:"), 4, 0)
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setValue(int(DEFAULT_THRESHOLD * 100))
        layout.addWidget(self.threshold_slider, 4, 1)

        self.threshold_label = QLabel(f"{DEFAULT_THRESHOLD:.2f}")
        layout.addWidget(self.threshold_label, 4, 2)
        self.threshold_slider.valueChanged.connect(
            lambda v: self.threshold_label.setText(f"{v/100:.2f}")
        )

        # Pattern selection
        layout.addWidget(QLabel("Select Patterns:"), 5, 0)
        self.pattern_list = QListWidget()
        self.pattern_list.addItems(CANDLE_PATTERNS)
        self.pattern_list.setSelectionMode(QListWidget.MultiSelection)
        self.select_all_patterns()
        layout.addWidget(self.pattern_list, 5, 1, 3, 3)

        # Buttons
        button_layout = QHBoxLayout()

        self.fetch_button = QPushButton("Fetch Data")
        self.fetch_button.clicked.connect(self.fetch_data)
        button_layout.addWidget(self.fetch_button)

        self.run_button = QPushButton("Run Backtest")
        self.run_button.clicked.connect(self.run_backtest)
        self.run_button.setEnabled(False)
        button_layout.addWidget(self.run_button)

        self.chart_button = QPushButton("Create Chart")
        self.chart_button.clicked.connect(self.create_chart)
        self.chart_button.setEnabled(False)
        button_layout.addWidget(self.chart_button)

        self.save_button = QPushButton("Save Results")
        self.save_button.clicked.connect(self.save_results)
        self.save_button.setEnabled(False)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout, 8, 0, 1, 4)

        panel.setLayout(layout)
        return panel

    def select_all_patterns(self):
        """Select all patterns in the list"""
        for i in range(self.pattern_list.count()):
            item = self.pattern_list.item(i)
            item.setSelected(True)

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

            if not ticker:
                QMessageBox.warning(self, "Warning", "Please enter a ticker/symbol")
                return

            log_user_action("Fetch data", {
                "market": market,
                "ticker": ticker,
                "start_date": start_date,
                "end_date": end_date
            })

            self.statusBar().showMessage(f"Fetching {market} data for {ticker}...")
            QApplication.processEvents()

            if market == "MOEX":
                self.data_client = MOEXClient()
                data = self.data_client.get_data(ticker, start_date, end_date)
            else:
                self.data_client = CryptoClient()
                data = self.data_client.get_data(ticker, start_date, end_date)

            if data is not None and not data.empty:
                self.current_data = data
                self.run_button.setEnabled(True)
                self.statusBar().showMessage(
                    f"Fetched {len(data)} bars for {ticker}"
                )
                log_app_info(f"Data fetched successfully: {len(data)} bars")
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
            # Get parameters
            patterns_to_use = [
                item.text()
                for item in self.pattern_list.selectedItems()
            ]

            if not patterns_to_use:
                QMessageBox.warning(self, "Warning", "Please select at least one pattern")
                return

            threshold = self.threshold_slider.value() / 100
            initial_capital = self.capital_spin.value()
            position_size_pct = self.position_spin.value()

            log_user_action("Run backtest", {
                "patterns_count": len(patterns_to_use),
                "threshold": threshold,
                "initial_capital": initial_capital,
                "position_size": position_size_pct
            })

            self.statusBar().showMessage("Running backtest...")
            QApplication.processEvents()

            # Detect patterns
            detector = PatternDetector(threshold=threshold)
            data_with_patterns = detector.detect_all_patterns(self.current_data.copy())

            # Run backtest
            engine = BacktestEngine(
                initial_capital=initial_capital,
                position_size_pct=position_size_pct
            )

            self.backtest_results = engine.run(data_with_patterns, patterns_to_use)

            # Calculate detailed metrics
            metrics_calc = MetricsCalculator()
            detailed_metrics = metrics_calc.calculate_detailed_metrics(
                self.backtest_results['trades'],
                self.backtest_results['equity_curve']
            )

            self.backtest_results['metrics'].update(detailed_metrics)

            # Display results
            self.display_results()

            self.chart_button.setEnabled(True)
            self.save_button.setEnabled(True)
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
        text += "BACKTEST RESULTS\n"
        text += "=" * 80 + "\n\n"

        text += f"Initial Capital: {metrics.get('initial_capital', 0):,.2f} RUB\n"
        text += f"Final Capital: {metrics.get('final_capital', 0):,.2f} RUB\n"
        text += f"Total Return: {metrics.get('total_return_pct', 0):.2f}%\n\n"

        text += f"Total Trades: {metrics.get('total_trades', 0)}\n"
        text += f"Winning Trades: {metrics.get('winning_trades', 0)}\n"
        text += f"Losing Trades: {metrics.get('losing_trades', 0)}\n"
        text += f"Win Rate: {metrics.get('win_rate', 0):.2f}%\n\n"

        text += f"Total P&L: {metrics.get('total_pnl', 0):,.2f} RUB\n"
        text += f"Average P&L per Trade: {metrics.get('avg_pnl', 0):,.2f} RUB\n"
        text += f"Average Win: {metrics.get('avg_win', 0):,.2f} RUB\n"
        text += f"Average Loss: {metrics.get('avg_loss', 0):,.2f} RUB\n"
        text += f"Profit Factor: {metrics.get('profit_factor', 0):.2f}\n\n"

        text += f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}\n"
        text += f"Maximum Drawdown: {metrics.get('max_drawdown', 0):.2f}%\n\n"

        text += "=" * 80 + "\n"
        text += "TRADE LIST\n"
        text += "=" * 80 + "\n\n"

        for i, trade in enumerate(trades, 1):
            text += f"Trade #{i}:\n"
            text += f"  Type: {trade.position_type.upper()}\n"
            text += f"  Entry: {trade.entry_date} at {trade.entry_price:.2f}\n"
            text += f"  Exit: {trade.exit_date} at {trade.exit_price:.2f}\n"
            text += f"  P&L: {trade.pnl:,.2f} RUB ({trade.pnl_percent:.2f}%)\n"
            text += f"  Pattern: {trade.pattern}\n"
            text += f"  Result: {'PROFIT' if trade.success else 'LOSS'}\n"
            text += "-" * 40 + "\n"

        self.results_text.setText(text)

    def create_chart(self):
        """Create interactive candlestick chart"""
        try:
            if not self.backtest_results:
                QMessageBox.warning(self, "Warning", "Please run backtest first")
                return

            log_user_action("Create chart")
            self.statusBar().showMessage("Creating chart...")
            QApplication.processEvents()

            # Create chart
            chart_builder = ChartBuilder()
            fig = chart_builder.create_candlestick_chart(
                self.backtest_results['df'],
                self.backtest_results['trades'],
                title=f"Backtest Results - {self.ticker_edit.text()}"
            )

            # Save as HTML and open in browser
            filename = f"chart_{self.ticker_edit.text()}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
            self.file_handler.save_chart_html(fig, filename)

            # Open in default browser
            chart_path = Path("results") / f"{filename}.html"
            webbrowser.open(f"file://{chart_path.absolute()}")

            self.statusBar().showMessage("Chart created and opened in browser")
            log_app_info("Chart created successfully")

        except Exception as e:
            log_error(e, "create_chart")
            QMessageBox.critical(self, "Error", f"Failed to create chart: {str(e)}")
            self.statusBar().showMessage("Error creating chart")

    def save_results(self):
        """Save backtest results to Excel"""
        try:
            if not self.backtest_results:
                QMessageBox.warning(self, "Warning", "No results to save")
                return

            log_user_action("Save results")

            # Get filename from user
            filename, ok = QInputDialog.getText(
                self,
                "Save Results",
                "Enter filename:",
                text=f"backtest_{self.ticker_edit.text()}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
            )

            if ok and filename:
                if self.file_handler.save_to_excel(self.backtest_results, filename):
                    QMessageBox.information(self, "Success", f"Results saved to results/{filename}.xlsx")
                    self.statusBar().showMessage(f"Results saved to {filename}.xlsx")
                    log_app_info(f"Results saved: {filename}.xlsx")
                else:
                    QMessageBox.warning(self, "Warning", "Failed to save results")

        except Exception as e:
            log_error(e, "save_results")
            QMessageBox.critical(self, "Error", f"Failed to save results: {str(e)}")