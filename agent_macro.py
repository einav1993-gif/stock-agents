#!/usr/bin/env python3
"""
🌍 agent_macro.py — סוכן המאקרו
==================================
מקורות מידע:
- Fear & Greed Index (CNN/Alternative.me) — חינמי, ללא מפתח
- VIX — מדד התנודתיות (יראת השוק) — דרך yfinance
- ביצועי סקטורים (XLK, XLF, XLE...) — דרך yfinance
- S&P 500 / NASDAQ מגמה יומית — דרך yfinance
- Put/Call Ratio — אינדיקטור סנטימנט אופציות
- מדד הדולר DXY — השפעה על מניות טכנולוגיה
"""

import requests
import yfinance as yf
from datetime import datetime


# ── ETFs לכל סקטור ──
SECTOR_ETFS = {
    "טכנולוגיה":   "XLK",
    "פיננסים":     "XLF",
    "אנרגיה":      "XLE",
    "בריאות":      "XLV",
    "צריכה":       "XLY",
    "תעשייה":      "XLI",
    "תקשורת":      "XLC",
    "נדל״ן":       "XLRE",
    "חומרים":      "XLB",
    "כלי עזר":     "XLU",
}


def get_fear_and_greed():
    """
    מושך את מדד הפחד/חמדנות מ-Alternative.me (חינמי, ללא מפתח API).
    0-25 = פחד קיצוני 😱 | 26-45 = פחד | 46-55 = נייטרלי | 56-75 = חמדנות | 76-100 = חמדנות קיצונית 🤑
    """
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=2", timeout=8)
        data = r.json()["data"]
        current = data[0]
        yesterday = data[1] if len(data) > 1 else None

        value = int(current["value"])
        label = current["value_classification"]

        # תרגום לעברית
        label_he = {
            "Extreme Fear":    "פחד קיצוני 😱",
            "Fear":            "פחד 😰",
            "Neutral":         "נייטרלי 😐",
            "Greed":           "חמדנות 😏",
            "Extreme Greed":   "חמדנות קיצונית 🤑"
        }.get(label, label)

        # שינוי מאתמול
        change = ""
        if yesterday:
            prev_val = int(yesterday["value"])
            diff = value - prev_val
            change = f"({'+' if diff > 0 else ''}{diff} מאתמול)"

        return {
            "value": value,
            "label": label_he,
            "change": change,
            "score_add": 0,
            "signal": ""
        }
    except Exception as e:
        return {"value": 50, "label": "נייטרלי", "change": "", "score_add": 0, "signal": f"שגיאה: {e}"}


def get_vix():
    """
    VIX — מדד התנודתיות/פחד של Wall Street.
    מתחת ל-15 = שקט | 15-20 = נורמלי | 20-30 = חרדה | מעל 30 = פאניקה
    """
    try:
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="2d")
        if hist.empty:
            return None

        current = float(hist["Close"].iloc[-1])
        prev    = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
        change  = current - prev

        if current < 15:
            label = "שקט מאוד 🟢 — שוק רגוע"
            score_add = 8
        elif current < 20:
            label = "נורמלי 🟡"
            score_add = 3
        elif current < 25:
            label = "מוגבר ⚠️ — זהירות"
            score_add = -5
        elif current < 30:
            label = "גבוה 🔴 — חרדה בשוק"
            score_add = -12
        else:
            label = "פאניקה 🚨 — אל תסחרי היום"
            score_add = -25

        return {
            "value": round(current, 2),
            "change": round(change, 2),
            "label": label,
            "score_add": score_add
        }
    except Exception as e:
        return {"value": 18, "label": "לא זמין", "change": 0, "score_add": 0}


def get_market_pulse():
    """
    מצב השוק הכללי — SPY, QQQ, IWM ביום הזה.
    """
    try:
        tickers = ["SPY", "QQQ", "IWM", "DXY"]
        data = yf.download(["SPY", "QQQ", "IWM"], period="2d", interval="1d",
                           auto_adjust=True, progress=False)

        results = {}
        close = data["Close"]
        for t in ["SPY", "QQQ", "IWM"]:
            if t in close.columns and len(close[t].dropna()) >= 2:
                today = float(close[t].iloc[-1])
                prev  = float(close[t].iloc[-2])
                pct   = (today - prev) / prev * 100
                results[t] = round(pct, 2)

        # מסקנה
        avg = sum(results.values()) / len(results) if results else 0
        if avg > 0.5:
            mood = "עולה 📈 — רוח גבית"
            score_add = 10
        elif avg > 0:
            mood = "קל עולה ↗️"
            score_add = 4
        elif avg > -0.5:
            mood = "שטוח ➡️"
            score_add = 0
        elif avg > -1:
            mood = "יורד קלות ↘️ — זהירות"
            score_add = -5
        else:
            mood = "יורד חזק 📉 — שוק חלש"
            score_add = -15

        return {
            "SPY": results.get("SPY", 0),
            "QQQ": results.get("QQQ", 0),
            "IWM": results.get("IWM", 0),
            "mood": mood,
            "score_add": score_add
        }
    except Exception as e:
        return {"SPY": 0, "QQQ": 0, "IWM": 0, "mood": "לא זמין", "score_add": 0}


def get_sector_performance():
    """
    ביצועי כל סקטור היום — מאפשר לזהות רוטציה.
    """
    try:
        etf_list = list(SECTOR_ETFS.values())
        data = yf.download(etf_list, period="2d", interval="1d",
                           auto_adjust=True, progress=False)

        sectors = {}
        close = data["Close"]
        for name, etf in SECTOR_ETFS.items():
            if etf in close.columns:
                vals = close[etf].dropna()
                if len(vals) >= 2:
                    pct = (float(vals.iloc[-1]) - float(vals.iloc[-2])) / float(vals.iloc[-2]) * 100
                    sectors[name] = round(pct, 2)

        # מיון
        sorted_sectors = sorted(sectors.items(), key=lambda x: x[1], reverse=True)
        top = sorted_sectors[:3]    # סקטורים חמים
        bottom = sorted_sectors[-3:] # סקטורים חלשים

        return {
            "all": dict(sorted_sectors),
            "hot": top,
            "weak": bottom
        }
    except Exception:
        return {"all": {}, "hot": [], "weak": []}


def run():
    """
    מריץ את כל ניתוחי המאקרו.
    Returns dict עם כל הנתונים.
    """
    print("🌍 [סוכן מאקרו] בודק מצב השוק הכללי...")

    fg  = get_fear_and_greed()
    vix = get_vix()
    mkt = get_market_pulse()
    sec = get_sector_performance()

    # ציון כולל למאקרו
    total_score = 0
    if vix:
        total_score += vix.get("score_add", 0)
    total_score += mkt.get("score_add", 0)

    # Fear & Greed — פחד קיצוני = הזדמנות קנייה (contrarian)
    fg_val = fg.get("value", 50)
    if fg_val < 25:
        total_score += 10  # פחד קיצוני = הזדמנות
    elif fg_val > 80:
        total_score -= 8   # חמדנות קיצונית = סיכון

    result = {
        "fear_greed": fg,
        "vix": vix,
        "market": mkt,
        "sectors": sec,
        "macro_score": round(total_score),
        "summary": _build_summary(fg, vix, mkt, sec)
    }

    print(f"✅ [סוכן מאקרו] Fear&Greed: {fg['value']} ({fg['label']}) | "
          f"VIX: {vix['value'] if vix else '—'} | "
          f"שוק: {mkt['mood']}")

    return result


def _build_summary(fg, vix, mkt, sec):
    parts = []
    parts.append(f"פחד/חמדנות: {fg['value']} — {fg['label']}")
    if vix:
        parts.append(f"VIX: {vix['value']} — {vix['label']}")
    parts.append(f"שוק: {mkt['mood']} (SPY {mkt['SPY']:+.1f}%)")
    if sec["hot"]:
        hot_str = ", ".join(f"{n} {p:+.1f}%" for n, p in sec["hot"][:2])
        parts.append(f"חם: {hot_str}")
    return " | ".join(parts)


if __name__ == "__main__":
    result = run()
    print(f"\nסיכום: {result['summary']}")
    print(f"ציון מאקרו: {result['macro_score']}")
    if result["sectors"]["hot"]:
        print("סקטורים חמים:")
        for name, pct in result["sectors"]["hot"]:
            print(f"  {name}: {pct:+.1f}%")
