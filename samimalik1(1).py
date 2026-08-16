# ============================================================
# samimalik1.py
# Sure Shot Sami Malik 1
# ============================================================

import pandas as pd


# ============================================================
# CANDLE FUNCTIONS
# ============================================================

def direction(c):
    if c["Close"] > c["Open"]:
        return "GREEN"
    elif c["Close"] < c["Open"]:
        return "RED"
    return "DOJI"


def candle_range(c):
    return float(c["High"] - c["Low"])


def body(c):
    return abs(float(c["Close"] - c["Open"]))


def upper_wick(c):
    return float(
        c["High"] - max(c["Open"], c["Close"])
    )


def lower_wick(c):
    return float(
        min(c["Open"], c["Close"]) - c["Low"]
    )


# ============================================================
# HAMMER
# ============================================================

def is_hammer(c):

    b = body(c)

    if b <= 0:
        return False

    lower = lower_wick(c)
    upper = upper_wick(c)

    return (
        lower >= b * 2
        and upper <= b
    )


def is_inverted_hammer(c):

    b = body(c)

    if b <= 0:
        return False

    upper = upper_wick(c)
    lower = lower_wick(c)

    return (
        upper >= b * 2
        and lower <= b
    )


# ============================================================
# HEALTHY CANDLE
# ============================================================

def average_range(df, lookback=20):

    if len(df) < 2:
        return 0

    ranges = (
        df["High"].astype(float)
        - df["Low"].astype(float)
    )

    return float(
        ranges.tail(lookback).mean()
    )


def is_healthy_candle(df, index):

    c = df.iloc[index]

    r = candle_range(c)
    b = body(c)

    avg = average_range(df)

    if r <= 0 or avg <= 0:
        return False

    # Healthy candle:
    # ना खूप छोटी, ना abnormal मोठी
    if r < avg * 0.60:
        return False

    if r > avg * 1.80:
        return False

    # Body meaningful असावी
    if b < r * 0.40:
        return False

    return True


# ============================================================
# BIG CANDLE
# ============================================================

def is_big_candle(df, index):

    avg = average_range(df)

    if avg <= 0:
        return False

    r = candle_range(df.iloc[index])

    return r >= avg * 1.80


# ============================================================
# RANGING MARKET
# ============================================================

def is_ranging_market(df, lookback=12):

    if len(df) < lookback:
        return False

    recent = df.tail(lookback)

    high = float(recent["High"].max())
    low = float(recent["Low"].min())

    total_range = high - low

    avg = average_range(recent)

    if avg <= 0:
        return False

    ratio = total_range / avg

    # Tight / controlled range
    return ratio <= 9


# ============================================================
# RETRACEMENT AREA
# ============================================================

def is_retracement_area(df, lookback=8):

    if len(df) < lookback:
        return False

    recent = df.tail(lookback)

    green = 0
    red = 0

    for _, c in recent.iterrows():

        d = direction(c)

        if d == "GREEN":
            green += 1

        elif d == "RED":
            red += 1

    # Market मध्ये pullback / mixed candles
    if green >= 2 and red >= 2:
        return True

    return False


# ============================================================
# SNR FILTER
# ============================================================

def near_snr(
    price,
    snr_levels=None,
    tolerance=0.0015
):

    if not snr_levels:
        return False

    for level in snr_levels:

        try:
            level = float(level)
        except:
            continue

        if level == 0:
            continue

        distance = abs(
            price - level
        ) / level

        if distance <= tolerance:
            return True

    return False


# ============================================================
# BUYER PATTERN
# ============================================================

def buyer_pattern(df):

    if len(df) < 5:
        return False

    # Structure:
    #
    # Green candles
    #        ↓
    # Red Hammer
    #        ↓
    # Big / Healthy candle
    #        ↓
    # Red candle = reversal entry

    c1 = df.iloc[-5]
    c2 = df.iloc[-4]
    c3 = df.iloc[-3]
    c4 = df.iloc[-2]
    c5 = df.iloc[-1]

    # Previous green candles
    previous_green = (
        direction(c1) == "GREEN"
        and direction(c2) == "GREEN"
    )

    # Hammer
    hammer = is_hammer(c3)

    # Big OR healthy candle
    strong = (
        is_big_candle(df, -2)
        or
        is_healthy_candle(df, -2)
    )

    # Last candle red
    last_red = (
        direction(c5) == "RED"
    )

    return (
        previous_green
        and hammer
        and strong
        and last_red
    )


# ============================================================
# SELLER PATTERN
# ============================================================

def seller_pattern(df):

    if len(df) < 5:
        return False

    # Structure:
    #
    # Red candles
    #       ↓
    # Green Hammer
    #       ↓
    # Big / Healthy candle
    #       ↓
    # Green candle = reversal entry

    c1 = df.iloc[-5]
    c2 = df.iloc[-4]
    c3 = df.iloc[-3]
    c4 = df.iloc[-2]
    c5 = df.iloc[-1]

    # Previous red candles
    previous_red = (
        direction(c1) == "RED"
        and direction(c2) == "RED"
    )

    # Green hammer
    hammer = (
        direction(c3) == "GREEN"
        and is_hammer(c3)
    )

    # Big OR healthy
    strong = (
        is_big_candle(df, -2)
        or
        is_healthy_candle(df, -2)
    )

    # Last green candle
    last_green = (
        direction(c5) == "GREEN"
    )

    return (
        previous_red
        and hammer
        and strong
        and last_green
    )


# ============================================================
# BUY CONFIDENCE
# ============================================================

def buy_confidence(
    df,
    snr_levels=None
):

    score = 0

    c1 = df.iloc[-5]
    c2 = df.iloc[-4]
    c3 = df.iloc[-3]
    c4 = df.iloc[-2]
    c5 = df.iloc[-1]

    # Previous green candles
    if direction(c1) == "GREEN":
        score += 10

    if direction(c2) == "GREEN":
        score += 10

    # Hammer
    if is_hammer(c3):
        score += 25

    # Strong candle
    if is_big_candle(df, -2):
        score += 15

    elif is_healthy_candle(df, -2):
        score += 15

    # Last red candle
    if direction(c5) == "RED":
        score += 15

    # Ranging
    if is_ranging_market(df):
        score += 10

    # Retracement
    if is_retracement_area(df):
        score += 10

    # SNR safe
    if not near_snr(
        float(c5["Close"]),
        snr_levels
    ):
        score += 5

    return min(score, 100)


# ============================================================
# SELL CONFIDENCE
# ============================================================

def sell_confidence(
    df,
    snr_levels=None
):

    score = 0

    c1 = df.iloc[-5]
    c2 = df.iloc[-4]
    c3 = df.iloc[-3]
    c4 = df.iloc[-2]
    c5 = df.iloc[-1]

    # Previous red candles
    if direction(c1) == "RED":
        score += 10

    if direction(c2) == "RED":
        score += 10

    # Green hammer
    if (
        direction(c3) == "GREEN"
        and is_hammer(c3)
    ):
        score += 25

    # Strong candle
    if is_big_candle(df, -2):
        score += 15

    elif is_healthy_candle(df, -2):
        score += 15

    # Last green
    if direction(c5) == "GREEN":
        score += 15

    # Ranging
    if is_ranging_market(df):
        score += 10

    # Retracement
    if is_retracement_area(df):
        score += 10

    # SNR safe
    if not near_snr(
        float(c5["Close"]),
        snr_levels
    ):
        score += 5

    return min(score, 100)


# ============================================================
# MAIN ANALYZER
# ============================================================

def analyze_samimalik1(
    df,
    snr_levels=None
):

    # --------------------------------------------------------
    # DATA CHECK
    # --------------------------------------------------------

    if df is None:

        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SAMI MALIK 1",
            "reason": "No data"
        }

    if len(df) < 20:

        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SAMI MALIK 1",
            "reason": "Minimum 20 candles required"
        }

    required = [
        "Open",
        "High",
        "Low",
        "Close"
    ]

    for col in required:

        if col not in df.columns:

            return {
                "signal": "HOLD",
                "confidence": 0,
                "strategy": "SAMI MALIK 1",
                "reason": f"Missing column: {col}"
            }

    data = df.copy()

    # Numeric conversion
    for col in required:

        data[col] = pd.to_numeric(
            data[col],
            errors="coerce"
        )

    data = data.dropna(
        subset=required
    ).reset_index(drop=True)

    if len(data) < 20:

        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SAMI MALIK 1",
            "reason": "Invalid candle data"
        }

    # --------------------------------------------------------
    # MARKET CONDITION
    # --------------------------------------------------------

    if not is_ranging_market(data):

        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SAMI MALIK 1",
            "reason": "Ranging market not confirmed"
        }

    # --------------------------------------------------------
    # RETRACEMENT
    # --------------------------------------------------------

    if not is_retracement_area(data):

        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SAMI MALIK 1",
            "reason": "Retracement area not confirmed"
        }

    # --------------------------------------------------------
    # SNR FILTER
    # --------------------------------------------------------

    last_price = float(
        data.iloc[-1]["Close"]
    )

    if near_snr(
        last_price,
        snr_levels
    ):

        return {
            "signal": "HOLD",
            "confidence": 0,
            "strategy": "SAMI MALIK 1",
            "reason": "SNR area - signal rejected"
        }

    # --------------------------------------------------------
    # BUY
    # --------------------------------------------------------

    buy = buyer_pattern(data)

    # --------------------------------------------------------
    # SELL
    # --------------------------------------------------------

    sell = seller_pattern(data)

    # --------------------------------------------------------
    # BUY RESULT
    # --------------------------------------------------------

    if buy and not sell:

        confidence = buy_confidence(
            data,
            snr_levels
        )

        return {
            "signal": "BUY",
            "confidence": confidence,
            "strategy": "SAMI MALIK 1",
            "reason": (
                "Green candles + hammer + "
                "big/healthy candle + "
                "red reversal candle"
            )
        }

    # --------------------------------------------------------
    # SELL RESULT
    # --------------------------------------------------------

    if sell and not buy:

        confidence = sell_confidence(
            data,
            snr_levels
        )

        return {
            "signal": "SELL",
            "confidence": confidence,
            "strategy": "SAMI MALIK 1",
            "reason": (
                "Red candles + green hammer + "
                "big/healthy candle + "
                "green reversal candle"
            )
        }

    # --------------------------------------------------------
    # NO SIGNAL
    # --------------------------------------------------------

    return {
        "signal": "HOLD",
        "confidence": 0,
        "strategy": "SAMI MALIK 1",
        "reason": "Pattern not confirmed"
    }


# ============================================================
# SHORT FUNCTION FOR MAIN.PY
# ============================================================

def signal(df, snr_levels=None):

    return analyze_samimalik1(
        df,
        snr_levels
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("===================================")
    print("   SURE SHOT SAMI MALIK 1")
    print("===================================")
    print()
    print("Strategy loaded successfully.")
    print()
    print("Use:")
    print()
    print("result = signal(df)")
    print()
    print("Result:")
    print("Signal      :", "BUY / SELL / HOLD")
    print("Confidence  :", "0 - 100%")
    print("===================================")