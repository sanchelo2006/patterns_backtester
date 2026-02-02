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

        # Trade details table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                result_id INTEGER,
                entry_date TEXT NOT NULL,
                exit_date TEXT NOT NULL,
                position_type TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL NOT NULL,
                pnl REAL NOT NULL,
                pnl_percent REAL NOT NULL,
                pattern TEXT,
                exit_reason TEXT,
                FOREIGN KEY (result_id) REFERENCES backtest_results (id)
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
            strategies.append({
                'id': row['id'],
                'name': row['name'],
                'patterns': json.loads(row['patterns']),
                'entry_rule': row['entry_rule'],
                'entry_params': json.loads(row['entry_params'] or '{}'),
                'exit_rule': row['exit_rule'],
                'exit_params': json.loads(row['exit_params'] or '{}'),
                'timeframe': row['timeframe'],
                'risk_params': json.loads(row['risk_params'] or '{}')
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

        # Save trades
        for trade in result_data.get('trades', []):
            cursor.execute('''
                INSERT INTO trades
                (result_id, entry_date, exit_date, position_type, entry_price,
                 exit_price, pnl, pnl_percent, pattern, exit_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result_id,
                trade['entry_date'],
                trade['exit_date'],
                trade['position_type'],
                trade['entry_price'],
                trade['exit_price'],
                trade['pnl'],
                trade['pnl_percent'],
                trade.get('pattern'),
                trade.get('exit_reason')
            ))

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
            # Load trades for this result
            cursor.execute('SELECT * FROM trades WHERE result_id = ?', (row['id'],))
            trades = cursor.fetchall()

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
                'trades': [dict(trade) for trade in trades]
            })

        conn.close()
        return results