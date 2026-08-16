# ============================================================
# SS8.py
# Sure Shot 8 Strategy
# Trend + SNR Break + Retracement
# ============================================================

import pandas as pd


# ------------------------------------------------------------
# Candle helpers
# ------------------------------------------------------------

def candle_info(c):
    """
    Return basic candle measurements.
    """

    o = float(c["Open"])
    h = float(c["High"])
    l = float(c["Low"])
    cl = float(c["Close"])

    body = abs(cl - o)
    total = h - l

    if total <= 0:
        return {
            "body": 0.0,
            "range": 0.0,
            "upper_wick": 0.0,
            "lower_wick": 0.0,
            "bull": False,
            "bear": False
        }

    upper_wick = h - max(o, cl)
    lower_wick = min(o, cl) - l

    return {
        "body": body,
        "range": total,
        "upper_wick": max(0.0, upper_wick),
        "lower_wick": max(0.0, lower_wick),
        "bull": cl > o,
        "bear": cl < o
    }


# ------------------------------------------------------------
# Candle filters
# ------------------------------------------------------------

def is_doji(c):
    x = candle_info(c)

    if x["range"] == 0:
        return True

    return x["body"] <= x["range"] * 0.20


def is_hammer(c):
    x = candle_info(c)

    if x["range"] == 0:
        return False

    # Hammer / inverted-hammer type candle filter
    long_lower = x["lower_wick"] >= x["body"] * 2
    long_upper = x["upper_wick"] >= x["body"] * 2

    return long_lower or long_upper


def is_big_candle(c, df, index):
    """
    Big candle = current range substantially larger
    than recent average range.
    """

    x = candle_info(c)

    if index < 5:
        return False

    ranges = []

    for i in range(max(0, index - 5), index):
        ci = candle_info(df.iloc[i])
        ranges.append(ci["range"])

    if not ranges:
        return False

    avg_range = sum(ranges) / len(ranges)

    if avg_range <= 0:
        return False

    return x["range"] >= avg_range * 1.8


# ------------------------------------------------------------
# Trend detection
# ------------------------------------------------------------

def market_trend(df, lookback=5):
    """
    Simple trend detection.

    Returns:
        BUYER_TREND
        SELLER_TREND
        RANGING
    """

    if len(df) < lookback + 1:
        return "RANGING"

    recent = df.tail(lookback)

    first_close = float(recent.iloc[0]["Close"])
    last_close = float(recent.iloc[-1]["Close"])

    if last_close > first_close:
        return "BUYER_TREND"

    if last_close < first_close:
        return "SELLER_TREND"

    return "RANGING"


# ------------------------------------------------------------
# SNR calculation
# ------------------------------------------------------------

def calculate_snr(df, lookback=10):
    """
    Approximate SNR levels from recent candles.

    Returns:
        support
        resistance
    """

    if len(df) < 3:
        return None, None

    recent = df.tail(lookback)

    support = float(recent["Low"].min())
    resistance = float(recent["High"].max())

    return support, resistance


# ------------------------------------------------------------
# Retracement detection
# ------------------------------------------------------------

def bullish_retracement(previous_candle, current_candle):
    """
    Price moved upward and current candle comes back
    into the previous candle's area.
    """

    prev = candle_info(previous_candle)
    cur = candle_info(current_candle)

    if not prev["bull"]:
        return False

    # Current candle should not be an extremely large candle
    if cur["range"] > prev["range"] * 1.5:
        return False

    # Current candle touches previous candle body/range
    prev_high = float(previous_candle["High"])
    prev_low = float(previous_candle["Low"])

    cur_high = float(current_candle["High"])
    cur_low = float(current_candle["Low"])

    return cur_low <= prev_high and cur_high >= prev_low


def bearish_retracement(previous_candle, current_candle):
    """
    Price moved downward and current candle retraces
    into previous candle's area.
    """

    prev = candle_info(previous_candle)
    cur = candle_info(current_candle)

    if not prev["bear"]:
        return False

    if cur["range"] > prev["range"] * 1.5:
        return False

    prev_high = float(previous_candle["High"])
    prev_low = float(previous_candle["Low"])

    cur_high = float(current_candle["High"])
    cur_low = float(current_candle["Low"])

    return cur_low <= prev_high and cur_high >= prev_low


# ------------------------------------------------------------
# SS8 Main Strategy
# ------------------------------------------------------------

def ss8_signal(df):
    """
    SS8 strategy.

    Expected columns:
        Open
        High
        Low
        Close

    Returns:
        {
            "signal": "BUY" / "SELL" / "HOLD",
            "confidence": number,
            "strategy": "SS8",
            "reason": text
        }
    """

    required = ["Open", "High", "Low", "Close"]

    for col in required:
        if col not in df.columns:
            return {
                "signal": "HOLD",
                "confidence": 0,
                "strategy": "SS8",
                "reason": f"Missing column: {col}"
            }

    if len(df) < 15:
        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SS8",
            "reason": "Not enough candles"
        }

    df = df.reset_index(drop=True)

    trend = market_trend(df)

    support, resistance = calculate_snr(df)

    if support is None or resistance is None:
        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SS8",
            "reason": "SNR unavailable"
        }

    # --------------------------------------------------------
    # Candle positions
    # --------------------------------------------------------

    break_candle = df.iloc[-3]
    retrace_candle = df.iloc[-2]
    last_candle = df.iloc[-1]

    break_info = candle_info(break_candle)
    retrace_info = candle_info(retrace_candle)
    last_info = candle_info(last_candle)

    # --------------------------------------------------------
    # Precautions
    # --------------------------------------------------------

    # Doji not allowed
    if is_doji(break_candle) or is_doji(retrace_candle):
        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SS8",
            "reason": "Doji detected"
        }

    # Hammer not allowed
    if is_hammer(break_candle) or is_hammer(retrace_candle):
        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SS8",
            "reason": "Hammer detected"
        }

    # Big candle not allowed for retracement
    if is_big_candle(retrace_candle, df, len(df) - 2):
        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SS8",
            "reason": "Retracement candle is too big"
        }

    # --------------------------------------------------------
    # BUY SETUP
    # --------------------------------------------------------

    buy_score = 0
    buy_reasons = []

    # Buyer trend
    if trend == "BUYER_TREND":
        buy_score += 25
        buy_reasons.append("Buyer trend")

    # SNR resistance break
    if float(break_candle["Close"]) > resistance:
        buy_score += 25
        buy_reasons.append("SNR resistance broken")

    # Break candle bullish
    if break_info["bull"]:
        buy_score += 15
        buy_reasons.append("Bullish break candle")

    # Retracement
    if bullish_retracement(break_candle, retrace_candle):
        buy_score += 20
        buy_reasons.append("Retracement area")

    # Last candle bullish confirmation
    if last_info["bull"]:
        buy_score += 15
        buy_reasons.append("Bullish confirmation")

    # --------------------------------------------------------
    # SELL SETUP
    # --------------------------------------------------------

    sell_score = 0
    sell_reasons = []

    # Seller trend
    if trend == "SELLER_TREND":
        sell_score += 25
        sell_reasons.append("Seller trend")

    # SNR support break
    if float(break_candle["Close"]) < support:
        sell_score += 25
        sell_reasons.append("SNR support broken")

    # Break candle bearish
    if break_info["bear"]:
        sell_score += 15
        sell_reasons.append("Bearish break candle")

    # Retracement
    if bearish_retracement(break_candle, retrace_candle):
        sell_score += 20
        sell_reasons.append("Retracement area")

    # Last candle bearish confirmation
    if last_info["bear"]:
        sell_score += 15
        sell_reasons.append("Bearish confirmation")

    # --------------------------------------------------------
    # Final decision
    # --------------------------------------------------------

    if buy_score >= 70 and buy_score > sell_score:
        return {
            "signal": "BUY",
            "confidence": min(buy_score, 100),
            "strategy": "SS8",
            "reason": " + ".join(buy_reasons)
        }

    if sell_score >= 70 and sell_score > buy_score:
        return {
            "signal": "SELL",
            "confidence": min(sell_score, 100),
            "strategy": "SS8",
            "reason": " + ".join(sell_reasons)
        }

    return {
        "signal": "HOLD",
        "confidence": max(buy_score, sell_score),
        "strategy": "SS8",
        "reason": "SS8 conditions not fully confirmed"
    }


# ------------------------------------------------------------
# Simple function for main.py
# ------------------------------------------------------------

def get_signal(df):
    """
    main.py can directly call:

        result = get_signal(df)
    """

    return ss8_signal(df)


# ------------------------------------------------------------
# Test
# ------------------------------------------------------------

if __name__ == "__main__":

    print("SS8 Strategy Loaded Successfully")

    # Example:
    # df = pd.read_csv("candles.csv")
    # result = ss8_signal(df)
    # print(result)