# ============================================================
# ss2.py
# Sure Shot 2 - Version 2
# Ranging Market Reversal + Retrace Strategy
# ============================================================

import pandas as pd


# ============================================================
# 1. BASIC CANDLE FUNCTIONS
# ============================================================

def body(c):
    return abs(float(c["Close"]) - float(c["Open"]))


def candle_range(c):
    return float(c["High"]) - float(c["Low"])


def upper_wick(c):
    return float(c["High"]) - max(
        float(c["Open"]),
        float(c["Close"])
    )


def lower_wick(c):
    return min(
        float(c["Open"]),
        float(c["Close"])
    ) - float(c["Low"])


def bullish(c):
    return float(c["Close"]) > float(c["Open"])


def bearish(c):
    return float(c["Close"]) < float(c["Open"])


# ============================================================
# 2. DOJI DETECTION
# ============================================================

def is_doji(c):

    rng = candle_range(c)

    if rng <= 0:
        return False

    b = body(c)

    ratio = b / rng

    return ratio <= 0.15


# ============================================================
# 3. HAMMER FILTER
# ============================================================

def is_hammer(c):

    b = body(c)
    rng = candle_range(c)

    if rng <= 0 or b <= 0:
        return False

    upper = upper_wick(c)
    lower = lower_wick(c)

    if lower >= b * 2 and upper <= b * 0.5:
        return True

    if upper >= b * 2 and lower <= b * 0.5:
        return True

    return False


# ============================================================
# 4. FULL CANDLE FILTER
# ============================================================

def is_full_candle(c):

    rng = candle_range(c)

    if rng <= 0:
        return True

    b = body(c)

    return (b / rng) >= 0.90


# ============================================================
# 5. RANGE DETECTION
# ============================================================

def get_range(df, lookback=20):

    if len(df) < lookback:
        return None, None

    recent = df.iloc[-lookback:]

    support = float(recent["Low"].min())
    resistance = float(recent["High"].max())

    return support, resistance


# ============================================================
# 6. RANGING MARKET CHECK
# ============================================================

def is_ranging_market(df, lookback=20):

    if len(df) < lookback:
        return False

    support, resistance = get_range(df, lookback)

    if support is None or resistance is None:
        return False

    price = float(df.iloc[-1]["Close"])

    if price <= 0:
        return False

    range_size = resistance - support

    # Range must exist
    if range_size <= 0:
        return False

    # Price should not be too far outside range
    upper_limit = resistance + range_size * 0.10
    lower_limit = support - range_size * 0.10

    if lower_limit <= price <= upper_limit:
        return True

    return False


# ============================================================
# 7. BUYERS AREA
# ============================================================

def in_buyers_area(df, lookback=20):

    support, resistance = get_range(df, lookback)

    if support is None:
        return False

    price = float(df.iloc[-1]["Close"])

    rng = resistance - support

    if rng <= 0:
        return False

    # Lower 25% of range
    buyers_limit = support + rng * 0.25

    return price <= buyers_limit


# ============================================================
# 8. SELLERS AREA
# ============================================================

def in_sellers_area(df, lookback=20):

    support, resistance = get_range(df, lookback)

    if resistance is None:
        return False

    price = float(df.iloc[-1]["Close"])

    rng = resistance - support

    if rng <= 0:
        return False

    # Upper 25% of range
    sellers_limit = resistance - rng * 0.25

    return price >= sellers_limit


# ============================================================
# 9. REVERSAL CANDLE
# ============================================================

def bullish_reversal(df, index):

    if index < 1:
        return False

    c = df.iloc[index]
    prev = df.iloc[index - 1]

    if not bullish(c):
        return False

    # Previous candle bearish
    if not bearish(prev):
        return False

    # Bullish engulfing
    engulfing = (
        float(c["Open"]) <= float(prev["Close"])
        and
        float(c["Close"]) >= float(prev["Open"])
    )

    # Strong bullish body
    rng = candle_range(c)

    if rng <= 0:
        return False

    body_ratio = body(c) / rng

    return engulfing or body_ratio >= 0.50


def bearish_reversal(df, index):

    if index < 1:
        return False

    c = df.iloc[index]
    prev = df.iloc[index - 1]

    if not bearish(c):
        return False

    if not bullish(prev):
        return False

    # Bearish engulfing
    engulfing = (
        float(c["Open"]) >= float(prev["Close"])
        and
        float(c["Close"]) <= float(prev["Open"])
    )

    rng = candle_range(c)

    if rng <= 0:
        return False

    body_ratio = body(c) / rng

    return engulfing or body_ratio >= 0.50


# ============================================================
# 10. RETRACE DETECTION
# ============================================================

def bullish_retrace(df):

    if len(df) < 4:
        return False

    c1 = df.iloc[-4]
    c2 = df.iloc[-3]
    c3 = df.iloc[-2]
    c4 = df.iloc[-1]

    # Previous move upward
    upward_move = (
        float(c2["Close"]) > float(c1["Close"])
        and
        float(c3["Close"]) >= float(c2["Close"])
    )

    # Current candle pulls back
    pullback = (
        float(c4["Low"]) < float(c3["Low"])
        or
        float(c4["Close"]) < float(c3["Close"])
    )

    return upward_move and pullback


def bearish_retrace(df):

    if len(df) < 4:
        return False

    c1 = df.iloc[-4]
    c2 = df.iloc[-3]
    c3 = df.iloc[-2]
    c4 = df.iloc[-1]

    # Previous move downward
    downward_move = (
        float(c2["Close"]) < float(c1["Close"])
        and
        float(c3["Close"]) <= float(c2["Close"])
    )

    # Current candle pulls back
    pullback = (
        float(c4["High"]) > float(c3["High"])
        or
        float(c4["Close"]) > float(c3["Close"])
    )

    return downward_move and pullback


# ============================================================
# 11. SHORT TAIL
# ============================================================

def short_tail(c):

    rng = candle_range(c)

    if rng <= 0:
        return False

    upper = upper_wick(c) / rng
    lower = lower_wick(c) / rng

    return upper <= 0.30 and lower <= 0.30


# ============================================================
# 12. SNR WARNING
# ============================================================

def near_range_boundary(df):

    support, resistance = get_range(df)

    if support is None:
        return True

    price = float(df.iloc[-1]["Close"])

    rng = resistance - support

    if rng <= 0:
        return True

    # Very close to boundary
    support_distance = abs(price - support) / rng
    resistance_distance = abs(price - resistance) / rng

    if support_distance <= 0.05:
        return True

    if resistance_distance <= 0.05:
        return True

    return False


# ============================================================
# 13. CONFIDENCE
# ============================================================

def calculate_confidence(
    ranging,
    reversal,
    area,
    retrace,
    shorttail,
    fullcandle,
    hammer,
    boundary
):

    confidence = 0

    if ranging:
        confidence += 20

    if reversal:
        confidence += 25

    if area:
        confidence += 20

    if retrace:
        confidence += 15

    if shorttail:
        confidence += 10

    if not fullcandle:
        confidence += 5

    if not hammer:
        confidence += 5

    # Penalties
    if not ranging:
        confidence -= 25

    if fullcandle:
        confidence -= 20

    if hammer:
        confidence -= 20

    if boundary:
        confidence -= 15

    confidence = max(0, min(100, confidence))

    return int(confidence)


# ============================================================
# 14. SS2 MAIN STRATEGY
# ============================================================

def strategy_two(df):

    reasons = []

    # --------------------------------------------------------
    # DATA CHECK
    # --------------------------------------------------------

    if df is None:

        return {
            "strategy": "Sure Shot 2",
            "signal": "WAIT",
            "confidence": 0,
            "reasons": ["DataFrame not found"]
        }

    if len(df) < 25:

        return {
            "strategy": "Sure Shot 2",
            "signal": "WAIT",
            "confidence": 0,
            "reasons": [
                f"Need minimum 25 candles, available {len(df)}"
            ]
        }

    # --------------------------------------------------------
    # RANGE
    # --------------------------------------------------------

    ranging = is_ranging_market(df)

    if ranging:
        reasons.append("Ranging market detected")
    else:
        reasons.append("Market is not clearly ranging")

        return {
            "strategy": "Sure Shot 2",
            "signal": "WAIT",
            "confidence": 0,
            "reasons": reasons
        }

    # --------------------------------------------------------
    # AREAS
    # --------------------------------------------------------

    buyers = in_buyers_area(df)
    sellers = in_sellers_area(df)

    # --------------------------------------------------------
    # SECOND LAST CANDLE
    # --------------------------------------------------------

    index = len(df) - 2

    bull_reverse = bullish_reversal(df, index)
    bear_reverse = bearish_reversal(df, index)

    # --------------------------------------------------------
    # LAST CANDLE
    # --------------------------------------------------------

    last = df.iloc[-1]

    last_doji = is_doji(last)
    last_hammer = is_hammer(last)
    last_full = is_full_candle(last)
    last_shorttail = short_tail(last)

    # --------------------------------------------------------
    # RETRACE
    # --------------------------------------------------------

    bull_retrace = bullish_retrace(df)
    bear_retrace = bearish_retrace(df)

    # --------------------------------------------------------
    # RANGE BOUNDARY
    # --------------------------------------------------------

    boundary = near_range_boundary(df)

    # ========================================================
    # SELL FROM BUYERS AREA
    # ========================================================

    # According to your notebook rule:
    # Buyers area -> next candle SELL

    sell_condition = (
        buyers
        and bear_reverse
        and not last_full
        and not last_hammer
        and not boundary
    )

    # ========================================================
    # BUY FROM SELLERS AREA
    # ========================================================

    # According to your notebook rule:
    # Sellers area -> next candle BUY

    buy_condition = (
        sellers
        and bull_reverse
        and not last_full
        and not last_hammer
        and not boundary
    )

    # ========================================================
    # BUY
    # ========================================================

    if buy_condition:

        confidence = calculate_confidence(
            ranging=True,
            reversal=True,
            area=True,
            retrace=bull_retrace,
            shorttail=last_shorttail,
            fullcandle=last_full,
            hammer=last_hammer,
            boundary=boundary
        )

        reasons.append("Sellers area")
        reasons.append("Bullish reversal detected")

        if bull_retrace:
            reasons.append("Bullish retrace detected")

        if last_shorttail:
            reasons.append("Last candle short-tail")

        reasons.append("No full candle")
        reasons.append("No hammer")

        return {
            "strategy": "Sure Shot 2",
            "signal": "BUY",
            "confidence": confidence}