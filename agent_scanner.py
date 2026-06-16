#!/usr/bin/env python3
"""
🔭 agent_scanner.py — סוכן הסריקה
====================================
תפקיד: מוצא כל בוקר אילו מניות שוות בדיקה.
מסתכל על: נפח מסחר חריג, תנועת מחיר גדולה, מניות שחם בשוק.
מחזיר רשימה מדורגת של מועמדות לניתוח עמוק.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# כל המניות שהסוכן יודע לסרוק
FULL_UNIVERSE = [
    # טכנולוגיה ומגה-קאפ
    "AAPL", "MSFT", "NVDA", "AMD", "GOOGL", "META", "AMZN", "TSLA",
    # פינטק וקריפטו
    "COIN", "HOOD", "SQ", "PYPL", "MSTR",
    # מניות ספקולטיביות חמות
    "PLTR", "SOFI", "RIVN", "MARA", "SMCI", "IONQ", "SOUN", "RGTI",
    "QBTS", "BBAI", "ARRY", "HIMS", "ARM",
    # שבבים
    "AVGO", "QCOM", "MU", "INTC", "TSM",
    # ביומד וקנאביס
    "MRNA", "BNTX",
    # סינים / EV
    "NIO", "XPEV", "BABA", "LCID",
    # בידור ומדיה
    "NFLX", "DIS", "RBLX", "SNAP", "UBER", "ROKU",
    # עוד ספקולטיביות
    "GME", "AMC", "FFIE", "MULN",
]


def run(top_n=25):
    """
    מריץ את הסריקה ומחזיר רשימת מועמדות מדורגת.

    Returns:
        list of dict: [{"ticker", "score", "reason", "change_pct", "volume_ratio", "price"}]
    """
    print("🔭 [סוכן סריקה] מתחיל לסרוק את השוק...")

    candidates = []

    try:
        # שליפת נתוני 5 ימים לכל המניות בבת אחת
        raw = yf.download(
            FULL_UNIVERSE,
            period="5d",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True
        )

        if raw.empty:
            print("⚠️  [סוכן סריקה] לא הצלחתי למשוך נתונים")
            return _fallback_list()

        close  = raw["Close"]
        volume = raw["Volume"]
        high   = raw["High"]
        low    = raw["Low"]

        for ticker in FULL_UNIVERSE:
            try:
                if ticker not in close.columns:
                    continue

                prices  = close[ticker].dropna()
                volumes = volume[ticker].dropna()

                if len(prices) < 2 or len(volumes) < 2:
                    continue

                today_price  = float(prices.iloc[-1])
                prev_price   = float(prices.iloc[-2])
                today_vol    = float(volumes.iloc[-1])
                avg_vol_4d   = float(volumes.iloc[:-1].mean())

                if today_price <= 0 or prev_price <= 0 or avg_vol_4d <= 0:
                    continue

                change_pct   = (today_price - prev_price) / prev_price * 100
                volume_ratio = today_vol / avg_vol_4d  # כמה פי הנפח הרגיל

                # ניקוד
                score  = 0
                reasons = []

                # תנועת מחיר
                abs_change = abs(change_pct)
                if abs_change >= 8:
                    score += 35
                    reasons.append(f"תנועה חדה {change_pct:+.1f}%")
                elif abs_change >= 5:
                    score += 25
                    reasons.append(f"תנועה חזקה {change_pct:+.1f}%")
                elif abs_change >= 3:
                    score += 15
                    reasons.append(f"תנועה {change_pct:+.1f}%")
                elif abs_change >= 1.5:
                    score += 5

                # נפח מסחר
                if volume_ratio >= 4:
                    score += 35
                    reasons.append(f"נפח פי {volume_ratio:.0f} מהרגיל!")
                elif volume_ratio >= 2.5:
                    score += 25
                    reasons.append(f"נפח פי {volume_ratio:.1f}")
                elif volume_ratio >= 1.5:
                    score += 12
                    reasons.append(f"נפח מוגבר x{volume_ratio:.1f}")

                # מחיר מינימלי (לא פני סטוק)
                if today_price < 1:
                    score -= 20
                elif today_price < 3:
                    score -= 8

                # נפח מינימלי אבסולוטי (מסחר יומי דורש נזילות)
                if today_vol < 1_000_000:
                    score -= 15
                elif today_vol < 3_000_000:
                    score -= 5

                if score > 0:
                    candidates.append({
                        "ticker":       ticker,
                        "score":        round(score),
                        "reason":       " | ".join(reasons) if reasons else "תנועה רגילה",
                        "change_pct":   round(change_pct, 2),
                        "volume_ratio": round(volume_ratio, 1),
                        "volume":       int(today_vol),
                        "price":        round(today_price, 2),
                    })

            except Exception:
                continue

    except Exception as e:
        print(f"⚠️  [סוכן סריקה] שגיאה: {e}")
        return _fallback_list()

    # מיון וחיתוך
    candidates.sort(key=lambda x: x["score"], reverse=True)
    result = candidates[:top_n]

    print(f"✅ [סוכן סריקה] נמצאו {len(candidates)} מועמדות, בחרתי {len(result)} מובילות:")
    for c in result[:8]:
        arrow = "📈" if c["change_pct"] > 0 else "📉"
        print(f"   {arrow} {c['ticker']:6s} | {c['change_pct']:+.1f}% | נפח x{c['volume_ratio']} | ניקוד {c['score']}")

    return result


def _fallback_list():
    """רשימת בסיס אם הסריקה נכשלת"""
    fallback = ["TSLA","NVDA","AMD","AAPL","META","COIN","PLTR","MARA","SMCI","SOFI"]
    return [{"ticker": t, "score": 50, "reason": "רשימת בסיס", "change_pct": 0,
             "volume_ratio": 1.0, "volume": 10_000_000, "price": 0} for t in fallback]


if __name__ == "__main__":
    results = run()
    print("\nתוצאות סריקה:")
    for r in results:
        print(f"  {r['ticker']}: {r['reason']}")
