import requests
import pandas as pd
import time
from datetime import datetime

# =========================================================
# SETTINGS
# =========================================================

INTERVAL = "1m"
LIMIT = 100

ASSETS = {
    "BTC/USD": "BTCUSDT",
    "ETH/USD": "ETHUSDT",
    "XRP/USD": "XRPUSDT",
    "SOL/USD": "SOLUSDT",
    "LTC/USD": "LTCUSDT",
    "DOGE/USD": "DOGEUSDT",
    "BNB/USD": "BNBUSDT",
    "ADA/USD": "ADAUSDT",
}

BINANCE_URL = "https://api.binance.com/api/v3/klines"


# =========================================================
# GET BINANCE DATA
# =========================================================

def get_candles(symbol):

    try:
        params = {
            "symbol": symbol,
            "interval": INTERVAL,
            "limit": LIMIT
        }

        r = requests.get(
            BINANCE_URL,
            params=params,
            timeout=10
        )

        r.raise_for_status()

        data = r.json()

        if not isinstance(data, list):
            return None

        df = pd.DataFrame(data, columns=[
            "OpenTime",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "CloseTime",
            "QuoteVolume",
            "Trades",
            "TakerBase",
            "TakerQuote",
            "Ignore"
        ])

        for col in ["Open", "High", "Low", "Close", "Volume"]:
            df[col] = pd.to_numeric(df[col])

        df["Time"] = pd.to_datetime(
            df["OpenTime"],
            unit="ms"
        )

        return df

    except Exception as e:

        print("Data error:", symbol, e)

        return None


# =========================================================
# INDICATORS
# =========================================================

def add_indicators(df):

    df = df.copy()

    df["EMA9"] = df["Close"].ewm(
        span=9,
        adjust=False
    ).mean()

    df["EMA21"] = df["Close"].ewm(
        span=21,
        adjust=False
    ).mean()

    df["Range"] = df["High"] - df["Low"]

    df["Body"] = abs(
        df["Close"] - df["Open"]
    )

    df["UpperTail"] = (
        df["High"] -
        df[["Open", "Close"]].max(axis=1)
    )

    df["LowerTail"] = (
        df[["Open", "Close"]].min(axis=1) -
        df["Low"]
    )

    return df


# =========================================================
# TREND
# =========================================================

def get_trend(df):

    last = df.iloc[-1]

    if last["EMA9"] > last["EMA21"]:
        return "UP"

    if last["EMA9"] < last["EMA21"]:
        return "DOWN"

    return "SIDEWAYS"


# =========================================================
# ENGULFING PATTERN
# =========================================================

def get_pattern(df):

    if len(df) < 3:
        return "NONE"

    prev = df.iloc[-2]
    curr = df.iloc[-1]

    # Previous bearish + current bullish
    bullish = (
        prev["Close"] < prev["Open"]
        and
        curr["Close"] > curr["Open"]
        and
        curr["Open"] <= prev["Close"]
        and
        curr["Close"] >= prev["Open"]
    )

    # Previous bullish + current bearish
    bearish = (
        prev["Close"] > prev["Open"]
        and
        curr["Close"] < curr["Open"]
        and
        curr["Open"] >= prev["Close"]
        and
        curr["Close"] <= prev["Open"]
    )

    if bullish:
        return "BULLISH ENGULFING"

    if bearish:
        return "BEARISH ENGULFING"

    return "NONE"


# =========================================================
# CANDLE STRENGTH
# =========================================================

def candle_strength(df):

    last = df.iloc[-1]

    candle_range = last["Range"]

    if candle_range <= 0:
        return "WEAK"

    body_ratio = (
        last["Body"] /
        candle_range
    )

    if body_ratio >= 0.70:
        return "STRONG"

    if body_ratio >= 0.45:
        return "MEDIUM"

    return "WEAK"


# =========================================================
# SHORT TAIL CHECK
# =========================================================

def short_tail(df):

    last = df.iloc[-1]

    candle_range = last["Range"]

    if candle_range <= 0:
        return False

    upper_ratio = (
        last["UpperTail"] /
        candle_range
    )

    lower_ratio = (
        last["LowerTail"] /
        candle_range
    )

    return (
        upper_ratio <= 0.25
        and
        lower_ratio <= 0.25
    )


# =========================================================
# SUPPORT / RESISTANCE
# =========================================================

def get_sr(df):

    recent = df.iloc[-21:-1]

    support = recent["Low"].min()
    resistance = recent["High"].max()

    return support, resistance


def near_sr(df):

    last_price = df.iloc[-1]["Close"]

    support, resistance = get_sr(df)

    price_range = resistance - support

    if price_range <= 0:
        return False, "NONE"

    distance_support = (
        abs(last_price - support)
        / price_range
    )

    distance_resistance = (
        abs(resistance - last_price)
        / price_range
    )

    # Too close to support
    if distance_support <= 0.05:
        return True, "SUPPORT"

    # Too close to resistance
    if distance_resistance <= 0.05:
        return True, "RESISTANCE"

    return False, "NONE"


# =========================================================
# SIGNAL ENGINE
# =========================================================

def calculate_signal(df):

    df = add_indicators(df)

    trend = get_trend(df)

    pattern = get_pattern(df)

    strength = candle_strength(df)

    short_tail_ok = short_tail(df)

    sr_block, sr_type = near_sr(df)

    buy_score = 0
    sell_score = 0

    reasons = []

    # -----------------------------------------------------
    # TREND
    # -----------------------------------------------------

    if trend == "UP":

        buy_score += 25
        reasons.append("UP trend")

    elif trend == "DOWN":

        sell_score += 25
        reasons.append("DOWN trend")

    # -----------------------------------------------------
    # ENGULFING
    # -----------------------------------------------------

    if pattern == "BULLISH ENGULFING":

        buy_score += 30
        reasons.append("Bullish engulfing")

    elif pattern == "BEARISH ENGULFING":

        sell_score += 30
        reasons.append("Bearish engulfing")

    # -----------------------------------------------------
    # CANDLE STRENGTH
    # -----------------------------------------------------

    if strength == "STRONG":

        if df.iloc[-1]["Close"] > df.iloc[-1]["Open"]:
            buy_score += 15

        elif df.iloc[-1]["Close"] < df.iloc[-1]["Open"]:
            sell_score += 15

        reasons.append("Strong candle")

    elif strength == "MEDIUM":

        if df.iloc[-1]["Close"] > df.iloc[-1]["Open"]:
            buy_score += 8

        elif df.iloc[-1]["Close"] < df.iloc[-1]["Open"]:
            sell_score += 8

    # -----------------------------------------------------
    # SHORT TAIL
    # -----------------------------------------------------

    if short_tail_ok:

        if df.iloc[-1]["Close"] > df.iloc[-1]["Open"]:
            buy_score += 10

        elif df.iloc[-1]["Close"] < df.iloc[-1]["Open"]:
            sell_score += 10

        reasons.append("Short tail")

    # -----------------------------------------------------
    # SUPPORT / RESISTANCE FILTER
    # -----------------------------------------------------

    if sr_block:

        # Do not force continuation near S/R
        buy_score = max(0, buy_score - 20)
        sell_score = max(0, sell_score - 20)

        reasons.append(
            "Near " + sr_type
        )

    # -----------------------------------------------------
    # FINAL SIGNAL
    # -----------------------------------------------------

    difference = abs(
        buy_score - sell_score
    )

    if (
        buy_score >= 50
        and
        buy_score > sell_score
        and
        not sr_block
    ):

        signal = "BUY"

        confidence = min(
            95,
            50 + difference
        )

    elif (
        sell_score >= 50
        and
        sell_score > buy_score
        and
        not sr_block
    ):

        signal = "SELL"

        confidence = min(
            95,
            50 + difference
        )

    else:

        signal = "HOLD"

        confidence = 50

    return {
        "signal": signal,
        "confidence": confidence,
        "trend": trend,
        "pattern": pattern,
        "strength": strength,
        "short_tail": short_tail_ok,
        "sr": sr_type if sr_block else "CLEAR",
        "buy_score": buy_score,
        "sell_score": sell_score,
        "reasons": reasons
    }


# =========================================================
# DISPLAY
# =========================================================

def analyze_asset(name, symbol):

    df = get_candles(symbol)

    if df is None:
        print("\n", name, "DATA ERROR")
        return

    if len(df) < 30:
        print("\n", name, "NOT ENOUGH DATA")
        return

    result = calculate_signal(df)

    last = df.iloc[-1]

    print("\n")
    print("========================================")
    print("Asset       :", name)
    print("Binance     :", symbol)
    print("Price       :", last["Close"])
    print("Candle      :", last["Time"])
    print("Trend       :", result["trend"])
    print("Pattern     :", result["pattern"])
    print("Strength    :", result["strength"])
    print("Short Tail  :", result["short_tail"])
    print("S/R Filter  :", result["sr"])
    print("----------------------------------------")
    print("BUY Score   :", result["buy_score"])
    print("SELL Score  :", result["sell_score"])
    print("----------------------------------------")
    print("FINAL SIGNAL:", result["signal"])
    print("CONFIDENCE  :", str(result["confidence"]) + "%")
    print("----------------------------------------")
    print("Reason      :", ", ".join(result["reasons"]))
    print("Candles     :", len(df))
    print("========================================")


# =========================================================
# ALL ASSETS
# =========================================================

def analyze_all():

    print("\n\n")
    print("########################################")
    print("   MULTI ASSET SIGNAL ENGINE")
    print("   Binance 1 Minute")
    print("   100 Candles")
    print("########################################")
    print("Time:", datetime.now())

    for name, symbol in ASSETS.items():

        analyze_asset(
            name,
            symbol
        )

        # Binance API वर अनावश्यक load टाळण्यासाठी
        time.sleep(0.3)


# =========================================================
# MAIN LOOP
# =========================================================

def main():

    print("Starting improved signal app...")

    while True:

        try:

            analyze_all()

            print("\nNext update in 60 seconds...")

            time.sleep(60)

        except KeyboardInterrupt:

            print("\nApp stopped.")
            break

        except Exception as e:

            print("\nMain error:", e)

            time.sleep(5)


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    main()