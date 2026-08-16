# ============================================================
# DOJI VERSION 1
# SNR FIRST TOUCH REVERSAL
# ============================================================

import pandas as pd


# ============================================================
# SETTINGS
# ============================================================

MIN_CANDLES = 30

DOJI_BODY_RATIO = 0.15

LONG_WICK_RATIO = 0.55

BIG_CANDLE_MULTIPLIER = 1.8

SNR_TOLERANCE = 0.0015

LOOKBACK = 20

HAMMER_WICK_RATIO = 2.0

TREND_EMA_FAST = 9
TREND_EMA_SLOW = 21


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(value, default=0.0):

    try:
        return float(value)

    except Exception:

        return default


# ============================================================
# CHECK DATA
# ============================================================

def prepare_dataframe(df):

    if df is None:
        return pd.DataFrame()

    df = df.copy()

    required = [
        "Open",
        "High",
        "Low",
        "Close"
    ]

    for col in required:

        if col not in df.columns:
            return pd.DataFrame()

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    df = df.dropna(
        subset=required
    ).reset_index(
        drop=True
    )

    return df


# ============================================================
# CANDLE INFORMATION
# ============================================================

def candle_info(row):

    o = safe_float(row["Open"])
    h = safe_float(row["High"])
    l = safe_float(row["Low"])
    c = safe_float(row["Close"])

    total_range = h - l

    body = abs(c - o)

    upper_wick = h - max(o, c)

    lower_wick = min(o, c) - l

    if total_range <= 0:

        body_ratio = 1.0
        upper_ratio = 0.0
        lower_ratio = 0.0

    else:

        body_ratio = body / total_range
        upper_ratio = upper_wick / total_range
        lower_ratio = lower_wick / total_range

    if c > o:
        colour = "GREEN"

    elif c < o:
        colour = "RED"

    else:
        colour = "DOJI"

    return {
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "range": total_range,
        "body": body,
        "upper_wick": upper_wick,
        "lower_wick": lower_wick,
        "body_ratio": body_ratio,
        "upper_ratio": upper_ratio,
        "lower_ratio": lower_ratio,
        "colour": colour
    }


# ============================================================
# DOJI DETECTION
# ============================================================

def is_doji(row):

    info = candle_info(row)

    if info["range"] <= 0:
        return False

    return (
        info["body_ratio"]
        <= DOJI_BODY_RATIO
    )


# ============================================================
# HAMMER DETECTION
# ============================================================

def is_hammer(row):

    info = candle_info(row)

    body = info["body"]

    if body <= 0:
        return False

    upper = info["upper_wick"]

    lower = info["lower_wick"]

    # Classic hammer
    if lower >= body * HAMMER_WICK_RATIO:

        if upper <= body:

            return True

    # Inverted hammer
    if upper >= body * HAMMER_WICK_RATIO:

        if lower <= body:

            return True

    return False


# ============================================================
# BIG CANDLE
# ============================================================

def is_big_candle(df, index):

    if index < 5:
        return False

    current = candle_info(
        df.iloc[index]
    )

    current_range = current["range"]

    previous_ranges = []

    start = max(
        0,
        index - 10
    )

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

    if average_range <= 0:
        return False

    return (
        current_range
        >= average_range * BIG_CANDLE_MULTIPLIER
    )


# ============================================================
# SNR LEVEL
# ============================================================

def calculate_snr(df, doji_index):

    row = df.iloc[doji_index]

    info = candle_info(row)

    # Doji high / low are used as possible SNR
    resistance = info["high"]

    support = info["low"]

    return support, resistance


# ============================================================
# PRICE NEAR LEVEL
# ============================================================

def near_level(price, level):

    if level == 0:
        return False

    difference = abs(
        price - level
    )

    tolerance = abs(level) * SNR_TOLERANCE

    return (
        difference <= tolerance
    )


# ============================================================
# TOUCH WITHOUT CROSS
# ============================================================

def touches_without_cross(
    row,
    level,
    direction
):

    info = candle_info(row)

    high = info["high"]
    low = info["low"]
    close = info["close"]

    if direction == "RESISTANCE":

        # Candle touches resistance
        touched = (
            high >= level
        )

        # Close must remain below
        not_crossed = (
            close < level
        )

        return (
            touched and
            not_crossed
        )

    if direction == "SUPPORT":

        touched = (
            low <= level
        )

        # Close must remain above
        not_crossed = (
            close > level
        )

        return (
            touched and
            not_crossed
        )

    return False


# ============================================================
# TREND DETECTION
# ============================================================

def market_trend(df):

    if len(df) < TREND_EMA_SLOW + 5:

        return "UNKNOWN"

    close = df["Close"]

    ema_fast = (
        close
        .ewm(
            span=TREND_EMA_FAST,
            adjust=False
        )
        .mean()
    )

    ema_slow = (
        close
        .ewm(
            span=TREND_EMA_SLOW,
            adjust=False
        )
        .mean()
    )

    fast = safe_float(
        ema_fast.iloc[-1]
    )

    slow = safe_float(
        ema_slow.iloc[-1]
    )

    if fast > slow:
        return "UP"

    if fast < slow:
        return "DOWN"

    return "SIDEWAYS"


# ============================================================
# RANGE / SHOCK FILTER
# ============================================================

def is_shock_area(df, index):

    if index < 10:
        return False

    current = candle_info(
        df.iloc[index]
    )

    ranges = []

    start = max(
        0,
        index - 10
    )

    for i in range(start, index):

        info = candle_info(
            df.iloc[i]
        )

        if info["range"] > 0:

            ranges.append(
                info["range"]
            )

    if not ranges:
        return False

    average = (
        sum(ranges)
        / len(ranges)
    )

    if average <= 0:
        return False

    return (
        current["range"]
        > average * 2.5
    )


# ============================================================
# DETECT SNR FIRST TOUCH
# ============================================================

def find_first_touch(
    df,
    doji_index,
    start_index,
    end_index
):

    support, resistance = (
        calculate_snr(
            df,
            doji_index
        )
    )

    for i in range(
        start_index,
        end_index
    ):

        row = df.iloc[i]

        # -----------------------------------------------
        # Resistance touch
        # -----------------------------------------------

        if touches_without_cross(
            row,
            resistance,
            "RESISTANCE"
        ):

            return {
                "index": i,
                "level": resistance,
                "type": "RESISTANCE"
            }

        # -----------------------------------------------
        # Support touch
        # -----------------------------------------------

        if touches_without_cross(
            row,
            support,
            "SUPPORT"
        ):

            return {
                "index": i,
                "level": support,
                "type": "SUPPORT"
            }

    return None


# ============================================================
# BUY SIGNAL
# ============================================================

def check_buy(df):

    n = len(df)

    if n < MIN_CANDLES:

        return False, 0, "Not enough candles"

    # Search recent Doji
    start = max(
        5,
        n - LOOKBACK
    )

    for doji_index in range(
        start,
        n - 2
    ):

        doji = df.iloc[
            doji_index
        ]

        if not is_doji(doji):
            continue

        # ------------------------------------------------
        # Doji should be in sellers / lower area
        # ------------------------------------------------

        recent = df.iloc[
            max(0, doji_index - 5):
            doji_index
        ]

        if len(recent) == 0:
            continue

        average_close = safe_float(
            recent["Close"].mean()
        )

        doji_close = safe_float(
            doji["Close"]
        )

        # Sellers area approximation
        if doji_close > average_close:
            continue

        # ------------------------------------------------
        # Find SNR first touch
        # ------------------------------------------------

        touch = find_first_touch(
            df,
            doji_index,
            doji_index + 1,
            n - 1
        )

        if touch is None:
            continue

        touch_index = touch["index"]

        # We need candle AFTER touch
        if touch_index >= n - 1:
            continue

        touch_candle = df.iloc[
            touch_index
        ]

        next_candle = df.iloc[
            touch_index + 1
        ]

        # ------------------------------------------------
        # Precautions
        # ------------------------------------------------

        if is_big_candle(
            df,
            touch_index
        ):
            continue

        if is_hammer(
            touch_candle
        ):
            continue

        if is_shock_area(
            df,
            touch_index
        ):
            continue

        # ------------------------------------------------
        # BUY confirmation
        # Next candle must be GREEN
        # ------------------------------------------------

        next_info = candle_info(
            next_candle
        )

        if next_info["colour"] == "GREEN":

            return (
                True,
                80,
                "DOJI + SNR first touch + GREEN confirmation"
            )

    return (
        False,
        0,
        "No valid BUY setup"
    )


# ============================================================
# SELL SIGNAL
# ============================================================

def check_sell(df):

    n = len(df)

    if n < MIN_CANDLES:

        return False, 0, "Not enough candles"

    start = max(
        5,
        n - LOOKBACK
    )

    for doji_index in range(
        start,
        n - 2
    ):

        doji = df.iloc[
            doji_index
        ]

        if not is_doji(doji):
            continue

        # ------------------------------------------------
        # Doji should be in buyers / upper area
        # ------------------------------------------------

        recent = df.iloc[
            max(0, doji_index - 5):
            doji_index
        ]

        if len(recent) == 0:
            continue

        average_close = safe_float(
            recent["Close"].mean()
        )

        doji_close = safe_float(
            doji["Close"]
        )

        # Buyers area approximation
        if doji_close < average_close:
            continue

        # ------------------------------------------------
        # Find first SNR touch
        # ------------------------------------------------

        touch = find_first_touch(
            df,
            doji_index,
            doji_index + 1,
            n - 1
        )

        if touch is None:
            continue

        touch_index = touch["index"]

        if touch_index >= n - 1:
            continue

        touch_candle = df.iloc[
            touch_index
        ]

        next_candle = df.iloc[
            touch_index + 1
        ]

        # ------------------------------------------------
        # Precautions
        # ------------------------------------------------

        if is_big_candle(
            df,
            touch_index
        ):
            continue

        if is_hammer(
            touch_candle
        ):
            continue

        if is_shock_area(
            df,
            touch_index
        ):
            continue

        # ------------------------------------------------
        # SELL confirmation
        # Next candle must be RED
        # ------------------------------------------------

        next_info = candle_info(
            next_candle
        )

        if next_info["colour"] == "RED":

            return (
                True,
                80,
                "DOJI + SNR first touch + RED confirmation"
            )

    return (
        False,
        0,
        "No valid SELL setup"
    )


# ============================================================
# MAIN SIGNAL FUNCTION
# ============================================================

def signal(df):

    df = prepare_dataframe(df)

    if len(df) < MIN_CANDLES:

        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason": "Not enough candles"
        }

    buy, buy_conf, buy_reason = (
        check_buy(df)
    )

    sell, sell_conf, sell_reason = (
        check_sell(df)
    )

    # --------------------------------------------------------
    # BUY
    # --------------------------------------------------------

    if buy and not sell:

        return {
            "signal": "BUY",
            "confidence": buy_conf,
            "reason": buy_reason
        }

    # --------------------------------------------------------
    # SELL
    # --------------------------------------------------------

    if sell and not buy:

        return {
            "signal": "SELL",
            "confidence": sell_conf,
            "reason": sell_reason
        }

    # --------------------------------------------------------
    # Conflict
    # --------------------------------------------------------

    if buy and sell:

        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason": "BUY and SELL conditions conflict"
        }

    # --------------------------------------------------------
    # HOLD
    # --------------------------------------------------------

    return {
        "signal": "HOLD",
        "confidence": 0,
        "reason": "No valid Doji Version 1 setup"
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
    print("DOJI VERSION 1")
    print("SNR FIRST TOUCH REVERSAL")
    print("=" * 60)

    try:

        from history import load_history

        # IMPORTANT:
        # येथे symbol/interval/limit देत नाही,
        # त्यामुळे तुमच्या सध्याच्या history.py
        # मध्ये load_history() असेल तरी चालेल.

        df = load_history()

        result = signal(df)

        print()
        print("Signal      :", result["signal"])
        print("Confidence  :", result["confidence"])
        print("Reason      :", result["reason"])
        print()

    except Exception as e:

        print()
        print("Test error:", e)
        print()
        print("history.py मधील load_history() चालत नसल्यास")
        print("main.py मधून strategy वापरा.")