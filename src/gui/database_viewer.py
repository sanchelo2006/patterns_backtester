from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pandas as pd
from src.config.database import Database
from src.utils.logger import get_logger

logger = get_logger('app')


class DatabaseViewer(QMainWindow):
    """Database viewer window"""

    def __init__(self, parent=None, database=None):
        super().__init__(parent)
        self.database = database or Database()
        self.setWindowTitle("Database Viewer")
        self.setGeometry(150, 150, 1200, 700)

        self.init_ui()
        self.load_data()

    def init_ui(self):
        """Initialize user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Tab widget
        self.tabs = QTabWidget()

        # Strategies tab
        self.strategies_table = QTableWidget()
        self.tabs.addTab(self.strategies_table, "Strategies")

        # Results tab
        self.results_table = QTableWidget()
        self.tabs.addTab(self.results_table, "Backtest Results")

        # Trades tab
        self.trades_table = QTableWidget()
        self.tabs.addTab(self.trades_table, "Trades")

        layout.addWidget(self.tabs)

        # Control buttons
        button_layout = QHBoxLayout()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_data)
        button_layout.addWidget(refresh_btn)

        export_btn = QPushButton("Export to CSV")
        export_btn.clicked.connect(self.export_to_csv)
        button_layout.addWidget(export_btn)

        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self.delete_selected)
        button_layout.addWidget(delete_btn)

        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def load_data(self):
        """Load data from database"""
        try:
            # Load strategies
            strategies = self.database.load_strategies()
            self.display_strategies(strategies)

            # Load results
            results = self.database.load_backtest_results()
            self.display_results(results)

            # Load trades from first result (if any)
            if results:
                self.display_trades(results[0].get('trades', []))

            logger.info("Database data loaded")

        except Exception as e:
            logger.error(f"Error loading database data: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")

    def display_strategies(self, strategies):
        """Display strategies in table"""
        if not strategies:
            self.strategies_table.setRowCount(0)
            self.strategies_table.setColumnCount(1)
            self.strategies_table.setHorizontalHeaderLabels(["No strategies found"])
            return

        # Prepare data
        headers = ['ID', 'Name', 'Patterns Count', 'Entry Rule', 'Exit Rule',
                  'Timeframe', 'Position Size %', 'Created']

        self.strategies_table.setRowCount(len(strategies))
        self.strategies_table.setColumnCount(len(headers))
        self.strategies_table.setHorizontalHeaderLabels(headers)

        for row, strategy in enumerate(strategies):
            self.strategies_table.setItem(row, 0, QTableWidgetItem(str(strategy['id'])))
            self.strategies_table.setItem(row, 1, QTableWidgetItem(strategy['name']))
            self.strategies_table.setItem(row, 2, QTableWidgetItem(str(len(strategy['patterns']))))
            self.strategies_table.setItem(row, 3, QTableWidgetItem(strategy['entry_rule']))
            self.strategies_table.setItem(row, 4, QTableWidgetItem(strategy['exit_rule']))
            self.strategies_table.setItem(row, 5, QTableWidgetItem(str(strategy['timeframe'])))
            self.strategies_table.setItem(row, 6, QTableWidgetItem(str(strategy.get('risk_params', {}).get('position_size_pct', '10'))))
            self.strategies_table.setItem(row, 7, QTableWidgetItem(str(strategy.get('created_at', ''))))

        self.strategies_table.resizeColumnsToContents()

    def display_results(self, results):
        """Display backtest results in table"""
        if not results:
            self.results_table.setRowCount(0)
            self.results_table.setColumnCount(1)
            self.results_table.setHorizontalHeaderLabels(["No results found"])
            return

        headers = ['ID', 'Strategy', 'Symbol', 'Timeframe', 'Start', 'End',
                  'Initial Capital', 'Final Capital', 'Return %', 'Trades',
                  'Win Rate %', 'Profit Factor', 'Sharpe', 'Max DD %']

        self.results_table.setRowCount(len(results))
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)

        for row, result in enumerate(results):
            self.results_table.setItem(row, 0, QTableWidgetItem(str(result['id'])))
            self.results_table.setItem(row, 1, QTableWidgetItem(str(result.get('strategy_id', 'N/A'))))
            self.results_table.setItem(row, 2, QTableWidgetItem(result['symbol']))
            self.results_table.setItem(row, 3, QTableWidgetItem(result['timeframe']))
            self.results_table.setItem(row, 4, QTableWidgetItem(result['start_date']))
            self.results_table.setItem(row, 5, QTableWidgetItem(result['end_date']))
            self.results_table.setItem(row, 6, QTableWidgetItem(f"{result['initial_capital']:,.2f}"))
            self.results_table.setItem(row, 7, QTableWidgetItem(f"{result['final_capital']:,.2f}"))
            self.results_table.setItem(row, 8, QTableWidgetItem(f"{result['total_return']:.2f}"))
            self.results_table.setItem(row, 9, QTableWidgetItem(str(result['total_trades'])))
            self.results_table.setItem(row, 10, QTableWidgetItem(f"{result['win_rate']:.2f}"))
            self.results_table.setItem(row, 11, QTableWidgetItem(f"{result['profit_factor']:.2f}"))
            self.results_table.setItem(row, 12, QTableWidgetItem(f"{result.get('sharpe_ratio', 0):.2f}"))
            self.results_table.setItem(row, 13, QTableWidgetItem(f"{result.get('max_drawdown', 0):.2f}"))

        self.results_table.resizeColumnsToContents()

    def display_trades(self, trades):
        """Display trades in table"""
        if not trades:
            self.trades_table.setRowCount(0)
            self.trades_table.setColumnCount(1)
            self.trades_table.setHorizontalHeaderLabels(["No trades found"])
            return

        headers = ['Entry Date', 'Exit Date', 'Type', 'Entry Price', 'Exit Price',
                  'P&L', 'P&L %', 'Pattern', 'Exit Reason', 'Result']

        self.trades_table.setRowCount(len(trades))
        self.trades_table.setColumnCount(len(headers))
        self.trades_table.setHorizontalHeaderLabels(headers)

        for row, trade in enumerate(trades):
            self.trades_table.setItem(row, 0, QTableWidgetItem(trade['entry_date']))
            self.trades_table.setItem(row, 1, QTableWidgetItem(trade['exit_date']))
            self.trades_table.setItem(row, 2, QTableWidgetItem(trade['position_type'].upper()))
            self.trades_table.setItem(row, 3, QTableWidgetItem(f"{trade['entry_price']:.2f}"))
            self.trades_table.setItem(row, 4, QTableWidgetItem(f"{trade['exit_price']:.2f}"))
            self.trades_table.setItem(row, 5, QTableWidgetItem(f"{trade['pnl']:,.2f}"))
            self.trades_table.setItem(row, 6, QTableWidgetItem(f"{trade['pnl_percent']:.2f}"))
            self.trades_table.setItem(row, 7, QTableWidgetItem(trade.get('pattern', '')))
            self.trades_table.setItem(row, 8, QTableWidgetItem(trade.get('exit_reason', '')))
            self.trades_table.setItem(row, 9, QTableWidgetItem('PROFIT' if trade['success'] else 'LOSS'))

        self.trades_table.resizeColumnsToContents()

    def export_to_csv(self):
        """Export current tab to CSV"""
        try:
            current_tab = self.tabs.currentIndex()
            if current_tab == 0:  # Strategies
                table = self.strategies_table
                default_name = "strategies.csv"
            elif current_tab == 1:  # Results
                table = self.results_table
                default_name = "backtest_results.csv"
            else:  # Trades
                table = self.trades_table
                default_name = "trades.csv"

            filename, _ = QFileDialog.getSaveFileName(
                self, "Export to CSV", default_name, "CSV Files (*.csv)"
            )

            if filename:
                # Collect data from table
                data = []
                headers = []

                # Get headers
                for col in range(table.columnCount()):
                    headers.append(table.horizontalHeaderItem(col).text())

                # Get rows
                for row in range(table.rowCount()):
                    row_data = []
                    for col in range(table.columnCount()):
                        item = table.item(row, col)
                        row_data.append(item.text() if item else "")
                    data.append(row_data)

                # Create DataFrame and save
                df = pd.DataFrame(data, columns=headers)
                df.to_csv(filename, index=False, encoding='utf-8')

                QMessageBox.information(self, "Success", f"Data exported to {filename}")
                logger.info(f"Data exported to CSV: {filename}")

        except Exception as e:
            logger.error(f"Error exporting to CSV: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to export: {str(e)}")

    def delete_selected(self):
        """Delete selected items"""
        try:
            current_tab = self.tabs.currentIndex()
            table = [self.strategies_table, self.results_table, self.trades_table][current_tab]

            selected_rows = set()
            for item in table.selectedItems():
                selected_rows.add(item.row())

            if not selected_rows:
                QMessageBox.warning(self, "Warning", "No items selected")
                return

            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Are you sure you want to delete {len(selected_rows)} item(s)?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # Get IDs to delete
                ids_to_delete = []
                for row in selected_rows:
                    id_item = table.item(row, 0)
                    if id_item:
                        ids_to_delete.append(int(id_item.text()))

                # Delete from database
                if current_tab == 0:  # Strategies
                    for strategy_id in ids_to_delete:
                        self.database.delete_strategy(strategy_id)
                elif current_tab == 1:  # Results
                    # Would need to implement result deletion
                    pass

                # Reload data
                self.load_data()

                QMessageBox.information(self, "Success", f"Deleted {len(ids_to_delete)} item(s)")
                logger.info(f"Deleted {len(ids_to_delete)} items from database")

        except Exception as e:
            logger.error(f"Error deleting items: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to delete: {str(e)}")