# ============================================================
# INJURED ELEPHANT STRATEGY
# ============================================================
# Rules from user's strategy notes:
#
# 1. SNR should be present
# 2. Retracement area should be present
# 3. Second-last candle = weak candle with big tail
# 4. Last candle = big candle
# 5. Big RED candle -> next GREEN = BUY
# 6. Big GREEN candle -> next RED = SELL
#
# Output:
# BUY / SELL / HOLD
# Confidence: 0-100
# ============================================================

import pandas as pd


# ------------------------------------------------------------
# Candle information
# ------------------------------------------------------------

def candle_info(candle):

    o = float(candle["Open"])
    h = float(candle["High"])
    l = float(candle["Low"])
    c = float(candle["Close"])

    body = abs(c - o)
    candle_range = h - l

    if candle_range <= 0:
        return {
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "body": 0.0,
            "range": 0.0,
            "upper_wick": 0.0,
            "lower_wick": 0.0,
            "bull": False,
            "bear": False
        }

    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    return {
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "body": body,
        "range": candle_range,
        "upper_wick": max(0.0, upper_wick),
        "lower_wick": max(0.0, lower_wick),
        "bull": c > o,
        "bear": c < o
    }


# ------------------------------------------------------------
# Big candle detection
# ------------------------------------------------------------

def is_big_candle(df, index, multiplier=1.5):

    if index < 5:
        return False

    current = candle_info(df.iloc[index])

    previous_ranges = []

    start = max(0, index - 5)

    for i in range(start, index):
        info = candle_info(df.iloc[i])

        if info["range"] > 0:
            previous_ranges.append(info["range"])

    if not previous_ranges:
        return False

    average_range = sum(previous_ranges) / len(previous_ranges)

    if average_range <= 0:
        return False

    return current["range"] >= average_range * multiplier


# ------------------------------------------------------------
# Weak candle with big tail
# ------------------------------------------------------------

def is_weak_tail_candle(candle):

    info = candle_info(candle)

    if info["range"] <= 0:
        return False

    body = info["body"]

    # Body should be relatively small
    small_body = body <= info["range"] * 0.45

    # One wick should be significantly larger
    big_lower_tail = info["lower_wick"] >= max(body * 1.5, info["range"] * 0.30)

    big_upper_tail = info["upper_wick"] >= max(body * 1.5, info["range"] * 0.30)

    return small_body and (big_lower_tail or big_upper_tail)


# ------------------------------------------------------------
# Retracement area
# ------------------------------------------------------------

def is_retracement_area(df):

    if len(df) < 4:
        return False

    c1 = candle_info(df.iloc[-4])
    c2 = candle_info(df.iloc[-3])
    c3 = candle_info(df.iloc[-2])

    # Upward movement followed by pullback
    bullish_move = (
        c1["bull"] or c2["bull"]
    )

    # Downward movement followed by pullback
    bearish_move = (
        c1["bear"] or c2["bear"]
    )

    # Current candle overlaps previous candle range
    overlap = (
        c3["low"] <= c2["high"]
        and
        c3["high"] >= c2["low"]
    )

    return overlap and (bullish_move or bearish_move)


# ------------------------------------------------------------
# SNR calculation
# ------------------------------------------------------------

def calculate_snr(df, lookback=10):

    if len(df) < 5:
        return None, None

    recent = df.tail(lookback)

    support = float(recent["Low"].min())
    resistance = float(recent["High"].max())

    return support, resistance


# ------------------------------------------------------------
# SNR proximity
# ------------------------------------------------------------

def near_snr(price, support, resistance, tolerance=0.002):

    if support is None or resistance is None:
        return False

    support_distance = abs(price - support) / price
    resistance_distance = abs(price - resistance) / price

    return (
        support_distance <= tolerance
        or
        resistance_distance <= tolerance
    )


# ------------------------------------------------------------
# SNR direction
# ------------------------------------------------------------

def snr_direction(price, support, resistance, tolerance=0.002):

    if support is None or resistance is None:
        return "NONE"

    support_distance = abs(price - support) / price
    resistance_distance = abs(price - resistance) / price

    if support_distance <= tolerance:
        return "SUPPORT"

    if resistance_distance <= tolerance:
        return "RESISTANCE"

    return "NONE"


# ------------------------------------------------------------
# Main strategy
# ------------------------------------------------------------

def injured_elephant_signal(df):

    required_columns = [
        "Open",
        "High",
        "Low",
        "Close"
    ]

    # Check columns
    for column in required_columns:

        if column not in df.columns:

            return {
                "signal": "HOLD",
                "confidence": 0,
                "strategy": "INJURED_ELEPHANT",
                "reason": f"Missing column: {column}"
            }

    # Minimum candles
    if len(df) < 15:

        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "INJURED_ELEPHANT",
            "reason": "Not enough candles"
        }

    df = df.copy().reset_index(drop=True)

    # --------------------------------------------------------
    # Important candles
    # --------------------------------------------------------

    second_last = df.iloc[-2]
    last = df.iloc[-1]

    second_info = candle_info(second_last)
    last_info = candle_info(last)

    # --------------------------------------------------------
    # SNR
    # --------------------------------------------------------

    support, resistance = calculate_snr(df)

    current_price = last_info["close"]

    snr_side = snr_direction(
        current_price,
        support,
        resistance
    )

    # --------------------------------------------------------
    # Retracement
    # --------------------------------------------------------

    retracement = is_retracement_area(df)

    # --------------------------------------------------------
    # Weak second-last candle
    # --------------------------------------------------------

    weak_candle = is_weak_tail_candle(second_last)

    # --------------------------------------------------------
    # Big last candle
    # --------------------------------------------------------

    big_last = is_big_candle(
        df,
        len(df) - 1
    )

    # --------------------------------------------------------
    # Scores
    # --------------------------------------------------------

    buy_score = 0
    sell_score = 0

    buy_reasons = []
    sell_reasons = []

    # ========================================================
    # BUY SETUP
    # ========================================================
    #
    # Photo rule:
    # Big RED -> next GREEN = BUY
    #

    if second_info["bear"]:
        buy_score += 20
        buy_reasons.append("Second-last candle RED")

    if weak_candle:
        buy_score += 20
        buy_reasons.append("Weak candle with big tail")

    if retracement:
        buy_score += 20
        buy_reasons.append("Retracement area")

    if snr_side == "SUPPORT":
        buy_score += 20
        buy_reasons.append("Near SNR support")

    if last_info["bull"]:
        buy_score += 10
        buy_reasons.append("Last candle GREEN")

    if big_last:
        buy_score += 10
        buy_reasons.append("Last candle BIG")

    # ========================================================
    # SELL SETUP
    # ========================================================
    #
    # Photo rule:
    # Big GREEN -> next RED = SELL
    #

    if second_info["bull"]:
        sell_score += 20
        sell_reasons.append("Second-last candle GREEN")

    if weak_candle:
        sell_score += 20
        sell_reasons.append("Weak candle with big tail")

    if retracement:
        sell_score += 20
        sell_reasons.append("Retracement area")

    if snr_side == "RESISTANCE":
        sell_score += 20
        sell_reasons.append("Near SNR resistance")

    if last_info["bear"]:
        sell_score += 10
        sell_reasons.append("Last candle RED")

    if big_last:
        sell_score += 10
        sell_reasons.append("Last candle BIG")

    # ========================================================
    # FINAL DECISION
    # ========================================================

    # Strong BUY
    if buy_score >= 70 and buy_score > sell_score:

        return {
            "signal": "BUY",
            "confidence": min(buy_score, 100),
            "strategy": "INJURED_ELEPHANT",
            "reason": " + ".join(buy_reasons)
        }

    # Strong SELL
    if sell_score >= 70 and sell_score > buy_score:

        return {
            "signal": "SELL",
            "confidence": min(sell_score, 100),
            "strategy": "INJURED_ELEPHANT",
            "reason": " + ".join(sell_reasons)
        }

    # HOLD
    return {
        "signal": "HOLD",
        "confidence": max(buy_score, sell_score),
        "strategy": "INJURED_ELEPHANT",
        "reason": "Injured Elephant conditions not fully confirmed"
    }


# ------------------------------------------------------------
# Easy function for main.py
# ------------------------------------------------------------

def get_signal(df):

    return injured_elephant_signal(df)


# ------------------------------------------------------------
# Test
# ------------------------------------------------------------

if __name__ == "__main__":

    print("----------------------------------------")
    print(" INJURED ELEPHANT STRATEGY")
    print("----------------------------------------")
    print("Strategy loaded successfully.")

    # Example:
    #
    # df = pd.read_csv("candles.csv")
    #
    # result = injured_elephant_signal(df)
    #
    # print("Signal     :", result["signal"])
    # print("Confidence :", result["confidence"], "%")
    # print("Reason     :", result["reason"])