# ss1.py
# Sure Shot 1 - Version 2
# Trend + Second Last Reversal + Last Short Tail
# Output: BUY / SELL / WAIT + Confidence

import pandas as pd


# =========================================================
# 1. CANDLE HELPERS
# =========================================================

def candle_body(c):
    return abs(float(c["Close"]) - float(c["Open"]))


def candle_range(c):
    return float(c["High"]) - float(c["Low"])


def upper_wick(c):
    return float(c["High"]) - max(float(c["Open"]), float(c["Close"]))


def lower_wick(c):
    return min(float(c["Open"]), float(c["Close"])) - float(c["Low"])


def is_bullish(c):
    return float(c["Close"]) > float(c["Open"])


def is_bearish(c):
    return float(c["Close"]) < float(c["Open"])


# =========================================================
# 2. EMA
# =========================================================

def add_ema(df):
    df = df.copy()

    df["EMA20"] = df["Close"].ewm(
        span=20,
        adjust=False
    ).mean()

    df["EMA50"] = df["Close"].ewm(
        span=50,
        adjust=False
    ).mean()

    return df


# =========================================================
# 3. TREND DETECTION
# =========================================================

def get_trend(df):

    if len(df) < 50:
        return "SIDEWAYS"

    last = df.iloc[-1]

    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])

    # Recent candles
    c1 = df.iloc[-5]
    c2 = df.iloc[-1]

    higher_high = float(c2["High"]) > float(c1["High"])
    higher_low = float(c2["Low"]) > float(c1["Low"])

    lower_high = float(c2["High"]) < float(c1["High"])
    lower_low = float(c2["Low"]) < float(c1["Low"])

    # BUY TREND
    if ema20 > ema50 and higher_high and higher_low:
        return "UP"

    # SELL TREND
    if ema20 < ema50 and lower_high and lower_low:
        return "DOWN"

    # EMA direction alone
    if ema20 > ema50:
        return "UP"

    if ema20 < ema50:
        return "DOWN"

    return "SIDEWAYS"


# =========================================================
# 4. FULL CANDLE
# =========================================================

def is_full_candle(c):

    body = candle_body(c)
    rng = candle_range(c)

    if rng <= 0:
        return True

    body_ratio = body / rng

    # Body >= 90% = Full candle
    return body_ratio >= 0.90


# =========================================================
# 5. HAMMER
# =========================================================

def is_hammer(c):

    body = candle_body(c)
    rng = candle_range(c)

    if rng <= 0 or body <= 0:
        return False

    upper = upper_wick(c)
    lower = lower_wick(c)

    # Hammer condition
    if lower > body * 2 and upper < body * 0.5:
        return True

    return False


# =========================================================
# 6. SHORT TAIL
# =========================================================

def is_short_tail(c):

    body = candle_body(c)
    rng = candle_range(c)

    if rng <= 0:
        return False

    upper = upper_wick(c)
    lower = lower_wick(c)

    # Both tails <= 30% of candle range
    upper_ratio = upper / rng
    lower_ratio = lower / rng

    if upper_ratio <= 0.30 and lower_ratio <= 0.30:
        return True

    return False


# =========================================================
# 7. REVERSAL CANDLE
# =========================================================

def is_bullish_reversal(df, index):

    if index < 1:
        return False

    c = df.iloc[index]
    prev = df.iloc[index - 1]

    # Basic bullish reversal
    if is_bullish(c) and is_bearish(prev):

        # Bullish engulfing
        engulfing = (
            float(c["Open"]) <= float(prev["Close"])
            and
            float(c["Close"]) >= float(prev["Open"])
        )

        # Strong bullish close
        body = candle_body(c)
        rng = candle_range(c)

        if rng > 0:
            body_ratio = body / rng
        else:
            body_ratio = 0

        if engulfing or body_ratio >= 0.50:
            return True

    return False


def is_bearish_reversal(df, index):

    if index < 1:
        return False

    c = df.iloc[index]
    prev = df.iloc[index - 1]

    # Basic bearish reversal
    if is_bearish(c) and is_bullish(prev):

        # Bearish engulfing
        engulfing = (
            float(c["Open"]) >= float(prev["Close"])
            and
            float(c["Close"]) <= float(prev["Open"])
        )

        # Strong bearish close
        body = candle_body(c)
        rng = candle_range(c)

        if rng > 0:
            body_ratio = body / rng
        else:
            body_ratio = 0

        if engulfing or body_ratio >= 0.50:
            return True

    return False


# =========================================================
# 8. SNR DETECTION
# =========================================================

def near_support_resistance(df, lookback=20):

    if len(df) < lookback + 1:
        return False

    current = df.iloc[-1]

    price = float(current["Close"])

    recent = df.iloc[-lookback:]

    support = float(recent["Low"].min())
    resistance = float(recent["High"].max())

    # 0.2% proximity
    support_distance = abs(price - support) / price
    resistance_distance = abs(price - resistance) / price

    if support_distance <= 0.002:
        return True

    if resistance_distance <= 0.002:
        return True

    return False


# =========================================================
# 9. FAKE BREAKOUT FILTER
# =========================================================

def fake_breakout(df):

    if len(df) < 20:
        return False

    recent = df.iloc[-20:-1]

    resistance = float(recent["High"].max())
    support = float(recent["Low"].min())

    last = df.iloc[-1]

    high = float(last["High"])
    low = float(last["Low"])
    close = float(last["Close"])

    # Break above resistance but close below it
    if high > resistance and close < resistance:
        return True

    # Break below support but close above it
    if low < support and close > support:
        return True

    return False


# =========================================================
# 10. CANDLE STRENGTH
# =========================================================

def candle_strength(c):

    body = candle_body(c)
    rng = candle_range(c)

    if rng <= 0:
        return 0

    strength = (body / rng) * 100

    return round(strength, 2)


# =========================================================
# 11. CONFIDENCE
# =========================================================

def calculate_confidence(
    trend,
    reversal,
    short_tail,
    full_candle,
    hammer,
    snr,
    fake_break
):

    confidence = 0

    # Trend
    if trend in ["UP", "DOWN"]:
        confidence += 25

    # Reversal
    if reversal:
        confidence += 25

    # Short tail
    if short_tail:
        confidence += 20

    # No full candle
    if not full_candle:
        confidence += 10

    # No hammer
    if not hammer:
        confidence += 10

    # No SNR
    if not snr:
        confidence += 5

    # No fake breakout
    if not fake_break:
        confidence += 5

    # Penalties
    if full_candle:
        confidence -= 20

    if hammer:
        confidence -= 20

    if snr:
        confidence -= 20

    if fake_break:
        confidence -= 20

    confidence = max(0, min(100, confidence))

    return int(confidence)


# =========================================================
# 12. MAIN SS1 STRATEGY
# =========================================================

def strategy_one(df):

    reasons = []

    # -----------------------------------------------------
    # DATA CHECK
    # -----------------------------------------------------

    if df is None:
        return {
            "strategy": "Sure Shot 1",
            "signal": "WAIT",
            "confidence": 0,
            "reasons": ["DataFrame not found"]
        }

    if len(df) < 60:
        return {
            "strategy": "Sure Shot 1",
            "signal": "WAIT",
            "confidence": 0,
            "reasons": [
                f"Need minimum 60 candles, available {len(df)}"
            ]
        }

    # -----------------------------------------------------
    # EMA
    # -----------------------------------------------------

    df = add_ema(df)

    # -----------------------------------------------------
    # TREND
    # -----------------------------------------------------

    trend = get_trend(df)

    if trend == "UP":
        reasons.append("UP trend detected")

    elif trend == "DOWN":
        reasons.append("DOWN trend detected")

    else:
        reasons.append("Sideways market")

        return {
            "strategy": "Sure Shot 1",
            "signal": "WAIT",
            "confidence": 0,
            "reasons": reasons
        }

    # -----------------------------------------------------
    # SECOND LAST CANDLE
    # -----------------------------------------------------

    second_last_index = len(df) - 2

    second_last = df.iloc[second_last_index]

    bullish_reversal = is_bullish_reversal(
        df,
        second_last_index
    )

    bearish_reversal = is_bearish_reversal(
        df,
        second_last_index
    )

    # -----------------------------------------------------
    # LAST CANDLE
    # -----------------------------------------------------

    last = df.iloc[-1]

    short_tail = is_short_tail(last)

    full_candle = is_full_candle(last)

    hammer = is_hammer(last)

    # -----------------------------------------------------
    # SNR
    # -----------------------------------------------------

    snr = near_support_resistance(df)

    # -----------------------------------------------------
    # FAKE BREAKOUT
    # -----------------------------------------------------

    fake_break = fake_breakout(df)

    # -----------------------------------------------------
    # BUY
    # -----------------------------------------------------

    buy_reversal = bullish_reversal
    buy_condition = (
        trend == "UP"
        and buy_reversal
        and short_tail
        and not full_candle
        and not hammer
        and not snr
        and not fake_break
    )

    # -----------------------------------------------------
    # SELL
    # -----------------------------------------------------

    sell_reversal = bearish_reversal
    sell_condition = (
        trend == "DOWN"
        and sell_reversal
        and short_tail
        and not full_candle
        and not hammer
        and not snr
        and not fake_break
    )

    # -----------------------------------------------------
    # CONFIDENCE
    # -----------------------------------------------------

    if buy_condition:

        confidence = calculate_confidence(
            trend="UP",
            reversal=True,
            short_tail=short_tail,
            full_candle=full_candle,
            hammer=hammer,
            snr=snr,
            fake_break=fake_break
        )

        reasons.append("Second-last bullish reversal")
        reasons.append("Last candle short-tail")
        reasons.append("No full candle")
        reasons.append("No hammer")
        reasons.append("No SNR")
        reasons.append("No fake breakout")

        return {
            "strategy": "Sure Shot 1",
            "signal": "BUY",
            "confidence": confidence,
            "reasons": reasons
        }

    # -----------------------------------------------------
    # SELL SIGNAL
    # -----------------------------------------------------

    if sell_condition:

        confidence = calculate_confidence(
            trend="DOWN",
            reversal=True,
            short_tail=short_tail,
            full_candle=full_candle,
            hammer=hammer,
            snr=snr,
            fake_break=fake_break
        )

        reasons.append("Second-last bearish reversal")
        reasons.append("Last candle short-tail")
        reasons.append("No full candle")
        reasons.append("No hammer")
        reasons.append("No SNR")
        reasons.append("No fake breakout")

        return {
            "strategy": "Sure Shot 1",
            "signal": "SELL",
            "confidence": confidence,
            "reasons": reasons
        }

    # -----------------------------------------------------
    # WAIT REASONS
    # -----------------------------------------------------

    if not short_tail:
        reasons.append("Last candle does not have short tail")

    if full_candle:
        reasons.append("Full candle detected")

    if hammer:
        reasons.append("Hammer detected")

    if snr:
        reasons.append("SNR area detected")

    if fake_break:
        reasons.append("Possible fake breakout")

    if trend == "UP" and not bullish_reversal:
        reasons.append("Bullish reversal not confirmed")

    if trend == "DOWN" and not bearish_reversal:
        reasons.append("Bearish reversal not confirmed")

    confidence = calculate_confidence(
        trend=trend,
        reversal=(
            bullish_reversal
            if trend == "UP"
            else bearish_reversal
        ),
        short_tail=short_tail,
        full_candle=full_candle,
        hammer=hammer,
        snr=snr,
        fake_break=fake_break
    )

    # -----------------------------------------------------
    # FINAL WAIT
    # -----------------------------------------------------

    return {
        "strategy": "Sure Shot 1",
        "signal": "WAIT",
        "confidence": confidence,
        "reasons": reasons
    }


# =========================================================
# 13. SIMPLE SIGNAL FUNCTION
# =========================================================

def signal(df):

    result = strategy_one(df)

    return result


# =========================================================
# 14. TEST
# =========================================================

if __name__ == "__main__":

    print("------------------------------------")
    print("Sure Shot 1 - Version 2")
    print("------------------------------------")
    print("Waiting for candle DataFrame...")
    print("Use: signal(df)")