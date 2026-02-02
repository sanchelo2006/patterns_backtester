from enum import Enum
from typing import Dict, Any, Optional, Tuple
import numpy as np
from dataclasses import dataclass


class ExitRule(Enum):
    STOP_LOSS_TAKE_PROFIT = "stop_loss_take_profit"
    TAKE_PROFIT_ONLY = "take_profit_only"
    OPPOSITE_PATTERN = "opposite_pattern"
    TIMEBASED_EXIT = "timebased_exit"
    TRAILING_STOP = "trailing_stop"


@dataclass
class ExitSignal:
    should_exit: bool
    exit_price: Optional[float] = None
    reason: str = ""
    is_profit: bool = False


class ExitRuleExecutor:
    """Execute exit rules for trades"""

    def __init__(self, rule: ExitRule, params: Dict[str, Any] = None):
        self.rule = rule
        self.params = params or {}

    def check_exit(
        self,
        entry_price: float,
        current_price: float,
        position_type: str,
        bars_since_entry: int,
        pattern_data: Dict[str, Any] = None,
        current_bar: Dict[str, Any] = None
    ) -> ExitSignal:
        """Check if we should exit based on the rule"""

        if self.rule == ExitRule.STOP_LOSS_TAKE_PROFIT:
            return self._check_stop_loss_take_profit(
                entry_price, current_price, position_type
            )

        elif self.rule == ExitRule.TAKE_PROFIT_ONLY:
            return self._check_take_profit_only(
                entry_price, current_price, position_type
            )

        elif self.rule == ExitRule.OPPOSITE_PATTERN:
            return self._check_opposite_pattern(
                pattern_data, entry_price, current_price, position_type
            )

        elif self.rule == ExitRule.TIMEBASED_EXIT:
            return self._check_timebased_exit(
                bars_since_entry, current_price
            )

        elif self.rule == ExitRule.TRAILING_STOP:
            return self._check_trailing_stop(
                entry_price, current_price, position_type, current_bar
            )

        return ExitSignal(should_exit=False)

    def _check_stop_loss_take_profit(
        self,
        entry_price: float,
        current_price: float,
        position_type: str
    ) -> ExitSignal:
        """Check stop loss and take profit"""
        stop_loss_pct = self.params.get('stop_loss_pct', 2.0) / 100
        take_profit_pct = self.params.get('take_profit_pct', 4.0) / 100

        if position_type == 'long':
            # Check take profit
            if current_price >= entry_price * (1 + take_profit_pct):
                return ExitSignal(
                    should_exit=True,
                    exit_price=current_price,
                    reason="Take profit reached",
                    is_profit=True
                )
            # Check stop loss
            elif current_price <= entry_price * (1 - stop_loss_pct):
                return ExitSignal(
                    should_exit=True,
                    exit_price=current_price,
                    reason="Stop loss triggered",
                    is_profit=False
                )

        else:  # short position
            # Check take profit
            if current_price <= entry_price * (1 - take_profit_pct):
                return ExitSignal(
                    should_exit=True,
                    exit_price=current_price,
                    reason="Take profit reached",
                    is_profit=True
                )
            # Check stop loss
            elif current_price >= entry_price * (1 + stop_loss_pct):
                return ExitSignal(
                    should_exit=True,
                    exit_price=current_price,
                    reason="Stop loss triggered",
                    is_profit=False
                )

        return ExitSignal(should_exit=False)

    def _check_take_profit_only(
        self,
        entry_price: float,
        current_price: float,
        position_type: str
    ) -> ExitSignal:
        """Check only take profit"""
        take_profit_pct = self.params.get('take_profit_pct', 4.0) / 100

        if position_type == 'long':
            if current_price >= entry_price * (1 + take_profit_pct):
                return ExitSignal(
                    should_exit=True,
                    exit_price=current_price,
                    reason="Take profit reached",
                    is_profit=True
                )
        else:  # short
            if current_price <= entry_price * (1 - take_profit_pct):
                return ExitSignal(
                    should_exit=True,
                    exit_price=current_price,
                    reason="Take profit reached",
                    is_profit=True
                )

        return ExitSignal(should_exit=False)

    def _check_opposite_pattern(
        self,
        pattern_data: Dict[str, Any],
        entry_price: float,
        current_price: float,
        position_type: str
    ) -> ExitSignal:
        """Check for opposite pattern signal"""
        if pattern_data and 'has_opposite_pattern' in pattern_data:
            if pattern_data['has_opposite_pattern']:
                return ExitSignal(
                    should_exit=True,
                    exit_price=current_price,
                    reason="Opposite pattern detected",
                    is_profit=(
                        (position_type == 'long' and current_price > entry_price) or
                        (position_type == 'short' and current_price < entry_price)
                    )
                )

        return ExitSignal(should_exit=False)

    def _check_timebased_exit(
        self,
        bars_since_entry: int,
        current_price: float
    ) -> ExitSignal:
        """Check time-based exit"""
        max_bars = self.params.get('max_bars', 20)

        if bars_since_entry >= max_bars:
            return ExitSignal(
                should_exit=True,
                exit_price=current_price,
                reason=f"Time exit after {bars_since_entry} bars",
                is_profit=True  # Assume profit for time exit
            )

        return ExitSignal(should_exit=False)

    def _check_trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        position_type: str,
        current_bar: Dict[str, Any]
    ) -> ExitSignal:
        """Check trailing stop"""
        trailing_stop_pct = self.params.get('trailing_stop_pct', 2.0) / 100

        # This is a simplified version - in real implementation,
        # you'd track the highest/lowest price since entry
        if position_type == 'long':
            highest_since_entry = current_bar.get('highest_since_entry', current_price)
            stop_price = highest_since_entry * (1 - trailing_stop_pct)

            if current_price <= stop_price:
                return ExitSignal(
                    should_exit=True,
                    exit_price=current_price,
                    reason="Trailing stop triggered",
                    is_profit=current_price > entry_price
                )

        else:  # short
            lowest_since_entry = current_bar.get('lowest_since_entry', current_price)
            stop_price = lowest_since_entry * (1 + trailing_stop_pct)

            if current_price >= stop_price:
                return ExitSignal(
                    should_exit=True,
                    exit_price=current_price,
                    reason="Trailing stop triggered",
                    is_profit=current_price < entry_price
                )

        return ExitSignal(should_exit=False)

    @staticmethod
    def get_description(rule: ExitRule) -> str:
        """Get description of exit rule"""
        descriptions = {
            ExitRule.STOP_LOSS_TAKE_PROFIT: "Stop loss and take profit",
            ExitRule.TAKE_PROFIT_ONLY: "Take profit only",
            ExitRule.OPPOSITE_PATTERN: "Exit on opposite pattern",
            ExitRule.TIMEBASED_EXIT: "Time-based exit after N bars",
            ExitRule.TRAILING_STOP: "Trailing stop loss"
        }
        return descriptions.get(rule, "Unknown rule")