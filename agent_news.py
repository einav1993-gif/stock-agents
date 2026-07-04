#!/usr/bin/env python3
"""
📰 agent_news.py — סוכן החדשות והסנטימנט
==========================================
תפקיד: מנתח חדשות עדכניות לכל מניה.
מחפש: הפתעות ברווחים, שדרוגי אנליסטים, חדשות חיוביות/שליליות,
       פרסומי מוצר, שותפויות, חקירות רגולטוריות.
מחזיר: ציון סנטימנט וסיכום הסיפור.
"""

import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

import yfinance as yf


def _headlines_from_google_rss(ticker):
    """
    Google News RSS — חינמי, בלי מפתח, עובד משרתים.
    מחזיר רשימת (כותרת, האם_מהיום).
    """
    try:
        q = urllib.parse.quote(f'"{ticker}" stock when:2d')
        url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            root = ET.fromstring(resp.read())

        today = datetime.now(timezone.utc).date()
        out = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            pub = item.findtext("pubDate") or ""
            if not title:
                continue
            is_today = False
            try:
                dt = datetime.strptime(pub[:16], "%a, %d %b %Y")
                is_today = dt.date() >= today - timedelta(days=1)
            except Exception:
                pass
            out.append((title, is_today))
            if len(out) >= 20:
                break
        return out
    except Exception:
        return []


def _headlines_from_yfinance(ticker):
    """מקור גיבוי — Yahoo (לרוב חסום בענן, עובד מקומית)."""
    try:
        news = yf.Ticker(ticker).news or []
        today_ts = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0).timestamp()
        out = []
        for a in news[:20]:
            content = a.get("content") or a
            title = (content.get("title") or a.get("title") or "").strip()
            pub_time = a.get("providerPublishTime", 0)
            if title:
                out.append((title, pub_time > today_ts))
        return out
    except Exception:
        return []


def get_headlines(ticker):
    """שרשרת מקורות: Google News RSS ← Yahoo. מחזיר [(כותרת, מהיום?)]."""
    headlines = _headlines_from_google_rss(ticker)
    if not headlines:
        headlines = _headlines_from_yfinance(ticker)
    return headlines


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
        headlines = get_headlines(ticker)

        if not headlines:
            result["summary"] = "לא נמצאו חדשות (כל המקורות)"
            return result

        bullish_score = 0
        bearish_score  = 0
        catalyst_found = ""
        headlines_today = []
        headlines_recent = []

        for original_title, is_today in headlines:
            title = original_title.lower()

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
