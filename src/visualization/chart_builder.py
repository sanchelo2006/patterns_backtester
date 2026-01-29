import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import List, Optional
from src.backtest.engine import Trade
from src.visualization.markers import get_marker_for_trade
from src.config.settings import CHART_HEIGHT, CHART_WIDTH
from src.utils.logger import get_logger

logger = get_logger('app')


class ChartBuilder:
    """Build interactive candlestick charts with trade markers"""

    def __init__(self, height: int = CHART_HEIGHT, width: int = CHART_WIDTH):
        self.height = height
        self.width = width

    def create_candlestick_chart(
        self,
        df: pd.DataFrame,
        trades: List[Trade],
        title: str = "Trading Strategy Backtest"
    ) -> go.Figure:
        """Create interactive candlestick chart with trade markers"""
        logger.info(f"Creating chart with {len(trades)} trades")

        # Create subplots
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
            subplot_titles=(title, "Volume")
        )

        # Add candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df['Open'],
                high=df['High'],
                low=df['Low'],
                close=df['Close'],
                name="OHLC"
            ),
            row=1, col=1
        )

        # Add volume bars
        colors = ['red' if row['Close'] < row['Open'] else 'green'
                 for _, row in df.iterrows()]

        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['Volume'],
                marker_color=colors,
                name="Volume"
            ),
            row=2, col=1
        )

        # Add trade markers
        self._add_trade_markers(fig, df, trades)

        # Update layout
        fig.update_layout(
            height=self.height,
            width=self.width,
            title=title,
            yaxis_title="Price",
            yaxis2_title="Volume",
            xaxis2_title="Date",
            showlegend=True,
            xaxis_rangeslider_visible=False
        )

        # Update axes
        fig.update_xaxes(
            rangeslider_thickness=0.05,
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(step="all")
                ])
            )
        )

        fig.update_yaxes(fixedrange=False)

        return fig

    def _add_trade_markers(self, fig: go.Figure, df: pd.DataFrame, trades: List[Trade]):
        """Add trade entry and exit markers to the chart"""

        entry_dates = []
        entry_prices = []
        entry_markers = []
        entry_texts = []

        exit_dates = []
        exit_prices = []
        exit_markers = []
        exit_texts = []

        for trade in trades:
            # Entry marker
            entry_config = get_marker_for_trade(trade, is_entry=True)
            entry_dates.append(trade.entry_date)
            entry_prices.append(trade.entry_price)
            entry_markers.append(entry_config)
            entry_texts.append(
                f"{trade.position_type.upper()} ENTRY<br>"
                f"Pattern: {trade.pattern}<br>"
                f"Price: {trade.entry_price:.2f}<br>"
                f"Date: {trade.entry_date}"
            )

            # Exit marker
            exit_config = get_marker_for_trade(trade, is_entry=False)
            exit_dates.append(trade.exit_date)
            exit_prices.append(trade.exit_price)
            exit_markers.append(exit_config)
            exit_texts.append(
                f"{trade.position_type.upper()} EXIT<br>"
                f"P&L: {trade.pnl:.2f} ({trade.pnl_percent:.2f}%)<br>"
                f"Price: {trade.exit_price:.2f}<br>"
                f"Date: {trade.exit_date}<br>"
                f"Result: {'PROFIT' if trade.success else 'LOSS'}"
            )

        # Add entry markers
        if entry_dates:
            fig.add_trace(
                go.Scatter(
                    x=entry_dates,
                    y=entry_prices,
                    mode='markers',
                    name='Entry Points',
                    marker=dict(
                        symbol=[m['symbol'] for m in entry_markers],
                        color=[m['color'] for m in entry_markers],
                        size=[m['size'] for m in entry_markers],
                        line=dict(width=2, color='black')
                    ),
                    text=entry_texts,
                    hoverinfo='text'
                ),
                row=1, col=1
            )

        # Add exit markers
        if exit_dates:
            fig.add_trace(
                go.Scatter(
                    x=exit_dates,
                    y=exit_prices,
                    mode='markers',
                    name='Exit Points',
                    marker=dict(
                        symbol=[m['symbol'] for m in exit_markers],
                        color=[m['color'] for m in exit_markers],
                        size=[m['size'] for m in exit_markers],
                        line=dict(width=2, color='black')
                    ),
                    text=exit_texts,
                    hoverinfo='text'
                ),
                row=1, col=1
            )

    def create_equity_curve_chart(self, equity_curve: pd.DataFrame) -> go.Figure:
        """Create equity curve chart"""
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=equity_curve['date'],
                y=equity_curve['equity'],
                mode='lines',
                name='Equity',
                line=dict(color='blue', width=2)
            )
        )

        fig.update_layout(
            height=400,
            width=800,
            title="Equity Curve",
            xaxis_title="Date",
            yaxis_title="Equity",
            showlegend=True
        )

        return fig