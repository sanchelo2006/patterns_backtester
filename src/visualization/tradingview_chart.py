import pandas as pd
import numpy as np
from typing import List
import talib
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from src.backtest.engine import Trade


def create_plotly_chart(df: pd.DataFrame, trades: List[Trade], title: str = "Chart"):
    """Create interactive chart using Plotly"""

    # DEBUG: Check data structure
    print(f"\n=== DEBUG CHART DATA ===")
    print(f"Data shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    if len(df) > 0:
        sample = df.iloc[:5]
        for i in range(min(5, len(df))):
            row = df.iloc[i]
            print(f"\nCandle {i}:")
            print(f"  Open: {row['Open']:.2f}, High: {row['High']:.2f}, Low: {row['Low']:.2f}, Close: {row['Close']:.2f}")
            print(f"  Wick sizes: Upper: {row['High'] - max(row['Open'], row['Close']):.2f}, "
                  f"Lower: {min(row['Open'], row['Close']) - row['Low']:.2f}")
    print("=======================\n")

    # Create subplots
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.5, 0.15, 0.15, 0.2],
        subplot_titles=[title, "Volume", "MACD", "RSI"]
    )

    # Add candlestick chart - FIXED VERSION
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name="Price",
            # This is the key: use the same colors for increasing/decreasing
            # but ensure wicks are visible
            increasing=dict(
                line=dict(color='#26a69a', width=1),  # Body outline and wick color
                fillcolor='#26a69a'  # Body fill color
            ),
            decreasing=dict(
                line=dict(color='#ef5350', width=1),  # Body outline and wick color
                fillcolor='#ef5350'  # Body fill color
            ),
            # Ensure wicks are visible
            line=dict(width=1),  # Overall line width
            whiskerwidth=0.8,  # Width of wicks relative to candles
            opacity=1  # Ensure full opacity
        ),
        row=1, col=1
    )

    # Add volume
    if 'Volume' in df.columns:
        colors = ['#26a69a' if close >= open_ else '#ef5350'
                 for close, open_ in zip(df['Close'], df['Open'])]

        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['Volume'],
                name="Volume",
                marker_color=colors,
                showlegend=False
            ),
            row=2, col=1
        )

    # Add MACD
    if len(df) > 26:
        add_macd_plotly(fig, df)

    # Add RSI
    if len(df) > 14:
        add_rsi_plotly(fig, df)

    # Add trade markers
    if trades:
        add_trade_markers_plotly(fig, df, trades)

    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Price",
        template="plotly_dark",
        height=900,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Remove range slider
    fig.update_xaxes(rangeslider_visible=False)

    # Show figure
    fig.show()


def add_macd_plotly(fig, df: pd.DataFrame):
    """Add MACD to Plotly figure"""
    try:
        close_prices = df['Close'].values.astype(float)
        macd, signal, hist = talib.MACD(
            close_prices,
            fastperiod=12,
            slowperiod=26,
            signalperiod=9
        )

        # MACD line
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=macd,
                name="MACD",
                line=dict(color='#2962FF', width=2)
            ),
            row=3, col=1
        )

        # Signal line
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=signal,
                name="Signal",
                line=dict(color='#FF6D00', width=2)
            ),
            row=3, col=1
        )

        # Histogram
        colors = ['#26a69a' if h >= 0 else '#ef5350' for h in hist]
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=hist,
                name="Histogram",
                marker_color=colors,
                showlegend=False
            ),
            row=3, col=1
        )

    except Exception as e:
        print(f"Error adding MACD to Plotly: {e}")


def add_rsi_plotly(fig, df: pd.DataFrame):
    """Add RSI to Plotly figure"""
    try:
        close_prices = df['Close'].values.astype(float)
        rsi = talib.RSI(close_prices, timeperiod=14)

        # RSI line
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=rsi,
                name="RSI",
                line=dict(color='#FF9800', width=2)
            ),
            row=4, col=1
        )

        # Add RSI levels
        fig.add_hline(y=30, line_dash="dash", line_color="red",
                     row=4, col=1, opacity=0.5)
        fig.add_hline(y=70, line_dash="dash", line_color="green",
                     row=4, col=1, opacity=0.5)

        # Set RSI y-axis range
        fig.update_yaxes(range=[0, 100], row=4, col=1)

    except Exception as e:
        print(f"Error adding RSI to Plotly: {e}")


def add_trade_markers_plotly(fig, df: pd.DataFrame, trades: List[Trade]):
    """Add trade markers to Plotly figure"""

    # Prepare marker data
    long_entries = {'x': [], 'y': []}
    long_exits = {'x': [], 'y': []}
    short_entries = {'x': [], 'y': []}
    short_exits = {'x': [], 'y': []}

    for trade in trades:
        # Find closest index for entry
        entry_idx = find_closest_index(df.index, trade.entry_date)
        if entry_idx is not None:
            if trade.position_type == 'long':
                long_entries['x'].append(df.index[entry_idx])
                long_entries['y'].append(df.iloc[entry_idx]['Close'])
            else:
                short_entries['x'].append(df.index[entry_idx])
                short_entries['y'].append(df.iloc[entry_idx]['Close'])

        # Find closest index for exit
        exit_idx = find_closest_index(df.index, trade.exit_date)
        if exit_idx is not None:
            if trade.position_type == 'long':
                long_exits['x'].append(df.index[exit_idx])
                long_exits['y'].append(df.iloc[exit_idx]['Close'])
            else:
                short_exits['x'].append(df.index[exit_idx])
                short_exits['y'].append(df.iloc[exit_idx]['Close'])

    # Add markers to chart
    if long_entries['x']:
        fig.add_trace(
            go.Scatter(
                x=long_entries['x'],
                y=long_entries['y'],
                mode='markers',
                name='Long Entry',
                marker=dict(symbol='triangle-up', size=12, color='green'),
                showlegend=True
            ),
            row=1, col=1
        )

    if long_exits['x']:
        fig.add_trace(
            go.Scatter(
                x=long_exits['x'],
                y=long_exits['y'],
                mode='markers',
                name='Long Exit',
                marker=dict(symbol='triangle-down', size=10, color='red'),
                showlegend=True
            ),
            row=1, col=1
        )

    if short_entries['x']:
        fig.add_trace(
            go.Scatter(
                x=short_entries['x'],
                y=short_entries['y'],
                mode='markers',
                name='Short Entry',
                marker=dict(symbol='triangle-down', size=12, color='orange'),
                showlegend=True
            ),
            row=1, col=1
        )

    if short_exits['x']:
        fig.add_trace(
            go.Scatter(
                x=short_exits['x'],
                y=short_exits['y'],
                mode='markers',
                name='Short Exit',
                marker=dict(symbol='triangle-up', size=10, color='blue'),
                showlegend=True
            ),
            row=1, col=1
        )


def find_closest_index(index, target_date):
    """Find closest index to target date"""
    if not isinstance(target_date, pd.Timestamp):
        target_date = pd.Timestamp(target_date)

    if len(index) == 0:
        return None

    # Find exact match
    for i, idx in enumerate(index):
        if idx.date() == target_date.date():
            return i

    # Find closest
    time_diff = abs(index - target_date)
    return time_diff.argmin()