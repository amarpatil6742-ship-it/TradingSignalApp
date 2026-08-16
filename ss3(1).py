# ============================================================
# ss3.py
# Sure Shot 3 - FFLC Strategy
# ============================================================

import pandas as pd


# ------------------------------------------------------------
# Candle helpers
# ------------------------------------------------------------

def is_green(candle):
    return candle["Close"] > candle["Open"]


def is_red(candle):
    return candle["Close"] < candle["Open"]


def candle_body(candle):
    return abs(candle["Close"] - candle["Open"])


# ------------------------------------------------------------
# FFLC BUY
#
# Rule from notebook:
# 1. Market should be trending upward
# 2. There should be several green candles
# 3. One red candle appears
# 4. Next green candle completely crosses the previous red candle
# 5. Signal is BUY for the NEXT green candle
# ------------------------------------------------------------

def bullish_fflc(df, min_green=3):

    if len(df) < min_green + 3:
        return False

    # Previous candles before the red candle
    red_index = len(df) - 2
    green_confirm_index = len(df) - 1

    red = df.iloc[red_index]
    confirm = df.iloc[green_confirm_index]

    # The candle before red
    before_red = df.iloc[red_index - min_green:red_index]

    # --------------------------------------------------------
    # 1. Previous candles must be green
    # --------------------------------------------------------

    green_count = sum(
        is_green(before_red.iloc[i])
        for i in range(len(before_red))
    )

    if green_count < min_green:
        return False

    # --------------------------------------------------------
    # 2. Middle candle must be RED
    # --------------------------------------------------------

    if not is_red(red):
        return False

    # --------------------------------------------------------
    # 3. Confirmation candle must be GREEN
    # --------------------------------------------------------

    if not is_green(confirm):
        return False

    # --------------------------------------------------------
    # 4. Green confirmation candle must completely cross
    #    previous red candle
    #
    # Red candle:
    #     Open > Close
    #
    # Green candle:
    #     Open < Close
    #
    # Complete body crossing:
    #     green Open <= red Close
    #     green Close >= red Open
    # --------------------------------------------------------

    complete_cross = (
        confirm["Open"] <= red["Close"]
        and
        confirm["Close"] >= red["Open"]
    )

    if not complete_cross:
        return False

    return True


# ------------------------------------------------------------
# FFLC SELL
#
# Rule:
# 1. Market should be trending downward
# 2. Several red candles
# 3. One green candle appears
# 4. Next red candle completely crosses previous green candle
# 5. Signal = SELL for NEXT red candle
# ------------------------------------------------------------

def bearish_fflc(df, min_red=3):

    if len(df) < min_red + 3:
        return False

    green_index = len(df) - 2
    confirm_index = len(df) - 1

    green = df.iloc[green_index]
    confirm = df.iloc[confirm_index]

    # Candles before green candle
    before_green = df.iloc[green_index - min_red:green_index]

    # --------------------------------------------------------
    # 1. Previous candles must be RED
    # --------------------------------------------------------

    red_count = sum(
        is_red(before_green.iloc[i])
        for i in range(len(before_green))
    )

    if red_count < min_red:
        return False

    # --------------------------------------------------------
    # 2. Middle candle must be GREEN
    # --------------------------------------------------------

    if not is_green(green):
        return False

    # --------------------------------------------------------
    # 3. Confirmation candle must be RED
    # --------------------------------------------------------

    if not is_red(confirm):
        return False

    # --------------------------------------------------------
    # 4. Red confirmation candle completely crosses
    #    previous green candle
    #
    # Green candle:
    #     Open < Close
    #
    # Red candle:
    #     Open > Close
    #
    # Complete body crossing:
    #     red Open >= green Close
    #     red Close <= green Open
    # --------------------------------------------------------

    complete_cross = (
        confirm["Open"] >= green["Close"]
        and
        confirm["Close"] <= green["Open"]
    )

    if not complete_cross:
        return False

    return True


# ------------------------------------------------------------
# Main signal function
# ------------------------------------------------------------

def signal(df):

    if df is None or len(df) < 6:
        return "HOLD"

    # Make sure OHLC columns are numeric
    required = ["Open", "High", "Low", "Close"]

    for col in required:
        if col not in df.columns:
            raise ValueError(
                f"Missing column: {col}"
            )

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    df = df.dropna(subset=required).reset_index(drop=True)

    if len(df) < 6:
        return "HOLD"

    # --------------------------------------------------------
    # BUY
    # --------------------------------------------------------

    if bullish_fflc(df, min_green=3):
        return "BUY"

    # --------------------------------------------------------
    # SELL
    # --------------------------------------------------------

    if bearish_fflc(df, min_red=3):
        return "SELL"

    # --------------------------------------------------------
    # No setup
    # --------------------------------------------------------

    return "HOLD"


# ------------------------------------------------------------
# Detailed signal
# ------------------------------------------------------------

def get_signal(df):

    result = signal(df)

    if result == "BUY":
        return {
            "signal": "BUY",
            "strategy": "SS3-FFLC",
            "reason": "Bullish FFLC continuation"
        }

    if result == "SELL":
        return {
            "signal": "SELL",
            "strategy": "SS3-FFLC",
            "reason": "Bearish FFLC continuation"
        }

    return {
        "signal": "HOLD",
        "strategy": "SS3-FFLC",
        "reason": "No valid FFLC setup"
    }


# ------------------------------------------------------------
# Test
# ------------------------------------------------------------

if __name__ == "__main__":

    data = {
        "Open":  [
            100, 102, 104, 106,
            108, 106, 111
        ],

        "High":  [
            103, 105, 107, 109,
            110, 112, 113
        ],

        "Low":   [
            99, 101, 103, 105,
            107, 105, 105
        ],

        "Close": [
            102, 104, 106, 108,
            109, 107, 112
        ]
    }

    df = pd.DataFrame(data)

    print("--------------------------------")
    print("SS3 - FFLC STRATEGY")
    print("--------------------------------")

    print("Signal:", signal(df))
    print("Details:", get_signal(df))