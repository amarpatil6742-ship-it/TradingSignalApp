# ============================================================
# sslorain.py
# Sure Shot Lorain Strategy
# Version 1.0
# ============================================================

import pandas as pd
import numpy as np


# ============================================================
# BASIC CANDLE FUNCTIONS
# ============================================================

def candle_direction(c):
    if c["Close"] > c["Open"]:
        return "GREEN"
    elif c["Close"] < c["Open"]:
        return "RED"
    return "DOJI"


def candle_range(c):
    return float(c["High"] - c["Low"])


def candle_body(c):
    return float(abs(c["Close"] - c["Open"]))


def upper_wick(c):
    return float(c["High"] - max(c["Open"], c["Close"]))


def lower_wick(c):
    return float(min(c["Open"], c["Close"]) - c["Low"])


# ============================================================
# HAMMER DETECTION
# ============================================================

def is_hammer(c):
    r = candle_range(c)

    if r <= 0:
        return False

    body = candle_body(c)
    upper = upper_wick(c)
    lower = lower_wick(c)

    if body <= 0:
        return False

    # Normal hammer:
    # Lower wick मोठी
    # Upper wick छोटी
    return (
        lower >= body * 2.0
        and upper <= body * 0.8
    )


def is_inverted_hammer(c):
    r = candle_range(c)

    if r <= 0:
        return False

    body = candle_body(c)
    upper = upper_wick(c)
    lower = lower_wick(c)

    if body <= 0:
        return False

    return (
        upper >= body * 2.0
        and lower <= body * 0.8
    )


# ============================================================
# ABNORMAL / BIG CANDLE
# ============================================================

def average_range(df, lookback=20):
    if len(df) < 2:
        return 0.0

    ranges = (
        df["High"].astype(float)
        - df["Low"].astype(float)
    )

    return float(
        ranges.tail(lookback).mean()
    )


def is_big_candle(df, index, multiplier=1.8):
    avg = average_range(df)

    if avg <= 0:
        return False

    r = candle_range(df.iloc[index])

    return r >= avg * multiplier


def is_abnormal_candle(df, index):
    avg = average_range(df)

    if avg <= 0:
        return False

    r = candle_range(df.iloc[index])

    # खूप मोठी candle
    if r > avg * 2.5:
        return True

    # zero / invalid candle
    if r <= 0:
        return True

    return False


# ============================================================
# RANGING MARKET
# ============================================================

def is_ranging_market(df, lookback=12):
    if len(df) < lookback:
        return False

    recent = df.tail(lookback)

    high = float(recent["High"].max())
    low = float(recent["Low"].min())

    total_range = high - low

    if total_range <= 0:
        return False

    avg_r = average_range(recent)

    if avg_r <= 0:
        return False

    # Ranging market मध्ये total range
    # खूप मोठा नसावा.
    ratio = total_range / avg_r

    return ratio <= 8.0


# ============================================================
# RETRACING AREA
# ============================================================

def is_retracing_area(df, lookback=8):
    if len(df) < lookback:
        return False

    recent = df.tail(lookback)

    first = recent.iloc[0]
    last = recent.iloc[-1]

    first_direction = candle_direction(first)

    # Recent movement
    green = sum(
        candle_direction(x) == "GREEN"
        for _, x in recent.iterrows()
    )

    red = sum(
        candle_direction(x) == "RED"
        for _, x in recent.iterrows()
    )

    # Pullback / mixed movement
    mixed = green >= 2 and red >= 2

    if mixed:
        return True

    # Price previous range मध्ये परत आला आहे का?
    high = float(recent["High"].max())
    low = float(recent["Low"].min())
    price = float(last["Close"])

    width = high - low

    if width <= 0:
        return False

    position = (price - low) / width

    return 0.25 <= position <= 0.75


# ============================================================
# LONG REJECTION WICK
# ============================================================

def has_long_lower_wick(c):
    body = candle_body(c)
    lower = lower_wick(c)

    if body <= 0:
        return False

    return lower >= body * 1.5


def has_long_upper_wick(c):
    body = candle_body(c)
    upper = upper_wick(c)

    if body <= 0:
        return False

    return upper >= body * 1.5


# ============================================================
# SNR CHECK
# ============================================================

def is_near_snr(price, snr_levels=None, tolerance=0.0015):
    """
    snr_levels example:
    [65000, 65200, 65500]

    जर SNR levels उपलब्ध नसतील तर
    False return होईल.
    """

    if snr_levels is None:
        return False

    if len(snr_levels) == 0:
        return False

    for level in snr_levels:

        level = float(level)

        if level == 0:
            continue

        distance = abs(price - level) / level

        if distance <= tolerance:
            return True

    return False


# ============================================================
# BUYER PATTERN
# ============================================================

def buyer_pattern(df):
    """
    Lorain buyer pattern:

    Candle 1 = rejection / long lower wick
    Candle 2 = GREEN
    Candle 3 = GREEN
    Next = RED candle expected for entry
    """

    if len(df) < 4:
        return False

    c1 = df.iloc[-4]
    c2 = df.iloc[-3]
    c3 = df.iloc[-2]
    c4 = df.iloc[-1]

    d1 = candle_direction(c1)
    d2 = candle_direction(c2)
    d3 = candle_direction(c3)
    d4 = candle_direction(c4)

    # First candle rejection
    rejection = has_long_lower_wick(c1)

    # दोन candles buyer side
    two_green = (
        d2 == "GREEN"
        and d3 == "GREEN"
    )

    # Next candle red
    next_red = d4 == "RED"

    return (
        rejection
        and two_green
        and next_red
    )


# ============================================================
# SELLER PATTERN
# ============================================================

def seller_pattern(df):
    """
    Lorain seller pattern:

    Candle 1 = rejection / long upper wick
    Candle 2 = RED
    Candle 3 = RED
    Next = GREEN candle expected for entry
    """

    if len(df) < 4:
        return False

    c1 = df.iloc[-4]
    c2 = df.iloc[-3]
    c3 = df.iloc[-2]
    c4 = df.iloc[-1]

    d1 = candle_direction(c1)
    d2 = candle_direction(c2)
    d3 = candle_direction(c3)
    d4 = candle_direction(c4)

    rejection = has_long_upper_wick(c1)

    two_red = (
        d2 == "RED"
        and d3 == "RED"
    )

    next_green = d4 == "GREEN"

    return (
        rejection
        and two_red
        and next_green
    )


# ============================================================
# CONFIDENCE CALCULATION
# ============================================================

def calculate_confidence(
    df,
    direction,
    snr_levels=None
):

    if len(df) < 4:
        return 0

    score = 0

    c1 = df.iloc[-4]
    c2 = df.iloc[-3]
    c3 = df.iloc[-2]
    c4 = df.iloc[-1]

    # --------------------------------------------------------
    # 1. Pattern
    # --------------------------------------------------------

    if direction == "BUY":
        if has_long_lower_wick(c1):
            score += 20

        if (
            candle_direction(c2) == "GREEN"
            and candle_direction(c3) == "GREEN"
        ):
            score += 20

        if candle_direction(c4) == "RED":
            score += 10

    elif direction == "SELL":

        if has_long_upper_wick(c1):
            score += 20

        if (
            candle_direction(c2) == "RED"
            and candle_direction(c3) == "RED"
        ):
            score += 20

        if candle_direction(c4) == "GREEN":
            score += 10

    # --------------------------------------------------------
    # 2. Ranging market
    # --------------------------------------------------------

    if is_ranging_market(df):
        score += 15

    # --------------------------------------------------------
    # 3. Retracing area
    # --------------------------------------------------------

    if is_retracing_area(df):
        score += 15

    # --------------------------------------------------------
    # 4. Last candle precautions
    # --------------------------------------------------------

    if not is_hammer(c4):
        score += 5

    if not is_inverted_hammer(c4):
        score += 5

    if not is_abnormal_candle(df, -1):
        score += 5

    # --------------------------------------------------------
    # 5. SNR
    # --------------------------------------------------------

    price = float(c4["Close"])

    if not is_near_snr(
        price,
        snr_levels
    ):
        score += 5

    return min(score, 100)


# ============================================================
# MAIN STRATEGY FUNCTION
# ============================================================

def analyze_sslorain(
    df,
    snr_levels=None
):
    """
    Return:

    {
        "signal": "BUY / SELL / HOLD",
        "confidence": 0-100,
        "strategy": "SS LORAIN",
        "reason": "...",
        "market": "RANGING / OTHER"
    }
    """

    required = [
        "Open",
        "High",
        "Low",
        "Close"
    ]

    if df is None:
        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SS LORAIN",
            "reason": "DataFrame is None",
            "market": "UNKNOWN"
        }

    if len(df) < 20:
        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SS LORAIN",
            "reason": "Minimum 20 candles required",
            "market": "UNKNOWN"
        }

    for col in required:
        if col not in df.columns:
            return {
                "signal": "HOLD",
                "confidence": 0,
                "strategy": "SS LORAIN",
                "reason": f"Missing column: {col}",
                "market": "UNKNOWN"
            }

    data = df.copy()

    for col in required:
        data[col] = pd.to_numeric(
            data[col],
            errors="coerce"
        )

    data = data.dropna(
        subset=required
    ).reset_index(drop=True)

    if len(data) < 20:
        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SS LORAIN",
            "reason": "Not enough valid candles",
            "market": "UNKNOWN"
        }

    # ========================================================
    # MARKET CONDITION
    # ========================================================

    ranging = is_ranging_market(data)

    market = (
        "RANGING"
        if ranging
        else "TRENDING/OTHER"
    )

    # Strategy requirement
    if not ranging:
        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SS LORAIN",
            "reason": "Ranging market not detected",
            "market": market
        }

    # ========================================================
    # RETRACING
    # ========================================================

    retracing = is_retracing_area(data)

    if not retracing:
        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SS LORAIN",
            "reason": "Retracing area not detected",
            "market": market
        }

    # ========================================================
    # LAST CANDLE
    # ========================================================

    last = data.iloc[-1]

    # Precaution:
    # Hammer / inverted hammer not allowed
    if is_hammer(last):
        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SS LORAIN",
            "reason": "Last candle is hammer",
            "market": market
        }

    if is_inverted_hammer(last):
        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SS LORAIN",
            "reason": "Last candle is inverted hammer",
            "market": market
        }

    # Big candle not allowed
    if is_big_candle(
        data,
        -1,
        multiplier=1.8
    ):
        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SS LORAIN",
            "reason": "Last candle is too big",
            "market": market
        }

    # Abnormal candle
    if is_abnormal_candle(data, -1):
        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SS LORAIN",
            "reason": "Abnormal candle detected",
            "market": market
        }

    # ========================================================
    # SNR FILTER
    # ========================================================

    price = float(last["Close"])

    if is_near_snr(
        price,
        snr_levels
    ):
        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SS LORAIN",
            "reason": "SNR area detected - signal rejected",
            "market": market
        }

    # ========================================================
    # BUY
    # ========================================================

    buy = buyer_pattern(data)

    # ========================================================
    # SELL
    # ========================================================

    sell = seller_pattern(data)

    # ========================================================
    # RESULT
    # ========================================================

    if buy and not sell:

        confidence = calculate_confidence(
            data,
            "BUY",
            snr_levels
        )

        return {
            "signal": "BUY",
            "confidence": confidence,
            "strategy": "SS LORAIN",
            "reason": (
                "Ranging + retracing + "
                "lower-wick rejection + "
                "buyer pattern"
            ),
            "market": market
        }

    if sell and not buy:

        confidence = calculate_confidence(
            data,
            "SELL",
            snr_levels
        )

        return {
            "signal": "SELL",
            "confidence": confidence,
            "strategy": "SS LORAIN",
            "reason": (
                "Ranging + retracing + "
                "upper-wick rejection + "
                "seller pattern"
            ),
            "market": market
        }

    # ========================================================
    # NO SIGNAL
    # ========================================================

    return {
        "signal": "HOLD",
        "confidence": 0,
        "strategy": "SS LORAIN",
        "reason": "SS Lorain pattern not confirmed",
        "market": market
    }


# ============================================================
# SHORT ALIAS
# ============================================================

def signal(df, snr_levels=None):
    """
    Main.py मधून वापरण्यासाठी.
    """

    result = analyze_sslorain(
        df,
        snr_levels
    )

    return result


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("----------------------------------")
    print("SS LORAIN STRATEGY")
    print("----------------------------------")

    print()
    print("Use:")
    print("result = analyze_sslorain(df)")
    print()
    print("Result format:")
    print("{")
    print('  "signal": "BUY/SELL/HOLD",')
    print('  "confidence": 0-100,')
    print('  "strategy": "SS LORAIN",')
    print('  "reason": "...",')
    print('  "market": "RANGING"')
    print("}")