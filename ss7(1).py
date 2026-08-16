# ============================================================
# SS7.PY
# SURE SHOT 7
#
# BUY:
# Trending market
# + Buyer area
# + Green hammer
# + Next candle green
# = BUY
#
# SELL:
# Trending market
# + Seller area
# + Red hammer
# + Next candle red
# = SELL
#
# Precautions:
# - Abnormal hammer avoid
# - Strong SNR area avoid
# ============================================================

import pandas as pd


# ============================================================
# SETTINGS
# ============================================================

MIN_CANDLES = 30

EMA_FAST = 9
EMA_SLOW = 21

# Hammer body / wick settings
MAX_BODY_RATIO = 0.45
MIN_WICK_RATIO = 0.45

# Avoid extremely large candles
MAX_RANGE_MULTIPLIER = 2.5

# SNR sensitivity
SNR_LOOKBACK = 20
SNR_TOLERANCE = 0.0025


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


# ============================================================
# CHECK DATAFRAME
# ============================================================

def check_dataframe(df):

    if df is None:
        return False

    if not isinstance(df, pd.DataFrame):
        return False

    required = [
        "Open",
        "High",
        "Low",
        "Close"
    ]

    for col in required:
        if col not in df.columns:
            return False

    if len(df) < MIN_CANDLES:
        return False

    return True


# ============================================================
# PREPARE DATA
# ============================================================

def prepare_data(df):

    data = df.copy()

    for col in [
        "Open",
        "High",
        "Low",
        "Close"
    ]:
        data[col] = pd.to_numeric(
            data[col],
            errors="coerce"
        )

    data = data.dropna(
        subset=[
            "Open",
            "High",
            "Low",
            "Close"
        ]
    ).reset_index(drop=True)

    if len(data) < MIN_CANDLES:
        return data

    # EMA
    data["EMA9"] = data["Close"].ewm(
        span=EMA_FAST,
        adjust=False
    ).mean()

    data["EMA21"] = data["Close"].ewm(
        span=EMA_SLOW,
        adjust=False
    ).mean()

    return data


# ============================================================
# CANDLE INFORMATION
# ============================================================

def candle_info(row):

    o = safe_float(row["Open"])
    h = safe_float(row["High"])
    l = safe_float(row["Low"])
    c = safe_float(row["Close"])

    candle_range = h - l

    if candle_range <= 0:
        return {
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "body": 0,
            "upper_wick": 0,
            "lower_wick": 0,
            "range": 0,
            "body_ratio": 0
        }

    body = abs(c - o)

    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    body_ratio = body / candle_range

    return {
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "body": body,
        "upper_wick": max(upper_wick, 0),
        "lower_wick": max(lower_wick, 0),
        "range": candle_range,
        "body_ratio": body_ratio
    }


# ============================================================
# GREEN CANDLE
# ============================================================

def is_green(row):

    return (
        safe_float(row["Close"])
        >
        safe_float(row["Open"])
    )


# ============================================================
# RED CANDLE
# ============================================================

def is_red(row):

    return (
        safe_float(row["Close"])
        <
        safe_float(row["Open"])
    )


# ============================================================
# BULLISH HAMMER
# ============================================================

def is_green_hammer(row):

    info = candle_info(row)

    if info["range"] <= 0:
        return False

    # Must be green
    if info["close"] <= info["open"]:
        return False

    # Body should not be too large
    if info["body_ratio"] > MAX_BODY_RATIO:
        return False

    # Lower wick should be significant
    if info["lower_wick"] < (
        info["range"] * MIN_WICK_RATIO
    ):
        return False

    # Lower wick should be bigger than upper wick
    if info["lower_wick"] <= info["upper_wick"]:
        return False

    return True


# ============================================================
# BEARISH HAMMER
# ============================================================

def is_red_hammer(row):

    info = candle_info(row)

    if info["range"] <= 0:
        return False

    # Must be red
    if info["close"] >= info["open"]:
        return False

    # Body should not be too large
    if info["body_ratio"] > MAX_BODY_RATIO:
        return False

    # Upper wick should be significant
    if info["upper_wick"] < (
        info["range"] * MIN_WICK_RATIO
    ):
        return False

    # Upper wick should be bigger than lower wick
    if info["upper_wick"] <= info["lower_wick"]:
        return False

    return True


# ============================================================
# ABNORMAL HAMMER CHECK
# ============================================================

def is_abnormal_candle(df, index):

    if index < 5:
        return False

    current = candle_info(
        df.iloc[index]
    )

    current_range = current["range"]

    if current_range <= 0:
        return True

    previous_ranges = []

    start = max(0, index - 5)

    for i in range(start, index):

        info = candle_info(
            df.iloc[i]
        )

        if info["range"] > 0:
            previous_ranges.append(
                info["range"]
            )

    if not previous_ranges:
        return False

    average_range = sum(
        previous_ranges
    ) / len(previous_ranges)

    # Extremely large candle
    if current_range > (
        average_range * MAX_RANGE_MULTIPLIER
    ):
        return True

    return False


# ============================================================
# TREND
# ============================================================

def market_trend(df, index):

    if index < EMA_SLOW:
        return "RANGING"

    row = df.iloc[index]

    ema9 = safe_float(row["EMA9"])
    ema21 = safe_float(row["EMA21"])
    close = safe_float(row["Close"])

    # Bullish trend
    if (
        ema9 > ema21
        and close > ema9
    ):
        return "UPTREND"

    # Bearish trend
    if (
        ema9 < ema21
        and close < ema9
    ):
        return "DOWNTREND"

    return "RANGING"


# ============================================================
# BUYER AREA
# ============================================================

def buyer_area(df, index):

    if index < 5:
        return False

    # Current trend must be bullish
    trend = market_trend(
        df,
        index
    )

    if trend != "UPTREND":
        return False

    # Recent candles should show upward structure
    closes = []

    start = max(
        0,
        index - 4
    )

    for i in range(start, index + 1):

        closes.append(
            safe_float(
                df.iloc[i]["Close"]
            )
        )

    if len(closes) < 3:
        return False

    # Basic higher-close condition
    higher_count = 0

    for i in range(1, len(closes)):

        if closes[i] > closes[i - 1]:
            higher_count += 1

    if higher_count < 2:
        return False

    return True


# ============================================================
# SELLER AREA
# ============================================================

def seller_area(df, index):

    if index < 5:
        return False

    trend = market_trend(
        df,
        index
    )

    if trend != "DOWNTREND":
        return False

    closes = []

    start = max(
        0,
        index - 4
    )

    for i in range(start, index + 1):

        closes.append(
            safe_float(
                df.iloc[i]["Close"]
            )
        )

    if len(closes) < 3:
        return False

    lower_count = 0

    for i in range(1, len(closes)):

        if closes[i] < closes[i - 1]:
            lower_count += 1

    if lower_count < 2:
        return False

    return True


# ============================================================
# SNR CHECK
# ============================================================

def near_snr(df, index):

    if index < 5:
        return False

    current = candle_info(
        df.iloc[index]
    )

    price = current["close"]

    start = max(
        0,
        index - SNR_LOOKBACK
    )

    previous = df.iloc[
        start:index
    ]

    if len(previous) < 5:
        return False

    resistance = safe_float(
        previous["High"].max()
    )

    support = safe_float(
        previous["Low"].min()
    )

    if price == 0:
        return False

    tolerance = (
        abs(price) * SNR_TOLERANCE
    )

    # Near resistance
    if abs(price - resistance) <= tolerance:
        return True

    # Near support
    if abs(price - support) <= tolerance:
        return True

    return False


# ============================================================
# SIGNAL
# ============================================================

def signal(df):

    if not check_dataframe(df):

        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason": "Not enough candle data"
        }

    data = prepare_data(df)

    if len(data) < MIN_CANDLES:

        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason": "Need more candles"
        }

    # --------------------------------------------------------
    # IMPORTANT
    #
    # SS7 pattern:
    # Previous candle = hammer
    # Current candle = confirmation candle
    # --------------------------------------------------------

    hammer_index = len(data) - 2
    confirmation_index = len(data) - 1

    hammer = data.iloc[
        hammer_index
    ]

    confirmation = data.iloc[
        confirmation_index
    ]

    # --------------------------------------------------------
    # Abnormal hammer
    # --------------------------------------------------------

    if is_abnormal_candle(
        data,
        hammer_index
    ):

        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason": "Abnormal hammer"
        }

    # --------------------------------------------------------
    # SNR precaution
    # --------------------------------------------------------

    if near_snr(
        data,
        hammer_index
    ):

        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason": "Near SNR area"
        }

    trend = market_trend(
        data,
        hammer_index
    )

    # ========================================================
    # BUY SETUP
    # ========================================================

    if (
        trend == "UPTREND"
        and buyer_area(
            data,
            hammer_index
        )
        and is_green_hammer(
            hammer
        )
        and is_green(
            confirmation
        )
    ):

        confidence = 85

        return {
            "signal": "BUY",
            "confidence": confidence,
            "reason": (
                "SS7: Uptrend + buyer area + "
                "green hammer + green confirmation"
            )
        }

    # ========================================================
    # SELL SETUP
    # ========================================================

    if (
        trend == "DOWNTREND"
        and seller_area(
            data,
            hammer_index
        )
        and is_red_hammer(
            hammer
        )
        and is_red(
            confirmation
        )
    ):

        confidence = 85

        return {
            "signal": "SELL",
            "confidence": confidence,
            "reason": (
                "SS7: Downtrend + seller area + "
                "red hammer + red confirmation"
            )
        }

    # ========================================================
    # NO SETUP
    # ========================================================

    return {
        "signal": "HOLD",
        "confidence": 0,
        "reason": (
            "SS7 conditions not satisfied"
        )
    }


# ============================================================
# ALTERNATIVE FUNCTIONS
# ============================================================

def generate_signal(df):

    return signal(df)


def get_signal(df):

    return signal(df)


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("SS7 - SURE SHOT 7")
    print("=" * 60)

    print()
    print("BUY :")
    print("Uptrend + Buyer Area")
    print("+ Green Hammer")
    print("+ Next Green Candle")
    print()

    print("SELL :")
    print("Downtrend + Seller Area")
    print("+ Red Hammer")
    print("+ Next Red Candle")
    print()

    print("Precautions:")
    print("- Abnormal hammer")
    print("- SNR area")
    print("- Ranging market")
    print()

    # --------------------------------------------------------
    # Optional test using history.py
    # --------------------------------------------------------

    try:

        from history import load_history

        try:

            test_df = load_history(
                symbol="BTCUSDT",
                interval="1m",
                limit=100
            )

        except TypeError:

            test_df = load_history()

        result = signal(
            test_df
        )

        print("-" * 60)
        print("TEST RESULT")
        print("-" * 60)

        print(
            "Signal     :",
            result["signal"]
        )

        print(
            "Confidence :",
            result["confidence"]
        )

        print(
            "Reason     :",
            result["reason"]
        )

    except Exception as e:

        print()
        print(
            "Test skipped:",
            e
        )

    print()
    print("=" * 60)