# ss6.py
# Sure Shot 6 - Ranging Market + Hammer + SNR Reversal
# Signal only - NO automatic order execution

import pandas as pd


# ============================================================
# 1. DATA CHECK
# ============================================================

def _prepare_df(df):
    """
    Required columns:
    Open, High, Low, Close

    Column names can be lower/upper case.
    """

    if df is None or len(df) < 10:
        return None

    data = df.copy()

    # Normalize column names
    rename = {}

    for col in data.columns:
        name = str(col).strip().lower()

        if name == "open":
            rename[col] = "Open"
        elif name == "high":
            rename[col] = "High"
        elif name == "low":
            rename[col] = "Low"
        elif name == "close":
            rename[col] = "Close"

    data.rename(columns=rename, inplace=True)

    required = ["Open", "High", "Low", "Close"]

    for col in required:
        if col not in data.columns:
            return None

    for col in required:
        data[col] = pd.to_numeric(
            data[col],
            errors="coerce"
        )

    data.dropna(
        subset=required,
        inplace=True
    )

    if len(data) < 10:
        return None

    data.reset_index(drop=True, inplace=True)

    return data


# ============================================================
# 2. CANDLE FUNCTIONS
# ============================================================

def candle_body(c):
    return abs(c["Close"] - c["Open"])


def candle_range(c):
    return c["High"] - c["Low"]


def upper_wick(c):
    return c["High"] - max(c["Open"], c["Close"])


def lower_wick(c):
    return min(c["Open"], c["Close"]) - c["Low"]


def is_green(c):
    return c["Close"] > c["Open"]


def is_red(c):
    return c["Close"] < c["Open"]


# ============================================================
# 3. HAMMER
# ============================================================

def is_hammer(c):
    """
    Normal hammer:
    - small body
    - long lower wick
    - small upper wick
    """

    rng = candle_range(c)
    body = candle_body(c)

    if rng <= 0:
        return False

    lw = lower_wick(c)
    uw = upper_wick(c)

    # Very small body is allowed
    if body > rng * 0.45:
        return False

    # Lower wick should be strong
    if lw < body * 1.5:
        return False

    # Upper wick should be relatively small
    if uw > body * 1.2:
        return False

    return True


def is_inverted_hammer(c):
    """
    Inverted hammer / shooting-star type candle.
    Used for the opposite-side reversal check.
    """

    rng = candle_range(c)
    body = candle_body(c)

    if rng <= 0:
        return False

    uw = upper_wick(c)
    lw = lower_wick(c)

    if body > rng * 0.45:
        return False

    if uw < body * 1.5:
        return False

    if lw > body * 1.2:
        return False

    return True


# ============================================================
# 4. ABNORMAL / BIG CANDLE FILTER
# ============================================================

def is_big_candle(df, index, lookback=10, multiplier=1.8):
    """
    Reject unusually large candles.
    """

    if index < 1:
        return False

    current_range = candle_range(df.iloc[index])

    if current_range <= 0:
        return True

    start = max(0, index - lookback)

    ranges = []

    for i in range(start, index):
        r = candle_range(df.iloc[i])

        if r > 0:
            ranges.append(r)

    if len(ranges) < 3:
        return False

    avg_range = sum(ranges) / len(ranges)

    return current_range > avg_range * multiplier


# ============================================================
# 5. RANGING MARKET
# ============================================================

def is_ranging_market(df, lookback=12):
    """
    Simple range-market filter.

    Price should remain inside a relatively narrow area.
    """

    if len(df) < lookback:
        return False

    recent = df.iloc[-lookback:]

    highest = recent["High"].max()
    lowest = recent["Low"].min()

    last_close = recent["Close"].iloc[-1]

    if last_close <= 0:
        return False

    range_percent = (
        (highest - lowest) / last_close
    ) * 100

    # Conservative range threshold
    return range_percent <= 1.5


# ============================================================
# 6. SNR CALCULATION
# ============================================================

def calculate_snr(df, lookback=12):
    """
    Approximate resistance/support from recent candles.
    """

    if len(df) < lookback:
        return None, None

    recent = df.iloc[-lookback:]

    resistance = recent["High"].max()
    support = recent["Low"].min()

    return support, resistance


# ============================================================
# 7. SNR TOLERANCE
# ============================================================

def snr_tolerance(df):
    """
    Small tolerance around SNR line.
    """

    if len(df) < 5:
        return 0

    recent = df.iloc[-5:]

    avg_range = (
        recent["High"] - recent["Low"]
    ).mean()

    if pd.isna(avg_range):
        return 0

    return avg_range * 0.10


# ============================================================
# 8. BUY SETUP
# ============================================================

def check_buy_setup(df):
    """
    BUY setup from SS6:

    1. Ranging market
    2. Previous candles show buying side
    3. Hammer near resistance/SNR
    4. Hammer should NOT properly break SNR
    5. Hammer closes below resistance
    6. Next candle gives bearish reversal
    """

    if len(df) < 8:
        return False, "Not enough candles"

    if not is_ranging_market(df):
        return False, "Market not ranging"

    # Last closed candle = confirmation candle
    confirm = df.iloc[-1]

    # Hammer candle = previous candle
    hammer = df.iloc[-2]

    # Before hammer
    previous = df.iloc[-6:-2]

    # --------------------------------------------------------
    # Big candle filter
    # --------------------------------------------------------

    if is_big_candle(df, len(df) - 2):
        return False, "Hammer candle is too big"

    if is_big_candle(df, len(df) - 1):
        return False, "Confirmation candle is too big"

    # --------------------------------------------------------
    # Hammer
    # --------------------------------------------------------

    if not is_hammer(hammer):
        return False, "No hammer"

    # --------------------------------------------------------
    # Previous candles
    # --------------------------------------------------------

    green_count = 0

    for _, c in previous.iterrows():
        if is_green(c):
            green_count += 1

    if green_count < 1:
        return False, "No previous green candle"

    # --------------------------------------------------------
    # SNR
    # --------------------------------------------------------

    support, resistance = calculate_snr(
        df.iloc[:-2],
        lookback=12
    )

    if resistance is None:
        return False, "SNR unavailable"

    tolerance = snr_tolerance(df)

    # Hammer should reach resistance area
    if hammer["High"] < resistance - tolerance:
        return False, "Hammer not near resistance"

    # Hammer must not decisively break resistance
    if hammer["Close"] >= resistance + tolerance:
        return False, "SNR breakout - setup rejected"

    # --------------------------------------------------------
    # Confirmation candle
    # --------------------------------------------------------

    # For reversal:
    # confirmation should be red
    if not is_red(confirm):
        return False, "No bearish confirmation"

    # Confirmation should move below hammer body
    hammer_body_low = min(
        hammer["Open"],
        hammer["Close"]
    )

    if confirm["Close"] >= hammer_body_low:
        return False, "Confirmation not strong enough"

    return True, "SS6 BUY reversal setup"


# ============================================================
# 9. SELL SETUP
# ============================================================

def check_sell_setup(df):
    """
    SELL setup from SS6:

    1. Ranging market
    2. Previous candles show selling side
    3. Hammer/inverted hammer near support
    4. Candle does not properly break SNR
    5. Confirmation candle becomes green
    6. Reversal confirmed
    """

    if len(df) < 8:
        return False, "Not enough candles"

    if not is_ranging_market(df):
        return False, "Market not ranging"

    confirm = df.iloc[-1]
    hammer = df.iloc[-2]

    previous = df.iloc[-6:-2]

    # --------------------------------------------------------
    # Big candle filter
    # --------------------------------------------------------

    if is_big_candle(df, len(df) - 2):
        return False, "Hammer candle is too big"

    if is_big_candle(df, len(df) - 1):
        return False, "Confirmation candle is too big"

    # --------------------------------------------------------
    # Hammer type
    # --------------------------------------------------------

    hammer_ok = (
        is_hammer(hammer)
        or is_inverted_hammer(hammer)
    )

    if not hammer_ok:
        return False, "No reversal candle"

    # --------------------------------------------------------
    # Previous red candles
    # --------------------------------------------------------

    red_count = 0

    for _, c in previous.iterrows():
        if is_red(c):
            red_count += 1

    if red_count < 1:
        return False, "No previous red candle"

    # --------------------------------------------------------
    # SNR
    # --------------------------------------------------------

    support, resistance = calculate_snr(
        df.iloc[:-2],
        lookback=12
    )

    if support is None:
        return False, "SNR unavailable"

    tolerance = snr_tolerance(df)

    # Candle should be near support
    if hammer["Low"] > support + tolerance:
        return False, "Candle not near support"

    # It should not decisively break support
    if hammer["Close"] <= support - tolerance:
        return False, "SNR breakout - setup rejected"

    # --------------------------------------------------------
    # Confirmation
    # --------------------------------------------------------

    if not is_green(confirm):
        return False, "No bullish confirmation"

    hammer_body_high = max(
        hammer["Open"],
        hammer["Close"]
    )

    if confirm["Close"] <= hammer_body_high:
        return False, "Confirmation not strong enough"

    return True, "SS6 SELL reversal setup"


# ============================================================
# 10. MAIN SIGNAL FUNCTION
# ============================================================

def signal(df):
    """
    Main function for main.py

    Returns:
        BUY
        SELL
        HOLD
    """

    data = _prepare_df(df)

    if data is None:
        return "HOLD"

    buy, _ = check_buy_setup(data)

    if buy:
        return "BUY"

    sell, _ = check_sell_setup(data)

    if sell:
        return "SELL"

    return "HOLD"


# ============================================================
# 11. DETAILED SIGNAL
# ============================================================

def get_signal_details(df):
    """
    Useful for testing/debugging.

    Returns dictionary.
    """

    data = _prepare_df(df)

    if data is None:
        return {
            "signal": "HOLD",
            "strategy": "SS6",
            "reason": "Invalid or insufficient data"
        }

    buy, buy_reason = check_buy_setup(data)

    if buy:
        return {
            "signal": "BUY",
            "strategy": "SS6",
            "reason": buy_reason
        }

    sell, sell_reason = check_sell_setup(data)

    if sell:
        return {
            "signal": "SELL",
            "strategy": "SS6",
            "reason": sell_reason
        }

    return {
        "signal": "HOLD",
        "strategy": "SS6",
        "reason": "No SS6 setup"
    }


# ============================================================
# 12. TEST
# ============================================================

if __name__ == "__main__":

    print("--------------------------------")
    print("SS6 STRATEGY")
    print("--------------------------------")
    print("Ranging Market + Hammer + SNR")
    print("Signal: BUY / SELL / HOLD")
    print("--------------------------------")