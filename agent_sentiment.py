#!/usr/bin/env python3
"""
🧠 agent_sentiment.py — סוכן הסנטימנט המתקדם
===============================================
מקורות:
1. Finnhub API (חינמי עם מפתח) — סנטימנט חדשות מקצועי
2. SEC EDGAR — קניות/מכירות פנים (insider trading) חינמי!
3. Alpha Vantage (חינמי עם מפתח) — סנטימנט חדשות + RSI מדויק
4. Stocktwits — סנטימנט רשתות חברתיות (ללא מפתח)

מפתחות API נקראים מ-GitHub Secrets (env variables).
אם אין מפתח — הסוכן עובד בצמצום ללא אותו מקור.
"""

import os
import requests
from datetime import datetime, timedelta, timezone


FINNHUB_KEY    = os.environ.get("FINNHUB_API_KEY", "")
ALPHAVANTAGE_KEY = os.environ.get("ALPHAVANTAGE_API_KEY", "")


# ─────────────────────────────────────────────
# 1. FINNHUB — סנטימנט חדשות מקצועי
# ─────────────────────────────────────────────
def get_finnhub_sentiment(ticker):
    """
    Finnhub מנתח כמה מאות אלפי מאמרים ביום ומחשב ציון סנטימנט.
    דורש מפתח חינמי מ-finnhub.io
    """
    if not FINNHUB_KEY:
        return None

    try:
        url = f"https://finnhub.io/api/v1/news-sentiment?symbol={ticker}&token={FINNHUB_KEY}"
        r = requests.get(url, timeout=8)
        if r.status_code != 200:
            return None

        data = r.json()
        buzz  = data.get("buzz", {})
        sent  = data.get("sentiment", {})

        score = float(sent.get("bullishPercent", 0.5)) * 100 - 50  # -50 עד +50

        return {
            "source": "Finnhub",
            "bullish_pct": round(float(sent.get("bullishPercent", 0)) * 100, 1),
            "bearish_pct": round(float(sent.get("bearishPercent", 0)) * 100, 1),
            "articles_count": buzz.get("articlesInLastWeek", 0),
            "buzz_score": buzz.get("buzz", 0),
            "score": round(score, 1)
        }
    except Exception:
        return None


# ─────────────────────────────────────────────
# 2. SEC EDGAR — Insider Trading (חינמי!)
# ─────────────────────────────────────────────
def get_insider_trading(ticker):
    """
    מושך קניות/מכירות של בעלי תפקידים בחברה מ-SEC EDGAR.
    כשמנהלים קונים מניות שלהם — זה אות חיובי חזק!
    ללא צורך במפתח API.
    """
    try:
        # שלב 1: מציאת CIK (מספר זיהוי SEC) לפי ticker
        search_url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt=2024-01-01&forms=4"
        headers = {"User-Agent": "StockAgents research@stockagents.com"}

        r = requests.get(
            f"https://data.sec.gov/submissions/CIK{ticker}.json",
            headers=headers, timeout=8
        )

        # חלופה: שימוש ב-OpenInsider (ללא API)
        oi_url = f"https://openinsider.com/screener?s={ticker}&o=&pl=&ph=&ll=&lh=&fd=30&fdr=&td=0&tdr=&fdlyl=&fdlyh=&daysago=30&xs=1&vl=&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=10&page=1"

        # מאחר שOpenInsider לא מחזיר JSON נקי, נשתמש ב-yfinance insider
        import yfinance as yf
        t = yf.Ticker(ticker)

        try:
            insider = t.insider_transactions
            if insider is not None and not insider.empty:
                # 30 ימים אחרונים
                recent = insider.head(10)
                buys  = 0
                sells = 0
                buy_value  = 0
                sell_value = 0

                for _, row in recent.iterrows():
                    shares = row.get("Shares", 0) or 0
                    value  = row.get("Value", 0) or 0
                    text   = str(row.get("Transaction", "") or row.get("Text", "")).lower()

                    if "purchase" in text or "buy" in text or "acquisition" in text:
                        buys += 1
                        buy_value += abs(value)
                    elif "sale" in text or "sell" in text or "disposition" in text:
                        sells += 1
                        sell_value += abs(value)

                if buys + sells == 0:
                    return None

                score = (buys - sells) * 10
                if buy_value > sell_value * 2:
                    score += 15

                label = ""
                if buys > sells * 2:
                    label = f"📈 {buys} קניות פנים — אות חיובי חזק!"
                elif sells > buys * 2:
                    label = f"📉 {sells} מכירות פנים — זהירות"
                else:
                    label = f"מעורב ({buys} קניות, {sells} מכירות)"

                return {
                    "source": "SEC/yfinance",
                    "buys": buys,
                    "sells": sells,
                    "buy_value": buy_value,
                    "sell_value": sell_value,
                    "label": label,
                    "score": min(30, max(-30, score))
                }
        except Exception:
            pass

        return None

    except Exception:
        return None


# ─────────────────────────────────────────────
# 3. ALPHA VANTAGE — סנטימנט חדשות AI
# ─────────────────────────────────────────────
def get_alphavantage_sentiment(ticker):
    """
    Alpha Vantage משתמש ב-AI לניתוח סנטימנט חדשות.
    חינמי עד 25 קריאות ביום.
    """
    if not ALPHAVANTAGE_KEY:
        return None

    try:
        url = (f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT"
               f"&tickers={ticker}&limit=50&apikey={ALPHAVANTAGE_KEY}")
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None

        data = r.json()
        feed = data.get("feed", [])
        if not feed:
            return None

        scores = []
        today_str = datetime.now().strftime("%Y%m%d")

        for article in feed[:20]:
            pub = article.get("time_published", "")[:8]
            is_today = pub == today_str

            for ts in article.get("ticker_sentiment", []):
                if ts.get("ticker") == ticker:
                    score = float(ts.get("ticker_sentiment_score", 0))
                    weight = 2 if is_today else 1
                    scores.extend([score] * weight)

        if not scores:
            return None

        avg = sum(scores) / len(scores)

        if avg > 0.15:
            label = "חיובי חזק 🟢"
        elif avg > 0.05:
            label = "חיובי 🟡"
        elif avg < -0.15:
            label = "שלילי חזק 🔴"
        elif avg < -0.05:
            label = "שלילי 🟠"
        else:
            label = "נייטרלי ⚪"

        return {
            "source": "Alpha Vantage AI",
            "score": round(avg * 100, 1),
            "label": label,
            "articles": len(feed)
        }
    except Exception:
        return None


# ─────────────────────────────────────────────
# 4. STOCKTWITS — סנטימנט רשתות חברתיות
# ─────────────────────────────────────────────
def get_stocktwits_sentiment(ticker):
    """
    Stocktwits — טוויטר של שוק ההון.
    מראה כמה מהמשקיעים הקמעונאיים אופטימיים/פסימיים.
    ללא מפתח API.
    """
    try:
        url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
        r = requests.get(url, timeout=6)
        if r.status_code != 200:
            return None

        messages = r.json().get("messages", [])
        if not messages:
            return None

        bulls = sum(1 for m in messages if m.get("entities", {}).get("sentiment", {}).get("basic") == "Bullish")
        bears = sum(1 for m in messages if m.get("entities", {}).get("sentiment", {}).get("basic") == "Bearish")
        total_with_sentiment = bulls + bears

        if total_with_sentiment == 0:
            return None

        bull_pct = bulls / total_with_sentiment * 100
        score = (bull_pct - 50) * 0.6  # -30 עד +30

        if bull_pct >= 70:
            label = f"😎 {bull_pct:.0f}% אופטימיים (Stocktwits)"
        elif bull_pct >= 55:
            label = f"🙂 {bull_pct:.0f}% אופטימיים"
        elif bull_pct <= 30:
            label = f"😟 {100-bull_pct:.0f}% פסימיים"
        else:
            label = f"😐 מעורב {bull_pct:.0f}%/{100-bull_pct:.0f}%"

        return {
            "source": "Stocktwits",
            "bullish_pct": round(bull_pct, 1),
            "bearish_pct": round(100 - bull_pct, 1),
            "messages": len(messages),
            "label": label,
            "score": round(score, 1)
        }
    except Exception:
        return None


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def analyze(ticker):
    """ניתוח סנטימנט מלא ממספר מקורות"""
    result = {
        "ticker": ticker,
        "finnhub": None,
        "alphavantage": None,
        "stocktwits": None,
        "insider": None,
        "combined_score": 0,
        "summary": ""
    }

    finnhub = get_finnhub_sentiment(ticker)
    av      = get_alphavantage_sentiment(ticker)
    st      = get_stocktwits_sentiment(ticker)
    insider = get_insider_trading(ticker)

    result["finnhub"]      = finnhub
    result["alphavantage"] = av
    result["stocktwits"]   = st
    result["insider"]      = insider

    # ציון משולב
    scores  = []
    sources = []

    if finnhub:
        scores.append(finnhub["score"])
        sources.append(f"Finnhub: {finnhub['bullish_pct']}% חיובי")
    if av:
        scores.append(av["score"])
        sources.append(f"AV: {av['label']}")
    if st:
        scores.append(st["score"])
        sources.append(st["label"])
    if insider:
        scores.append(insider["score"])
        sources.append(insider["label"])

    result["combined_score"] = round(sum(scores) / len(scores)) if scores else 0
    result["summary"] = " | ".join(sources) if sources else "אין נתוני סנטימנט"

    return result


def run(tickers):
    """מריץ ניתוח סנטימנט על רשימת מניות"""
    print(f"🧠 [סוכן סנטימנט] מנתח {len(tickers)} מניות...")
    sources_used = []
    if FINNHUB_KEY:    sources_used.append("Finnhub")
    if ALPHAVANTAGE_KEY: sources_used.append("Alpha Vantage")
    sources_used.extend(["Stocktwits", "SEC Insider"])
    print(f"   מקורות: {', '.join(sources_used)}")

    results = {}
    for ticker in tickers:
        results[ticker] = analyze(ticker)

    print(f"✅ [סוכן סנטימנט] סיים")
    return results


if __name__ == "__main__":
    test = ["TSLA", "NVDA", "COIN"]
    results = run(test)
    for t, r in results.items():
        print(f"\n{t}: ציון {r['combined_score']} | {r['summary']}")
