# ============================================================
# ss5.py
# Sure Shot 5 Strategy
# ============================================================

import pandas as pd


# ============================================================
# SETTINGS
# ============================================================

MIN_CANDLES = 30

EMA_FAST = 9
EMA_SLOW = 21

SNR_LOOKBACK = 20

# Small candle body must be <= this fraction
# of previous candle body
SMALL_BODY_RATIO = 0.60

# Big/strong candle body
BIG_BODY_RATIO = 1.20

# SNR breakout tolerance
BREAKOUT_BUFFER = 0.0005


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(value, default=0.0):

    try:
        return float(value)

    except Exception:
        return default


# ============================================================
# PREPARE DATA
# ============================================================

def prepare_dataframe(df):

    if df is None:
        return None

    if not isinstance(df, pd.DataFrame):
        return None

    required = [
        "Open",
        "High",
        "Low",
        "Close"
    ]

    for col in required:

        if col not in df.columns:
            return None

    data = df.copy()

    for col in required:

        data[col] = pd.to_numeric(
            data[col],
            errors="coerce"
        )

    data = data.dropna(
        subset=required
    ).reset_index(drop=True)

    return data


# ============================================================
# CANDLE INFORMATION
# ============================================================

def candle_info(row):

    o = safe_float(row["Open"])
    h = safe_float(row["High"])
    l = safe_float(row["Low"])
    c = safe_float(row["Close"])

    body = abs(c - o)

    candle_range = h - l

    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    if candle_range <= 0:
        body_ratio = 0

    else:
        body_ratio = body / candle_range

    return {
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "body": body,
        "range": candle_range,
        "upper_wick": max(upper_wick, 0),
        "lower_wick": max(lower_wick, 0),
        "body_ratio": body_ratio
    }


# ============================================================
# GREEN / RED CANDLE
# ============================================================

def is_green(row):

    return safe_float(row["Close"]) > safe_float(row["Open"])


def is_red(row):

    return safe_float(row["Close"]) < safe_float(row["Open"])


# ============================================================
# HAMMER
# ============================================================

def is_hammer(row):

    c = candle_info(row)

    body = c["body"]

    if body <= 0:
        return False

    # Classic hammer:
    # lower wick significantly larger than body
    # small upper wick

    return (
        c["lower_wick"] >= body * 2.0
        and
        c["upper_wick"] <= body * 0.50
    )


# ============================================================
# INVERTED HAMMER
# ============================================================

def is_inverted_hammer(row):

    c = candle_info(row)

    body = c["body"]

    if body <= 0:
        return False

    return (
        c["upper_wick"] >= body * 2.0
        and
        c["lower_wick"] <= body * 0.50
    )


# ============================================================
# ABNORMAL / VERY LARGE CANDLE
# ============================================================

def is_abnormal_candle(df, index):

    if index < 5:
        return False

    current = candle_info(
        df.iloc[index]
    )

    current_range = current["range"]

    previous_ranges = []

    start = max(0, index - 10)

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

    avg_range = sum(
        previous_ranges
    ) / len(previous_ranges)

    if avg_range <= 0:
        return False

    return current_range >= avg_range * 2.0


# ============================================================
# STRONG / BIG CANDLE
# ============================================================

def is_big_candle(df, index):

    if index < 1:
        return False

    current = candle_info(
        df.iloc[index]
    )

    previous = candle_info(
        df.iloc[index - 1]
    )

    if previous["body"] <= 0:
        return False

    return (
        current["body"]
        >= previous["body"] * BIG_BODY_RATIO
    )


# ============================================================
# SMALL CANDLE
# ============================================================

def is_small_candle(current, previous):

    c = candle_info(current)
    p = candle_info(previous)

    if p["body"] <= 0:
        return False

    return (
        c["body"]
        <= p["body"] * SMALL_BODY_RATIO
    )


# ============================================================
# INSIDE BODY
# ============================================================

def inside_previous_body(current, previous):

    c = candle_info(current)
    p = candle_info(previous)

    current_high = c["high"]
    current_low = c["low"]

    previous_high_body = max(
        p["open"],
        p["close"]
    )

    previous_low_body = min(
        p["open"],
        p["close"]
    )

    return (
        current_high <= previous_high_body
        and
        current_low >= previous_low_body
    )


# ============================================================
# INSIDE RANGE
# ============================================================

def inside_previous_range(current, previous):

    c = candle_info(current)
    p = candle_info(previous)

    return (
        c["high"] <= p["high"]
        and
        c["low"] >= p["low"]
    )


# ============================================================
# BUY SMALL RED CANDLE
# ============================================================

def buy_setup(previous, current):

    # Previous candle should be green
    if not is_green(previous):
        return False

    # Current candle should be red
    if not is_red(current):
        return False

    # Current candle should be small
    if not is_small_candle(
        current,
        previous
    ):
        return False

    # Current candle inside previous candle
    if not inside_previous_range(
        current,
        previous
    ):
        return False

    return True


# ============================================================
# SELL SMALL GREEN CANDLE
# ============================================================

def sell_setup(previous, current):

    # Previous candle should be red
    if not is_red(previous):
        return False

    # Current candle should be green
    if not is_green(current):
        return False

    # Current candle should be small
    if not is_small_candle(
        current,
        previous
    ):
        return False

    # Current candle inside previous candle
    if not inside_previous_range(
        current,
        previous
    ):
        return False

    return True


# ============================================================
# TREND
# ============================================================

def get_trend(df):

    if len(df) < EMA_SLOW:
        return "UNKNOWN"

    close = pd.to_numeric(
        df["Close"],
        errors="coerce"
    )

    ema_fast = close.ewm(
        span=EMA_FAST,
        adjust=False
    ).mean()

    ema_slow = close.ewm(
        span=EMA_SLOW,
        adjust=False
    ).mean()

    fast = safe_float(
        ema_fast.iloc[-1]
    )

    slow = safe_float(
        ema_slow.iloc[-1]
    )

    previous_fast = safe_float(
        ema_fast.iloc[-2]
    )

    previous_slow = safe_float(
        ema_slow.iloc[-2]
    )

    # Bullish trend
    if (
        fast > slow
        and
        previous_fast >= previous_slow
    ):
        return "UP"

    # Bearish trend
    if (
        fast < slow
        and
        previous_fast <= previous_slow
    ):
        return "DOWN"

    return "RANGE"


# ============================================================
# SUPPORT / RESISTANCE
# ============================================================

def get_snr(df):

    if len(df) < 5:
        return None, None

    lookback = min(
        SNR_LOOKBACK,
        len(df) - 1
    )

    recent = df.iloc[
        -lookback - 1:-1
    ]

    resistance = safe_float(
        recent["High"].max()
    )

    support = safe_float(
        recent["Low"].min()
    )

    return support, resistance


# ============================================================
# BUY BREAKOUT
# ============================================================

def buy_snr_breakout(df):

    if len(df) < 5:
        return False

    support, resistance = get_snr(df)

    if resistance is None:
        return False

    current = candle_info(
        df.iloc[-1]
    )

    previous = candle_info(
        df.iloc[-2]
    )

    buffer = (
        resistance
        * BREAKOUT_BUFFER
    )

    # Current candle closes above resistance
    if current["close"] > resistance + buffer:

        # Previous candle did not already close
        # strongly above resistance
        if previous["close"] <= resistance + buffer:
            return True

    return False


# ============================================================
# SELL BREAKDOWN
# ============================================================

def sell_snr_breakout(df):

    if len(df) < 5:
        return False

    support, resistance = get_snr(df)

    if support is None:
        return False

    current = candle_info(
        df.iloc[-1]
    )

    previous = candle_info(
        df.iloc[-2]
    )

    buffer = (
        support
        * BREAKOUT_BUFFER
    )

    # Current candle closes below support
    if current["close"] < support - buffer:

        # Previous candle did not already close
        # strongly below support
        if previous["close"] >= support - buffer:
            return True

    return False


# ============================================================
# BREAKOUT DIRECTION
# ============================================================

def breakout_direction(df):

    if len(df) < 5:
        return "NONE"

    if buy_snr_breakout(df):
        return "UP"

    if sell_snr_breakout(df):
        return "DOWN"

    return "NONE"


# ============================================================
# PRECAUTIONS
# ============================================================

def precautions_ok(df):

    if len(df) < 3:
        return False

    # Last candle
    last_index = len(df) - 1

    last = df.iloc[last_index]

    # --------------------------------------------------------
    # Hammer
    # --------------------------------------------------------

    if is_hammer(last):
        return False

    # --------------------------------------------------------
    # Inverted hammer
    # --------------------------------------------------------

    if is_inverted_hammer(last):
        return False

    # --------------------------------------------------------
    # Abnormal candle
    # --------------------------------------------------------

    if is_abnormal_candle(
        df,
        last_index
    ):
        return False

    return True


# ============================================================
# CONFIDENCE
# ============================================================

def calculate_confidence(
    direction,
    trend,
    breakout,
    setup,
    df
):

    confidence = 50.0

    # Trend confirmation
    if (
        direction == "BUY"
        and trend == "UP"
    ):
        confidence += 15

    elif (
        direction == "SELL"
        and trend == "DOWN"
    ):
        confidence += 15

    # SNR breakout
    if breakout:
        confidence += 15

    # Inside candle setup
    if setup:
        confidence += 10

    # Last candle is directional
    if len(df) >= 1:

        last = df.iloc[-1]

        if (
            direction == "BUY"
            and is_green(last)
        ):
            confidence += 5

        elif (
            direction == "SELL"
            and is_red(last)
        ):
            confidence += 5

    return min(
        round(confidence, 2),
        100.0
    )


# ============================================================
# MAIN SIGNAL FUNCTION
# ============================================================

def signal(df):

    data = prepare_dataframe(df)

    if data is None:

        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason": "Invalid dataframe"
        }

    # Need enough candles
    if len(data) < MIN_CANDLES:

        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason": (
                f"Need at least "
                f"{MIN_CANDLES} candles"
            )
        }

    # --------------------------------------------------------
    # Precautions
    # --------------------------------------------------------

    if not precautions_ok(data):

        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason": (
                "Precaution failed: "
                "hammer/inverted hammer/"
                "abnormal candle"
            )
        }

    # --------------------------------------------------------
    # Trend
    # --------------------------------------------------------

    trend = get_trend(data)

    # SS5 is a trending-market strategy
    if trend not in ("UP", "DOWN"):

        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason": (
                "Market is not clearly trending"
            )
        }

    # --------------------------------------------------------
    # Previous + current candle
    # --------------------------------------------------------

    previous = data.iloc[-2]
    current = data.iloc[-1]

    # --------------------------------------------------------
    # BUY setup
    # --------------------------------------------------------

    buy_setup_found = buy_setup(
        previous,
        current
    )

    # --------------------------------------------------------
    # SELL setup
    # --------------------------------------------------------

    sell_setup_found = sell_setup(
        previous,
        current
    )

    # --------------------------------------------------------
    # BUY
    # --------------------------------------------------------

    if (
        trend == "UP"
        and
        buy_setup_found
    ):

        confidence = calculate_confidence(
            "BUY",
            trend,
            True,
            True,
            data
        )

        return {
            "signal": "BUY",
            "confidence": confidence,
            "reason": (
                "SS5 BUY: "
                "uptrend + green candle + "
                "small red inside candle + "
                "bullish continuation"
            )
        }

    # --------------------------------------------------------
    # SELL
    # --------------------------------------------------------

    if (
        trend == "DOWN"
        and
        sell_setup_found
    ):

        confidence = calculate_confidence(
            "SELL",
            trend,
            True,
            True,
            data
        )

        return {
            "signal": "SELL",
            "confidence": confidence,
            "reason": (
                "SS5 SELL: "
                "downtrend + red candle + "
                "small green inside candle + "
                "bearish continuation"
            )
        }

    # --------------------------------------------------------
    # HOLD
    # --------------------------------------------------------

    return {
        "signal": "HOLD",
        "confidence": 0,
        "reason": (
            "SS5 pattern not confirmed"
        )
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


# =========================================================