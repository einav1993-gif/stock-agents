#!/usr/bin/env python3
"""
🕯️  agent_technical.py — סוכן הניתוח הטכני
=============================================
תפקיד: מנתח את התמונה הטכנית המלאה של כל מניה.
בודק: RSI, MACD, EMA, Bollinger Bands, נפח, תבניות נרות יפניים,
       תמיכות/התנגדויות, מומנטום, Trend.
רמת אנליסט Wall Street — לא משאיר שום אינדיקטור מחוץ לתמונה.
"""

import data_layer
import pandas as pd
import numpy as np


def _detect_candle_patterns(df):
    """
    מזהה תבניות נרות יפניים קלאסיות.
    מחזיר: רשימת תבניות שנמצאו בנר האחרון.
    """
    patterns = []
    if len(df) < 3:
        return patterns

    # נר אחרון ולפניו
    o, h, l, c = df["Open"].iloc[-1], df["High"].iloc[-1], df["Low"].iloc[-1], df["Close"].iloc[-1]
    o2, h2, l2, c2 = df["Open"].iloc[-2], df["High"].iloc[-2], df["Low"].iloc[-2], df["Close"].iloc[-2]
    o3, h3, l3, c3 = df["Open"].iloc[-3], df["High"].iloc[-3], df["Low"].iloc[-3], df["Close"].iloc[-3]

    body      = abs(c - o)
    full_range = h - l
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    if full_range == 0:
        return patterns

    body_pct       = body / full_range
    upper_wick_pct = upper_wick / full_range
    lower_wick_pct = lower_wick / full_range

    # ── Doji (גוף קטן מאוד — חוסר החלטה) ──
    if body_pct < 0.1:
        patterns.append("Doji — חוסר החלטה ⚖️")

    # ── Hammer (פטיש — היפוך מטה לעלייה) ──
    if lower_wick_pct > 0.5 and body_pct < 0.35 and upper_wick_pct < 0.1:
        patterns.append("Hammer 🔨 — פוטנציאל היפוך לעלייה")

    # ── Shooting Star (כוכב ירי — היפוך מעלייה לירידה) ──
    if upper_wick_pct > 0.5 and body_pct < 0.35 and lower_wick_pct < 0.1:
        patterns.append("Shooting Star ⭐ — אזהרת היפוך לירידה")

    # ── Bullish Engulfing (בליעה עולה) ──
    prev_bearish = c2 < o2
    curr_bullish = c > o
    if prev_bearish and curr_bullish and o <= c2 and c >= o2:
        patterns.append("Bullish Engulfing 🟢 — היפוך חזק לעלייה")

    # ── Bearish Engulfing (בליעה יורדת) ──
    prev_bullish = c2 > o2
    curr_bearish = c < o
    if prev_bullish and curr_bearish and o >= c2 and c <= o2:
        patterns.append("Bearish Engulfing 🔴 — היפוך חזק לירידה")

    # ── Morning Star (כוכב בוקר — 3 נרות, היפוך לעלייה) ──
    if c3 < o3 and body_pct < 0.15 and c > o and c > (o3 + c3) / 2:
        patterns.append("Morning Star 🌅 — היפוך חזק לעלייה (3 נרות)")

    # ── Evening Star (כוכב ערב — 3 נרות, היפוך לירידה) ──
    if c3 > o3 and body_pct < 0.15 and c < o and c < (o3 + c3) / 2:
        patterns.append("Evening Star 🌆 — היפוך לירידה (3 נרות)")

    # ── Marubozu (נר גדול ללא פתיל — כוח חד כיוון) ──
    if body_pct > 0.85:
        if c > o:
            patterns.append("Bullish Marubozu 💪 — כוח קנייה מוחץ")
        else:
            patterns.append("Bearish Marubozu 😤 — כוח מכירה מוחץ")

    return patterns


def analyze(ticker):
    """
    ניתוח טכני מלא של מניה.

    Returns dict עם כל האינדיקטורים ומסקנה.
    """
    result = {
        "ticker": ticker,
        "trend": "לא ידוע",
        "rsi": None,
        "rsi_signal": "",
        "macd_signal": "",
        "ema_signal": "",
        "bb_signal": "",
        "volume_signal": "",
        "candle_patterns": [],
        "support": None,
        "resistance": None,
        "score": 0,
        "signals": [],
        "warnings": [],
        "summary": ""
    }

    try:
        # שליפת נתוני 3 חודשים — דרך שכבת הנתונים העמידה (yfinance→Stooq)
        df = data_layer.get_daily(ticker, period="3mo")

        if df is None or df.empty or len(df) < 20:
            result["summary"] = "אין מספיק נתונים"
            return result

        # ── RSI ──
        delta = df["Close"].diff()
        gain  = delta.where(delta > 0, 0).rolling(14).mean()
        loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs    = gain / loss.replace(0, 1e-10)
        rsi   = float((100 - 100 / (1 + rs)).iloc[-1])
        result["rsi"] = round(rsi, 1)

        if rsi < 30:
            result["rsi_signal"] = f"RSI {rsi:.0f} — אזור קנייה קיצוני 🟢"
            result["score"] += 20
            result["signals"].append("RSI oversold")
        elif rsi < 45:
            result["rsi_signal"] = f"RSI {rsi:.0f} — אזור חיובי"
            result["score"] += 8
        elif rsi > 70:
            result["rsi_signal"] = f"RSI {rsi:.0f} — קנוי יתר ⚠️"
            result["score"] -= 10
            result["warnings"].append("RSI overbought")
        elif rsi > 55:
            result["rsi_signal"] = f"RSI {rsi:.0f} — מומנטום חיובי"
            result["score"] += 5
        else:
            result["rsi_signal"] = f"RSI {rsi:.0f} — נייטרלי"

        # ── MACD ──
        ema12 = df["Close"].ewm(span=12).mean()
        ema26 = df["Close"].ewm(span=26).mean()
        macd  = ema12 - ema26
        signal_line = macd.ewm(span=9).mean()
        histogram   = macd - signal_line

        macd_now  = float(macd.iloc[-1])
        sig_now   = float(signal_line.iloc[-1])
        hist_now  = float(histogram.iloc[-1])
        hist_prev = float(histogram.iloc[-2])

        if macd_now > sig_now and hist_now > hist_prev:
            result["macd_signal"] = "MACD חוצה מעלה — מומנטום חיובי 🟢"
            result["score"] += 15
            result["signals"].append("MACD bullish crossover")
        elif macd_now > sig_now:
            result["macd_signal"] = "MACD מעל קו האות — טרנד חיובי"
            result["score"] += 7
        elif macd_now < sig_now and hist_now < hist_prev:
            result["macd_signal"] = "MACD חוצה מטה — מומנטום שלילי 🔴"
            result["score"] -= 12
            result["warnings"].append("MACD bearish")
        else:
            result["macd_signal"] = "MACD מתחת לקו — זהירות"
            result["score"] -= 5

        # ── EMA 9/20/50 ──
        ema9  = float(df["Close"].ewm(span=9).mean().iloc[-1])
        ema20 = float(df["Close"].ewm(span=20).mean().iloc[-1])
        ema50 = float(df["Close"].ewm(span=50).mean().iloc[-1])
        price = float(df["Close"].iloc[-1])

        if price > ema9 > ema20 > ema50:
            result["ema_signal"] = "מחיר מעל EMA 9>20>50 — טרנד עולה חזק 📈"
            result["score"] += 18
            result["trend"] = "עולה חזק"
            result["signals"].append("EMA bullish alignment")
        elif price > ema9 > ema20:
            result["ema_signal"] = "מחיר מעל EMA 9>20 — טרנד עולה"
            result["score"] += 10
            result["trend"] = "עולה"
        elif price < ema9 < ema20 < ema50:
            result["ema_signal"] = "מחיר מתחת EMA 9<20<50 — טרנד יורד חזק 📉"
            result["score"] -= 15
            result["trend"] = "יורד חזק"
            result["warnings"].append("EMA bearish alignment")
        elif price < ema20:
            result["ema_signal"] = "מחיר מתחת EMA20 — זהירות"
            result["score"] -= 6
            result["trend"] = "יורד"
        else:
            result["ema_signal"] = "מחיר בין ממוצעים — צפה"
            result["trend"] = "צידי"

        # ── Bollinger Bands ──
        sma20   = df["Close"].rolling(20).mean()
        std20   = df["Close"].rolling(20).std()
        bb_up   = float((sma20 + 2 * std20).iloc[-1])
        bb_low  = float((sma20 - 2 * std20).iloc[-1])
        bb_mid  = float(sma20.iloc[-1])
        bb_pct  = (price - bb_low) / (bb_up - bb_low) if bb_up != bb_low else 0.5
        bb_width = (bb_up - bb_low) / bb_mid * 100

        if bb_pct <= 0.05:
            result["bb_signal"] = f"מגע ברצועה התחתונה — bounce פוטנציאלי 🟢"
            result["score"] += 15
        elif bb_pct >= 0.95:
            result["bb_signal"] = f"מגע ברצועה העליונה — התנגדות 🔴"
            result["score"] -= 8
        elif bb_width < 3:
            result["bb_signal"] = f"Squeeze — פריצה מתקרבת ⚡"
            result["score"] += 10
            result["signals"].append("BB squeeze")
        elif bb_pct > 0.5:
            result["bb_signal"] = f"בחצי עליון — מומנטום חיובי"
            result["score"] += 3
        else:
            result["bb_signal"] = f"בחצי תחתון — ניטרלי"

        # ── נפח יחסי ──
        avg_vol = float(df["Volume"].rolling(20).mean().iloc[-1])
        today_vol = float(df["Volume"].iloc[-1])
        vol_ratio = today_vol / avg_vol if avg_vol > 0 else 1

        if vol_ratio >= 3:
            result["volume_signal"] = f"נפח פי {vol_ratio:.0f} — עניין מוסדי! 🔥"
            result["score"] += 20
        elif vol_ratio >= 2:
            result["volume_signal"] = f"נפח פי {vol_ratio:.1f} — עניין גבוה"
            result["score"] += 10
        elif vol_ratio >= 1.3:
            result["volume_signal"] = f"נפח מעל הממוצע x{vol_ratio:.1f}"
            result["score"] += 4
        else:
            result["volume_signal"] = f"נפח רגיל x{vol_ratio:.1f}"

        # ── תמיכה והתנגדות (20 ימים) ──
        result["support"]    = round(float(df["Low"].rolling(20).min().iloc[-1]), 2)
        result["resistance"] = round(float(df["High"].rolling(20).max().iloc[-1]), 2)

        # ── תבניות נרות ──
        try:
            # הוספת עמודת Open אם חסרה
            if "Open" not in df.columns:
                df["Open"] = df["Close"].shift(1)
            result["candle_patterns"] = _detect_candle_patterns(df)
            for p in result["candle_patterns"]:
                if "עלייה" in p or "Bullish" in p or "בוקר" in p or "פטיש" in p:
                    result["score"] += 10
                elif "ירידה" in p or "Bearish" in p or "ערב" in p:
                    result["score"] -= 8
        except Exception:
            pass

        # ── סיכום ──
        result["score"] = max(-100, min(100, result["score"]))
        sig_text = f"{len(result['signals'])} אותות חיוביים" if result["signals"] else ""
        warn_text = f"{len(result['warnings'])} אזהרות" if result["warnings"] else ""
        result["summary"] = " | ".join(filter(None, [
            f"טרנד: {result['trend']}",
            f"RSI {rsi:.0f}",
            sig_text,
            warn_text
        ]))

    except Exception as e:
        result["summary"] = f"שגיאה בניתוח טכני: {e}"

    return result


def run(tickers):
    """מריץ ניתוח טכני על רשימת מניות"""
    print(f"🕯️  [סוכן טכני] מנתח {len(tickers)} מניות...")
    results = {}
    bullish = 0

    for ticker in tickers:
        r = analyze(ticker)
        results[ticker] = r
        if r["score"] > 20:
            bullish += 1

    print(f"✅ [סוכן טכני] {bullish}/{len(tickers)} מניות עם תמונה טכנית חיובית")
    return results


if __name__ == "__main__":
    test = ["TSLA", "NVDA", "COIN"]
    results = run(test)
    for t, r in results.items():
        print(f"\n{t}: ציון {r['score']} | {r['summary']}")
        for p in r["candle_patterns"]:
            print(f"  🕯️  {p}")
