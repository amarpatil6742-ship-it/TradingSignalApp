# ============================================================
# ssmutabin.py
# Sure Shot Mutabin Muhammad
# Candlestick + Ranging Market + SNR Strategy
# ============================================================

import pandas as pd
import numpy as np


# ------------------------------------------------------------
# Basic candle functions
# ------------------------------------------------------------

def candle_color(candle):
    """Return GREEN, RED or DOJI."""

    if candle["Close"] > candle["Open"]:
        return "GREEN"

    elif candle["Close"] < candle["Open"]:
        return "RED"

    return "DOJI"


def candle_body(candle):
    return abs(candle["Close"] - candle["Open"])


def candle_range(candle):
    return candle["High"] - candle["Low"]


def upper_wick(candle):
    return candle["High"] - max(candle["Open"], candle["Close"])


def lower_wick(candle):
    return min(candle["Open"], candle["Close"]) - candle["Low"]


# ------------------------------------------------------------
# Hammer detection
# ------------------------------------------------------------

def is_hammer(candle):

    body = candle_body(candle)
    total = candle_range(candle)

    if total <= 0:
        return False

    upper = upper_wick(candle)
    lower = lower_wick(candle)

    # Very small body
    if body <= total * 0.30:

        # Normal hammer type
        if lower >= body * 2 and upper <= body:
            return True

        # Inverted hammer type
        if upper >= body * 2 and lower <= body:
            return True

    return False


# ------------------------------------------------------------
# Abnormal / Big candle detection
# ------------------------------------------------------------

def is_big_candle(df, index, lookback=10, multiplier=1.8):

    if index < lookback:
        return False

    current_range = candle_range(df.iloc[index])

    previous_ranges = []

    for i in range(index - lookback, index):
        r = candle_range(df.iloc[i])

        if r > 0:
            previous_ranges.append(r)

    if len(previous_ranges) == 0:
        return False

    average_range = np.mean(previous_ranges)

    return current_range > average_range * multiplier


# ------------------------------------------------------------
# Doji detection
# ------------------------------------------------------------

def is_doji(candle, threshold=0.20):

    total = candle_range(candle)

    if total <= 0:
        return True

    body = candle_body(candle)

    return body <= total * threshold


# ------------------------------------------------------------
# Ranging market detection
# ------------------------------------------------------------

def is_ranging_market(
    df,
    lookback=20,
    max_range_ratio=0.035
):
    """
    Simple ranging-market detection.

    Market is considered ranging when the total movement
    of recent candles is relatively small.
    """

    if len(df) < lookback:
        return False

    recent = df.iloc[-lookback:]

    highest = recent["High"].max()
    lowest = recent["Low"].min()

    if lowest <= 0:
        return False

    total_range = highest - lowest

    ratio = total_range / lowest

    return ratio <= max_range_ratio


# ------------------------------------------------------------
# Find support and resistance
# ------------------------------------------------------------

def calculate_snr(df, lookback=20):

    if len(df) < lookback:
        return None, None

    recent = df.iloc[-lookback:]

    support = recent["Low"].min()
    resistance = recent["High"].max()

    return support, resistance


# ------------------------------------------------------------
# SNR proximity
# ------------------------------------------------------------

def near_support(price, support, tolerance):

    return abs(price - support) <= tolerance


def near_resistance(price, resistance, tolerance):

    return abs(price - resistance) <= tolerance


# ------------------------------------------------------------
# BUY pattern
# ------------------------------------------------------------

def buy_pattern(df):

    if len(df) < 6:
        return False

    i = len(df) - 1

    c1 = df.iloc[i - 3]
    c2 = df.iloc[i - 2]
    c3 = df.iloc[i - 1]
    c4 = df.iloc[i]

    # --------------------------------------------------------
    # Previous candles should show some bullish activity
    # --------------------------------------------------------

    green_count = 0

    for c in [c1, c2]:
        if candle_color(c) == "GREEN":
            green_count += 1

    if green_count < 1:
        return False

    # --------------------------------------------------------
    # Sudden RED candle
    # --------------------------------------------------------

    if candle_color(c3) != "RED":
        return False

    # Red candle should be reasonably strong
    if candle_body(c3) <= 0:
        return False

    # --------------------------------------------------------
    # Confirmation GREEN candle
    # --------------------------------------------------------

    if candle_color(c4) != "GREEN":
        return False

    # Green candle must cross red candle body
    red_body_top = max(c3["Open"], c3["Close"])

    if c4["Close"] <= red_body_top:
        return False

    # --------------------------------------------------------
    # Hammer protection
    # --------------------------------------------------------

    if is_hammer(c3) or is_hammer(c4):
        return False

    # --------------------------------------------------------
    # Abnormal candle protection
    # --------------------------------------------------------

    if is_big_candle(df, i - 1):
        return False

    if is_big_candle(df, i):
        return False

    return True


# ------------------------------------------------------------
# SELL pattern
# ------------------------------------------------------------

def sell_pattern(df):

    if len(df) < 6:
        return False

    i = len(df) - 1

    c1 = df.iloc[i - 3]
    c2 = df.iloc[i - 2]
    c3 = df.iloc[i - 1]
    c4 = df.iloc[i]

    # --------------------------------------------------------
    # Previous candles should show bearish activity
    # --------------------------------------------------------

    red_count = 0

    for c in [c1, c2]:
        if candle_color(c) == "RED":
            red_count += 1

    if red_count < 1:
        return False

    # --------------------------------------------------------
    # Sudden GREEN candle
    # --------------------------------------------------------

    if candle_color(c3) != "GREEN":
        return False

    if candle_body(c3) <= 0:
        return False

    # --------------------------------------------------------
    # Confirmation RED candle
    # --------------------------------------------------------

    if candle_color(c4) != "RED":
        return False

    green_body_bottom = min(c3["Open"], c3["Close"])

    if c4["Close"] >= green_body_bottom:
        return False

    # --------------------------------------------------------
    # Hammer protection
    # --------------------------------------------------------

    if is_hammer(c3) or is_hammer(c4):
        return False

    # --------------------------------------------------------
    # Abnormal candle protection
    # --------------------------------------------------------

    if is_big_candle(df, i - 1):
        return False

    if is_big_candle(df, i):
        return False

    return True


# ------------------------------------------------------------
# Main Strategy
# ------------------------------------------------------------

def signal(
    df,
    snr_tolerance_percent=0.003,
    ranging_lookback=20
):
    """
    Returns:

        BUY
        SELL
        HOLD
    """

    # --------------------------------------------------------
    # Data validation
    # --------------------------------------------------------

    required_columns = [
        "Open",
        "High",
        "Low",
        "Close"
    ]

    for column in required_columns:

        if column not in df.columns:
            raise ValueError(
                f"Missing column: {column}"
            )

    if len(df) < 25:
        return "HOLD"

    # --------------------------------------------------------
    # Convert numeric columns
    # --------------------------------------------------------

    data = df.copy()

    for column in required_columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce"
        )

    data = data.dropna(
        subset=required_columns
    ).reset_index(drop=True)

    if len(data) < 25:
        return "HOLD"

    # --------------------------------------------------------
    # Ranging market requirement
    # --------------------------------------------------------

    if not is_ranging_market(
        data,
        lookback=ranging_lookback
    ):
        return "HOLD"

    # --------------------------------------------------------
    # SNR calculation
    # --------------------------------------------------------

    support, resistance = calculate_snr(
        data,
        lookback=ranging_lookback
    )

    if support is None or resistance is None:
        return "HOLD"

    current = data.iloc[-1]

    price = float(current["Close"])

    tolerance = price * snr_tolerance_percent

    # --------------------------------------------------------
    # BUY / SELL pattern
    # --------------------------------------------------------

    buy = buy_pattern(data)
    sell = sell_pattern(data)

    # --------------------------------------------------------
    # BUY only near SUPPORT
    # --------------------------------------------------------

    if buy:

        if near_support(
            price,
            support,
            tolerance
        ):
            return "BUY"

    # --------------------------------------------------------
    # SELL only near RESISTANCE
    # --------------------------------------------------------

    if sell:

        if near_resistance(
            price,
            resistance,
            tolerance
        ):
            return "SELL"

    return "HOLD"


# ------------------------------------------------------------
# Detailed signal
# ------------------------------------------------------------

def get_signal_details(df):

    result = {
        "signal": "HOLD",
        "market": "UNKNOWN",
        "support": None,
        "resistance": None,
        "reason": ""
    }

    if len(df) < 25:
        result["reason"] = "Not enough candles"
        return result

    try:

        data = df.copy()

        required_columns = [
            "Open",
            "High",
            "Low",
            "Close"
        ]

        for column in required_columns:
            data[column] = pd.to_numeric(
                data[column],
                errors="coerce"
            )

        data = data.dropna(
            subset=required_columns
        ).reset_index(drop=True)

        support, resistance = calculate_snr(
            data,
            lookback=20
        )

        result["support"] = support
        result["resistance"] = resistance

        # Market condition
        if is_ranging_market(data):
            result["market"] = "RANGING"
        else:
            result["market"] = "TRENDING"

        if result["market"] != "RANGING":
            result["reason"] = (
                "Ranging market requirement failed"
            )
            return result

        # Check patterns
        buy = buy_pattern(data)
        sell = sell_pattern(data)

        price = float(data.iloc[-1]["Close"])

        tolerance = price * 0.003

        if buy and near_support(
            price,
            support,
            tolerance
        ):

            result["signal"] = "BUY"

            result["reason"] = (
                "BUY pattern + ranging market + "
                "support/SNR confirmation"
            )

            return result

        if sell and near_resistance(
            price,
            resistance,
            tolerance
        ):

            result["signal"] = "SELL"

            result["reason"] = (
                "SELL pattern + ranging market + "
                "resistance/SNR confirmation"
            )

            return result

        result["reason"] = (
            "Pattern/SNR confirmation not complete"
        )

        return result

    except Exception as e:

        result["reason"] = str(e)

        return result


# ------------------------------------------------------------
# Test function
# ------------------------------------------------------------

def test_strategy(df):

    print("=" * 50)
    print("SS MUTABIN MUHAMMAD")
    print("=" * 50)

    details = get_signal_details(df)

    print("Market     :", details["market"])
    print("Support    :", details["support"])
    print("Resistance :", details["resistance"])
    print("Signal     :", details["signal"])
    print("Reason     :", details["reason"])

    print("=" * 50)

    return details["signal"]


# ------------------------------------------------------------
# Standalone test
# ------------------------------------------------------------

if __name__ == "__main__":

    print("ssmutabin.py loaded successfully.")

    print(
        "Use: signal(df)"
    )