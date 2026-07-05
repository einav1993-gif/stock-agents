#!/usr/bin/env python3
"""
🔑 finnhub_source.py — מקור נתונים פונדמנטלי דרך Finnhub
==========================================================
Yahoo חוסמת שרתים, ולכן דירוגי אנליסטים ויעדי מחיר הגיעו כ"לא ידוע".
Finnhub (מפתח חינמי ב-Secret בשם FINNHUB_API_KEY) עונה משרתים בלי חסימה.

מספק:
  • recommendation(ticker) — Buy/Hold/Sell + כמה אנליסטים
  • price_target(ticker)   — יעד ממוצע + פוטנציאל עלייה מול המחיר
כל הקריאות מוגנות: אם אין מפתח או שהקריאה נכשלה — מחזיר None,
והסוכן הפונדמנטלי פשוט נופל חזרה ל-Yahoo כמו קודם.

מגבלת התוכנית החינמית: 60 קריאות לדקה — מספיק בשפע ל-25 מניות.
"""

import json
import os
import time
import urllib.request

API_KEY = os.environ.get("FINNHUB_API_KEY", "").strip()
BASE = "https://finnhub.io/api/v1"

_last_call = [0.0]  # ויסות קצב פשוט


def _get(path):
    """קריאת GET ל-Finnhub עם המפתח. מחזיר dict/list או None."""
    if not API_KEY:
        return None
    # לא יותר מ~5 קריאות בשנייה
    gap = time.time() - _last_call[0]
    if gap < 0.2:
        time.sleep(0.2 - gap)
    _last_call[0] = time.time()
    try:
        sep = "&" if "?" in path else "?"
        url = f"{BASE}{path}{sep}token={API_KEY}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def has_key():
    return bool(API_KEY)


def recommendation(ticker):
    """
    דירוג אנליסטים עדכני.
    מחזיר dict: {label, score_add, buy, hold, sell, total} או None.
    """
    data = _get(f"/stock/recommendation?symbol={ticker}")
    if not data or not isinstance(data, list):
        return None
    latest = data[0]  # החודש האחרון
    strong_buy = int(latest.get("strongBuy", 0) or 0)
    buy        = int(latest.get("buy", 0) or 0)
    hold       = int(latest.get("hold", 0) or 0)
    sell       = int(latest.get("sell", 0) or 0)
    strong_sell= int(latest.get("strongSell", 0) or 0)

    buys  = strong_buy + buy
    sells = sell + strong_sell
    total = buys + hold + sells
    if total == 0:
        return None

    buy_pct = buys / total
    if buy_pct >= 0.7:
        label, score_add = f"Strong Buy ({buys}/{total} אנליסטים) 🌟", 15
    elif buy_pct >= 0.5:
        label, score_add = f"Buy ({buys}/{total})", 8
    elif sells > buys:
        label, score_add = f"Sell ({sells}/{total} מוכרים)", -10
    else:
        label, score_add = f"Hold ({hold}/{total})", 0

    return {
        "label": label, "score_add": score_add,
        "buy": buys, "hold": hold, "sell": sells, "total": total,
    }


def price_target(ticker, current_price=None):
    """
    יעד מחיר אנליסטים ממוצע.
    מחזיר dict: {target, upside_pct, high, low} או None.
    """
    data = _get(f"/stock/price-target?symbol={ticker}")
    if not data or not isinstance(data, dict):
        return None
    target = data.get("targetMean")
    if not target:
        return None
    out = {"target": round(float(target), 2),
           "high": data.get("targetHigh"), "low": data.get("targetLow"),
           "upside_pct": None}
    if current_price and current_price > 0:
        out["upside_pct"] = round((float(target) - current_price) / current_price * 100, 1)
    return out


def quote(ticker):
    """
    מחיר בזמן אמת דרך Finnhub /quote (עובד משרתים, בניגוד ל-Yahoo).
    מחזיר dict: {price, high, low, open, prev_close} או None.
    'c'=current, 'h'=high היום, 'l'=low היום, 'o'=open, 'pc'=prev close.
    """
    data = _get(f"/quote?symbol={ticker}")
    if not data or not isinstance(data, dict):
        return None
    price = data.get("c")
    if not price:  # 0 או None = אין נתון
        return None
    return {
        "price":      round(float(price), 2),
        "high":       round(float(data.get("h") or price), 2),
        "low":        round(float(data.get("l") or price), 2),
        "open":       round(float(data.get("o") or price), 2),
        "prev_close": round(float(data.get("pc") or price), 2),
    }


if __name__ == "__main__":
    if not has_key():
        print("⚠️  אין מפתח FINNHUB_API_KEY בסביבה")
    else:
        for t in ["AAPL", "TSLA"]:
            print(t, recommendation(t), price_target(t))
