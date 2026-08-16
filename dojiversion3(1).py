# dojiversion3.py
# Doji Version 3 Strategy
# BUY / SELL / HOLD

import pandas as pd
import numpy as np


# =========================================================
# SETTINGS
# =========================================================

EMA_FAST = 9
EMA_SLOW = 21

ATR_PERIOD = 14

# Doji body किती छोटा असावा
DOJI_BODY_RATIO = 0.25

# Big candle filter
BIG_CANDLE_ATR = 1.8

# SNR जवळ signal टाळण्यासाठी
SNR_ATR_DISTANCE = 0.25

# Trend strength
TREND_MIN_DISTANCE_ATR = 0.20


# =========================================================
# COLUMN CHECK
# =========================================================

def prepare_dataframe(df):
    """
    DataFrame मध्ये Open, High, Low, Close columns आहेत
    याची खात्री करते.
    """

    df = df.copy()

    # Column names standard करा
    rename_map = {}

    for col in df.columns:
        name = str(col).strip().lower()

        if name == "open":
            rename_map[col] = "Open"
        elif name == "high":
            rename_map[col] = "High"
        elif name == "low":
            rename_map[col] = "Low"
        elif name == "close":
            rename_map[col] = "Close"
        elif name == "volume":
            rename_map[col] = "Volume"

    df.rename(columns=rename_map, inplace=True)

    required = ["Open", "High", "Low", "Close"]

    for col in required:
        if col not in df.columns:
            raise ValueError(
                f"Missing column: {col}. "
                f"Required: Open, High, Low, Close"
            )

    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df.dropna(subset=required, inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df


# =========================================================
# ATR
# =========================================================

def calculate_atr(df, period=ATR_PERIOD):

    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    previous_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - previous_close).abs()
    tr3 = (low - previous_close).abs()

    true_range = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    atr = true_range.rolling(period).mean()

    return atr


# =========================================================
# EMA
# =========================================================

def calculate_ema(df):

    df["EMA_FAST"] = (
        df["Close"]
        .ewm(span=EMA_FAST, adjust=False)
        .mean()
    )

    df["EMA_SLOW"] = (
        df["Close"]
        .ewm(span=EMA_SLOW, adjust=False)
        .mean()
    )

    return df


# =========================================================
# CANDLE FUNCTIONS
# =========================================================

def candle_body(candle):

    return abs(
        candle["Close"] - candle["Open"]
    )


def candle_range(candle):

    return (
        candle["High"] - candle["Low"]
    )


def upper_wick(candle):

    return (
        candle["High"]
        - max(candle["Open"], candle["Close"])
    )


def lower_wick(candle):

    return (
        min(candle["Open"], candle["Close"])
        - candle["Low"]
    )


# =========================================================
# DOJI
# =========================================================

def is_doji(candle):

    rng = candle_range(candle)

    if rng <= 0:
        return False

    body = candle_body(candle)

    return body <= rng * DOJI_BODY_RATIO


# =========================================================
# HAMMER
# =========================================================

def is_hammer(candle):

    rng = candle_range(candle)

    if rng <= 0:
        return False

    body = candle_body(candle)

    upper = upper_wick(candle)
    lower = lower_wick(candle)

    # body फार मोठा नसावा
    if body > rng * 0.45:
        return False

    # lower wick मोठा
    if lower >= body * 2 and lower >= upper * 1.3:
        return True

    return False


# =========================================================
# INVERTED HAMMER
# =========================================================

def is_inverted_hammer(candle):

    rng = candle_range(candle)

    if rng <= 0:
        return False

    body = candle_body(candle)

    upper = upper_wick(candle)
    lower = lower_wick(candle)

    if body > rng * 0.45:
        return False

    if upper >= body * 2 and upper >= lower * 1.3:
        return True

    return False


# =========================================================
# BIG CANDLE
# =========================================================

def is_big_candle(df, index):

    if index < 1:
        return False

    atr = df["ATR"].iloc[index]

    if pd.isna(atr) or atr <= 0:
        return False

    candle_range_value = (
        df["High"].iloc[index]
        - df["Low"].iloc[index]
    )

    return candle_range_value >= (
        atr * BIG_CANDLE_ATR
    )


# =========================================================
# CANDLE DIRECTION
# =========================================================

def is_green(candle):

    return candle["Close"] > candle["Open"]


def is_red(candle):

    return candle["Close"] < candle["Open"]


# =========================================================
# TREND DETECTION
# =========================================================

def market_trend(df):

    if len(df) < EMA_SLOW + 5:
        return "UNKNOWN"

    last = df.iloc[-1]

    atr = last["ATR"]

    if pd.isna(atr) or atr <= 0:
        return "UNKNOWN"

    ema_fast = last["EMA_FAST"]
    ema_slow = last["EMA_SLOW"]

    distance = abs(
        ema_fast - ema_slow
    )

    # BUYERS TREND
    if (
        ema_fast > ema_slow
        and distance >= atr * TREND_MIN_DISTANCE_ATR
    ):
        return "BUYERS"

    # SELLERS TREND
    if (
        ema_fast < ema_slow
        and distance >= atr * TREND_MIN_DISTANCE_ATR
    ):
        return "SELLERS"

    # Otherwise ranging
    return "RANGING"


# =========================================================
# SNR DETECTION
# =========================================================

def find_snr_levels(df, lookback=20):

    if len(df) < lookback:
        lookback = len(df)

    recent = df.tail(lookback)

    resistance = recent["High"].max()
    support = recent["Low"].min()

    return support, resistance


def near_snr(df, index):

    if index < 5:
        return False

    atr = df["ATR"].iloc[index]

    if pd.isna(atr) or atr <= 0:
        return False

    support, resistance = find_snr_levels(
        df.iloc[:index + 1]
    )

    close = df["Close"].iloc[index]

    distance_support = abs(
        close - support
    )

    distance_resistance = abs(
        close - resistance
    )

    limit = atr * SNR_ATR_DISTANCE

    if distance_support <= limit:
        return True

    if distance_resistance <= limit:
        return True

    return False


# =========================================================
# PRECAUTION CHECK
# =========================================================

def precaution_failed(df, index):

    if index < 2:
        return True, "Not enough candles"

    current = df.iloc[index]

    # Doji स्वतः current candle असावा
    if not is_doji(current):
        return True, "Current candle is not Doji"

    # फोटोतील rule:
    # Doji नंतर/पुढील candle big नसावा.
    # Signal current closed candle वर तयार करताना
    # previous candle तपासतो.

    previous = df.iloc[index - 1]

    # Previous candle abnormal big असल्यास avoid
    if is_big_candle(df, index - 1):
        return True, "Previous candle is BIG"

    # Hammer / inverted hammer precaution
    if is_hammer(previous):
        return True, "Previous candle is Hammer"

    if is_inverted_hammer(previous):
        return True, "Previous candle is Inverted Hammer"

    # SNR जवळ signal avoid
    if near_snr(df, index):
        return True, "Near SNR"

    return False, "OK"


# =========================================================
# DOJI V3 CORE
# =========================================================

def doji_version3(df):

    df = prepare_dataframe(df)

    minimum = EMA_SLOW + ATR_PERIOD + 5

    if len(df) < minimum:
        return {
            "signal": "HOLD",
            "reason": "Not enough candles",
            "market": "UNKNOWN"
        }

    df["ATR"] = calculate_atr(df)

    df = calculate_ema(df)

    index = len(df) - 1

    current = df.iloc[index]

    # -----------------------------------------------------
    # Current candle Doji आहे का?
    # -----------------------------------------------------

    if not is_doji(current):

        return {
            "signal": "HOLD",
            "reason": "No Doji",
            "market": market_trend(df)
        }

    # -----------------------------------------------------
    # Precautions
    # -----------------------------------------------------

    failed, reason = precaution_failed(
        df,
        index
    )

    if failed:

        return {
            "signal": "HOLD",
            "reason": reason,
            "market": market_trend(df)
        }

    # -----------------------------------------------------
    # Market condition
    # -----------------------------------------------------

    trend = market_trend(df)

    # =====================================================
    # TRENDING MARKET
    # =====================================================

    if trend == "BUYERS":

        # Doji in buyers trend
        # Continuation = BUY

        return {
            "signal": "BUY",
            "reason": "Doji + Buyers Trend = Continuation",
            "market": "BUYERS"
        }

    if trend == "SELLERS":

        # Doji in sellers trend
        # Continuation = SELL

        return {
            "signal": "SELL",
            "reason": "Doji + Sellers Trend = Continuation",
            "market": "SELLERS"
        }

    # =====================================================
    # RANGING MARKET
    # =====================================================

    if trend == "RANGING":

        support, resistance = find_snr_levels(df)

        close = current["Close"]
        atr = current["ATR"]

        # -------------------------------------------------
        # Upper range / sellers area
        # -------------------------------------------------

        upper_distance = abs(
            resistance - close
        )

        # -------------------------------------------------
        # Lower range / buyers area
        # -------------------------------------------------

        lower_distance = abs(
            close - support
        )

        range_limit = atr * 2.0

        # Doji near resistance
        # Reversal = SELL

        if upper_distance <= range_limit:

            return {
                "signal": "SELL",
                "reason": (
                    "Ranging Market + "
                    "Doji at Sellers Area = Reversal"
                ),
                "market": "RANGING"
            }

        # Doji near support
        # Reversal = BUY

        if lower_distance <= range_limit:

            return {
                "signal": "BUY",
                "reason": (
                    "Ranging Market + "
                    "Doji at Buyers Area = Reversal"
                ),
                "market": "RANGING"
            }

        return {
            "signal": "HOLD",
            "reason": (
                "Ranging Market but Doji "
                "not at clear area"
            ),
            "market": "RANGING"
        }

    # =====================================================
    # UNKNOWN
    # =====================================================

    return {
        "signal": "HOLD",
        "reason": "Market condition unknown",
        "market": "UNKNOWN"
    }


# =========================================================
# MAIN SIGNAL FUNCTION
# =========================================================

def signal(df):

    result = doji_version3(df)

    return result["signal"]


# =========================================================
# DETAILED SIGNAL
# =========================================================

def get_signal_details(df):

    return doji_version3(df)


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    print("====================================")
    print("      DOJI VERSION 3 STRATEGY")
    print("====================================")

    # Example data
    data = {
        "Open": [
            100, 101, 102, 103, 104,
            105, 106, 107, 108, 109,
            110, 111, 112, 113, 114,
            115, 116, 117, 118, 119,
            120, 121, 122, 123, 124,
            125, 126, 127, 128, 129
        ],

        "High": [
            102, 103, 104, 105, 106,
            107, 108, 109, 110, 111,
            112, 113, 114, 115, 116,
            117, 118, 119, 120, 121,
            122, 123, 124, 125, 126,
            127, 128, 129, 130, 131
        ],

        "Low": [
            99, 100, 101, 102, 103,
            104, 105, 106, 107, 108,
            109, 110, 111, 112, 113,
            114, 115, 116, 117, 118,
            119, 120, 121, 122, 123,
            124, 125, 126, 127, 128
        ],

        "Close": [
            101, 102, 103, 104, 105,
            106, 107, 108, 109, 110,
            111, 112, 113, 114, 115,
            116, 117, 118, 119, 120,
            121, 122, 123, 124, 125,
            126, 127, 128, 129, 130
        ]
    }

    test_df = pd.DataFrame(data)

    result = get_signal_details(test_df)

    print()
    print("Signal :", result["signal"])
    print("Market :", result["market"])
    print("Reason :", result["reason"])
    print()
    print("====================================")