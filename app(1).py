import os
import sys
import time
import importlib
import threading
import requests
import pandas as pd

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView


# =========================================================
# SETTINGS
# =========================================================

INTERVAL = "1m"
LIMIT = 100

BASE_URL = "https://api.binance.com"

RUNNING = False
CURRENT_SYMBOL = "BTCUSDT"

STRATEGIES = {}


# =========================================================
# LOAD ALL STRATEGY FILES
# =========================================================

def load_strategies():

    global STRATEGIES

    STRATEGIES = {}

    folder = os.path.dirname(os.path.abspath(__file__))

    excluded = {
        "app.py",
        "__init__.py",
        "history.py"
    }

    for filename in os.listdir(folder):

        if not filename.endswith(".py"):
            continue

        if filename in excluded:
            continue

        module_name = filename[:-3]

        if module_name.startswith("_"):
            continue

        try:

            module = importlib.import_module(module_name)

            STRATEGIES[module_name] = module

            print("Strategy loaded:", module_name)

        except Exception as e:

            print("Strategy load error:", module_name, e)

    print("Total strategies:", len(STRATEGIES))


# =========================================================
# GET USDT PAIRS
# =========================================================

def get_usdt_pairs():

    try:

        url = BASE_URL + "/api/v3/exchangeInfo"

        data = requests.get(url, timeout=10).json()

        pairs = []

        for item in data["symbols"]:

            if (
                item.get("quoteAsset") == "USDT"
                and item.get("status") == "TRADING"
                and item.get("isSpotTradingAllowed", True)
            ):

                pairs.append(item["symbol"])

        pairs.sort()

        return pairs

    except Exception as e:

        print("Pair error:", e)

        return [
            "BTCUSDT",
            "ETHUSDT",
            "BNBUSDT",
            "SOLUSDT",
            "XRPUSDT"
        ]


# =========================================================
# GET 100 CANDLES
# =========================================================

def get_candles(symbol):

    try:

        url = BASE_URL + "/api/v3/klines"

        params = {
            "symbol": symbol,
            "interval": INTERVAL,
            "limit": LIMIT
        }

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        data = response.json()

        rows = []

        for candle in data:

            rows.append({

                "Time": pd.to_datetime(
                    candle[0],
                    unit="ms"
                ),

                "Open": float(candle[1]),
                "High": float(candle[2]),
                "Low": float(candle[3]),
                "Close": float(candle[4]),
                "Volume": float(candle[5])

            })

        return pd.DataFrame(rows)

    except Exception as e:

        print("Candle error:", e)

        return None


# =========================================================
# LIVE PRICE
# =========================================================

def get_price(symbol):

    try:

        url = BASE_URL + "/api/v3/ticker/price"

        response = requests.get(
            url,
            params={"symbol": symbol},
            timeout=5
        )

        data = response.json()

        return float(data["price"])

    except Exception:

        return 0.0


# =========================================================
# NORMALIZE SIGNAL
# =========================================================

def normalize_signal(result):

    if result is None:
        return "HOLD"

    if isinstance(result, str):

        value = result.upper().strip()

        if "BUY" in value:
            return "BUY"

        if "SELL" in value:
            return "SELL"

        return "HOLD"

    if isinstance(result, dict):

        for key in [
            "signal",
            "Signal",
            "action",
            "Action"
        ]:

            if key in result:

                return normalize_signal(
                    result[key]
                )

        return "HOLD"

    if isinstance(result, (list, tuple)):

        if len(result) > 0:

            return normalize_signal(
                result[0]
            )

    return "HOLD"


# =========================================================
# RUN ONE STRATEGY
# =========================================================

def run_strategy(module, df):

    try:

        if hasattr(module, "signal"):

            result = module.signal(df)

        elif hasattr(module, "generate_signal"):

            result = module.generate_signal(df)

        elif hasattr(module, "get_signal"):

            result = module.get_signal(df)

        else:

            return "HOLD"

        return normalize_signal(result)

    except Exception as e:

        print(
            "Strategy error:",
            module.__name__,
            e
        )

        return "HOLD"


# =========================================================
# RUN ALL STRATEGIES
# =========================================================

def run_all_strategies(df):

    results = []

    buy = 0
    sell = 0
    hold = 0

    for name, module in STRATEGIES.items():

        signal = run_strategy(
            module,
            df
        )

        results.append(
            (name, signal)
        )

        if signal == "BUY":
            buy += 1

        elif signal == "SELL":
            sell += 1

        else:
            hold += 1

    return results, buy, sell, hold


# =========================================================
# FINAL SIGNAL
# =========================================================

def final_signal(buy, sell, hold):

    total = buy + sell + hold

    if total == 0:

        return "HOLD", 0

    # BUY majority
    if buy > sell and buy > hold:

        confidence = int(
            (buy / total) * 100
        )

        return "BUY", confidence

    # SELL majority
    if sell > buy and sell > hold:

        confidence = int(
            (sell / total) * 100
        )

        return "SELL", confidence

    return "HOLD", 0


# =========================================================
# MAIN APP
# =========================================================

class TradingApp(App):

    def build(self):

        self.title = "MULTI STRATEGY SIGNAL"

        self.root_layout = BoxLayout(
            orientation="vertical",
            padding=15,
            spacing=10
        )

        # TITLE
        self.title_label = Label(
            text="MULTI STRATEGY SIGNAL",
            font_size=24,
            size_hint_y=None,
            height=50
        )

        self.root_layout.add_widget(
            self.title_label
        )

        # SYMBOL DROPDOWN
        self.symbol_spinner = Spinner(
            text="BTCUSDT",
            values=("BTCUSDT",),
            font_size=22,
            size_hint_y=None,
            height=55
        )

        self.symbol_spinner.bind(
            text=self.change_symbol
        )

        self.root_layout.add_widget(
            self.symbol_spinner
        )

        # PRICE
        self.price_label = Label(
            text="Live Price: --",
            font_size=20
        )

        self.root_layout.add_widget(
            self.price_label
        )

        # SIGNAL
        self.signal_label = Label(
            text="FINAL SIGNAL: HOLD",
            font_size=28
        )

        self.root_layout.add_widget(
            self.signal_label
        )

        # CONFIDENCE
        self.confidence_label = Label(
            text="CONFIDENCE: 0%",
            font_size=20
        )

        self.root_layout.add_widget(
            self.confidence_label
        )

        # COUNTS
        self.count_label = Label(
            text="BUY: 0   SELL: 0   HOLD: 0",
            font_size=18
        )

        self.root_layout.add_widget(
            self.count_label
        )

        # STRATEGY RESULTS TITLE
        self.strategy_title = Label(
            text="STRATEGY-WISE RESULTS",
            font_size=18,
            size_hint_y=None,
            height=40
        )

        self.root_layout.add_widget(
            self.strategy_title
        )

        # SCROLL AREA
        scroll = ScrollView()

        self.strategy_box = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=3
        )

        self.strategy_box.bind(
            minimum_height=
            self.strategy_box.setter(
                "height"
            )
        )

        scroll.add_widget(
            self.strategy_box
        )

        self.root_layout.add_widget(
            scroll
        )

        # START
        self.start_button = Button(
            text="START",
            font_size=22,
            size_hint_y=None,
            height=55
        )

        self.start_button.bind(
            on_press=self.start_strategy
        )

        self.root_layout.add_widget(
            self.start_button
        )

        # STOP
        self.stop_button = Button(
            text="STOP",
            font_size=22,
            size_hint_y=None,
            height=55
        )

        self.stop_button.bind(
            on_press=self.stop_strategy
        )

        self.root_layout.add_widget(
            self.stop_button
        )

        # FOOTER
        self.footer = Label(
            text=(
                "Symbol: BTCUSDT\n"
                "Timeframe: 1 Minute\n"
                "Mode: PAPER SIGNAL"
            ),
            font_size=14,
            size_hint_y=None,
            height=65
        )

        self.root_layout.add_widget(
            self.footer
        )

        # LOAD STRATEGIES
        Clock.schedule_once(
            self.initialize,
            0.5
        )

        return self.root_layout

    # =====================================================
    # INITIALIZE
    # =====================================================

    def initialize(self, dt):

        load_strategies()

        self.strategy_title.text = (
            f"STRATEGIES LOADED: "
            f"{len(STRATEGIES)}"
        )

        threading.Thread(
            target=self.load_pairs,
            daemon=True
        ).start()

    # =====================================================
    # LOAD PAIRS
    # =====================================================

    def load_pairs(self):

        pairs = get_usdt_pairs()

        def update_spinner(dt):

            self.symbol_spinner.values = tuple(
                pairs
            )

        Clock.schedule_once(
            update_spinner
        )

    # =====================================================
    # CHANGE SYMBOL
    # =====================================================

    def change_symbol(
        self,
        spinner,
        text
    ):

        global CURRENT_SYMBOL

        CURRENT_SYMBOL = text

        self.footer.text = (
            f"Symbol: {CURRENT_SYMBOL}\n"
            "Timeframe: 1 Minute\n"
            "Mode: PAPER SIGNAL"
        )

    # =====================================================
    # START
    # =====================================================

    def start_strategy(self, instance):

        global RUNNING

        if RUNNING:
            return

        RUNNING = True

        threading.Thread(
            target=self.strategy_loop,
            daemon=True
        ).start()

    # =====================================================
    # STOP
    # =====================================================

    def stop_strategy(self, instance):

        global RUNNING

        RUNNING = False

        self.signal_label.text = (
            "FINAL SIGNAL: STOPPED"
        )

    # =====================================================
    # STRATEGY LOOP
    # =====================================================

    def strategy_loop(self):

        global RUNNING

        while RUNNING:

            symbol = CURRENT_SYMBOL

            price = get_price(
                symbol
            )

            df = get_candles(
                symbol
            )

            if df is not None and len(df) >= 20:

                results, buy, sell, hold = (
                    run_all_strategies(df)
                )

                signal, confidence = (
                    final_signal(
                        buy,
                        sell,
                        hold
                    )
                )

                Clock.schedule_once(
                    lambda dt,
                    p=price,
                    s=signal,
                    c=confidence,
                    b=buy,
                    se=sell,
                    h=hold,
                    r=results:
                    self.update_screen(
                        p,
                        s,
                        c,
                        b,
                        se,
                        h,
                        r
                    )
                )

            time.sleep(5)

    # =====================================================
    # UPDATE SCREEN
    # =====================================================

    def update_screen(
        self,
        price,
        signal,
        confidence,
        buy,
        sell,
        hold,
        results
    ):

        self.price_label.text = (
            f"Live Price: {price:.4f}"
        )

        self.signal_label.text = (
            f"FINAL SIGNAL: {signal}"
        )

        self.confidence_label.text = (
            f"CONFIDENCE: {confidence}%"
        )

        self.count_label.text = (
            f"BUY: {buy}   "
            f"SELL: {sell}   "
            f"HOLD: {hold}"
        )

        self.strategy_box.clear_widgets()

        for name, result in results:

            label = Label(
                text=f"{name}  →  {result}",
                font_size=14,
                size_hint_y=None,
                height=30
            )

            self.strategy_box.add_widget(
                label
            )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    TradingApp().run()