# ============================================================
# ss4.py
# SURE SHOT 4
# SNR BREAKOUT + ABNORMAL CANDLE STRATEGY
# ============================================================

import pandas as pd
import numpy as np


# ============================================================
# SETTINGS
# ============================================================

MIN_CANDLES = 30

ATR_PERIOD = 14

SNR_LOOKBACK = 20

AVERAGE_BODY_PERIOD = 10

BIG_CANDLE_MULTIPLIER = 1.5

SNR_TOLERANCE = 0.002

MAX_WICK_RATIO = 0.60

MIN_BODY_RATIO = 0.35


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(value, default=0.0):

    try:
        value = float(value)

        if np.isnan(value):
            return default

        return value

    except Exception:

        return default


# ============================================================
# PREPARE DATA
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
# CANDLE CALCULATIONS
# ============================================================

def candle_values(row):

    open_price = safe_float(row["Open"])
    high_price = safe_float(row["High"])
    low_price = safe_float(row["Low"])
    close_price = safe_float(row["Close"])

    total_range = high_price - low_price

    body = abs(close_price - open_price)

    upper_wick = high_price - max(
        open_price,
        close_price
    )

    lower_wick = min(
        open_price,
        close_price
    ) - low_price

    return (
        open_price,
        high_price,
        low_price,
        close_price,
        total_range,
        body,
        upper_wick,
        lower_wick
    )


# ============================================================
# CANDLE COLOR
# ============================================================

def candle_color(row):

    open_price = safe_float(row["Open"])
    close_price = safe_float(row["Close"])

    if close_price > open_price:
        return "GREEN"

    if close_price < open_price:
        return "RED"

    return "DOJI"


# ============================================================
# ATR
# ============================================================

def calculate_atr(df, period=ATR_PERIOD):

    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    previous_close = close.shift(1)

    tr1 = high - low

    tr2 = abs(
        high - previous_close
    )

    tr3 = abs(
        low - previous_close
    )

    true_range = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    atr = true_range.rolling(
        period
    ).mean()

    return atr


# ============================================================
# BIG / ABNORMAL CANDLE
# ============================================================

def is_abnormal_candle(df, index):

    if index < AVERAGE_BODY_PERIOD:
        return False

    row = df.iloc[index]

    _, _, _, _, candle_range, body, _, _ = candle_values(
        row
    )

    previous_bodies = []

    start = max(
        0,
        index - AVERAGE_BODY_PERIOD
    )

    for i in range(start, index):

        r = df.iloc[i]

        o = safe_float(r["Open"])
        c = safe_float(r["Close"])

        previous_bodies.append(
            abs(c - o)
        )

    if not previous_bodies:
        return False

    average_body = np.mean(
        previous_bodies
    )

    if average_body <= 0:
        return False

    # Big body
    big_body = (
        body >=
        average_body *
        BIG_CANDLE_MULTIPLIER
    )

    # Also check range
    average_range = []

    for i in range(start, index):

        r = df.iloc[i]

        h = safe_float(r["High"])
        l = safe_float(r["Low"])

        average_range.append(
            h - l
        )

    avg_range = np.mean(
        average_range
    ) if average_range else 0

    big_range = (
        avg_range > 0 and
        candle_range >=
        avg_range * 1.3
    )

    return (
        big_body or
        big_range
    )


# ============================================================
# HAMMER CHECK
# ============================================================

def is_hammer(row):

    (
        open_price,
        high_price,
        low_price,
        close_price,
        candle_range,
        body,
        upper_wick,
        lower_wick
    ) = candle_values(row)

    if candle_range <= 0:
        return False

    body_ratio = (
        body / candle_range
    )

    upper_ratio = (
        upper_wick /
        candle_range
    )

    lower_ratio = (
        lower_wick /
        candle_range
    )

    # Small body + long lower wick
    bullish_hammer = (
        body_ratio <= 0.35 and
        lower_ratio >= 0.55 and
        lower_wick >= body * 2
    )

    # Small body + long upper wick
    bearish_hammer = (
        body_ratio <= 0.35 and
        upper_ratio >= 0.55 and
        upper_wick >= body * 2
    )

    return (
        bullish_hammer or
        bearish_hammer
    )


# ============================================================
# WICK CHECK
# ============================================================

def has_abnormal_wick(row):

    (
        open_price,
        high_price,
        low_price,
        close_price,
        candle_range,
        body,
        upper_wick,
        lower_wick
    ) = candle_values(row)

    if candle_range <= 0:
        return True

    upper_ratio = (
        upper_wick /
        candle_range
    )

    lower_ratio = (
        lower_wick /
        candle_range
    )

    return (
        upper_ratio > MAX_WICK_RATIO or
        lower_ratio > MAX_WICK_RATIO
    )


# ============================================================
# SUPPORT / RESISTANCE
# ============================================================

def get_snr(df, index):

    start = max(
        0,
        index - SNR_LOOKBACK
    )

    previous = df.iloc[
        start:index
    ]

    if len(previous) < 5:
        return None, None

    resistance = safe_float(
        previous["High"].max()
    )

    support = safe_float(
        previous["Low"].min()
    )

    return support, resistance


# ============================================================
# SNR TOUCH
# ============================================================

def near_level(price, level):

    if level is None:
        return False

    if level == 0:
        return False

    difference = abs(
        price - level
    )

    return (
        difference /
        abs(level)
        <= SNR_TOLERANCE
    )


# ============================================================
# BUY BREAKOUT
# ============================================================

def bullish_breakout(
    previous,
    current,
    resistance
):

    if resistance is None:
        return False

    previous_close = safe_float(
        previous["Close"]
    )

    current_close = safe_float(
        current["Close"]
    )

    current_open = safe_float(
        current["Open"]
    )

    # Previous candle was at/below resistance
    was_below = (
        previous_close <=
        resistance
    )

    # Current candle crosses resistance
    crossed = (
        current_close >
        resistance
    )

    green = (
        current_close >
        current_open
    )

    return (
        was_below and
        crossed and
        green
    )


# ============================================================
# BEARISH BREAKDOWN
# ============================================================

def bearish_breakdown(
    previous,
    current,
    support
):

    if support is None:
        return False

    previous_close = safe_float(
        previous["Close"]
    )

    current_close = safe_float(
        current["Close"]
    )

    current_open = safe_float(
        current["Open"]
    )

    # Previous candle was at/above support
    was_above = (
        previous_close >=
        support
    )

    # Current candle crosses support
    crossed = (
        current_close <
        support
    )

    red = (
        current_close <
        current_open
    )

    return (
        was_above and
        crossed and
        red
    )


# ============================================================
# STRONG BULLISH CANDLE
# ============================================================

def strong_bullish_candle(row):

    (
        open_price,
        high_price,
        low_price,
        close_price,
        candle_range,
        body,
        upper_wick,
        lower_wick
    ) = candle_values(row)

    if candle_range <= 0:
        return False

    body_ratio = (
        body /
        candle_range
    )

    return (
        close_price > open_price and
        body_ratio >= MIN_BODY_RATIO and
        upper_wick <
        candle_range * MAX_WICK_RATIO
    )


# ============================================================
# STRONG BEARISH CANDLE
# ============================================================

def strong_bearish_candle(row):

    (
        open_price,
        high_price,
        low_price,
        close_price,
        candle_range,
        body,
        upper_wick,
        lower_wick
    ) = candle_values(row)

    if candle_range <= 0:
        return False

    body_ratio = (
        body /
        candle_range
    )

    return (
        close_price < open_price and
        body_ratio >= MIN_BODY_RATIO and
        lower_wick <
        candle_range * MAX_WICK_RATIO
    )


# ============================================================
# TREND CHECK
# ============================================================

def trend_direction(df, index):

    if index < 10:
        return "NONE"

    closes = df["Close"]

    recent = closes.iloc[
        max(0, index - 5):index
    ]

    if len(recent) < 3:
        return "NONE"

    first = safe_float(
        recent.iloc[0]
    )

    last = safe_float(
        recent.iloc[-1]
    )

    if last > first:
        return "UP"

    if last < first:
        return "DOWN"

    return "NONE"


# ============================================================
# SIGNAL
# ============================================================

def signal(df):

    df = prepare_dataframe(df)

    if len(df) < MIN_CANDLES:

        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason":
                "SS4: Not enough candles"
        }

    # --------------------------------------------------------
    # IMPORTANT:
    # Use last CLOSED candle as pattern candle.
    # --------------------------------------------------------

    current_index = len(df) - 1

    previous_index = len(df) - 2

    current = df.iloc[
        current_index
    ]

    previous = df.iloc[
        previous_index
    ]

    # --------------------------------------------------------
    # Candle safety
    # --------------------------------------------------------

    if is_hammer(current):

        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason":
                "SS4: Hammer candle - avoid"
        }

    if has_abnormal_wick(current):

        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason":
                "SS4: Abnormal/large wick - avoid"
        }

    # --------------------------------------------------------
    # SNR
    # --------------------------------------------------------

    support, resistance = get_snr(
        df,
        current_index
    )

    # --------------------------------------------------------
    # Big / abnormal candle
    # --------------------------------------------------------

    abnormal = is_abnormal_candle(
        df,
        current_index
    )

    # --------------------------------------------------------
    # Candle direction
    # --------------------------------------------------------

    current_color = candle_color(
        current
    )

    previous_color = candle_color(
        previous
    )

    # ========================================================
    # BUY SETUP
    # ========================================================

    buy_breakout = bullish_breakout(
        previous,
        current,
        resistance
    )

    buy_strong = strong_bullish_candle(
        current
    )

    # ========================================================
    # SELL SETUP
    # ========================================================

    sell_breakdown = bearish_breakdown(
        previous,
        current,
        support
    )

    sell_strong = strong_bearish_candle(
        current
    )

    # ========================================================
    # TREND
    # ========================================================

    trend = trend_direction(
        df,
        current_index
    )

    # ========================================================
    # BUY SCORE
    # ========================================================

    buy_score = 0
    buy_reasons = []

    if buy_breakout:

        buy_score += 45

        buy_reasons.append(
            "SNR resistance breakout"
        )

    if buy_strong:

        buy_score += 20

        buy_reasons.append(
            "Strong green candle"
        )

    if abnormal:

        buy_score += 20

        buy_reasons.append(
            "Abnormal/big candle"
        )

    if trend == "UP":

        buy_score += 10

        buy_reasons.append(
            "Uptrend"
        )

    if current_color == "GREEN":

        buy_score += 5


    # ========================================================
    # SELL SCORE
    # ========================================================

    sell_score = 0
    sell_reasons = []

    if sell_breakdown:

        sell_score += 45

        sell_reasons.append(
            "SNR support breakdown"
        )

    if sell_strong:

        sell_score += 20

        sell_reasons.append(
            "Strong red candle"
        )

    if abnormal:

        sell_score += 20

        sell_reasons.append(
            "Abnormal/big candle"
        )

    if trend == "DOWN":

        sell_score += 10

        sell_reasons.append(
            "Downtrend"
        )

    if current_color == "RED":

        sell_score += 5


    # ========================================================
    # FINAL BUY
    # ========================================================

    if (
        buy_breakout and
        buy_strong
    ):

        confidence = min(
            buy_score,
            100
        )

        reason = (
            "SS4 BUY: " +
            ", ".join(
                buy_reasons
            )
        )

        return {
            "signal": "BUY",
            "confidence": round(
                confidence,
                2
            ),
            "reason": reason
        }


    # ========================================================
    # FINAL SELL
    # ========================================================

    if (
        sell_breakdown and
        sell_strong
    ):

        confidence = min(
            sell_score,
            100
        )

        reason = (
            "SS4 SELL: " +
            ", ".join(
                sell_reasons
            )
        )

        return {
            "signal": "SELL",
            "confidence": round(
                confidence,
                2
            ),
            "reason": reason
        }


    # ========================================================
    # NO CONFIRMED SIGNAL
    # ========================================================

    return {
        "signal": "HOLD",
        "confidence": 0,
        "reason":
            "SS4: No confirmed SNR breakout/breakdown"
    }


# ============================================================
# ALTERNATIVE FUNCTION
# ============================================================

def generate_signal(df):

    return signal(df)


# ============================================================
# ALTERNATIVE FUNCTION
# ============================================================

def get_signal(df):

    return signal(df)


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print(
        "SS4 strategy module loaded successfully."
    )

    print(
        "Use signal(df) to generate signal."
    )