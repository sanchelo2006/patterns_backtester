import sqlite3
from pathlib import Path
from typing import Dict, List, Any
import json
from src.utils.logger import get_logger

logger = get_logger('app')


class Database:
    """SQLite database handler for strategies and results"""

    def __init__(self, db_path: str = "database/strategies.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.init_database()
        self.update_database_schema()

    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Strategies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                patterns TEXT NOT NULL,
                entry_rule TEXT NOT NULL,
                entry_params TEXT,
                exit_rule TEXT NOT NULL,
                exit_params TEXT,
                timeframe TEXT,
                risk_params TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Backtest results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id INTEGER,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                initial_capital REAL NOT NULL,
                final_capital REAL NOT NULL,
                total_return REAL NOT NULL,
                total_trades INTEGER NOT NULL,
                win_rate REAL NOT NULL,
                profit_factor REAL NOT NULL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                metrics TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (strategy_id) REFERENCES strategies (id)
            )
        ''')


        conn.commit()
        conn.close()
        logger.info("Database initialized")

    def save_strategy(self, strategy_data: Dict[str, Any]) -> int:
        """Save strategy to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO strategies
            (name, patterns, entry_rule, entry_params, exit_rule, exit_params, timeframe, risk_params)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            strategy_data['name'],
            json.dumps(strategy_data['patterns']),
            strategy_data['entry_rule'],
            json.dumps(strategy_data.get('entry_params', {})),
            strategy_data['exit_rule'],
            json.dumps(strategy_data.get('exit_params', {})),
            strategy_data.get('timeframe'),
            json.dumps(strategy_data.get('risk_params', {}))
        ))

        strategy_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Strategy saved: {strategy_data['name']} (ID: {strategy_id})")
        return strategy_id

    def load_strategies(self) -> List[Dict[str, Any]]:
        """Load all strategies from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM strategies ORDER BY created_at DESC')
        rows = cursor.fetchall()

        strategies = []
        for row in rows:
            try:
                # Parse JSON fields
                patterns = json.loads(row['patterns'] or '[]')
                entry_params = json.loads(row['entry_params'] or '{}')
                exit_params = json.loads(row['exit_params'] or '{}')
                risk_params = json.loads(row['risk_params'] or '{}')

                # Extract position size from risk_params or use default
                position_size_pct = risk_params.get('position_size_pct', 10.0)

                # Extract stop_loss and take_profit from exit_params
                stop_loss_pct = exit_params.get('stop_loss_pct',
                            exit_params.get('trailing_stop_pct', 2.0))
                take_profit_pct = exit_params.get('take_profit_pct', 4.0)

                # Extract max_bars_hold from exit_params or risk_params
                max_bars_hold = exit_params.get('max_bars',
                            risk_params.get('max_bars_hold', 20))

                strategy = {
                    'id': row['id'],
                    'name': row['name'],
                    'patterns': patterns,
                    'entry_rule': row['entry_rule'],
                    'entry_params': entry_params,
                    'exit_rule': row['exit_rule'],
                    'exit_params': exit_params,
                    'position_size_pct': position_size_pct,
                    'stop_loss_pct': stop_loss_pct,
                    'take_profit_pct': take_profit_pct,
                    'max_bars_hold': max_bars_hold,
                    'created_at': row['created_at'],
                    'enabled': True
                }

                # Handle old strategies that might have timeframe
                if row['timeframe']:
                    strategy['timeframe'] = row['timeframe']

                strategies.append(strategy)

            except json.JSONDecodeError as e:
                logger.error(f"Error parsing strategy {row['id']}: {str(e)}")
                # Create a basic strategy with defaults
                strategies.append({
                    'id': row['id'],
                    'name': row['name'],
                    'patterns': [],
                    'entry_rule': row['entry_rule'],
                    'entry_params': {},
                    'exit_rule': row['exit_rule'],
                    'exit_params': {},
                    'position_size_pct': 10.0,
                    'stop_loss_pct': 2.0,
                    'take_profit_pct': 4.0,
                    'max_bars_hold': 20,
                    'created_at': row['created_at'],
                    'enabled': True
                })

        conn.close()
        return strategies

    def delete_strategy(self, strategy_id: int):
        """Delete strategy from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM strategies WHERE id = ?', (strategy_id,))
        conn.commit()
        conn.close()

        logger.info(f"Strategy deleted: ID {strategy_id}")

    def save_backtest_result(self, result_data: Dict[str, Any]) -> int:
        """Save backtest result to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO backtest_results
            (strategy_id, symbol, timeframe, start_date, end_date, initial_capital,
             final_capital, total_return, total_trades, win_rate, profit_factor,
             sharpe_ratio, max_drawdown, metrics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result_data.get('strategy_id'),
            result_data['symbol'],
            result_data['timeframe'],
            result_data['start_date'],
            result_data['end_date'],
            result_data['initial_capital'],
            result_data['final_capital'],
            result_data['total_return'],
            result_data['total_trades'],
            result_data['win_rate'],
            result_data['profit_factor'],
            result_data.get('sharpe_ratio'),
            result_data.get('max_drawdown'),
            json.dumps(result_data.get('metrics', {}))
        ))

        result_id = cursor.lastrowid

        conn.commit()
        conn.close()

        logger.info(f"Backtest result saved: ID {result_id}")
        return result_id

    def load_backtest_results(self, strategy_id: int = None) -> List[Dict[str, Any]]:
        """Load backtest results from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if strategy_id:
            cursor.execute('''
                SELECT * FROM backtest_results
                WHERE strategy_id = ?
                ORDER BY created_at DESC
            ''', (strategy_id,))
        else:
            cursor.execute('SELECT * FROM backtest_results ORDER BY created_at DESC')

        rows = cursor.fetchall()
        results = []

        for row in rows:

            results.append({
                'id': row['id'],
                'strategy_id': row['strategy_id'],
                'symbol': row['symbol'],
                'timeframe': row['timeframe'],
                'start_date': row['start_date'],
                'end_date': row['end_date'],
                'initial_capital': row['initial_capital'],
                'final_capital': row['final_capital'],
                'total_return': row['total_return'],
                'total_trades': row['total_trades'],
                'win_rate': row['win_rate'],
                'profit_factor': row['profit_factor'],
                'sharpe_ratio': row['sharpe_ratio'],
                'max_drawdown': row['max_drawdown'],
                'metrics': json.loads(row['metrics'] or '{}'),
            })

        conn.close()
        return results

    def update_database_schema(self):
        """Update database schema to handle new structure"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Check if we need to add new columns
            cursor.execute("PRAGMA table_info(strategies)")
            columns = [col[1] for col in cursor.fetchall()]

            # Add risk_params if missing (for backward compatibility)
            if 'risk_params' not in columns:
                cursor.execute('ALTER TABLE strategies ADD COLUMN risk_params TEXT DEFAULT "{}"')
                logger.info("Added risk_params column to strategies table")

            # Update old strategies to have proper risk_params
            cursor.execute('SELECT id, exit_params FROM strategies WHERE risk_params = "{}" OR risk_params IS NULL')
            old_strategies = cursor.fetchall()

            for strategy_id, exit_params_json in old_strategies:
                try:
                    exit_params = json.loads(exit_params_json or '{}')
                    risk_params = {
                        'position_size_pct': 10.0,
                        'max_bars_hold': exit_params.get('max_bars', 20)
                    }
                    cursor.execute(
                        'UPDATE strategies SET risk_params = ? WHERE id = ?',
                        (json.dumps(risk_params), strategy_id)
                    )
                except:
                    pass

            conn.commit()
            logger.info("Database schema updated")

        except Exception as e:
            logger.error(f"Error updating database schema: {str(e)}")
            conn.rollback()
        finally:
            conn.close()

    def delete_backtest_result(self, result_id: int):
        """Delete backtest result from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('DELETE FROM backtest_results WHERE id = ?', (result_id,))
            conn.commit()
            logger.info(f"Backtest result deleted: ID {result_id}")
        except Exception as e:
            logger.error(f"Error deleting backtest result {result_id}: {str(e)}")
            raise
        finally:
            conn.close()

    def delete_all_backtest_results(self):
        """Delete ALL backtest results from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('DELETE FROM backtest_results')
            conn.commit()
            logger.info("All backtest results deleted")
        except Exception as e:
            logger.error(f"Error deleting all backtest results: {str(e)}")
            raise
        finally:
            conn.close()

    def delete_all_strategies(self):
        """Delete ALL strategies from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # First delete all backtest results (due to foreign key constraint)
            cursor.execute('DELETE FROM backtest_results')
            # Then delete all strategies
            cursor.execute('DELETE FROM strategies')
            conn.commit()
            logger.info("All strategies and results deleted")
        except Exception as e:
            logger.error(f"Error deleting all strategies: {str(e)}")
            raise
        finally:
            conn.close()

    def clean_database(self):
        """Clean entire database - delete everything"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Delete all data from all tables
            cursor.execute('DELETE FROM backtest_results')
            cursor.execute('DELETE FROM strategies')

            # Reset auto-increment counters
            cursor.execute('DELETE FROM sqlite_sequence WHERE name="strategies"')
            cursor.execute('DELETE FROM sqlite_sequence WHERE name="backtest_results"')

            conn.commit()
            logger.info("Database cleaned completely")
        except Exception as e:
            logger.error(f"Error cleaning database: {str(e)}")
            raise
        finally:
            conn.close()