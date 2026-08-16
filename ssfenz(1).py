# ============================================================
# SSFENZ.PY
# SURE SHOT FENZ / GILLBAAT STRATEGY
# ============================================================

import pandas as pd


# ------------------------------------------------------------
# Candle Information
# ------------------------------------------------------------

def candle_info(candle):

    o = float(candle["Open"])
    h = float(candle["High"])
    l = float(candle["Low"])
    c = float(candle["Close"])

    candle_range = h - l
    body = abs(c - o)

    if candle_range <= 0:
        return {
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "range": 0,
            "body": 0,
            "upper_wick": 0,
            "lower_wick": 0,
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
        "range": candle_range,
        "body": body,
        "upper_wick": max(0, upper_wick),
        "lower_wick": max(0, lower_wick),
        "bull": c > o,
        "bear": c < o
    }


# ------------------------------------------------------------
# HAMMER DETECTION
# ------------------------------------------------------------

def is_hammer(candle):

    x = candle_info(candle)

    if x["range"] <= 0:
        return False

    body = x["body"]
    lower = x["lower_wick"]
    upper = x["upper_wick"]
    rng = x["range"]

    # Body relatively small
    small_body = body <= rng * 0.45

    # Long lower wick
    long_lower_wick = lower >= max(
        body * 1.5,
        rng * 0.30
    )

    # Upper wick should not be very large
    small_upper_wick = upper <= rng * 0.35

    return (
        small_body
        and
        long_lower_wick
        and
        small_upper_wick
    )


# ------------------------------------------------------------
# LONG / STRONG CANDLE
# ------------------------------------------------------------

def is_long_candle(df, index, multiplier=1.40):

    if index < 5:
        return False

    current = candle_info(df.iloc[index])

    if current["range"] <= 0:
        return False

    previous_ranges = []

    start = max(0, index - 5)

    for i in range(start, index):

        x = candle_info(df.iloc[i])

        if x["range"] > 0:
            previous_ranges.append(x["range"])

    if not previous_ranges:
        return False

    average_range = sum(previous_ranges) / len(previous_ranges)

    return current["range"] >= average_range * multiplier


# ------------------------------------------------------------
# TREND DETECTION
# ------------------------------------------------------------

def market_trend(df, lookback=6):

    if len(df) < lookback:
        return "RANGE"

    recent = df.tail(lookback)

    first_close = float(recent.iloc[0]["Close"])
    last_close = float(recent.iloc[-1]["Close"])

    move = last_close - first_close

    if first_close == 0:
        return "RANGE"

    percentage_move = abs(move / first_close)

    # Minimum movement
    if percentage_move < 0.0005:
        return "RANGE"

    if move > 0:
        return "UPTREND"

    if move < 0:
        return "DOWNTREND"

    return "RANGE"


# ------------------------------------------------------------
# RETRACEMENT DETECTION
# ------------------------------------------------------------

def is_retracement(df):

    if len(df) < 5:
        return False

    c1 = candle_info(df.iloc[-5])
    c2 = candle_info(df.iloc[-4])
    c3 = candle_info(df.iloc[-3])
    c4 = candle_info(df.iloc[-2])

    # Previous movement
    bullish_move = (
        c1["bull"] or
        c2["bull"] or
        c3["bull"]
    )

    bearish_move = (
        c1["bear"] or
        c2["bear"] or
        c3["bear"]
    )

    # Last completed candle overlaps previous range
    overlap = (
        c4["low"] <= c3["high"]
        and
        c4["high"] >= c3["low"]
    )

    return overlap and (
        bullish_move or bearish_move
    )


# ------------------------------------------------------------
# SUPPORT / RESISTANCE
# ------------------------------------------------------------

def calculate_snr(df, lookback=15):

    if len(df) < 5:
        return None, None

    recent = df.tail(lookback)

    support = float(recent["Low"].min())
    resistance = float(recent["High"].max())

    return support, resistance


# ------------------------------------------------------------
# PRICE NEAR SNR
# ------------------------------------------------------------

def near_support(price, support, tolerance=0.002):

    if support is None:
        return False

    if price == 0:
        return False

    distance = abs(price - support) / price

    return distance <= tolerance


def near_resistance(price, resistance, tolerance=0.002):

    if resistance is None:
        return False

    if price == 0:
        return False

    distance = abs(price - resistance) / price

    return distance <= tolerance


# ------------------------------------------------------------
# SNR BREAK
# ------------------------------------------------------------

def support_break(candle, support):

    if support is None:
        return False

    x = candle_info(candle)

    return x["close"] < support


def resistance_break(candle, resistance):

    if resistance is None:
        return False

    x = candle_info(candle)

    return x["close"] > resistance


# ------------------------------------------------------------
# MAIN SSFENZ STRATEGY
# ------------------------------------------------------------

def ssfenz_signal(df):

    required_columns = [
        "Open",
        "High",
        "Low",
        "Close"
    ]

    # --------------------------------------------------------
    # Check columns
    # --------------------------------------------------------

    for col in required_columns:

        if col not in df.columns:

            return {
                "signal": "HOLD",
                "confidence": 0,
                "strategy": "SSFENZ",
                "reason": "Missing column: " + col
            }

    # --------------------------------------------------------
    # Minimum candles
    # --------------------------------------------------------

    if len(df) < 15:

        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SSFENZ",
            "reason": "Not enough candles"
        }

    df = df.copy().reset_index(drop=True)

    # --------------------------------------------------------
    # Candles
    # --------------------------------------------------------

    hammer_candle = df.iloc[-3]
    long_candle = df.iloc[-2]
    current_candle = df.iloc[-1]

    hammer = candle_info(hammer_candle)
    long = candle_info(long_candle)
    current = candle_info(current_candle)

    # --------------------------------------------------------
    # Hammer
    # --------------------------------------------------------

    hammer_found = is_hammer(hammer_candle)

    # --------------------------------------------------------
    # Long candle
    # --------------------------------------------------------

    long_found = is_long_candle(
        df,
        len(df) - 2
    )

    # --------------------------------------------------------
    # Trend
    # --------------------------------------------------------

    trend = market_trend(df)

    # --------------------------------------------------------
    # Retracement
    # --------------------------------------------------------

    retracement = is_retracement(df)

    # --------------------------------------------------------
    # SNR
    # --------------------------------------------------------

    support, resistance = calculate_snr(df)

    # Price near SNR
    near_sup = near_support(
        long["close"],
        support
    )

    near_res = near_resistance(
        long["close"],
        resistance
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
    # Photo:
    #
    # Hammer / weak candle
    #        +
    # Long RED candle
    #        =
    # Next GREEN / BUY
    #
    # ========================================================

    if hammer_found:
        buy_score += 20
        buy_reasons.append("Hammer pattern")

    if long_found:
        buy_score += 20
        buy_reasons.append("Long candle")

    if long["bear"]:
        buy_score += 15
        buy_reasons.append("Long candle is RED")

    if current["bull"]:
        buy_score += 15
        buy_reasons.append("Current candle is GREEN")

    if trend == "UPTREND":
        buy_score += 15
        buy_reasons.append("Trending market")

    if retracement:
        buy_score += 10
        buy_reasons.append("Retracement area")

    if near_sup:
        buy_score += 5
        buy_reasons.append("Near support")

    # ========================================================
    # SELL SETUP
    # ========================================================
    #
    # Photo:
    #
    # Hammer / weak candle
    #        +
    # Long GREEN candle
    #        =
    # Next RED / SELL
    #
    # ========================================================

    if hammer_found:
        sell_score += 20
        sell_reasons.append("Hammer pattern")

    if long_found:
        sell_score += 20
        sell_reasons.append("Long candle")

    if long["bull"]:
        sell_score += 15
        sell_reasons.append("Long candle is GREEN")

    if current["bear"]:
        sell_score += 15
        sell_reasons.append("Current candle is RED")

    if trend == "DOWNTREND":
        sell_score += 15
        sell_reasons.append("Trending market")

    if retracement:
        sell_score += 10
        sell_reasons.append("Retracement area")

    if near_res:
        sell_score += 5
        sell_reasons.append("Near resistance")

    # ========================================================
    # FINAL SIGNAL
    # ========================================================

    # BUY
    if (
        buy_score >= 70
        and
        buy_score > sell_score
    ):

        return {
            "signal": "BUY",
            "confidence": min(buy_score, 100),
            "strategy": "SSFENZ",
            "reason": " + ".join(buy_reasons)
        }

    # SELL
    if (
        sell_score >= 70
        and
        sell_score > buy_score
    ):

        return {
            "signal": "SELL",
            "confidence": min(sell_score, 100),
            "strategy": "SSFENZ",
            "reason": " + ".join(sell_reasons)
        }

    # HOLD
    return {
        "signal": "HOLD",
        "confidence": max(
            buy_score,
            sell_score
        ),
        "strategy": "SSFENZ",
        "reason": "SSFENZ conditions not fully confirmed"
    }


# ------------------------------------------------------------
# MAIN FUNCTION
# ------------------------------------------------------------

def get_signal(df):

    return ssfenz_signal(df)


# ------------------------------------------------------------
# TEST
# ------------------------------------------------------------

if __name__ == "__main__":

    print()
    print("======================================")
    print("       SSFENZ STRATEGY")
    print("======================================")
    print("Strategy loaded successfully.")
    print()
    print("Rules:")
    print("1. Hammer / weak candle")
    print("2. Long candle")
    print("3. Trending market")
    print("4. Retracement area")
    print("5. BUY / SELL confirmation")
    print()