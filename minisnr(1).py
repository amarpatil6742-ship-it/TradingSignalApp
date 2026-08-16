# minisnr.py
# Mini SNR Strategy
# Works with OHLC pandas DataFrame

import pandas as pd


def candle_color(candle):
    """
    Candle color:
    GREEN = Close > Open
    RED   = Close < Open
    DOJI  = Close == Open
    """

    if candle["Close"] > candle["Open"]:
        return "GREEN"

    elif candle["Close"] < candle["Open"]:
        return "RED"

    return "DOJI"


def candle_body(candle):
    """Candle body size"""

    return abs(
        float(candle["Close"]) - float(candle["Open"])
    )


def candle_range(candle):
    """Total candle range"""

    return float(candle["High"]) - float(candle["Low"])


def is_running_candle(candle):
    """
    Running candle check.

    मोठा body आणि छोटा opposite wick असलेली candle
    running candle म्हणून consider केली जाते.
    """

    body = candle_body(candle)
    rng = candle_range(candle)

    if rng <= 0:
        return False

    body_ratio = body / rng

    return body_ratio >= 0.50


def head_match(candle1, candle2, tolerance_ratio=0.001):
    """
    दोन candles चे HEAD / HIGH जवळ आहेत का ते तपासतो.

    tolerance_ratio:
    0.001 = 0.1%
    """

    high1 = float(candle1["High"])
    high2 = float(candle2["High"])

    reference = max(abs(high1), abs(high2), 1e-12)

    difference = abs(high1 - high2)

    tolerance = reference * tolerance_ratio

    return difference <= tolerance


def mini_snr_signal(df):
    """
    MINI SNR SIGNAL

    Rule:

    1. Previous candle आणि running candle चा HEAD match पाहतो.
    2. RED + HEAD MATCH  -> BUY
    3. GREEN + HEAD MATCH -> SELL
    4. DOJI -> HOLD
    5. Running candle नसल्यास HOLD

    Returns:
        signal
        confidence
        reason
    """

    if df is None:
        return "HOLD", 0, "No data"

    if len(df) < 2:
        return "HOLD", 0, "At least 2 candles required"

    required_columns = [
        "Open",
        "High",
        "Low",
        "Close"
    ]

    for column in required_columns:
        if column not in df.columns:
            return "HOLD", 0, f"Missing column: {column}"

    previous = df.iloc[-2]
    running = df.iloc[-1]

    previous_color = candle_color(previous)
    running_color = candle_color(running)

    # Running candle check
    if not is_running_candle(running):
        return (
            "HOLD",
            20,
            "Running candle condition not satisfied"
        )

    # Head matching
    if not head_match(previous, running):
        return (
            "HOLD",
            25,
            "Mini SNR head not matched"
        )

    # -----------------------------
    # RED HEAD MATCH
    # -----------------------------

    if running_color == "RED":

        return (
            "BUY",
            75,
            "RED running candle + HEAD MATCH -> BUY"
        )

    # -----------------------------
    # GREEN HEAD MATCH
    # -----------------------------

    if running_color == "GREEN":

        return (
            "SELL",
            75,
            "GREEN running candle + HEAD MATCH -> SELL"
        )

    # -----------------------------
    # DOJI
    # -----------------------------

    return (
        "HOLD",
        30,
        "DOJI candle - no Mini SNR signal"
    )


def get_minisnr_signal(df):
    """
    Simple function for main.py

    Returns only:
        BUY / SELL / HOLD
    """

    signal, confidence, reason = mini_snr_signal(df)

    return signal


def get_minisnr_result(df):
    """
    Complete result.

    Example:

    {
        "strategy": "Mini SNR",
        "signal": "BUY",
        "confidence": 75,
        "reason": "..."
    }
    """

    signal, confidence, reason = mini_snr_signal(df)

    return {
        "strategy": "Mini SNR",
        "signal": signal,
        "confidence": confidence,
        "reason": reason
    }


# --------------------------------------------------
# TEST
# --------------------------------------------------

if __name__ == "__main__":

    data = {
        "Open":  [100, 101],
        "High":  [105, 105],
        "Low":   [99, 100],
        "Close": [103, 102]
    }

    df = pd.DataFrame(data)

    result = get_minisnr_result(df)

    print("--------------------------------")
    print("MINI SNR STRATEGY")
    print("--------------------------------")
    print("Strategy   :", result["strategy"])
    print("Signal     :", result["signal"])
    print("Confidence :", result["confidence"], "%")
    print("Reason     :", result["reason"])
    print("--------------------------------")