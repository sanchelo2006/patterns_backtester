import pandas as pd
import apimoex
import requests
from typing import Optional, Tuple
from datetime import datetime, timedelta
from src.utils.logger import get_logger

logger = get_logger('app')


class MOEXClient:
    """Client for MOEX data"""

    def __init__(self):
        self.session = requests.Session()

    def get_data(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        interval: int = 24
    ) -> Optional[pd.DataFrame]:
        """Get historical data from MOEX"""
        try:
            logger.info(f"Fetching MOEX data for {ticker} from {start_date} to {end_date}")

            # Get data using the correct function signature
            data = apimoex.get_board_history(
                self.session,
                ticker,
                start=start_date,
                end=end_date
            )

            if not data:
                logger.warning(f"No data found for {ticker}")
                return None

            df = pd.DataFrame(data)

            # Convert date column
            if 'TRADEDATE' in df.columns:
                df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
                df.set_index('TRADEDATE', inplace=True)
            elif 'begin' in df.columns:
                df['begin'] = pd.to_datetime(df['begin'])
                df.set_index('begin', inplace=True)

            # Rename columns to match expected format
            column_mapping = {
                'OPEN': 'Open',
                'open': 'Open',
                'HIGH': 'High',
                'high': 'High',
                'LOW': 'Low',
                'low': 'Low',
                'CLOSE': 'Close',
                'close': 'Close',
                'VALUE': 'Volume',
                'value': 'Volume',
                'VOLUME': 'Volume',
                'volume': 'Volume'
            }

            for old_col, new_col in column_mapping.items():
                if old_col in df.columns and new_col not in df.columns:
                    df[new_col] = df[old_col]

            # Ensure we have all required columns
            required_cols = ['Open', 'High', 'Low', 'Close']
            if not all(col in df.columns for col in required_cols):
                # If missing columns, try to create them from available data
                if 'Close' not in df.columns and 'LAST' in df.columns:
                    df['Close'] = df['LAST']
                if 'Open' not in df.columns and 'Close' in df.columns:
                    # Use previous close as open (simplification)
                    df['Open'] = df['Close'].shift(1).fillna(df['Close'])
                if 'High' not in df.columns and 'Close' in df.columns:
                    df['High'] = df[['Open', 'Close']].max(axis=1)
                if 'Low' not in df.columns and 'Close' in df.columns:
                    df['Low'] = df[['Open', 'Close']].min(axis=1)

            # Add Volume if missing
            if 'Volume' not in df.columns:
                df['Volume'] = 0

            # Ensure numeric types
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # Drop rows with NaN values
            df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])

            logger.info(f"Retrieved {len(df)} rows for {ticker}")
            return df

        except Exception as e:
            logger.error(f"Error fetching MOEX data: {str(e)}", exc_info=True)
            return None

    def get_available_tickers(self) -> list:
        """Get list of available tickers"""
        try:
            with requests.Session() as session:
                securities = apimoex.find_securities(session, '')
                return [sec['secid'] for sec in securities]
        except Exception as e:
            logger.error(f"Error fetching tickers: {str(e)}")
            return []

    def get_ticker_info(self, ticker: str) -> dict:
        """Get information about a specific ticker"""
        try:
            with requests.Session() as session:
                info = apimoex.find_security(session, ticker)
                return info if info else {}
        except Exception as e:
            logger.error(f"Error fetching ticker info: {str(e)}")
            return {}