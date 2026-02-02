# moex_client.py - Updated version
import pandas as pd
import apimoex
import requests
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import time
from src.utils.logger import get_logger

logger = get_logger('app')


class MOEXClient:
    """Client for MOEX data with correct API usage"""

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

            # Parse timeframe
            if timeframe == '1h' or 'hour' in timeframe.lower():
                return self._get_intraday_data(ticker, start_date, end_date, interval=60)
            elif timeframe == '4h':
                return self._get_intraday_data(ticker, start_date, end_date, interval=240)
            elif 'min' in timeframe.lower():
                # Extract minutes
                minutes = int(''.join(filter(str.isdigit, timeframe)))
                return self._get_intraday_data(ticker, start_date, end_date, interval=minutes)
            else:
                # Default to daily data
                return self._get_daily_data(ticker, start_date, end_date)

        except Exception as e:
            logger.error(f"Error fetching MOEX data: {str(e)}", exc_info=True)
            return None

    def _get_daily_data(
        self,
        ticker: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """Get daily data using apimoex"""
        try:
            logger.info(f"Fetching daily data for {ticker}")

            # Use correct API call for MOEX
            data = apimoex.get_board_history(
                session=self.session,
                security=ticker,
                start=start_date,
                end=end_date,
                board='TQBR'  # Add board parameter
            )

            if not data:
                logger.warning(f"No daily data found for {ticker}")
                return None

            df = pd.DataFrame(data)

            # Process dataframe
            if 'TRADEDATE' in df.columns:
                df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
                df.set_index('TRADEDATE', inplace=True)

            # Rename columns
            column_mapping = {
                'OPEN': 'Open',
                'HIGH': 'High',
                'LOW': 'Low',
                'CLOSE': 'Close',
                'VALUE': 'Volume',
                'VOLUME': 'Volume',
                'WAPRICE': 'WAP',  # Weighted Average Price
                'NUMTRADES': 'Trades'
            }

            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df[new_col] = df[old_col]

            # Ensure required columns exist
            required = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in required:
                if col not in df.columns:
                    # Fill missing with appropriate values
                    if col == 'Open':
                        df['Open'] = df['Close'].shift(1).fillna(df['Close'])
                    elif col == 'High':
                        df['High'] = df[['Open', 'Close']].max(axis=1)
                    elif col == 'Low':
                        df['Low'] = df[['Open', 'Close']].min(axis=1)
                    elif col == 'Close' and 'WAP' in df.columns:
                        df['Close'] = df['WAP']
                    elif col == 'Volume':
                        df['Volume'] = 0

            # Convert to numeric
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # Drop NaN values
            df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])

            # Sort by date
            df = df.sort_index()

            # Filter by date range
            df = df[(df.index >= pd.Timestamp(start_date)) &
                    (df.index <= pd.Timestamp(end_date))]

            logger.info(f"Retrieved {len(df)} daily bars for {ticker}")
            return df

        except Exception as e:
            logger.error(f"Error fetching daily data: {str(e)}")
            return None

    def _get_intraday_data(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        interval: int = 60  # minutes
    ) -> Optional[pd.DataFrame]:
        """Get intraday data using MOEX ISS API directly"""
        try:
            logger.info(f"Fetching intraday data for {ticker} (interval: {interval}min)")

            # MOEX ISS API for candles
            url = f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/{ticker}/candles.json"

            all_data = []
            current_start = pd.Timestamp(start_date)
            current_end = pd.Timestamp(end_date)

            # Fetch data in chunks (max 500 candles per request)
            while current_start <= current_end:
                # Format dates for MOEX API
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
                    logger.info(f"Fetched {len(candles)} candles from {from_date} to {to_date}")

                # Move to next period
                current_start += timedelta(days=31)

                # Rate limiting
                time.sleep(0.1)

            if not all_data:
                logger.warning(f"No intraday data found for {ticker}")
                # Fallback to daily data
                return self._get_daily_data(ticker, start_date, end_date)

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

            # Sort by date
            df = df.sort_index()

            # Filter by date range
            df = df[(df.index >= pd.Timestamp(start_date)) &
                    (df.index <= pd.Timestamp(end_date))]

            # Remove duplicates
            df = df[~df.index.duplicated(keep='first')]

            logger.info(f"Retrieved {len(df)} intraday bars for {ticker}")
            return df

        except Exception as e:
            logger.error(f"Error fetching intraday data: {str(e)}")
            # Fallback to daily data
            return self._get_daily_data(ticker, start_date, end_date)

    def get_available_tickers(self) -> list:
        """Get list of available tickers"""
        try:
            with requests.Session() as session:
                securities = apimoex.find_securities(session, '')
                return [sec['secid'] for sec in securities if sec.get('boardid') == 'TQBR']
        except Exception as e:
            logger.error(f"Error fetching tickers: {str(e)}")
            return []