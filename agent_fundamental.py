#!/usr/bin/env python3
"""
📊 agent_fundamental.py — סוכן הפונדמנטלים
============================================
תפקיד: מנתח את הבסיס הפיננסי של כל מניה.
בודק: דוחות רווח (earnings), המלצות אנליסטים, יעד מחיר,
       מכפיל רווח, גידול הכנסות, short interest.
רמת: אנליסט מוסדי בנק השקעות.
"""

import yfinance as yf
from datetime import datetime, timezone, timedelta


def analyze(ticker):
    """
    ניתוח פונדמנטלי מלא.

    Returns dict עם ממצאים ומסקנה.
    """
    result = {
        "ticker": ticker,
        "earnings_date": None,
        "earnings_days_away": None,
        "last_eps_surprise": None,    # % הפתעה בדוח האחרון
        "analyst_rating": "לא ידוע",
        "analyst_target": None,
        "upside_pct": None,           # % פוטנציאל עלייה ליעד
        "pe_ratio": None,
        "revenue_growth": None,
        "short_interest": None,
        "score": 0,
        "signals": [],
        "warnings": [],
        "summary": ""
    }

    try:
        t = yf.Ticker(ticker)

        # ── מידע כללי ──
        info = t.info or {}
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0

        # ── תאריך דוח הבא ──
        try:
            cal = t.calendar
            if cal is not None and not (hasattr(cal, 'empty') and cal.empty):
                if isinstance(cal, dict):
                    earnings_date = cal.get("Earnings Date")
                    if earnings_date and hasattr(earnings_date, '__iter__'):
                        earnings_date = list(earnings_date)[0] if earnings_date else None
                elif hasattr(cal, 'iloc'):
                    earnings_date = cal.iloc[0, 0] if len(cal) > 0 else None
                else:
                    earnings_date = None

                if earnings_date:
                    if hasattr(earnings_date, 'date'):
                        ed = earnings_date.date()
                    else:
                        ed = earnings_date
                    days_away = (ed - datetime.now().date()).days
                    result["earnings_date"] = str(ed)
                    result["earnings_days_away"] = days_away

                    if 0 <= days_away <= 3:
                        result["score"] += 20
                        result["signals"].append(f"דוח רווחים בעוד {days_away} ימים! 🔥")
                    elif days_away < 0 and days_away >= -5:
                        result["score"] += 10
                        result["signals"].append("דוח רווחים רלוונטי לאחרונה")
        except Exception:
            pass

        # ── הפתעת EPS אחרונה ──
        try:
            hist_earnings = t.earnings_history
            if hist_earnings is not None and not hist_earnings.empty:
                last = hist_earnings.iloc[-1]
                eps_est  = last.get("epsEstimate") or last.get("EPS Estimate") or 0
                eps_act  = last.get("epsActual")   or last.get("Reported EPS") or 0
                if eps_est and eps_est != 0:
                    surprise = (eps_act - eps_est) / abs(eps_est) * 100
                    result["last_eps_surprise"] = round(surprise, 1)
                    if surprise > 10:
                        result["score"] += 15
                        result["signals"].append(f"הפתעת EPS +{surprise:.0f}%! 💰")
                    elif surprise > 0:
                        result["score"] += 5
                    elif surprise < -10:
                        result["score"] -= 12
                        result["warnings"].append(f"החמצת EPS {surprise:.0f}%")
        except Exception:
            pass

        # ── המלצות אנליסטים ──
        try:
            recs = t.recommendations
            if recs is not None and not recs.empty:
                # הסינון לחודש האחרון
                recent = recs.tail(10)
                grades = []
                for _, row in recent.iterrows():
                    grade = (row.get("To Grade") or row.get("toGrade") or "").lower()
                    grades.append(grade)

                buy_count    = sum(1 for g in grades if any(x in g for x in ["buy","outperform","overweight","strong buy"]))
                sell_count   = sum(1 for g in grades if any(x in g for x in ["sell","underperform","underweight"]))
                hold_count   = sum(1 for g in grades if "hold" in g or "neutral" in g or "market" in g)

                total = buy_count + sell_count + hold_count
                if total > 0:
                    buy_pct = buy_count / total
                    if buy_pct >= 0.7:
                        result["analyst_rating"] = f"Strong Buy ({buy_count}/{total} אנליסטים) 🌟"
                        result["score"] += 15
                        result["signals"].append("רוב האנליסטים ממליצים קנייה")
                    elif buy_pct >= 0.5:
                        result["analyst_rating"] = f"Buy ({buy_count}/{total})"
                        result["score"] += 8
                    elif sell_count > buy_count:
                        result["analyst_rating"] = f"Sell ({sell_count}/{total} מוכרים)"
                        result["score"] -= 10
                        result["warnings"].append("אנליסטים ממליצים מכירה")
                    else:
                        result["analyst_rating"] = f"Hold ({hold_count}/{total})"
        except Exception:
            pass

        # ── יעד מחיר אנליסטים ──
        try:
            target = info.get("targetMeanPrice") or info.get("targetMedianPrice")
            if target and current_price and current_price > 0:
                result["analyst_target"] = round(float(target), 2)
                upside = (float(target) - current_price) / current_price * 100
                result["upside_pct"] = round(upside, 1)
                if upside > 25:
                    result["score"] += 15
                    result["signals"].append(f"יעד אנליסטים +{upside:.0f}% מעל המחיר!")
                elif upside > 10:
                    result["score"] += 7
                    result["signals"].append(f"יעד אנליסטים +{upside:.0f}%")
                elif upside < -10:
                    result["score"] -= 10
                    result["warnings"].append(f"מחיר מעל יעד אנליסטים {upside:.0f}%")
        except Exception:
            pass

        # ── מכפיל רווח P/E ──
        try:
            pe = info.get("trailingPE") or info.get("forwardPE")
            if pe and pe > 0:
                result["pe_ratio"] = round(float(pe), 1)
                if pe > 200:
                    result["warnings"].append(f"P/E גבוה מאוד: {pe:.0f}x")
                elif pe < 0:
                    result["warnings"].append("הפסד נקי")
        except Exception:
            pass

        # ── Short Interest ──
        try:
            short_pct = info.get("shortPercentOfFloat")
            if short_pct:
                result["short_interest"] = round(float(short_pct) * 100, 1)
                if result["short_interest"] > 20:
                    result["score"] += 12
                    result["signals"].append(f"Short squeeze פוטנציאלי! ({result['short_interest']:.0f}% short)")
                elif result["short_interest"] > 10:
                    result["signals"].append(f"short interest גבוה {result['short_interest']:.0f}%")
        except Exception:
            pass

        # ── סיכום ──
        result["score"] = max(-50, min(50, result["score"]))
        parts = [result["analyst_rating"]]
        if result["upside_pct"]:
            parts.append(f"פוטנציאל +{result['upside_pct']:.0f}%")
        if result["earnings_days_away"] is not None and result["earnings_days_away"] >= 0:
            parts.append(f"דוח בעוד {result['earnings_days_away']}י׳")
        result["summary"] = " | ".join(p for p in parts if p and p != "לא ידוע")

    except Exception as e:
        result["summary"] = f"שגיאה בניתוח פונדמנטלי: {e}"

    return result


def run(tickers):
    """מריץ ניתוח פונדמנטלי על רשימת מניות"""
    print(f"📊 [סוכן פונדמנטלי] מנתח {len(tickers)} מניות...")
    results = {}
    with_catalyst = 0

    for ticker in tickers:
        r = analyze(ticker)
        results[ticker] = r
        if r["score"] > 10:
            with_catalyst += 1

    print(f"✅ [סוכן פונדמנטלי] {with_catalyst} מניות עם אותות פונדמנטליים חיוביים")
    return results


if __name__ == "__main__":
    test = ["TSLA", "NVDA", "COIN"]
    results = run(test)
    for t, r in results.items():
        print(f"\n{t}: ציון {r['score']} | {r['summary']}")
        for s in r["signals"]:
            print(f"  ✅ {s}")
        for w in r["warnings"]:
            print(f"  ⚠️  {w}")
