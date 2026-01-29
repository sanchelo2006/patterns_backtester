from pybit.unified_trading import HTTP
import pandas as pd
from typing import Optional, List
from datetime import datetime, timedelta
import time
from src.config.settings import BYBIT_TESTNET, BYBIT_API_KEY, BYBIT_API_SECRET
from src.utils.logger import get_logger

logger = get_logger('app')


class CryptoClient:
    """Client for Bybit cryptocurrency data"""

    def __init__(self):
        try:
            self.session = HTTP(
                testnet=BYBIT_TESTNET,
                api_key=BYBIT_API_KEY if BYBIT_API_KEY else None,
                api_secret=BYBIT_API_SECRET if BYBIT_API_SECRET else None
            )
            logger.info("Crypto client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize crypto client: {str(e)}")
            self.session = None

    def get_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = 'D'
    ) -> Optional[pd.DataFrame]:
        """Get historical data from Bybit"""
        try:
            if not self.session:
                logger.warning("Crypto client not initialized")
                return None

            logger.info(f"Fetching crypto data for {symbol} from {start_date} to {end_date}")

            # Convert dates to timestamps
            try:
                start_ts = int(pd.Timestamp(start_date).timestamp() * 1000)
                end_ts = int(pd.Timestamp(end_date).timestamp() * 1000)
            except Exception as e:
                logger.error(f"Invalid date format: {str(e)}")
                return None

            # Fetch data
            all_data = []
            current_start = start_ts
            max_requests = 10  # Limit requests to avoid rate limits

            for attempt in range(max_requests):
                try:
                    response = self.session.get_kline(
                        category="spot",
                        symbol=symbol,
                        interval=interval,
                        start=current_start,
                        end=end_ts,
                        limit=1000
                    )

                    if response['retCode'] != 0:
                        logger.warning(f"Bybit API error: {response['retMsg']}")
                        break

                    candles = response['result']['list']
                    if not candles:
                        break

                    all_data.extend(candles)

                    # Get timestamp of last candle
                    last_timestamp = int(candles[-1][0])
                    if last_timestamp <= current_start:
                        break

                    current_start = last_timestamp + 1

                    if len(candles) < 1000:
                        break

                    # Small delay to avoid rate limiting
                    time.sleep(0.1)

                except Exception as e:
                    logger.error(f"Error in request attempt {attempt + 1}: {str(e)}")
                    if attempt < max_requests - 1:
                        time.sleep(1)
                        continue
                    else:
                        break

            if not all_data:
                logger.warning(f"No data found for {symbol}")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(all_data, columns=[
                'timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'turnover'
            ])

            # Convert timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(float).astype(int), unit='ms')
            df.set_index('timestamp', inplace=True)

            # Sort by date
            df = df.sort_index()

            # Convert to float
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = df[col].astype(float)

            # Filter by date range
            mask = (df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))
            df = df[mask]

            logger.info(f"Retrieved {len(df)} rows for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Error fetching crypto data: {str(e)}", exc_info=True)
            return None

    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols"""
        try:
            if not self.session:
                return []

            response = self.session.get_instruments_info(category="spot")
            if response['retCode'] == 0:
                symbols = [inst['symbol'] for inst in response['result']['list']]
                return symbols
            return []
        except Exception as e:
            logger.error(f"Error fetching symbols: {str(e)}")
            return []