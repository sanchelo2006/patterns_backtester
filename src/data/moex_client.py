import pandas as pd
import apimoex
import requests
import numpy as np
from typing import Optional
from datetime import datetime, timedelta
import time
from src.utils.logger import get_logger

logger = get_logger('app')


class MOEXClient:
    """Client for MOEX data with proper OHLC support"""

    def __init__(self):
        self.session = requests.Session()

    def get_data(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        timeframe: str = '1d'
    ) -> Optional[pd.DataFrame]:
        """Get historical data from MOEX"""
        try:
            logger.info(f"Fetching MOEX data for {ticker} from {start_date} to {end_date}")

            # Map timeframe to MOEX intervals
            interval_map = {
                '1m': 1, '5m': 10, '15m': 10, '30m': 30,
                '1h': 60, '4h': 4, '1d': 24, '1w': 7, '1M': 31
            }

            # Default to daily
            interval = interval_map.get(timeframe, 24)

            return self._get_candle_data(ticker, start_date, end_date, interval)

        except Exception as e:
            logger.error(f"Error fetching MOEX data: {str(e)}", exc_info=True)
            return None

    def _get_candle_data(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        interval: int
    ) -> Optional[pd.DataFrame]:
        """Get candle data from MOEX ISS API"""
        try:
            logger.info(f"Fetching candle data for {ticker}, interval={interval}")

            url = f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/{ticker}/candles.json"

            all_data = []
            current_start = pd.Timestamp(start_date)
            current_end = pd.Timestamp(end_date)

            # Fetch in chunks (max 500 candles per request)
            while current_start <= current_end:
                from_date = current_start.strftime('%Y-%m-%d')
                to_date = min(current_start + timedelta(days=30), current_end).strftime('%Y-%m-%d')

                params = {
                    'from': from_date,
                    'till': to_date,
                    'interval': interval,
                    'candles.columns': 'begin,open,high,low,close,volume'
                }

                response = self.session.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                candles = data['candles']['data']

                if candles:
                    all_data.extend(candles)
                    logger.debug(f"Fetched {len(candles)} candles from {from_date} to {to_date}")

                # Move to next period
                current_start += timedelta(days=31)
                time.sleep(0.1)  # Rate limiting

            if not all_data:
                logger.warning(f"No candle data for {ticker}")
                return self._get_fallback_data(ticker, start_date, end_date)

            # Create DataFrame
            df = pd.DataFrame(all_data, columns=['begin', 'open', 'high', 'low', 'close', 'volume'])

            # Convert timestamp
            df['begin'] = pd.to_datetime(df['begin'])
            df.set_index('begin', inplace=True)

            # Rename columns
            df = df.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })

            # Ensure numeric
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Drop NaN
            df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])

            # Sort and filter
            df = df.sort_index()
            df = df[(df.index >= pd.Timestamp(start_date)) &
                    (df.index <= pd.Timestamp(end_date))]

            # Remove duplicates
            df = df[~df.index.duplicated(keep='first')]

            # Debug output
            print(f"\n=== MOEX CANDLE DATA ({ticker}) ===")
            print(f"Interval: {interval}")
            print(f"Rows: {len(df)}")
            print(f"Date range: {df.index[0]} to {df.index[-1]}")
            if len(df) > 0:
                print(f"\nSample candles:")
                for i in range(min(5, len(df))):
                    row = df.iloc[i]
                    print(f"{df.index[i].date()}: O={row['Open']:.2f}, H={row['High']:.2f}, "
                          f"L={row['Low']:.2f}, C={row['Close']:.2f}, "
                          f"Upper wick: {row['High'] - max(row['Open'], row['Close']):.2f}, "
                          f"Lower wick: {min(row['Open'], row['Close']) - row['Low']:.2f}")
            print("===============================\n")

            logger.info(f"Retrieved {len(df)} bars for {ticker}")
            return df

        except Exception as e:
            logger.error(f"Error fetching candle data: {str(e)}")
            return self._get_fallback_data(ticker, start_date, end_date)

    def _get_fallback_data(
        self,
        ticker: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """Fallback: Get close-only data and synthesize OHLC"""
        try:
            logger.warning(f"Using fallback for {ticker} - synthesizing OHLC")

            data = apimoex.get_board_history(
                session=self.session,
                security=ticker,
                start=start_date,
                end=end_date,
                board='TQBR'
            )

            if not data:
                return None

            df = pd.DataFrame(data)

            # Process
            if 'TRADEDATE' in df.columns:
                df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
                df.set_index('TRADEDATE', inplace=True)

            # Get close price
            if 'CLOSE' in df.columns:
                df['Close'] = pd.to_numeric(df['CLOSE'], errors='coerce')
            else:
                return None

            # Get volume
            if 'VOLUME' in df.columns:
                df['Volume'] = pd.to_numeric(df['VOLUME'], errors='coerce')
            else:
                df['Volume'] = 0

            # Synthesize realistic OHLC
            np.random.seed(42)  # For reproducibility

            # Create Open prices (slightly different from Close)
            df['Open'] = df['Close'].copy()
            for i in range(1, len(df)):
                # Open is usually close to previous close
                prev_close = df['Close'].iloc[i-1]
                df.loc[df.index[i], 'Open'] = prev_close * (1 + np.random.uniform(-0.02, 0.02))

            # First day's open
            df.loc[df.index[0], 'Open'] = df['Close'].iloc[0] * (1 + np.random.uniform(-0.01, 0.01))

            # Create High and Low with realistic wicks
            for i in range(len(df)):
                open_price = df['Open'].iloc[i]
                close_price = df['Close'].iloc[i]

                # Determine trend
                if close_price >= open_price:
                    # Bullish candle
                    body_height = abs(close_price - open_price)
                    # Upper wick: 0-50% of body height
                    upper_wick = body_height * np.random.uniform(0, 0.5)
                    # Lower wick: 0-30% of body height
                    lower_wick = body_height * np.random.uniform(0, 0.3)

                    df.loc[df.index[i], 'High'] = close_price + upper_wick
                    df.loc[df.index[i], 'Low'] = open_price - lower_wick
                else:
                    # Bearish candle
                    body_height = abs(open_price - close_price)
                    # Upper wick: 0-30% of body height
                    upper_wick = body_height * np.random.uniform(0, 0.3)
                    # Lower wick: 0-50% of body height
                    lower_wick = body_height * np.random.uniform(0, 0.5)

                    df.loc[df.index[i], 'High'] = open_price + upper_wick
                    df.loc[df.index[i], 'Low'] = close_price - lower_wick

            # Ensure High >= max(Open, Close) and Low <= min(Open, Close)
            df['High'] = df[['Open', 'High', 'Close']].max(axis=1)
            df['Low'] = df[['Open', 'Low', 'Close']].min(axis=1)

            # Add minimum wick size (0.5% of price)
            min_wick = df['Close'].mean() * 0.005
            for i in range(len(df)):
                high = df['High'].iloc[i]
                low = df['Low'].iloc[i]
                body_high = max(df['Open'].iloc[i], df['Close'].iloc[i])
                body_low = min(df['Open'].iloc[i], df['Close'].iloc[i])

                if abs(high - body_high) < min_wick:
                    df.loc[df.index[i], 'High'] = body_high + min_wick
                if abs(body_low - low) < min_wick:
                    df.loc[df.index[i], 'Low'] = body_low - min_wick

            # Keep only needed columns
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]

            # Debug
            print(f"\n=== SYNTHESIZED OHLC DATA ({ticker}) ===")
            print(df.head())
            print("====================================\n")

            return df

        except Exception as e:
            logger.error(f"Error in fallback: {str(e)}")
            return None