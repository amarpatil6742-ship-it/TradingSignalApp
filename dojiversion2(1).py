import time
import traceback
import pandas as pd

# ============================================================
# DOJI VERSION 2
# SNR FIRST TOUCH REVERSAL
# ============================================================

SYMBOL = "BTCUSDT"
INTERVAL = "1m"
HISTORY_LIMIT = 100

print("=" * 70)
print("DOJI VERSION 2")
print("SNR FIRST TOUCH REVERSAL")
print("=" * 70)


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


# ============================================================
# PREPARE DATAFRAME
# ============================================================

def prepare_dataframe(df):

    if df is None:
        return pd.DataFrame(
            columns=[
                "Time",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume"
            ]
        )

    df = df.copy()

    required = [
        "Time",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume"
    ]

    for col in required:
        if col not in df.columns:

            if col == "Time":
                df[col] = range(len(df))

            else:
                df[col] = 0.0

    # Numeric conversion
    for col in [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume"
    ]:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    # Remove invalid OHLC rows
    df = df.dropna(
        subset=[
            "Open",
            "High",
            "Low",
            "Close"
        ]
    )

    # Last 100 candles
    df = df.tail(
        HISTORY_LIMIT
    )

    df.reset_index(
        drop=True,
        inplace=True
    )

    return df


# ============================================================
# LOAD HISTORY
# ============================================================

def load_initial_history():

    try:

        from history import load_history

        # IMPORTANT:
        # तुमच्या history.py मध्ये load_history()
        # arguments घेत नाही, म्हणून इथे no-argument call.

        df = load_history()

        df = prepare_dataframe(df)

        print(
            "Historical candles loaded:",
            len(df)
        )

        return df

    except Exception as e:

        print()
        print(
            "History loading error:",
            e
        )

        return pd.DataFrame(
            columns=[
                "Time",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume"
            ]
        )


# ============================================================
# CANDLE UPDATE
# ============================================================

def process_candle(df, candle):

    new_row = {
        "Time": candle["Time"],
        "Open": safe_float(candle["Open"]),
        "High": safe_float(candle["High"]),
        "Low": safe_float(candle["Low"]),
        "Close": safe_float(candle["Close"]),
        "Volume": safe_float(candle["Volume"])
    }

    # No candles yet
    if len(df) == 0:

        df = pd.DataFrame(
            [new_row]
        )

    else:

        last_time = str(
            df.iloc[-1]["Time"]
        )

        new_time = str(
            new_row["Time"]
        )

        # Same candle -> update
        if last_time == new_time:

            for key in new_row:

                df.loc[
                    df.index[-1],
                    key
                ] = new_row[key]

        # New candle -> append
        else:

            df = pd.concat(
                [
                    df,
                    pd.DataFrame(
                        [new_row]
                    )
                ],
                ignore_index=True
            )

    # Keep only last 100
    df = df.tail(
        HISTORY_LIMIT
    ).reset_index(
        drop=True
    )

    return df


# ============================================================
# DOJI DETECTION
# ============================================================

def is_doji(candle):

    o = safe_float(candle["Open"])
    h = safe_float(candle["High"])
    l = safe_float(candle["Low"])
    c = safe_float(candle["Close"])

    body = abs(c - o)

    total_range = h - l

    if total_range <= 0:
        return False

    # Doji body small compared to full candle
    body_ratio = body / total_range

    return body_ratio <= 0.20


# ============================================================
# HAMMER DETECTION
# ============================================================

def is_hammer(candle):

    o = safe_float(candle["Open"])
    h = safe_float(candle["High"])
    l = safe_float(candle["Low"])
    c = safe_float(candle["Close"])

    body = abs(c - o)

    upper_wick = h - max(o, c)

    lower_wick = min(o, c) - l

    total_range = h - l

    if total_range <= 0:
        return False

    if body == 0:
        body = total_range * 0.01

    # Hammer:
    # lower wick >= 2x body
    # upper wick relatively small

    if (
        lower_wick >= body * 2
        and upper_wick <= body
    ):
        return True

    return False


# ============================================================
# TREND CHECK
# ============================================================

def detect_trend(df):

    if len(df) < 10:
        return "UNKNOWN"

    closes = df["Close"].tail(10)

    first = safe_float(
        closes.iloc[0]
    )

    last = safe_float(
        closes.iloc[-1]
    )

    if last > first:
        return "UP"

    if last < first:
        return "DOWN"

    return "RANGE"


# ============================================================
# SIMPLE SNR DETECTION
# ============================================================

def calculate_snr(df):

    if len(df) < 10:

        return None, None

    recent = df.tail(20)

    resistance = safe_float(
        recent["High"].max()
    )

    support = safe_float(
        recent["Low"].min()
    )

    return support, resistance


# ============================================================
# FIRST TOUCH CHECK
# ============================================================

def first_touch_snr(df):

    if len(df) < 5:

        return False, None

    support, resistance = calculate_snr(
        df
    )

    if support is None:
        return False, None

    current = df.iloc[-1]

    close = safe_float(
        current["Close"]
    )

    high = safe_float(
        current["High"]
    )

    low = safe_float(
        current["Low"]
    )

    # Small tolerance
    price_range = max(
        resistance - support,
        0.00000001
    )

    tolerance = price_range * 0.02

    # Near support
    if abs(low - support) <= tolerance:

        return True, "SUPPORT"

    # Near resistance
    if abs(high - resistance) <= tolerance:

        return True, "RESISTANCE"

    # Close near support
    if abs(close - support) <= tolerance:

        return True, "SUPPORT"

    # Close near resistance
    if abs(close - resistance) <= tolerance:

        return True, "RESISTANCE"

    return False, None


# ============================================================
# DOJI VERSION 2 SIGNAL
# ============================================================

def signal(df):

    """
    DOJI VERSION 2

    BUY:
        - Market has support
        - Doji appears near support
        - First touch
        - Current candle should not be hammer

    SELL:
        - Market has resistance
        - Doji appears near resistance
        - First touch
        - Current candle should not be hammer

    Otherwise HOLD.
    """

    if df is None:
        return "HOLD", 0

    if len(df) < 10:
        return "HOLD", 0

    current = df.iloc[-1]

    # --------------------------------------------------------
    # Doji check
    # --------------------------------------------------------

    if not is_doji(current):

        return (
            "HOLD",
            0
        )

    # --------------------------------------------------------
    # Hammer precaution
    # --------------------------------------------------------

    if is_hammer(current):

        return (
            "HOLD",
            0
        )

    # --------------------------------------------------------
    # SNR
    # --------------------------------------------------------

    touched, level = first_touch_snr(
        df
    )

    if not touched:

        return (
            "HOLD",
            0
        )

    # --------------------------------------------------------
    # Trend
    # --------------------------------------------------------

    trend = detect_trend(
        df
    )

    # --------------------------------------------------------
    # BUY
    # Doji at support
    # --------------------------------------------------------

    if level == "SUPPORT":

        confidence = 75

        if trend == "DOWN":
            confidence += 5

        if trend == "RANGE":
            confidence += 5

        confidence = min(
            confidence,
            100
        )

        return (
            "BUY",
            confidence
        )

    # --------------------------------------------------------
    # SELL
    # Doji at resistance
    # --------------------------------------------------------

    if level == "RESISTANCE":

        confidence = 75

        if trend == "UP":
            confidence += 5

        if trend == "RANGE":
            confidence += 5

        confidence = min(
            confidence,
            100
        )

        return (
            "SELL",
            confidence
        )

    return (
        "HOLD",
        0
    )


# ============================================================
# DISPLAY SIGNAL
# ============================================================

def display_signal(df):

    if len(df) == 0:
        return

    current = df.iloc[-1]

    sig, confidence = signal(
        df
    )

    trend = detect_trend(
        df
    )

    touched, level = first_touch_snr(
        df
    )

    print()
    print("-" * 70)

    print(
        "DOJI VERSION 2"
    )

    print(
        "Symbol      :",
        SYMBOL
    )

    print(
        "Timeframe   :",
        INTERVAL
    )

    print(
        "Time        :",
        current["Time"]
    )

    print(
        "Open        :",
        current["Open"]
    )

    print(
        "High        :",
        current["High"]
    )

    print(
        "Low         :",
        current["Low"]
    )

    print(
        "Close       :",
        current["Close"]
    )

    print(
        "Trend       :",
        trend
    )

    print(
        "SNR Touch   :",
        level if touched else "NO"
    )

    print(
        "Doji        :",
        "YES" if is_doji(current)
        else "NO"
    )

    print(
        "Hammer      :",
        "YES" if is_hammer(current)
        else "NO"
    )

    print("-" * 70)

    print(
        "SIGNAL      :",
        sig
    )

    print(
        "CONFIDENCE  :",
        f"{confidence:.2f}%"
    )

    print("-" * 70)


# ============================================================
# BINANCE LIVE DATA
# ============================================================

def start_live():

    try:

        import websocket
        import json

    except ImportError:

        print()
        print(
            "websocket-client installed नाही."
        )

        print()
        print(
            "Pydroid 3 मध्ये install करा:"
        )

        print(
            "pip install websocket-client"
        )

        return

    # --------------------------------------------------------
    # Load 100 candles
    # --------------------------------------------------------

    df = load_initial_history()

    print()
    print(
        "Starting live Binance data..."
    )

    print(
        "Candles:",
        len(df)
    )

    # --------------------------------------------------------
    # Binance WebSocket
    # --------------------------------------------------------

    ws_url = (
        "wss://stream.binance.com:9443/ws/"
        f"{SYMBOL.lower()}@kline_{INTERVAL}"
    )

    # ========================================================
    # MESSAGE
    # ========================================================

    def on_message(
        ws,
        message
    ):

        nonlocal df

        try:

            data = json.loads(
                message
            )

            if "k" not in data:
                return

            kline = data["k"]

            candle = {

                "Time":
                    pd.to_datetime(
                        kline["t"],
                        unit="ms"
                    ),

                "Open":
                    kline["o"],

                "High":
                    kline["h"],

                "Low":
                    kline["l"],

                "Close":
                    kline["c"],

                "Volume":
                    kline["v"]
            }

            # Update candle
            df = process_candle(
                df,
                candle
            )

            # ------------------------------------------------
            # Candle CLOSED
            # ------------------------------------------------

            if kline["x"]:

                print()

                print(
                    "\nNew 1-minute candle closed."
                )

                display_signal(
                    df
                )

            else:

                # Live price
                print(
                    f"\rLive Price: "
                    f"{candle['Close']}",
                    end=""
                )

        except Exception as e:

            print()

            print(
                "Message error:",
                e
            )


    # ========================================================
    # OPEN
    # ========================================================

    def on_open(ws):

        print()
        print(
            "Binance WebSocket CONNECTED"
        )

        print(
            "Symbol    :",
            SYMBOL
        )

        print(
            "Timeframe :",
            INTERVAL
        )

        print()


    # ========================================================
    # ERROR
    # ========================================================

    def on_error(
        ws,
        error
    ):

        print()

        print(
            "WebSocket error:",
            error
        )


    # ========================================================
    # CLOSE
    # ========================================================

    def on_close(
        ws,
        close_status_code,
        close_msg
    ):

        print()

        print(
            "WebSocket disconnected."
        )


    # ========================================================
    # RECONNECT LOOP
    # ========================================================

    while True:

        try:

            ws = websocket.WebSocketApp(

                ws_url,

                on_open=on_open,

                on_message=on_message,

                on_error=on_error,

                on_close=on_close
            )

            ws.run_forever()

        except KeyboardInterrupt:

            print()
            print(
                "Program stopped."
            )

            break

        except Exception as e:

            print()

            print(
                "Connection error:",
                e
            )

        print()
        print(
            "Reconnecting in 5 seconds..."
        )

        time.sleep(5)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    try:

        start_live()

    except KeyboardInterrupt:

        print()
        print(
            "Stopped by user."
        )

    except Exception as e:

        print()
        print(
            "Fatal Error:",
            e
        )

        traceback.print_exc()