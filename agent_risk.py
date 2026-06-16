#!/usr/bin/env python3
"""
⚖️  agent_risk.py — סוכן ניהול הסיכונים
==========================================
תפקיד: מחשב עבור כל מניה את:
- נקודת כניסה אופטימלית
- Stop Loss (עצירת הפסד)
- יעד רווח (Take Profit)
- גודל הפוזיציה (כמה לקנות)
- יחס סיכוי/סיכון (Risk/Reward)
זהו הסוכן שמגן על הכסף שלך.
"""

import yfinance as yf
import numpy as np


VIRTUAL_CAPITAL = 10_000   # הון וירטואלי בדולר
MAX_RISK_PER_TRADE = 0.015  # מקסימום 1.5% הפסד מהתיק בעסקה


def analyze(ticker, current_price=None):
    """
    מחשב ניהול סיכונים מלא עבור מניה.

    Returns dict עם כניסה, עצירה, יעד, כמות.
    """
    result = {
        "ticker": ticker,
        "current_price": current_price,
        # לונג
        "entry_price": None,
        "stop_loss": None,
        "stop_loss_pct": None,
        "target_1": None,
        "target_2": None,
        # שורט
        "short_entry": None,
        "short_stop": None,
        "short_stop_pct": None,
        "short_target_1": None,
        "short_target_2": None,
        # כללי
        "shares": None,
        "max_loss_usd": None,
        "risk_reward": None,
        "atr": None,
        "volatility_level": "בינוני",
        "score": 0,
        "verdict": "",
        "summary": ""
    }

    try:
        # שליפת נתונים
        df = yf.download(ticker, period="1mo", interval="1d",
                         auto_adjust=True, progress=False)

        if df.empty or len(df) < 5:
            result["summary"] = "אין מספיק נתונים"
            return result

        price = current_price or float(df["Close"].iloc[-1])
        result["current_price"] = round(price, 2)

        # ── ATR — Average True Range (תנודתיות) ──
        high  = df["High"]
        low   = df["Low"]
        close = df["Close"]

        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low  - close.shift(1)).abs()
        ], axis=1).max(axis=1)

        atr = float(tr.rolling(14).mean().iloc[-1])
        result["atr"] = round(atr, 3)
        atr_pct = atr / price * 100

        # רמת תנודתיות
        if atr_pct > 6:
            result["volatility_level"] = "גבוהה מאוד 🔥"
            result["score"] -= 5
        elif atr_pct > 3:
            result["volatility_level"] = "גבוהה"
        elif atr_pct > 1.5:
            result["volatility_level"] = "בינונית"
        else:
            result["volatility_level"] = "נמוכה"

        # ── חישוב Stop Loss על בסיס ATR ──
        # Stop Loss = 1.5x ATR מתחת למחיר הכניסה
        sl_distance = atr * 1.5
        sl_pct      = sl_distance / price * 100

        # מגבלות: לא פחות מ-1% ולא יותר מ-4%
        sl_pct = max(1.0, min(4.0, sl_pct))
        sl_distance = price * sl_pct / 100

        # ── לונג (קנייה) ──
        result["entry_price"]   = round(price, 2)
        result["stop_loss"]     = round(price - sl_distance, 2)
        result["stop_loss_pct"] = round(sl_pct, 1)
        result["target_1"]      = round(price + sl_distance * 1.5, 2)
        result["target_2"]      = round(price + sl_distance * 3.0, 2)
        result["risk_reward"]   = 3.0

        # ── שורט (מכירה בחסר) ──
        # בשורט: כניסה = מחיר נוכחי, Stop מעל, יעד מתחת
        result["short_entry"]     = round(price, 2)
        result["short_stop"]      = round(price + sl_distance, 2)   # Stop מעל
        result["short_stop_pct"]  = round(sl_pct, 1)
        result["short_target_1"]  = round(price - sl_distance * 1.5, 2)  # יעד 1 מתחת
        result["short_target_2"]  = round(price - sl_distance * 3.0, 2)  # יעד 2 מתחת

        # ── גודל פוזיציה ──
        # כמה מניות לקנות כך שהפסד מקסימלי = 1.5% מהתיק
        max_loss_usd = VIRTUAL_CAPITAL * MAX_RISK_PER_TRADE
        shares = max_loss_usd / sl_distance if sl_distance > 0 else 0
        shares = max(1, int(shares))

        # בדיקה שהפוזיציה לא עולה על 25% מהתיק
        position_value = shares * price
        if position_value > VIRTUAL_CAPITAL * 0.25:
            shares = int(VIRTUAL_CAPITAL * 0.25 / price)
            shares = max(1, shares)

        result["shares"]       = shares
        result["max_loss_usd"] = round(shares * sl_distance, 2)

        # ── ניקוד סיכון/סיכוי ──
        if atr_pct > 3 and sl_pct <= 3:
            result["score"] += 15  # תנודתיות גבוהה עם stop הגיוני — הזדמנות
        if sl_pct <= 2:
            result["score"] += 10  # stop קרוב = פחות סיכון
        if sl_pct > 3.5:
            result["score"] -= 10  # stop רחוק מדי

        # ── מסקנה ──
        rr = result["risk_reward"]
        if rr >= 3 and sl_pct <= 2.5:
            result["verdict"] = "✅ כדאי — יחס מצוין"
        elif rr >= 2:
            result["verdict"] = "⚠️  כדאי בזהירות"
        else:
            result["verdict"] = "❌ יחס סיכוי/סיכון לא מספיק"

        result["summary"] = (
            f"כניסה: ${price:.2f} | "
            f"Stop: ${result['stop_loss']:.2f} (-{sl_pct:.1f}%) | "
            f"יעד: ${result['target_2']:.2f} | "
            f"כמות: {shares} מניות"
        )

    except Exception as e:
        result["summary"] = f"שגיאת חישוב: {e}"

    return result


def run(tickers_with_prices=None, tickers=None):
    """מריץ ניתוח סיכון על רשימת מניות"""
    if tickers_with_prices is None and tickers is not None:
        tickers_with_prices = {t: None for t in tickers}

    print(f"⚖️  [סוכן סיכון] מחשב כניסה/עצירה/יעד עבור {len(tickers_with_prices)} מניות...")
    results = {}

    for ticker, price in tickers_with_prices.items():
        results[ticker] = analyze(ticker, price)

    print(f"✅ [סוכן סיכון] סיום חישוב ניהול סיכונים")
    return results


# import pandas must be at module level
import pandas as pd

if __name__ == "__main__":
    test = {"TSLA": None, "NVDA": None, "COIN": None}
    results = run(test)
    for t, r in results.items():
        print(f"\n{t}: {r['summary']}")
        print(f"  מסקנה: {r['verdict']}")
