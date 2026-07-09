#!/usr/bin/env python3
"""בדיקת הסימולטור מקצה לקצה עם נתונים סינתטיים."""
import json, os
import numpy as np, pandas as pd
from datetime import datetime, timedelta

import data_layer

# תאריך מסחר קבוע לבדיקה (שני), כדי שתאריך הבר האחרון יתאים ל-date_open
TRADE_DAY = "2026-07-06"

# נתונים סינתטיים: מנייה שעולה ותפגע ביעד
def make_df(ticker, last_price, high_mult=1.10, low_mult=0.99):
    idx = pd.bdate_range(end=pd.Timestamp(TRADE_DAY), periods=5)
    close = np.linspace(last_price*0.95, last_price, 5)
    df = pd.DataFrame({
        "Open": close*0.998, "High": close*high_mult,
        "Low": close*low_mult, "Close": close,
        "Volume": [1e7]*5}, index=idx)
    return df

# ננתב את data_layer למחירים מבוקרים
prices = {"HOOD": 112.73}
def fake_daily(t, period="5d"):
    if t in prices:
        # HOOD: היעד ב-119.49, high יגיע ל-124 → פגיעה ביעד
        return make_df(t, prices[t], high_mult=1.10, low_mult=0.99)
    return None
data_layer.get_daily = fake_daily
data_layer.get_last_price = lambda t: prices.get(t, 100)

import paper_trader
paper_trader.PORTFOLIO_PATH = "/tmp/portfolio_test.json"
if os.path.exists("/tmp/portfolio_test.json"):
    os.remove("/tmp/portfolio_test.json")

# ── בוקר: פתיחת פוזיציה ──
top5 = [{
    "ticker": "HOOD", "trade_type": "long", "total_score": 42,
    "entry": 112.73, "stop_loss": 108.22, "target_1": 119.49,
    "shares": 3, "degraded_data": False,
}]
p, orders = paper_trader.open_positions(top5, date_str="2026-07-06")
assert len(orders) == 1, f"expected 1 order, got {orders}"
assert p["cash"] < 1000, "cash should decrease after buy"
print(f"✔ בוקר: נקנו {orders[0]['shares']} מניות HOOD ב-${orders[0]['entry']}, מזומן נותר ${p['cash']:.2f}")

# ── ערב: סגירה — HOOD פגעה ביעד ──
p2, closed = paper_trader.close_positions(date_str="2026-07-06")
assert len(closed) == 1, f"expected 1 close, got {closed}"
assert closed[0]["reason"].startswith("✅"), f"expected target hit, got {closed[0]['reason']}"
assert closed[0]["pnl"] > 0, "target hit should be profit"
print(f"✔ ערב: {closed[0]['ticker']} {closed[0]['reason']} → רווח ${closed[0]['pnl']:+.2f} ({closed[0]['pnl_pct']:+.1f}%)")

st = paper_trader.stats()
assert st["equity"] > 1000, f"equity should grow after winning trade: {st['equity']}"
assert st["closed_count"] == 1
assert st["win_rate"] == 100
print(f"✔ סטטיסטיקה: שווי ${st['equity']:.2f} ({st['total_return_pct']:+.1f}%), הצלחה {st['win_rate']}%, drawdown {st['max_drawdown_pct']}%")

# ── בדיקת סטופ: מנייה שיורדת ──
prices2 = {"XYZ": 100.0}
def fake_daily2(t, period="5d"):
    if t == "XYZ":
        # low יגיע ל-91, סטופ ב-96 → פגיעה בסטופ
        return make_df(t, 100.0, high_mult=1.01, low_mult=0.91)
    return None
data_layer.get_daily = fake_daily2
data_layer.get_last_price = lambda t: 100
top_s = [{"ticker":"XYZ","trade_type":"long","total_score":40,
          "entry":100.0,"stop_loss":96.0,"target_1":106.0,"shares":2,"degraded_data":False}]
paper_trader.open_positions(top_s, date_str="2026-07-06")
_, closed2 = paper_trader.close_positions(date_str="2026-07-06")
assert closed2[0]["reason"].startswith("🛑"), f"expected stop, got {closed2[0]['reason']}"
assert closed2[0]["pnl"] < 0
print(f"✔ סטופ: {closed2[0]['ticker']} {closed2[0]['reason']} → הפסד ${closed2[0]['pnl']:+.2f}")

# ── בקרה: לא קונים מנייה עם ציון שלילי ("הימנע") ולא ביום degraded ──
avoid = [{"ticker":"AAA","trade_type":"none","total_score":-3,"has_data":True,"entry":50,"stop_loss":48,"target_1":54,"shares":5,"degraded_data":False}]
_, o = paper_trader.open_positions(avoid, date_str="2026-07-08")
assert len(o) == 0, "should not buy negative-score signal"
degraded = [{"ticker":"BBB","trade_type":"long","total_score":50,"has_data":True,"entry":50,"stop_loss":48,"target_1":54,"shares":5,"degraded_data":True}]
_, o2 = paper_trader.open_positions(degraded, date_str="2026-07-08")
assert len(o2) == 0, "should not buy on degraded data"
print("✔ בקרה: לא קונה ציון שלילי ולא קונה ביום נתונים לא אמינים")

print("\n✅ כל בדיקות הסימולטור עברו")
