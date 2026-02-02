from enum import Enum
from typing import Dict, Any, Optional
import numpy as np


class EntryRule(Enum):
    OPEN_NEXT_CANDLE = "open_next_candle"
    MIDDLE_OF_PATTERN = "middle_of_pattern"
    CLOSE_PATTERN = "close_pattern"


class EntryRuleExecutor:
    """Execute entry rules for trades"""

    @staticmethod
    def execute(
        rule: EntryRule,
        pattern_data: Dict[str, Any],
        current_price: float,
        params: Dict[str, Any] = None
    ) -> float:
        """Execute entry rule and return entry price"""
        params = params or {}

        if rule == EntryRule.OPEN_NEXT_CANDLE:
            # Use open price of the next candle after pattern
            return current_price

        elif rule == EntryRule.MIDDLE_OF_PATTERN:
            # Use middle price of the pattern
            if 'pattern_high' in pattern_data and 'pattern_low' in pattern_data:
                high = pattern_data['pattern_high']
                low = pattern_data['pattern_low']
                return (high + low) / 2
            return current_price

        elif rule == EntryRule.CLOSE_PATTERN:
            # Use closing price of the pattern candle
            if 'pattern_close' in pattern_data:
                return pattern_data['pattern_close']
            return current_price

        return current_price

    @staticmethod
    def get_description(rule: EntryRule) -> str:
        """Get description of entry rule"""
        descriptions = {
            EntryRule.OPEN_NEXT_CANDLE: "Open price of next candle after pattern",
            EntryRule.MIDDLE_OF_PATTERN: "Price at middle of pattern formation",
            EntryRule.CLOSE_PATTERN: "Closing price of pattern candle"
        }
        return descriptions.get(rule, "Unknown rule")