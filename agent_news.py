#!/usr/bin/env python3
"""
📰 agent_news.py — סוכן החדשות והסנטימנט
==========================================
תפקיד: מנתח חדשות עדכניות לכל מניה.
מחפש: הפתעות ברווחים, שדרוגי אנליסטים, חדשות חיוביות/שליליות,
       פרסומי מוצר, שותפויות, חקירות רגולטוריות.
מחזיר: ציון סנטימנט וסיכום הסיפור.
"""

import yfinance as yf
from datetime import datetime, timezone


# מילות מפתח בוליות (חדשות חיוביות)
BULLISH_KEYWORDS = [
    "beat", "exceed", "record", "surge", "jump", "soar", "rally", "upgrade",
    "buy", "outperform", "strong", "growth", "profit", "revenue", "deal",
    "partnership", "contract", "approval", "fda", "patent", "launch",
    "guidance", "raise", "upside", "breakout", "milestone", "win",
    "expand", "acquisition", "merger", "buyback", "dividend"
]

# מילות מפתח דוביות (חדשות שליליות)
BEARISH_KEYWORDS = [
    "miss", "below", "cut", "downgrade", "sell", "underperform", "weak",
    "loss", "decline", "drop", "fall", "crash", "warning", "risk",
    "investigation", "lawsuit", "sec", "fraud", "recall", "delay",
    "layoff", "bankruptcy", "debt", "downside", "concern", "disappoint",
    "resign", "fired", "short", "overvalued"
]

# מילות מפתח קטליסט חזק (זזות מניות ביום)
CATALYST_KEYWORDS = [
    "earnings", "results", "quarter", "q1", "q2", "q3", "q4",
    "fda", "approval", "merger", "acquisition", "buyout",
    "split", "buyback", "guidance", "contract", "deal",
    "partnership", "investigation", "halt", "short squeeze"
]


def analyze_news(ticker):
    """
    מנתח חדשות עבור מניה ספציפית.

    Returns dict:
        sentiment_score: -100 עד +100
        sentiment_label: "חיובי חזק" / "חיובי" / "נייטרלי" / "שלילי" / "שלילי חזק"
        catalyst: האם יש קטליסט ביום? (True/False)
        catalyst_type: סוג הקטליסט
        headlines: רשימת כותרות חשובות
        news_count_today: כמה חדשות היום
        summary: סיכום קצר
    """
    result = {
        "ticker": ticker,
        "sentiment_score": 0,
        "sentiment_label": "נייטרלי",
        "catalyst": False,
        "catalyst_type": "",
        "headlines": [],
        "news_count_today": 0,
        "summary": "אין חדשות משמעותיות"
    }

    try:
        t = yf.Ticker(ticker)
        news = t.news

        if not news:
            return result

        today_ts = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0).timestamp()

        bullish_score = 0
        bearish_score  = 0
        catalyst_found = ""
        headlines_today = []
        headlines_recent = []

        for article in news[:20]:  # עד 20 חדשות אחרונות
            title = (article.get("title") or "").lower()
            pub_time = article.get("providerPublishTime", 0)
            is_today = pub_time > today_ts

            if not title:
                continue

            # ניקוד סנטימנט
            bull = sum(1 for kw in BULLISH_KEYWORDS if kw in title)
            bear = sum(1 for kw in BEARISH_KEYWORDS if kw in title)

            # חדשות היום מקבלות משקל כפול
            weight = 2 if is_today else 1
            bullish_score += bull * weight
            bearish_score += bear * weight

            # קטליסט?
            for kw in CATALYST_KEYWORDS:
                if kw in title:
                    catalyst_found = kw
                    break

            # שמירת כותרות
            original_title = article.get("title", "")
            if is_today:
                headlines_today.append(original_title)
                result["news_count_today"] += 1
            elif len(headlines_recent) < 3:
                headlines_recent.append(original_title)

        # חישוב ציון סופי
        raw_score = (bullish_score - bearish_score) * 10
        result["sentiment_score"] = max(-100, min(100, raw_score))
        result["catalyst"] = bool(catalyst_found)
        result["catalyst_type"] = catalyst_found

        # תיוג
        s = result["sentiment_score"]
        if s >= 40:
            result["sentiment_label"] = "חיובי חזק 🟢🟢"
        elif s >= 15:
            result["sentiment_label"] = "חיובי 🟢"
        elif s <= -40:
            result["sentiment_label"] = "שלילי חזק 🔴🔴"
        elif s <= -15:
            result["sentiment_label"] = "שלילי 🔴"
        else:
            result["sentiment_label"] = "נייטרלי ⚪"

        # כותרות
        result["headlines"] = (headlines_today + headlines_recent)[:4]

        # סיכום
        parts = []
        if result["news_count_today"] > 0:
            parts.append(f"{result['news_count_today']} חדשות היום")
        if catalyst_found:
            parts.append(f"קטליסט: {catalyst_found}")
        if bullish_score > 0:
            parts.append(f"{bullish_score} אותות חיוביים")
        if bearish_score > 0:
            parts.append(f"{bearish_score} אותות שליליים")
        result["summary"] = " | ".join(parts) if parts else "ללא חדשות בולטות"

    except Exception as e:
        result["summary"] = f"שגיאה בטעינת חדשות: {e}"

    return result


def run(tickers):
    """
    מריץ ניתוח חדשות על רשימת מניות.

    Returns:
        dict: {ticker -> news_result}
    """
    print(f"📰 [סוכן חדשות] מנתח חדשות עבור {len(tickers)} מניות...")
    results = {}
    bullish_count = 0
    catalyst_count = 0

    for ticker in tickers:
        r = analyze_news(ticker)
        results[ticker] = r
        if r["sentiment_score"] > 15:
            bullish_count += 1
        if r["catalyst"]:
            catalyst_count += 1

    print(f"✅ [סוכן חדשות] {bullish_count} מניות עם סנטימנט חיובי, {catalyst_count} עם קטליסט")
    return results


if __name__ == "__main__":
    test = ["TSLA", "NVDA", "COIN", "AMD"]
    results = run(test)
    for t, r in results.items():
        print(f"\n{t}: {r['sentiment_label']} | {r['summary']}")
        for h in r["headlines"][:2]:
            print(f"  📰 {h}")
