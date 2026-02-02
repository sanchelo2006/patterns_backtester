import pandas as pd

def test_moex_data():
    """Test what data MOEX actually returns"""
    import apimoex
    import requests

    session = requests.Session()

    # Test with SBER
    data = apimoex.get_board_history(
        session=session,
        security='SBER',
        start='2024-01-01',
        end='2024-01-10',
        board='TQBR'
    )

    if data:
        df = pd.DataFrame(data)
        print("\n=== TEST: MOEX API RESPONSE ===")
        print(f"Columns: {df.columns.tolist()}")
        print(f"Number of rows: {len(df)}")
        if len(df) > 0:
            print("\nFirst row:")
            for col in df.columns:
                print(f"  {col}: {df.iloc[0][col]}")
        print("===============================\n")

print(test_moex_data())