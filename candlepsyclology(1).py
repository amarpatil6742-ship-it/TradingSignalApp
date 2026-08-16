# ============================================================
# candle_psychology.py
# Candles Psychology of Big Candles
# ============================================================

import pandas as pd


# ------------------------------------------------------------
# BASIC CANDLE FUNCTIONS
# ------------------------------------------------------------

def candle_color(candle):
    """Return GREEN / RED / DOJI"""

    if candle["Close"] > candle["Open"]:
        return "GREEN"

    elif candle["Close"] < candle["Open"]:
        return "RED"

    return "DOJI"


def candle_body(candle):
    """Candle body"""

    return abs(
        float(candle["Close"]) - float(candle["Open"])
    )


def candle_range(candle):
    """Full candle range"""

    return float(candle["High"]) - float(candle["Low"])


def body_ratio(candle):
    """
    Body / Total Range

    Example:
    0.70 = 70% body
    """

    rng = candle_range(candle)

    if rng <= 0:
        return 0

    return candle_body(candle) / rng


def is_big_candle(candle, minimum_body_ratio=0.60):
    """
    Big candle condition.

    Default:
    Body >= 60% of total candle range
    """

    return body_ratio(candle) >= minimum_body_ratio


# ------------------------------------------------------------
# SNR DISTANCE
# ------------------------------------------------------------

def near_snr(price, snr, tolerance=0.001):
    """
    Check whether price is close to SNR.

    tolerance = 0.001 means approximately 0.1%
    """

    if snr is None:
        return False

    price = float(price)
    snr = float(snr)

    if snr == 0:
        return False

    distance = abs(price - snr) / abs(snr)

    return distance <= tolerance


# ------------------------------------------------------------
# BUYER EXHAUSTION
# ------------------------------------------------------------

def buyer_exhaustion(df, snr):
    """
    BUYER EXHAUSTION

    Logic from notebook:

    1. Big GREEN candle
    2. Candle is around SNR
    3. Closing point comes back/rejects from SNR
    4. Next RED candle confirms reversal

    Signal:
        SELL
    """

    if len(df) < 2:
        return False

    previous = df.iloc[-2]
    current = df.iloc[-1]

    previous_color = candle_color(previous)
    current_color = candle_color(current)

    # Previous candle must be big green
    if previous_color != "GREEN":
        return False

    if not is_big_candle(previous):
        return False

    # Previous candle should interact with SNR
    if not near_snr(previous["High"], snr):
        return False

    # Current candle should be RED
    if current_color != "RED":
        return False

    # Current candle confirms reversal
    if current["Close"] >= previous["Close"]:
        return False

    return True


# ------------------------------------------------------------
# BUYER POWER
# ------------------------------------------------------------

def buyer_power(df, snr):
    """
    POWER OF BUYERS

    Logic from notebook:

    1. Big GREEN candle
    2. Candle crosses SNR
    3. Closing point stays above SNR
    4. Next GREEN candle confirms continuation

    Signal:
        BUY
    """

    if len(df) < 2:
        return False

    previous = df.iloc[-2]
    current = df.iloc[-1]

    previous_color = candle_color(previous)
    current_color = candle_color(current)

    # Previous must be big GREEN candle
    if previous_color != "GREEN":
        return False

    if not is_big_candle(previous):
        return False

    # Previous candle must cross SNR
    if previous["Open"] >= snr:
        return False

    if previous["Close"] <= snr:
        return False

    # Next candle must be GREEN
    if current_color != "GREEN":
        return False

    # Current candle should continue above SNR
    if current["Close"] <= snr:
        return False

    return True


# ------------------------------------------------------------
# SELLER EXHAUSTION
# ------------------------------------------------------------

def seller_exhaustion(df, snr):
    """
    SELLER EXHAUSTION

    Opposite of buyer exhaustion.

    Big RED candle near SNR
    +
    next GREEN candle
    =
    BUY
    """

    if len(df) < 2:
        return False

    previous = df.iloc[-2]
    current = df.iloc[-1]

    previous_color = candle_color(previous)
    current_color = candle_color(current)

    # Previous must be big RED
    if previous_color != "RED":
        return False

    if not is_big_candle(previous):
        return False

    # Previous candle touches SNR
    if not near_snr(previous["Low"], snr):
        return False

    # Next candle GREEN
    if current_color != "GREEN":
        return False

    # Reversal confirmation
    if current["Close"] <= previous["Close"]:
        return False

    return True


# ------------------------------------------------------------
# SELLER POWER
# ------------------------------------------------------------

def seller_power(df, snr):
    """
    POWER OF SELLERS

    Big RED candle crosses SNR
    +
    next RED candle continues
    =
    SELL
    """

    if len(df) < 2:
        return False

    previous = df.iloc[-2]
    current = df.iloc[-1]

    previous_color = candle_color(previous)
    current_color = candle_color(current)

    # Previous must be big RED
    if previous_color != "RED":
        return False

    if not is_big_candle(previous):
        return False

    # Previous candle crosses SNR downward
    if previous["Open"] <= snr:
        return False

    if previous["Close"] >= snr:
        return False

    # Next candle RED
    if current_color != "RED":
        return False

    # Continue below SNR
    if current["Close"] >= snr:
        return False

    return True


# ------------------------------------------------------------
# MAIN STRATEGY
# ------------------------------------------------------------

def candle_psychology_signal(df, snr):
    """
    Main Candles Psychology Strategy.

    Returns:

        BUY
        SELL
        HOLD
    """

    if df is None:
        return "HOLD", 0, "No data"

    if len(df) < 2:
        return "HOLD", 0, "Minimum 2 candles required"

    # Buyer exhaustion
    if buyer_exhaustion(df, snr):

        return (
            "SELL",
            80,
            "Buyer exhaustion at SNR"
        )

    # Buyer power
    if buyer_power(df, snr):

        return (
            "BUY",
            80,
            "Power of buyers - SNR crossed"
        )

    # Seller exhaustion
    if seller_exhaustion(df, snr):

        return (
            "BUY",
            80,
            "Seller exhaustion at SNR"
        )

    # Seller power
    if seller_power(df, snr):

        return (
            "SELL",
            80,
            "Power of sellers - SNR crossed"
        )

    return (
        "HOLD",
        20,
        "No candle psychology setup"
    )


# ------------------------------------------------------------
# RESULT FOR MAIN.PY
# ------------------------------------------------------------

def get_candle_psychology_result(df, snr):
    """
    Returns dictionary for main.py
    """

    signal, confidence, reason = candle_psychology_signal(
        df,
        snr
    )

    return {
        "strategy": "Candle Psychology",
        "signal": signal,
        "confidence": confidence,
        "reason": reason
    }


# ------------------------------------------------------------
# SIMPLE SIGNAL FUNCTION
# ------------------------------------------------------------

def get_signal(df, snr):
    """
    Returns only BUY / SELL / HOLD
    """

    signal, confidence, reason = candle_psychology_signal(
        df,
        snr
    )

    return signal


# ------------------------------------------------------------
# TEST
# ------------------------------------------------------------

if __name__ == "__main__":

    data = {
        "Open":  [100, 105, 106],
        "High":  [103, 110, 109],
        "Low":   [99, 104, 105],
        "Close": [102, 109, 108]
    }

    df = pd.DataFrame(data)

    # Example SNR
    snr = 108

    result = get_candle_psychology_result(
        df,
        snr
    )

    print("----------------------------------")
    print("CANDLE PSYCHOLOGY")
    print("----------------------------------")

    print("Strategy   :", result["strategy"])
    print("Signal     :", result["signal"])
    print("Confidence :", result["confidence"], "%")
    print("Reason     :", result["reason"])

    print("----------------------------------")