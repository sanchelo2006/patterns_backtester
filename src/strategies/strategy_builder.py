from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from enum import Enum
import json
from src.strategies.entry_rules import EntryRule
from src.strategies.exit_rules import ExitRule
from src.config.settings import CANDLE_PATTERNS
from src.utils.logger import get_logger

logger = get_logger('app')


class TimeFrame(Enum):
    """Supported timeframes"""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAILY = "1d"
    WEEKLY = "1w"
    MONTHLY = "1M"


@dataclass
class Strategy:
    """Trading strategy definition"""
    name: str
    patterns: List[str]  # List of pattern names to use
    entry_rule: EntryRule
    entry_params: Dict[str, Any]
    exit_rule: ExitRule
    exit_params: Dict[str, Any]
    timeframe: TimeFrame
    position_size_pct: float = 10.0
    stop_loss_pct: float = 2.0
    take_profit_pct: float = 4.0
    max_bars_hold: int = 20
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert strategy to dictionary for serialization"""
        return {
            'name': self.name,
            'patterns': self.patterns,
            'entry_rule': self.entry_rule.value,
            'entry_params': self.entry_params,
            'exit_rule': self.exit_rule.value,
            'exit_params': self.exit_params,
            'timeframe': self.timeframe.value,
            'position_size_pct': self.position_size_pct,
            'stop_loss_pct': self.stop_loss_pct,
            'take_profit_pct': self.take_profit_pct,
            'max_bars_hold': self.max_bars_hold,
            'enabled': self.enabled
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Strategy':
        """Create strategy from dictionary"""
        return cls(
            name=data['name'],
            patterns=data['patterns'],
            entry_rule=EntryRule(data['entry_rule']),
            entry_params=data.get('entry_params', {}),
            exit_rule=ExitRule(data['exit_rule']),
            exit_params=data.get('exit_params', {}),
            timeframe=TimeFrame(data['timeframe']),
            position_size_pct=data.get('position_size_pct', 10.0),
            stop_loss_pct=data.get('stop_loss_pct', 2.0),
            take_profit_pct=data.get('take_profit_pct', 4.0),
            max_bars_hold=data.get('max_bars_hold', 20),
            enabled=data.get('enabled', True)
        )


class StrategyBuilder:
    """Build and manage trading strategies"""

    def __init__(self):
        self.strategies: Dict[str, Strategy] = {}

    def create_strategy(
        self,
        name: str,
        patterns: List[str],
        entry_rule: EntryRule,
        exit_rule: ExitRule,
        timeframe: TimeFrame,
        entry_params: Dict[str, Any] = None,
        exit_params: Dict[str, Any] = None,
        position_size_pct: float = 10.0,
        stop_loss_pct: float = 2.0,
        take_profit_pct: float = 4.0,
        max_bars_hold: int = 20
    ) -> Strategy:
        """Create a new trading strategy"""

        # Validate patterns
        for pattern in patterns:
            if pattern not in CANDLE_PATTERNS:
                logger.warning(f"Unknown pattern: {pattern}")

        # Set default parameters based on exit rule
        if exit_params is None:
            exit_params = {}

            if exit_rule == ExitRule.STOP_LOSS_TAKE_PROFIT:
                exit_params = {
                    'stop_loss_pct': stop_loss_pct,
                    'take_profit_pct': take_profit_pct
                }
            elif exit_rule == ExitRule.TAKE_PROFIT_ONLY:
                exit_params = {
                    'take_profit_pct': take_profit_pct
                }
            elif exit_rule == ExitRule.TIMEBASED_EXIT:
                exit_params = {
                    'max_bars': max_bars_hold
                }
            elif exit_rule == ExitRule.TRAILING_STOP:
                exit_params = {
                    'trailing_stop_pct': stop_loss_pct
                }

        strategy = Strategy(
            name=name,
            patterns=patterns,
            entry_rule=entry_rule,
            entry_params=entry_params or {},
            exit_rule=exit_rule,
            exit_params=exit_params,
            timeframe=timeframe,
            position_size_pct=position_size_pct,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            max_bars_hold=max_bars_hold
        )

        self.strategies[name] = strategy
        logger.info(f"Strategy created: {name}")

        return strategy

    def save_strategy_to_db(self, strategy: Strategy, db_handler) -> int:
        """Save strategy to database"""
        strategy_data = strategy.to_dict()
        return db_handler.save_strategy(strategy_data)

    def load_strategy_from_db(self, name: str, db_handler) -> Optional[Strategy]:
        """Load strategy from database by name"""
        strategies = db_handler.load_strategies()
        for strategy_data in strategies:
            if strategy_data['name'] == name:
                return Strategy.from_dict(strategy_data)
        return None

    def get_all_strategies(self, db_handler) -> List[Strategy]:
        """Load all strategies from database"""
        strategies_data = db_handler.load_strategies()
        return [Strategy.from_dict(data) for data in strategies_data]

    def delete_strategy(self, name: str, db_handler):
        """Delete strategy from database"""
        strategies = db_handler.load_strategies()
        for strategy_data in strategies:
            if strategy_data['name'] == name:
                db_handler.delete_strategy(strategy_data['id'])
                logger.info(f"Strategy deleted: {name}")
                break

    def validate_strategy(self, strategy: Strategy) -> List[str]:
        """Validate strategy and return list of errors"""
        errors = []

        if not strategy.name:
            errors.append("Strategy name is required")

        if not strategy.patterns:
            errors.append("At least one pattern must be selected")

        if strategy.position_size_pct <= 0 or strategy.position_size_pct > 100:
            errors.append("Position size must be between 0 and 100%")

        if strategy.stop_loss_pct <= 0:
            errors.append("Stop loss must be positive")

        if strategy.take_profit_pct <= 0:
            errors.append("Take profit must be positive")

        if strategy.max_bars_hold <= 0:
            errors.append("Max bars to hold must be positive")

        return errors