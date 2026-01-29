import talib
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from src.config.settings import CANDLE_PATTERNS
from src.utils.logger import get_logger

logger = get_logger('app')


class PatternDetector:
    """Detects candlestick patterns using TA-Lib"""

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self.patterns = CANDLE_PATTERNS

    def detect_all_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect all candlestick patterns"""
        logger.info(f"Detecting patterns with threshold {self.threshold}")

        # Ensure required columns exist
        required_cols = ['Open', 'High', 'Low', 'Close']
        if not all(col in df.columns for col in required_cols):
            logger.error(f"Missing required columns. Available: {df.columns.tolist()}")
            return df

        # Convert to numpy arrays for TA-Lib
        open_prices = df['Open'].values.astype(float)
        high_prices = df['High'].values.astype(float)
        low_prices = df['Low'].values.astype(float)
        close_prices = df['Close'].values.astype(float)

        # Detect each pattern
        for pattern_name in self.patterns:
            try:
                pattern_func = getattr(talib, pattern_name)
                result = pattern_func(open_prices, high_prices, low_prices, close_prices)

                # Apply threshold
                if self.threshold != 0.5:
                    result = np.where(np.abs(result) > 100 * (self.threshold - 0.5) * 2, result, 0)

                df[pattern_name] = result
                logger.debug(f"Detected pattern: {pattern_name}")

            except Exception as e:
                logger.warning(f"Could not detect pattern {pattern_name}: {str(e)}")

        return df

    def get_signal(self, row: pd.Series, patterns_to_use: List[str]) -> Tuple[int, str]:
        """
        Get trading signal based on patterns
        Returns: (signal, pattern_name)
        signal: 1 for buy, -1 for sell, 0 for no signal
        """
        for pattern in patterns_to_use:
            if pattern in row:
                value = row[pattern]
                if value > 0:  # Bullish pattern
                    return 1, pattern
                elif value < 0:  # Bearish pattern
                    return -1, pattern
        return 0, ''