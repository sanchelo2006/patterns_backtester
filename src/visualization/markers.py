from enum import Enum
from typing import Dict


class MarkerType(Enum):
    """Marker types for trades"""
    ENTER_PROFIT_LONG = 'green_triangle_up'      # Green triangle up
    EXIT_PROFIT_LONG = 'red_triangle_up'         # Red triangle up
    ENTER_LOSS_LONG = 'yellow_triangle_down'     # Yellow triangle down
    EXIT_LOSS_LONG = 'blue_triangle_down'        # Blue triangle down
    ENTER_PROFIT_SHORT = 'red_square'            # Red square
    EXIT_PROFIT_SHORT = 'green_square'           # Green square
    ENTER_LOSS_SHORT = 'yellow_square'           # Yellow square
    EXIT_LOSS_SHORT = 'blue_square'              # Blue square


MARKER_CONFIGS = {
    MarkerType.ENTER_PROFIT_LONG: {
        'symbol': 'triangle-up',
        'color': 'green',
        'size': 12
    },
    MarkerType.EXIT_PROFIT_LONG: {
        'symbol': 'triangle-up',
        'color': 'red',
        'size': 12
    },
    MarkerType.ENTER_LOSS_LONG: {
        'symbol': 'triangle-down',
        'color': 'yellow',
        'size': 12
    },
    MarkerType.EXIT_LOSS_LONG: {
        'symbol': 'triangle-down',
        'color': 'blue',
        'size': 12
    },
    MarkerType.ENTER_PROFIT_SHORT: {
        'symbol': 'square',
        'color': 'red',
        'size': 10
    },
    MarkerType.EXIT_PROFIT_SHORT: {
        'symbol': 'square',
        'color': 'green',
        'size': 10
    },
    MarkerType.ENTER_LOSS_SHORT: {
        'symbol': 'square',
        'color': 'yellow',
        'size': 10
    },
    MarkerType.EXIT_LOSS_SHORT: {
        'symbol': 'square',
        'color': 'blue',
        'size': 10
    }
}


def get_marker_for_trade(trade: 'Trade', is_entry: bool = True) -> Dict:
    """Get marker configuration for a trade"""
    if trade.position_type == 'long':
        if trade.success:
            if is_entry:
                marker_type = MarkerType.ENTER_PROFIT_LONG
            else:
                marker_type = MarkerType.EXIT_PROFIT_LONG
        else:
            if is_entry:
                marker_type = MarkerType.ENTER_LOSS_LONG
            else:
                marker_type = MarkerType.EXIT_LOSS_LONG
    else:  # short
        if trade.success:
            if is_entry:
                marker_type = MarkerType.ENTER_PROFIT_SHORT
            else:
                marker_type = MarkerType.EXIT_PROFIT_SHORT
        else:
            if is_entry:
                marker_type = MarkerType.ENTER_LOSS_SHORT
            else:
                marker_type = MarkerType.EXIT_LOSS_SHORT

    return MARKER_CONFIGS[marker_type]