from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pandas as pd
from src.config.database import Database
from src.utils.logger import get_logger
import sqlite3

logger = get_logger('app')


class DatabaseViewer(QMainWindow):
    """Database viewer window with delete functionality"""

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

        # Tab widget with only 2 tabs
        self.tabs = QTabWidget()

        # Strategies tab
        self.strategies_table = QTableWidget()
        self.tabs.addTab(self.strategies_table, "Strategies")

        # Results tab
        self.results_table = QTableWidget()
        self.tabs.addTab(self.results_table, "Backtest Results")

        layout.addWidget(self.tabs)

        # Control buttons - TOP ROW
        top_button_layout = QHBoxLayout()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_data)
        top_button_layout.addWidget(refresh_btn)

        export_btn = QPushButton("Export to CSV")
        export_btn.clicked.connect(self.export_to_csv)
        top_button_layout.addWidget(export_btn)

        top_button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        top_button_layout.addWidget(close_btn)

        layout.addLayout(top_button_layout)

        # DELETE buttons - BOTTOM ROW
        delete_button_layout = QHBoxLayout()
        delete_button_layout.addWidget(QLabel("Delete Operations:"))

        # Strategy delete buttons
        self.delete_strategy_btn = QPushButton("Delete Selected Strategy")
        self.delete_strategy_btn.clicked.connect(self.delete_selected_strategy)
        self.delete_strategy_btn.setStyleSheet("background-color: #ffcccc;")
        delete_button_layout.addWidget(self.delete_strategy_btn)

        self.delete_all_strategies_btn = QPushButton("Delete ALL Strategies")
        self.delete_all_strategies_btn.clicked.connect(self.delete_all_strategies)
        self.delete_all_strategies_btn.setStyleSheet("background-color: #ff6666; color: white;")
        delete_button_layout.addWidget(self.delete_all_strategies_btn)

        delete_button_layout.addSpacing(20)

        # Results delete buttons
        self.delete_result_btn = QPushButton("Delete Selected Result")
        self.delete_result_btn.clicked.connect(self.delete_selected_result)
        self.delete_result_btn.setStyleSheet("background-color: #ccccff;")
        delete_button_layout.addWidget(self.delete_result_btn)

        self.delete_all_results_btn = QPushButton("Delete ALL Results")
        self.delete_all_results_btn.clicked.connect(self.delete_all_results)
        self.delete_all_results_btn.setStyleSheet("background-color: #6666ff; color: white;")
        delete_button_layout.addWidget(self.delete_all_results_btn)

        delete_button_layout.addStretch()

        layout.addLayout(delete_button_layout)

    def load_data(self):
        """Load data from database"""
        try:
            # Load strategies
            strategies = self.database.load_strategies()
            self.display_strategies(strategies)

            # Load results
            results = self.database.load_backtest_results()
            self.display_results(results)

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

        # Prepare data - REMOVED timeframe
        headers = ['ID', 'Name', 'Patterns Count', 'Entry Rule', 'Exit Rule',
                  'Position Size %', 'Created']

        self.strategies_table.setRowCount(len(strategies))
        self.strategies_table.setColumnCount(len(headers))
        self.strategies_table.setHorizontalHeaderLabels(headers)

        for row, strategy in enumerate(strategies):
            self.strategies_table.setItem(row, 0, QTableWidgetItem(str(strategy.get('id', ''))))
            self.strategies_table.setItem(row, 1, QTableWidgetItem(strategy.get('name', '')))
            self.strategies_table.setItem(row, 2, QTableWidgetItem(str(len(strategy.get('patterns', [])))))
            self.strategies_table.setItem(row, 3, QTableWidgetItem(strategy.get('entry_rule', '')))
            self.strategies_table.setItem(row, 4, QTableWidgetItem(strategy.get('exit_rule', '')))
            # Position Size %
            pos_size = str(strategy.get('position_size_pct', '10'))
            self.strategies_table.setItem(row, 5, QTableWidgetItem(pos_size))
            self.strategies_table.setItem(row, 6, QTableWidgetItem(str(strategy.get('created_at', ''))))

        self.strategies_table.resizeColumnsToContents()

    def display_results(self, results):
        """Display backtest results in table"""
        if not results:
            self.results_table.setRowCount(0)
            self.results_table.setColumnCount(1)
            self.results_table.setHorizontalHeaderLabels(["No results found"])
            return

        headers = ['ID', 'Strategy ID', 'Symbol', 'Timeframe', 'Start', 'End',
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
            else:
                QMessageBox.warning(self, "Warning", "No data to export")
                return

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

    # ========== DELETE METHODS ==========

    def delete_selected_strategy(self):
        """Delete selected strategy from database"""
        try:
            table = self.strategies_table
            selected_rows = set()

            for item in table.selectedItems():
                selected_rows.add(item.row())

            if not selected_rows:
                QMessageBox.warning(self, "Warning", "No strategy selected")
                return

            # Get strategy IDs and names for confirmation
            strategies_to_delete = []
            for row in selected_rows:
                id_item = table.item(row, 0)
                name_item = table.item(row, 1)
                if id_item and name_item:
                    strategies_to_delete.append({
                        'id': int(id_item.text()),
                        'name': name_item.text()
                    })

            # Confirm deletion
            strategy_names = "\n".join([f"- {s['name']} (ID: {s['id']})" for s in strategies_to_delete])
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Are you sure you want to delete {len(strategies_to_delete)} strategy(ies)?\n\n"
                f"{strategy_names}\n\n"
                f"Warning: This will also delete all associated backtest results!",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                deleted_count = 0
                for strategy in strategies_to_delete:
                    try:
                        self.database.delete_strategy(strategy['id'])
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Error deleting strategy {strategy['id']}: {str(e)}")

                # Reload data
                self.load_data()

                QMessageBox.information(self, "Success",
                    f"Deleted {deleted_count} of {len(strategies_to_delete)} strategy(ies)")
                logger.info(f"Deleted {deleted_count} strategies from database")

        except Exception as e:
            logger.error(f"Error deleting strategy: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to delete strategy: {str(e)}")

    def delete_all_strategies(self):
        """Delete ALL strategies from database"""
        try:
            # Get total count
            strategies = self.database.load_strategies()
            if not strategies:
                QMessageBox.information(self, "Info", "No strategies to delete")
                return

            # Confirm deletion - use StandardButtons correctly
            reply = QMessageBox.critical(
                self,
                "DANGER: Delete ALL Strategies",
                f"ARE YOU ABSOLUTELY SURE?\n\n"
                f"This will delete ALL {len(strategies)} strategies and ALL associated backtest results!\n\n"
                f"This action cannot be undone!\n\n"
                f"Type 'DELETE ALL STRATEGIES' to confirm:",
                QMessageBox.Cancel | QMessageBox.Ok,  # Use StandardButtons
                QMessageBox.Cancel
            )

            if reply == QMessageBox.Ok:  # Check against StandardButton
                # Ask for text confirmation
                text, ok = QInputDialog.getText(
                    self,
                    "Final Confirmation",
                    "Type 'DELETE ALL STRATEGIES' to confirm deletion:"
                )

                if ok and text == "DELETE ALL STRATEGIES":
                    # Delete all strategies using the proper database method
                    self.database.delete_all_strategies()

                    # Reload data
                    self.load_data()

                    QMessageBox.information(
                        self,
                        "Success",
                        f"Deleted {len(strategies)} strategies from database"
                    )
                    logger.info(f"Deleted {len(strategies)} strategies from database")
                else:
                    QMessageBox.information(self, "Cancelled", "Deletion cancelled")

        except Exception as e:
            logger.error(f"Error deleting all strategies: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to delete strategies: {str(e)}")

    def delete_selected_result(self):
        """Delete selected backtest result from database"""
        try:
            table = self.results_table
            selected_rows = set()

            for item in table.selectedItems():
                selected_rows.add(item.row())

            if not selected_rows:
                QMessageBox.warning(self, "Warning", "No result selected")
                return

            # Get result IDs for confirmation
            results_to_delete = []
            for row in selected_rows:
                id_item = table.item(row, 0)
                symbol_item = table.item(row, 2)
                if id_item and symbol_item:
                    results_to_delete.append({
                        'id': int(id_item.text()),
                        'symbol': symbol_item.text()
                    })

            # Confirm deletion
            result_info = "\n".join([f"- {r['symbol']} (ID: {r['id']})" for r in results_to_delete])
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Are you sure you want to delete {len(results_to_delete)} backtest result(s)?\n\n"
                f"{result_info}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                deleted_count = 0
                for result in results_to_delete:
                    try:
                        # We need to add a delete_result method to Database class
                        self._delete_backtest_result(result['id'])
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Error deleting result {result['id']}: {str(e)}")

                # Reload data
                self.load_data()

                QMessageBox.information(self, "Success",
                    f"Deleted {deleted_count} of {len(results_to_delete)} backtest result(s)")
                logger.info(f"Deleted {deleted_count} backtest results from database")

        except Exception as e:
            logger.error(f"Error deleting result: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to delete result: {str(e)}")

    def delete_all_results(self):
        """Delete ALL backtest results from database"""
        try:
            # Get total count
            results = self.database.load_backtest_results()
            if not results:
                QMessageBox.information(self, "Info", "No results to delete")
                return

            # Confirm deletion - use StandardButtons correctly
            reply = QMessageBox.critical(
                self,
                "DANGER: Delete ALL Results",
                f"ARE YOU ABSOLUTELY SURE?\n\n"
                f"This will delete ALL {len(results)} backtest results!\n\n"
                f"This action cannot be undone!\n\n"
                f"Type 'DELETE ALL RESULTS' to confirm:",
                QMessageBox.Cancel | QMessageBox.Ok,  # Use StandardButtons
                QMessageBox.Cancel
            )

            if reply == QMessageBox.Ok:  # Check against StandardButton
                # Ask for text confirmation
                text, ok = QInputDialog.getText(
                    self,
                    "Final Confirmation",
                    "Type 'DELETE ALL RESULTS' to confirm deletion:"
                )

                if ok and text == "DELETE ALL RESULTS":
                    # Delete all results using the proper database method
                    self.database.delete_all_backtest_results()

                    # Reload data
                    self.load_data()

                    QMessageBox.information(
                        self,
                        "Success",
                        f"Deleted {len(results)} backtest results from database"
                    )
                    logger.info(f"Deleted {len(results)} backtest results from database")
                else:
                    QMessageBox.information(self, "Cancelled", "Deletion cancelled")

        except Exception as e:
            logger.error(f"Error deleting all results: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to delete results: {str(e)}")

    def _delete_backtest_result(self, result_id: int):
        """Helper method to delete a backtest result"""
        self.database.delete_backtest_result(result_id)