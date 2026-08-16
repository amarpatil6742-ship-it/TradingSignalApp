# ============================================================
# ssfa.py
# Sure Shot Factor / Sure Shot Andy Strategy
# ============================================================

import pandas as pd


# ------------------------------------------------------------
# 1. Candle information
# ------------------------------------------------------------

def candle_info(candle):
    """
    Candle चे body, upper wick, lower wick calculate करते.
    """

    o = float(candle["Open"])
    h = float(candle["High"])
    l = float(candle["Low"])
    c = float(candle["Close"])

    body = abs(c - o)
    total_range = h - l

    if total_range <= 0:
        total_range = 0.00000001

    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    bullish = c > o
    bearish = c < o

    body_percent = (body / total_range) * 100
    upper_percent = (upper_wick / total_range) * 100
    lower_percent = (lower_wick / total_range) * 100

    return {
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "body": body,
        "range": total_range,
        "upper_wick": upper_wick,
        "lower_wick": lower_wick,
        "body_percent": body_percent,
        "upper_percent": upper_percent,
        "lower_percent": lower_percent,
        "bullish": bullish,
        "bearish": bearish
    }


# ------------------------------------------------------------
# 2. Weak candle
# ------------------------------------------------------------

def is_weak_candle(candle):
    """
    Second-last candle weak आहे का?

    Weak candle:
    - Body छोटा
    - Candle range च्या तुलनेत body कमी
    """

    x = candle_info(candle)

    if x["range"] <= 0:
        return False

    return x["body_percent"] <= 45


# ------------------------------------------------------------
# 3. Hammer
# ------------------------------------------------------------

def is_hammer(candle):
    """
    BUY pattern:

    Long lower wick
    Small body
    Small/medium upper wick
    """

    x = candle_info(candle)

    if x["range"] <= 0:
        return False

    # Lower wick body पेक्षा मोठा
    lower_condition = x["lower_wick"] >= x["body"] * 1.5

    # Upper wick तुलनेने छोटा
    upper_condition = x["upper_wick"] <= x["body"] * 1.2

    # Body range च्या 45% पेक्षा कमी
    body_condition = x["body_percent"] <= 45

    return (
        lower_condition
        and upper_condition
        and body_condition
    )


# ------------------------------------------------------------
# 4. Shooting Star
# ------------------------------------------------------------

def is_shooting_star(candle):
    """
    SELL pattern:

    Long upper wick
    Small body
    Small lower wick
    """

    x = candle_info(candle)

    if x["range"] <= 0:
        return False

    upper_condition = x["upper_wick"] >= x["body"] * 1.5

    lower_condition = x["lower_wick"] <= x["body"] * 1.2

    body_condition = x["body_percent"] <= 45

    return (
        upper_condition
        and lower_condition
        and body_condition
    )


# ------------------------------------------------------------
# 5. Ranging market detection
# ------------------------------------------------------------

def is_ranging_market(df, lookback=20):
    """
    Market ranging आहे का हे पाहते.

    Strong trend नसताना candles एका relatively
    छोट्या range मध्ये असतील तर ranging मानतो.
    """

    if len(df) < lookback:
        return False

    recent = df.tail(lookback)

    high = recent["High"].max()
    low = recent["Low"].min()

    if high <= low:
        return False

    total_range = high - low

    avg_close = recent["Close"].mean()

    if avg_close == 0:
        return False

    range_percent = (total_range / avg_close) * 100

    # Crypto/Forex साठी basic threshold
    return range_percent <= 3.0


# ------------------------------------------------------------
# 6. SNR detection
# ------------------------------------------------------------

def find_snr_levels(df, lookback=20):
    """
    Recent candles मधून basic Support / Resistance levels शोधते.
    """

    if len(df) < lookback:
        return None, None

    recent = df.tail(lookback)

    support = float(recent["Low"].min())
    resistance = float(recent["High"].max())

    return support, resistance


# ------------------------------------------------------------
# 7. Candle SNR proximity
# ------------------------------------------------------------

def near_support(candle, support, tolerance=0.003):
    """
    Candle support जवळ आहे का?
    """

    if support is None:
        return False

    low = float(candle["Low"])

    distance = abs(low - support) / support

    return distance <= tolerance


def near_resistance(candle, resistance, tolerance=0.003):
    """
    Candle resistance जवळ आहे का?
    """

    if resistance is None:
        return False

    high = float(candle["High"])

    distance = abs(high - resistance) / resistance

    return distance <= tolerance


# ------------------------------------------------------------
# 8. Hammer wick near support
# ------------------------------------------------------------

def hammer_at_support(candle, support):
    """
    BUY साठी:
    Hammer + Support जवळ
    """

    if not is_hammer(candle):
        return False

    return near_support(candle, support)


# ------------------------------------------------------------
# 9. Shooting star near resistance
# ------------------------------------------------------------

def shooting_star_at_resistance(candle, resistance):
    """
    SELL साठी:
    Shooting Star + Resistance जवळ
    """

    if not is_shooting_star(candle):
        return False

    return near_resistance(candle, resistance)


# ------------------------------------------------------------
# 10. Main SSFA strategy
# ------------------------------------------------------------

def ssfa_signal(df):
    """
    SSFA final signal.

    Returns:

    BUY
    SELL
    HOLD

    तसेच confidence आणि reasons.
    """

    result = {
        "strategy": "SSFA",
        "signal": "HOLD",
        "confidence": 0,
        "reason": [],
        "pattern": None,
        "market": "UNKNOWN"
    }

    # Minimum candles
    if df is None or len(df) < 20:
        result["reason"].append(
            "Minimum 20 candles required"
        )
        return result

    required_columns = [
        "Open",
        "High",
        "Low",
        "Close"
    ]

    for col in required_columns:
        if col not in df.columns:
            result["reason"].append(
                f"Missing column: {col}"
            )
            return result

    # --------------------------------------------------------
    # Last 2 candles
    # --------------------------------------------------------

    second_last = df.iloc[-2]
    last = df.iloc[-1]

    # --------------------------------------------------------
    # Market
    # --------------------------------------------------------

    ranging = is_ranging_market(df)

    if ranging:
        result["market"] = "RANGING"
    else:
        result["market"] = "TRENDING"

    # SSFA च्या requirement नुसार ranging market preferred
    if not ranging:
        result["reason"].append(
            "Market is not ranging"
        )

    # --------------------------------------------------------
    # Weak second-last candle
    # --------------------------------------------------------

    weak = is_weak_candle(second_last)

    if weak:
        result["reason"].append(
            "Second-last candle is weak"
        )
    else:
        result["reason"].append(
            "Second-last candle is not weak"
        )

    # --------------------------------------------------------
    # SNR
    # --------------------------------------------------------

    support, resistance = find_snr_levels(df)

    # --------------------------------------------------------
    # BUY
    # --------------------------------------------------------

    buy_score = 0

    if ranging:
        buy_score += 20

    if weak:
        buy_score += 20

    if is_hammer(last):
        buy_score += 30
        result["pattern"] = "HAMMER"

    if hammer_at_support(last, support):
        buy_score += 30
        result["reason"].append(
            "Hammer wick is near support"
        )

    # --------------------------------------------------------
    # SELL
    # --------------------------------------------------------

    sell_score = 0

    if ranging:
        sell_score += 20

    if weak:
        sell_score += 20

    if is_shooting_star(last):
        sell_score += 30
        result["pattern"] = "SHOOTING_STAR"

    if shooting_star_at_resistance(last, resistance):
        sell_score += 30
        result["reason"].append(
            "Upper wick rejection near resistance"
        )

    # --------------------------------------------------------
    # Final decision
    # --------------------------------------------------------

    if buy_score >= 70 and buy_score > sell_score:

        result["signal"] = "BUY"
        result["confidence"] = min(buy_score, 100)

        result["reason"].append(
            "SSFA BUY conditions matched"
        )

    elif sell_score >= 70 and sell_score > buy_score:

        result["signal"] = "SELL"
        result["confidence"] = min(sell_score, 100)

        result["reason"].append(
            "SSFA SELL conditions matched"
        )

    else:

        result["signal"] = "HOLD"

        result["confidence"] = max(
            buy_score,
            sell_score
        )

        result["reason"].append(
            "SSFA conditions are not strong enough"
        )

    return result


# ------------------------------------------------------------
# 11. Simple signal function
# ------------------------------------------------------------

def signal(df):
    """
    Main.py मधून ही function call करू शकतो.
    """

    result = ssfa_signal(df)

    return (
        result["signal"],
        result["confidence"]
    )


# ------------------------------------------------------------
# 12. Test
# ------------------------------------------------------------

if __name__ == "__main__":

    print("================================")
    print(" SSFA STRATEGY TEST")
    print("================================")

    # Example data
    data = {
        "Open": [
            100, 101, 102, 101, 100,
            101, 102, 103, 102, 101,
            100, 101, 102, 101, 100,
            101, 102, 101, 100, 99
        ],

        "High": [
            101, 102, 103, 102, 101,
            102, 103, 104, 103, 102,
            101, 102, 103, 102, 101,
            102, 103, 102, 101, 101
        ],

        "Low": [
            99, 100, 101, 100, 99,
            100, 101, 102, 101, 100,
            99, 100, 101, 100, 99,
            100, 101, 99, 98, 97
        ],

        "Close": [
            100, 101, 102, 101, 100,
            101, 102, 103, 102, 101,
            100, 101, 102, 101, 100,
            101, 102, 100, 99, 100
        ]
    }

    df = pd.DataFrame(data)

    result = ssfa_signal(df)

    print()
    print("Strategy   :", result["strategy"])
    print("Market     :", result["market"])
    print("Pattern    :", result["pattern"])
    print("Signal     :", result["signal"])
    print("Confidence :", str(result["confidence"]) + "%")

    print()
    print("Reasons:")

    for reason in result["reason"]:
        print("-", reason)

    print()
    print("================================")