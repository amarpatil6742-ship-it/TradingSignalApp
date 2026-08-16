# ============================================================
# SSYS.PY
# Sure Shot - Double Hammer Strategy
# Version 1.0
# ============================================================

import pandas as pd
import numpy as np


# ------------------------------------------------------------
# SETTINGS
# ------------------------------------------------------------

LOOKBACK = 20

# Abnormal / Big candle filter
BIG_CANDLE_MULTIPLIER = 2.0

# Hammer definition
MIN_WICK_BODY_RATIO = 1.5
MAX_OPPOSITE_WICK_RATIO = 0.8

# SNR distance
SNR_DISTANCE = 0.0015


# ------------------------------------------------------------
# BASIC CANDLE FUNCTIONS
# ------------------------------------------------------------

def candle_color(row):
    if row["Close"] > row["Open"]:
        return "GREEN"
    elif row["Close"] < row["Open"]:
        return "RED"
    return "DOJI"


def candle_parts(row):
    open_price = float(row["Open"])
    high = float(row["High"])
    low = float(row["Low"])
    close = float(row["Close"])

    body = abs(close - open_price)

    upper_wick = high - max(open_price, close)
    lower_wick = min(open_price, close) - low

    total_range = high - low

    return body, upper_wick, lower_wick, total_range


# ------------------------------------------------------------
# HAMMER DETECTION
# ------------------------------------------------------------

def is_hammer(row):

    body, upper_wick, lower_wick, total_range = candle_parts(row)

    if total_range <= 0:
        return False

    # Doji avoid
    if body <= 0:
        return False

    # Lower wick should be bigger
    if lower_wick < body * MIN_WICK_BODY_RATIO:
        return False

    # Upper wick should be relatively small
    if upper_wick > body * MAX_OPPOSITE_WICK_RATIO:
        return False

    return True


# ------------------------------------------------------------
# ABNORMAL CANDLE FILTER
# ------------------------------------------------------------

def is_abnormal_candle(df, index):

    if index < 5:
        return False

    ranges = (
        df["High"].astype(float) -
        df["Low"].astype(float)
    )

    current_range = ranges.iloc[index]

    previous_ranges = ranges.iloc[max(0, index - 5):index]

    if len(previous_ranges) == 0:
        return False

    average_range = previous_ranges.mean()

    if average_range <= 0:
        return False

    return current_range > average_range * BIG_CANDLE_MULTIPLIER


# ------------------------------------------------------------
# DOJI FILTER
# ------------------------------------------------------------

def is_doji(row):

    body, upper_wick, lower_wick, total_range = candle_parts(row)

    if total_range <= 0:
        return True

    return body <= total_range * 0.10


# ------------------------------------------------------------
# SNR DETECTION
# ------------------------------------------------------------

def near_snr(df, index):

    if index < LOOKBACK:
        return False

    current_close = float(df.iloc[index]["Close"])

    previous = df.iloc[
        max(0, index - LOOKBACK):index
    ]

    resistance = float(previous["High"].max())
    support = float(previous["Low"].min())

    # Distance from support/resistance
    support_distance = abs(current_close - support) / current_close
    resistance_distance = abs(current_close - resistance) / current_close

    if support_distance <= SNR_DISTANCE:
        return True

    if resistance_distance <= SNR_DISTANCE:
        return True

    return False


# ------------------------------------------------------------
# RANGING MARKET DETECTION
# ------------------------------------------------------------

def is_ranging_market(df, index):

    if index < LOOKBACK:
        return False

    data = df.iloc[
        index - LOOKBACK:index
    ].copy()

    high = data["High"].astype(float).max()
    low = data["Low"].astype(float).min()

    close = float(data["Close"].iloc[-1])

    if close <= 0:
        return False

    range_percent = (high - low) / close

    # Small range = ranging market
    return range_percent < 0.015


# ------------------------------------------------------------
# RETRACE DETECTION
# ------------------------------------------------------------

def has_retrace(df, index):

    if index < 5:
        return False

    current = df.iloc[index]

    previous = df.iloc[index - 5:index]

    previous_high = previous["High"].astype(float).max()
    previous_low = previous["Low"].astype(float).min()

    close = float(current["Close"])

    # Price returning into previous range
    if previous_low < close < previous_high:
        return True

    return False


# ------------------------------------------------------------
# DOUBLE HAMMER
# ------------------------------------------------------------

def double_hammer(df, index):

    if index < 2:
        return False

    candle1 = df.iloc[index - 2]
    candle2 = df.iloc[index - 1]

    hammer1 = is_hammer(candle1)
    hammer2 = is_hammer(candle2)

    return hammer1 and hammer2


# ------------------------------------------------------------
# DOUBLE HAMMER COLOR
# ------------------------------------------------------------

def hammer_pattern(df, index):

    if not double_hammer(df, index):
        return None

    candle1 = df.iloc[index - 2]
    candle2 = df.iloc[index - 1]

    color1 = candle_color(candle1)
    color2 = candle_color(candle2)

    return color1, color2


# ------------------------------------------------------------
# SIGNAL LOGIC
# ------------------------------------------------------------

def generate_signal(df):

    if df is None:
        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason": "No data"
        }

    if len(df) < LOOKBACK + 3:
        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason": "Not enough candles"
        }

    df = df.copy()

    index = len(df) - 1

    # Last closed candle
    last = df.iloc[index]

    # --------------------------------------------------------
    # PRECAUTIONS
    # --------------------------------------------------------

    # 1. Doji
    if is_doji(last):

        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason": "Doji candle - NO TRADE"
        }

    # 2. Big / abnormal candle
    if is_abnormal_candle(df, index):

        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason": "Abnormal / big candle - NO TRADE"
        }

    # 3. SNR
    if near_snr(df, index):

        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason": "Near SNR level - NO TRADE"
        }

    # 4. Retrace
    if has_retrace(df, index):

        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason": "Retrace detected - NO TRADE"
        }

    # --------------------------------------------------------
    # DOUBLE HAMMER
    # --------------------------------------------------------

    pattern = hammer_pattern(df, index)

    if pattern is None:

        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason": "Double hammer not found"
        }

    first_color, second_color = pattern

    # --------------------------------------------------------
    # SSYS PATTERN
    #
    # Green + Red  -> BUY
    # Red + Green  -> SELL
    #
    # Other combinations are filtered.
    # --------------------------------------------------------

    signal = "HOLD"

    if first_color == "GREEN" and second_color == "RED":
        signal = "BUY"

    elif first_color == "RED" and second_color == "GREEN":
        signal = "SELL"

    else:

        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason": f"Pattern {first_color} + {second_color} not confirmed"
        }

    # --------------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------------

    confidence = 70

    # Strong double hammer
    confidence += 10

    # Valid ranging market
    if is_ranging_market(df, index):
        confidence += 5

    confidence = min(confidence, 95)

    return {
        "signal": signal,
        "confidence": confidence,
        "pattern": f"{first_color} + {second_color}",
        "reason": "SSYS Double Hammer confirmed"
    }


# ------------------------------------------------------------
# SIMPLE FUNCTION FOR MAIN.PY
# ------------------------------------------------------------

def signal(df):

    result = generate_signal(df)

    return result["signal"]


# ------------------------------------------------------------
# FULL RESULT FUNCTION
# ------------------------------------------------------------

def get_signal(df):

    return generate_signal(df)


# ------------------------------------------------------------
# TEST
# ------------------------------------------------------------

if __name__ == "__main__":

    print("=" * 50)
    print("SSYS - SURE SHOT DOUBLE HAMMER")
    print("=" * 50)

    print()
    print("Strategy:")
    print("GREEN + RED  -> BUY")
    print("RED + GREEN  -> SELL")
    print()
    print("Precautions:")
    print("1. Doji       -> NO TRADE")
    print("2. Big candle -> NO TRADE")
    print("3. SNR        -> NO TRADE")
    print("4. Retrace    -> NO TRADE")
    print("=" * 50)