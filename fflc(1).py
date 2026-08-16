# ============================================================
# fflc.py
# FFLC - Full Fill Last Candle Strategy
# ============================================================

import pandas as pd


# ============================================================
# SETTINGS
# ============================================================

MIN_CANDLES = 20

# SNR जवळ candle आहे असे मानण्यासाठी tolerance
SNR_TOLERANCE = 0.0015

# Full-fill किती प्रमाणात झाले पाहिजे
FILL_TOLERANCE = 0.0005


# ============================================================
# CANDLE COLOR
# ============================================================

def candle_color(candle):
    if candle["Close"] > candle["Open"]:
        return "GREEN"

    elif candle["Close"] < candle["Open"]:
        return "RED"

    return "DOJI"


# ============================================================
# CANDLE RANGE
# ============================================================

def candle_range(candle):
    return float(candle["High"] - candle["Low"])


# ============================================================
# CANDLE BODY
# ============================================================

def candle_body(candle):
    return abs(
        float(candle["Close"] - candle["Open"])
    )


# ============================================================
# LONELY CANDLE
# ============================================================

def is_lonely_candle(df, index):
    """
    Lonely candle म्हणजे setup मधील स्वतंत्र
    reversal/reference candle.

    येथे आसपासच्या candles पेक्षा body/range
    स्पष्टपणे वेगळी आहे का ते तपासले जाते.
    """

    if index < 2 or index + 2 >= len(df):
        return False

    current = df.iloc[index]

    current_range = candle_range(current)

    if current_range <= 0:
        return False

    before_1 = candle_range(df.iloc[index - 1])
    before_2 = candle_range(df.iloc[index - 2])

    after_1 = candle_range(df.iloc[index + 1])
    after_2 = candle_range(df.iloc[index + 2])

    average_neighbours = (
        before_1 +
        before_2 +
        after_1 +
        after_2
    ) / 4

    # अत्यंत मोठी candle नको
    if current_range > average_neighbours * 2.5:
        return False

    return True


# ============================================================
# FULL FILL - BULLISH
# ============================================================

def bullish_full_fill(previous_candle, last_candle):
    """
    Previous RED candle ला last GREEN candle
    पूर्णपणे cover/cross करते का?
    """

    previous_open = float(previous_candle["Open"])
    previous_close = float(previous_candle["Close"])

    last_open = float(last_candle["Open"])
    last_close = float(last_candle["Close"])

    # Previous candle RED असावी
    if previous_close >= previous_open:
        return False

    # Last candle GREEN असावी
    if last_close <= last_open:
        return False

    # Full body fill / cross
    if (
        last_open <= previous_close + abs(previous_close) * FILL_TOLERANCE
        and
        last_close >= previous_open - abs(previous_open) * FILL_TOLERANCE
    ):
        return True

    return False


# ============================================================
# FULL FILL - BEARISH
# ============================================================

def bearish_full_fill(previous_candle, last_candle):
    """
    Previous GREEN candle ला last RED candle
    पूर्णपणे cover/cross करते का?
    """

    previous_open = float(previous_candle["Open"])
    previous_close = float(previous_candle["Close"])

    last_open = float(last_candle["Open"])
    last_close = float(last_candle["Close"])

    # Previous candle GREEN असावी
    if previous_close <= previous_open:
        return False

    # Last candle RED असावी
    if last_close >= last_open:
        return False

    # Full body fill / cross
    if (
        last_open >= previous_close - abs(previous_close) * FILL_TOLERANCE
        and
        last_close <= previous_open + abs(previous_open) * FILL_TOLERANCE
    ):
        return True

    return False


# ============================================================
# SIMPLE SNR DETECTION
# ============================================================

def find_snr_levels(df, lookback=20):

    if len(df) < lookback:
        return None, None

    recent = df.iloc[-lookback:]

    resistance = float(recent["High"].max())
    support = float(recent["Low"].min())

    return support, resistance


# ============================================================
# PRICE NEAR SNR
# ============================================================

def is_near_snr(price, support, resistance):

    if support is None or resistance is None:
        return False

    support_distance = abs(price - support) / price
    resistance_distance = abs(price - resistance) / price

    if support_distance <= SNR_TOLERANCE:
        return True

    if resistance_distance <= SNR_TOLERANCE:
        return True

    return False


# ============================================================
# MARKET TREND
# ============================================================

def detect_trend(df, lookback=8):

    if len(df) < lookback:
        return "UNKNOWN"

    closes = df["Close"].astype(float)

    first = float(closes.iloc[-lookback])
    last = float(closes.iloc[-1])

    change = (last - first) / first

    if change > 0.001:
        return "BUYER"

    elif change < -0.001:
        return "SELLER"

    return "RANGING"


# ============================================================
# TREND STRUCTURE
# ============================================================

def bullish_structure(df):

    if len(df) < 5:
        return False

    highs = df["High"].astype(float).iloc[-5:]
    lows = df["Low"].astype(float).iloc[-5:]

    return (
        highs.iloc[-1] >= highs.iloc[-2]
        and
        lows.iloc[-1] >= lows.iloc[-2]
    )


def bearish_structure(df):

    if len(df) < 5:
        return False

    highs = df["High"].astype(float).iloc[-5:]
    lows = df["Low"].astype(float).iloc[-5:]

    return (
        highs.iloc[-1] <= highs.iloc[-2]
        and
        lows.iloc[-1] <= lows.iloc[-2]
    )


# ============================================================
# HAMMER FILTER
# ============================================================

def is_hammer(candle):

    high = float(candle["High"])
    low = float(candle["Low"])

    open_price = float(candle["Open"])
    close_price = float(candle["Close"])

    body = abs(close_price - open_price)
    total_range = high - low

    if total_range <= 0 or body <= 0:
        return False

    upper_wick = (
        high - max(open_price, close_price)
    )

    lower_wick = (
        min(open_price, close_price) - low
    )

    # Hammer
    if lower_wick >= body * 2 and upper_wick <= body:
        return True

    # Inverted hammer
    if upper_wick >= body * 2 and lower_wick <= body:
        return True

    return False


# ============================================================
# BIG CANDLE FILTER
# ============================================================

def is_big_candle(df, index):

    if index < 5:
        return False

    current_range = candle_range(df.iloc[index])

    old_ranges = []

    for i in range(index - 5, index):
        old_ranges.append(
            candle_range(df.iloc[i])
        )

    average_range = sum(old_ranges) / len(old_ranges)

    if average_range <= 0:
        return False

    return current_range > average_range * 2.5


# ============================================================
# FFLC MAIN STRATEGY
# ============================================================

def fflc_signal(df):

    # --------------------------------------------------------
    # Data check
    # --------------------------------------------------------

    required = [
        "Open",
        "High",
        "Low",
        "Close"
    ]

    for column in required:

        if column not in df.columns:

            return {
                "signal": "HOLD",
                "confidence": 0,
                "strategy": "FFLC",
                "reason": f"Missing column: {column}"
            }

    if len(df) < MIN_CANDLES:

        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "FFLC",
            "reason": "Not enough candles"
        }


    # --------------------------------------------------------
    # Copy data
    # --------------------------------------------------------

    df = df.copy().reset_index(drop=True)


    # --------------------------------------------------------
    # Important candles
    # --------------------------------------------------------

    lonely = df.iloc[-3]
    previous = df.iloc[-2]
    last = df.iloc[-1]


    # --------------------------------------------------------
    # Current candle should be closed before signal
    # --------------------------------------------------------

    last_color = candle_color(last)

    if last_color == "DOJI":

        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "FFLC",
            "reason": "Last candle is Doji"
        }


    # --------------------------------------------------------
    # Hammer precaution
    # --------------------------------------------------------

    if is_hammer(previous):

        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "FFLC",
            "reason": "Hammer detected - NO TRADE"
        }


    # --------------------------------------------------------
    # Big candle precaution
    # --------------------------------------------------------

    if is_big_candle(df, len(df) - 2):

        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "FFLC",
            "reason": "Big candle - NO TRADE"
        }


    # --------------------------------------------------------
    # SNR detection
    # --------------------------------------------------------

    support, resistance = find_snr_levels(
        df.iloc[:-3]
    )


    # Lonely candle SNR check
    lonely_price = float(lonely["Close"])

    if is_near_snr(
        lonely_price,
        support,
        resistance
    ):

        # Photo rule:
        # SNR area + lonely candle
        # setup is considered
        pass


    # --------------------------------------------------------
    # Market trend
    # --------------------------------------------------------

    trend = detect_trend(
        df.iloc[:-1]
    )


    # ========================================================
    # BUYER TREND
    # ========================================================

    if trend == "BUYER":

        # Photo rule:
        # Buyer friendly market
        # Last Full Fill candle RED
        # Next candle GREEN

        if (
            candle_color(previous) == "RED"
            and
            last_color == "GREEN"
        ):

            if bullish_full_fill(
                lonely,
                previous
            ):

                confidence = 75

                if bullish_structure(df.iloc[:-1]):
                    confidence += 10

                return {
                    "signal": "BUY",
                    "confidence": min(confidence, 90),
                    "strategy": "FFLC",
                    "reason": (
                        "Buyer trend + "
                        "Red Full-Fill candle + "
                        "Next Green candle"
                    )
                }


    # ========================================================
    # SELLER TREND
    # ========================================================

    if trend == "SELLER":

        # Photo rule:
        # Seller friendly market
        # Last Full Fill candle GREEN
        # Next candle RED

        if (
            candle_color(previous) == "GREEN"
            and
            last_color == "RED"
        ):

            if bearish_full_fill(
                lonely,
                previous
            ):

                confidence = 75

                if bearish_structure(df.iloc[:-1]):
                    confidence += 10

                return {
                    "signal": "SELL",
                    "confidence": min(confidence, 90),
                    "strategy": "FFLC",
                    "reason": (
                        "Seller trend + "
                        "Green Full-Fill candle + "
                        "Next Red candle"
                    )
                }


    # ========================================================
    # NO SETUP
    # ========================================================

    return {
        "signal": "HOLD",
        "confidence": 0,
        "strategy": "FFLC",
        "reason": "FFLC conditions not satisfied"
    }


# ============================================================
# SIMPLE FUNCTION FOR SIGNAL ENGINE
# ============================================================

def signal(df):

    result = fflc_signal(df)

    return result["signal"]


# ============================================================
# DETAILED SIGNAL
# ============================================================

def get_signal(df):

    return fflc_signal(df)


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 50)
    print("FFLC STRATEGY")
    print("Full Fill Last Candle")
    print("=" * 50)

    print()
    print("BUY RULE:")
    print("Buyer trend")
    print("+")
    print("Red Full Fill candle")
    print("+")
    print("Next Green candle")
    print("=" * 40)

    print()
    print("SELL RULE:")
    print("Seller trend")
    print("+")
    print("Green Full Fill candle")
    print("+")
    print("Next Red candle")
    print("=" * 40)

    print()
    print("Precautions:")
    print("1. SNR area check")
    print("2. Lonely candle")
    print("3. Big candle = NO TRADE")
    print("4. Hammer = NO TRADE")
    print("5. Invalid setup = HOLD")