import requests
import pandas as pd

def load_history():
    url = "https://api.binance.com/api/v3/klines"

    params = {
        "symbol": "BTCUSDT",
        "interval": "1m",
        "limit": 100
    }

    data = requests.get(url, params=params).json()

    df = pd.DataFrame(data)
    df = df[[0,1,2,3,4,5]]
    df.columns = ["Time","Open","High","Low","Close","Volume"]

    for col in ["Open","High","Low","Close","Volume"]:
        df[col] = df[col].astype(float)

    return df