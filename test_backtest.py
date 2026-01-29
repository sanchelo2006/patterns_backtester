import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / 'src'
sys.path.append(str(src_path))

from data.moex_client import MOEXClient
from data.crypto_client import CryptoClient
from patterns.pattern_detector import PatternDetector
from backtest.engine import BacktestEngine
from visualization.chart_builder import ChartBuilder
import pandas as pd

def test_moex():
    """Test MOEX client"""
    print("Testing MOEX client...")
    client = MOEXClient()

    # Test with SBER (one of the most liquid stocks on MOEX)
    data = client.get_data(
        ticker="SBER",
        start_date="2023-01-01",
        end_date="2023-12-31"
    )

    if data is not None:
        print(f"Successfully fetched {len(data)} rows")
        print(f"Columns: {data.columns.tolist()}")
        print(f"First few rows:\n{data.head()}")
        print(f"Date range: {data.index[0]} to {data.index[-1]}")
        return data
    else:
        print("Failed to fetch MOEX data")
        return None

def test_crypto():
    """Test Crypto client"""
    print("\nTesting Crypto client...")
    client = CryptoClient()

    # Test with BTCUSDT
    data = client.get_data(
        symbol="BTCUSDT",
        start_date="2023-01-01",
        end_date="2023-01-31"  # Smaller range for testing
    )

    if data is not None:
        print(f"Successfully fetched {len(data)} rows")
        print(f"Columns: {data.columns.tolist()}")
        print(f"First few rows:\n{data.head()}")
        return data
    else:
        print("Failed to fetch crypto data")
        return None

def test_patterns(df):
    """Test pattern detection"""
    print("\nTesting pattern detection...")

    detector = PatternDetector(threshold=0.5)
    patterns_df = detector.detect_all_patterns(df.copy())

    # Count patterns detected
    pattern_cols = [col for col in patterns_df.columns if col.startswith('CDL')]
    print(f"Detected {len(pattern_cols)} patterns")

    # Check which patterns have signals
    for pattern in pattern_cols[:10]:  # Show first 10
        signal_count = (patterns_df[pattern] != 0).sum()
        if signal_count > 0:
            print(f"{pattern}: {signal_count} signals")

    return patterns_df

def test_backtest(df_with_patterns):
    """Test backtest engine"""
    print("\nTesting backtest engine...")

    # Use a subset of patterns for testing
    test_patterns = ['CDLENGULFING', 'CDLHAMMER', 'CDLSHOOTINGSTAR', 'CDLMORNINGSTAR']

    engine = BacktestEngine(
        initial_capital=1000000,
        position_size_pct=10,
        commission=0.001
    )

    results = engine.run(df_with_patterns, test_patterns)

    print(f"Total trades: {len(results['trades'])}")
    print(f"Final capital: {results['metrics'].get('final_capital', 0):,.2f}")
    print(f"Total return: {results['metrics'].get('total_return_pct', 0):.2f}%")
    print(f"Win rate: {results['metrics'].get('win_rate', 0):.2f}%")

    return results

def test_chart(results):
    """Test chart creation"""
    print("\nTesting chart creation...")

    if len(results['trades']) == 0:
        print("No trades to chart")
        return

    chart_builder = ChartBuilder()
    fig = chart_builder.create_candlestick_chart(
        results['df'],
        results['trades'],
        title="Test Backtest Results"
    )

    # Save to HTML
    fig.write_html("test_chart.html")
    print("Chart saved to test_chart.html")

    # Show equity curve
    equity_fig = chart_builder.create_equity_curve_chart(results['equity_curve'])
    equity_fig.write_html("test_equity_curve.html")
    print("Equity curve saved to test_equity_curve.html")

def main():
    """Main test function"""
    print("Starting backtest system tests...")

    # Test MOEX
    moex_data = test_moex()

    if moex_data is not None:
        # Test patterns on MOEX data
        patterns_data = test_patterns(moex_data)

        # Test backtest
        results = test_backtest(patterns_data)

        # Test chart
        test_chart(results)

    print("\nAll tests completed!")

if __name__ == "__main__":
    main()