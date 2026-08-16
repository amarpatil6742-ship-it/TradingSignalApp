# ============================================================
# SAMI MALIK SURE SHOT 3
# RANGING MARKET + RETRACING AREA + BLOOD SNR
# ============================================================

import pandas as pd


# ============================================================
# SETTINGS
# ============================================================

MIN_CANDLES = 40

LOOKBACK = 30

SNR_TOLERANCE = 0.0015

RANGE_LOOKBACK = 20

RANGE_MAX_RATIO = 0.035

BIG_CANDLE_MULTIPLIER = 1.8

HAMMER_WICK_RATIO = 2.0

MAX_RETRACE_RATIO = 0.60

MIN_RETRACE_RATIO = 0.15


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(value, default=0.0):

    try:
        return float(value)

    except Exception:
        return default


# ============================================================
# PREPARE DATAFRAME
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
# CANDLE INFO
# ============================================================

def candle_info(row):

    o = safe_float(row["Open"])
    h = safe_float(row["High"])
    l = safe_float(row["Low"])
    c = safe_float(row["Close"])

    candle_range = h - l

    body = abs(c - o)

    upper_wick = h - max(o, c)

    lower_wick = min(o, c) - l

    if candle_range <= 0:

        body_ratio = 1.0

        upper_ratio = 0.0

        lower_ratio = 0.0

    else:

        body_ratio = body / candle_range

        upper_ratio = upper_wick / candle_range

        lower_ratio = lower_wick / candle_range

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
        "range": candle_range,
        "body": body,
        "upper_wick": upper_wick,
        "lower_wick": lower_wick,
        "body_ratio": body_ratio,
        "upper_ratio": upper_ratio,
        "lower_ratio": lower_ratio,
        "colour": colour
    }


# ============================================================
# DOJI
# ============================================================

def is_doji(row):

    info = candle_info(row)

    if info["range"] <= 0:
        return False

    return (
        info["body_ratio"] <= 0.15
    )


# ============================================================
# HAMMER
# ============================================================

def is_hammer(row):

    info = candle_info(row)

    body = info["body"]

    if body <= 0:
        return False

    upper = info["upper_wick"]

    lower = info["lower_wick"]

    # Normal hammer
    if (
        lower >= body * HAMMER_WICK_RATIO
        and upper <= body
    ):
        return True

    # Inverted hammer
    if (
        upper >= body * HAMMER_WICK_RATIO
        and lower <= body
    ):
        return True

    return False


# ============================================================
# AVERAGE CANDLE RANGE
# ============================================================

def average_range(df, index, lookback=10):

    start = max(
        0,
        index - lookback
    )

    values = []

    for i in range(
        start,
        index
    ):

        info = candle_info(
            df.iloc[i]
        )

        if info["range"] > 0:

            values.append(
                info["range"]
            )

    if not values:
        return 0.0

    return sum(values) / len(values)


# ============================================================
# BIG CANDLE
# ============================================================

def is_big_candle(df, index):

    current = candle_info(
        df.iloc[index]
    )

    avg = average_range(
        df,
        index,
        10
    )

    if avg <= 0:
        return False

    return (
        current["range"]
        >= avg * BIG_CANDLE_MULTIPLIER
    )


# ============================================================
# RANGE MARKET DETECTION
# ============================================================

def is_ranging_market(df):

    if len(df) < RANGE_LOOKBACK:
        return False

    recent = df.tail(
        RANGE_LOOKBACK
    )

    high = safe_float(
        recent["High"].max()
    )

    low = safe_float(
        recent["Low"].min()
    )

    close = safe_float(
        recent["Close"].iloc[-1]
    )

    if close <= 0:
        return False

    total_range = high - low

    range_ratio = (
        total_range / close
    )

    # Market must not be strongly expanding
    if range_ratio > RANGE_MAX_RATIO:
        return False

    # Need repeated movement inside range
    highs = recent["High"].tolist()
    lows = recent["Low"].tolist()

    if len(highs) < 5:
        return False

    return True


# ============================================================
# FIND BLOOD SNR
# ============================================================

def find_blood_snr(df):

    if len(df) < 10:
        return None

    recent = df.tail(
        LOOKBACK
    )

    highs = [
        safe_float(x)
        for x in recent["High"]
    ]

    lows = [
        safe_float(x)
        for x in recent["Low"]
    ]

    closes = [
        safe_float(x)
        for x in recent["Close"]
    ]

    if not highs or not lows:
        return None

    resistance = max(highs)

    support = min(lows)

    current = closes[-1]

    # --------------------------------------------------------
    # Select closest meaningful SNR
    # --------------------------------------------------------

    distance_resistance = abs(
        current - resistance
    )

    distance_support = abs(
        current - support
    )

    if distance_resistance < distance_support:

        return {
            "level": resistance,
            "type": "RESISTANCE"
        }

    return {
        "level": support,
        "type": "SUPPORT"
    }


# ============================================================
# PRICE NEAR SNR
# ============================================================

def near_snr(price, level):

    if level == 0:
        return False

    tolerance = (
        abs(level)
        * SNR_TOLERANCE
    )

    return (
        abs(price - level)
        <= tolerance
    )


# ============================================================
# CANDLE TOUCHES SNR
# ============================================================

def candle_touches_snr(
    row,
    level
):

    info = candle_info(row)

    return (
        info["low"] <= level
        <= info["high"]
    )


# ============================================================
# SNR GAP CHECK
# ============================================================

def has_snr_gap(
    row,
    level
):

    info = candle_info(row)

    high = info["high"]

    low = info["low"]

    # If candle range does not reach level,
    # there is a gap from SNR.
    if level > high:

        distance = level - high

    elif level < low:

        distance = low - level

    else:

        distance = 0

    tolerance = (
        abs(level)
        * SNR_TOLERANCE
    )

    return (
        distance > tolerance
    )


# ============================================================
# SNR RESPECT
# ============================================================

def respects_snr(
    row,
    level,
    side
):

    info = candle_info(row)

    close = info["close"]

    high = info["high"]

    low = info["low"]

    # --------------------------------------------------------
    # Resistance
    # --------------------------------------------------------

    if side == "SELL":

        # Candle can touch resistance,
        # but should not close strongly above it.

        if close > level:

            return False

        if high < level:

            return False

        return True

    # --------------------------------------------------------
    # Support
    # --------------------------------------------------------

    if side == "BUY":

        if close < level:

            return False

        if low > level:

            return False

        return True

    return False


# ============================================================
# FIND RETRACING AREA
# ============================================================

def calculate_retrace(
    df,
    index,
    side
):

    if index < 5:
        return None

    start = max(
        0,
        index - 8
    )

    recent = df.iloc[
        start:index + 1
    ]

    if len(recent) < 4:
        return None

    high = safe_float(
        recent["High"].max()
    )

    low = safe_float(
        recent["Low"].min()
    )

    total = high - low

    if total <= 0:
        return None

    current = candle_info(
        df.iloc[index]
    )

    close = current["close"]

    # --------------------------------------------------------
    # BUY retracement
    # --------------------------------------------------------

    if side == "BUY":

        distance_from_low = (
            close - low
        )

        ratio = (
            distance_from_low / total
        )

        return {
            "ratio": ratio,
            "high": high,
            "low": low,
            "range": total
        }

    # --------------------------------------------------------
    # SELL retracement
    # --------------------------------------------------------

    if side == "SELL":

        distance_from_high = (
            high - close
        )

        ratio = (
            distance_from_high / total
        )

        return {
            "ratio": ratio,
            "high": high,
            "low": low,
            "range": total
        }

    return None


# ============================================================
# VALID RETRACING AREA
# ============================================================

def valid_retracing_area(
    df,
    index,
    side
):

    result = calculate_retrace(
        df,
        index,
        side
    )

    if result is None:
        return False

    ratio = result["ratio"]

    # Retracement must not be too small
    if ratio < MIN_RETRACE_RATIO:
        return False

    # Retracement must not be too large
    if ratio > MAX_RETRACE_RATIO:
        return False

    return True


# ============================================================
# PRECAUTION CHECK
# ============================================================

def precautions_ok(
    df,
    index,
    level,
    side
):

    row = df.iloc[index]

    # --------------------------------------------------------
    # 1. SNR gap not allowed
    # --------------------------------------------------------

    if has_snr_gap(
        row,
        level
    ):

        return False, "SNR gap"

    # --------------------------------------------------------
    # 2. Hammer not allowed
    # --------------------------------------------------------

    if is_hammer(row):

        return False, "Hammer"

    # --------------------------------------------------------
    # 3. Big candle not allowed
    # --------------------------------------------------------

    if is_big_candle(
        df,
        index
    ):

        return False, "Big candle"

    # --------------------------------------------------------
    # 4. Doji not allowed
    # --------------------------------------------------------

    if is_doji(row):

        return False, "Doji"

    # --------------------------------------------------------
    # 5. SNR must be respected
    # --------------------------------------------------------

    if not respects_snr(
        row,
        level,
        side
    ):

        return False, "SNR broken"

    # --------------------------------------------------------
    # 6. Retracing area
    # --------------------------------------------------------

    if not valid_retracing_area(
        df,
        index,
        side
    ):

        return False, "Invalid retracing area"

    return True, ""


# ============================================================
# BUY SETUP
# ============================================================

def check_buy(df):

    n = len(df)

    if n < MIN_CANDLES:

        return (
            False,
            0,
            "Not enough candles"
        )

    # Must be ranging
    if not is_ranging_market(df):

        return (
            False,
            0,
            "Market is not ranging"
        )

    snr = find_blood_snr(df)

    if snr is None:

        return (
            False,
            0,
            "No blood SNR"
        )

    level = snr["level"]

    # Search latest candles
    start = max(
        5,
        n - LOOKBACK
    )

    for i in range(
        start,
        n
    ):

        row = df.iloc[i]

        info = candle_info(row)

        # ----------------------------------------------------
        # BUY requires green reaction
        # ----------------------------------------------------

        if info["colour"] != "GREEN":
            continue

        # Candle must touch SNR
        if not candle_touches_snr(
            row,
            level
        ):
            continue

        # ----------------------------------------------------
        # Precautions
        # ----------------------------------------------------

        ok, reason = precautions_ok(
            df,
            i,
            level,
            "BUY"
        )

        if not ok:
            continue

        # ----------------------------------------------------
        # Confirmation candle
        # ----------------------------------------------------

        if i < n - 1:

            next_row = df.iloc[
                i + 1
            ]

            next_info = candle_info(
                next_row
            )

            if next_info["colour"] == "GREEN":

                return (
                    True,
                    82,
                    "Ranging + retracing area + blood SNR + BUY confirmation"
                )

        # If current candle itself is latest closed candle
        if i == n - 1:

            return (
                True,
                78,
                "Ranging + retracing area + blood SNR"
            )

    return (
        False,
        0,
        "No valid BUY setup"
    )


# ============================================================
# SELL SETUP
# ============================================================

def check_sell(df):

    n = len(df)

    if n < MIN_CANDLES:

        return (
            False,
            0,
            "Not enough candles"
        )

    # Must be ranging
    if not is_ranging_market(df):

        return (
            False,
            0,
            "Market is not ranging"
        )

    snr = find_blood_snr(df)

    if snr is None:

        return (
            False,
            0,
            "No blood SNR"
        )

    level = snr["level"]

    start = max(
        5,
        n - LOOKBACK
    )

    for i in range(
        start,
        n
    ):

        row = df.iloc[i]

        info = candle_info(row)

        # ----------------------------------------------------
        # SELL requires red reaction
        # ----------------------------------------------------

        if info["colour"] != "RED":
            continue

        # Candle must touch SNR
        if not candle_touches_snr(
            row,
            level
        ):
            continue

        # ----------------------------------------------------
        # Precautions
        # ----------------------------------------------------

        ok, reason = precautions_ok(
            df,
            i,
            level,
            "SELL"
        )

        if not ok:
            continue

        # ----------------------------------------------------
        # Confirmation candle
        # ----------------------------------------------------

        if i < n - 1:

            next_row = df.iloc[
                i + 1
            ]

            next_info = candle_info(
                next_row
            )

            if next_info["colour"] == "RED":

                return (
                    True,
                    82,
                    "Ranging + retracing area + blood SNR + SELL confirmation"
                )

        if i == n - 1:

            return (
                True,
                78,
                "Ranging + retracing area + blood SNR"
            )

    return (
        False,
        0,
        "No valid SELL setup"
    )


# ============================================================
# MAIN SIGNAL
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
        "reason": "No valid Sami Malik SS3 setup"
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

    print("=" * 65)
    print("SAMI MALIK SURE SHOT 3")
    print("RANGING + RETRACING + BLOOD SNR")
    print("=" * 65)

    try:

        from history import load_history

        df = load_history()

        result = signal(df)

        print()
        print(
            "SIGNAL     :",
            result["signal"]
        )

        print(
            "CONFIDENCE :",
            result["confidence"]
        )

        print(
            "REASON     :",
            result["reason"]
        )

        print()

    except Exception as e:

        print()
        print(
            "Test error:",
            e
        )
        print()