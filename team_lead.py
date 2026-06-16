#!/usr/bin/env python3
"""
👑 team_lead.py — ראש צוות הסוכנים
=====================================
מנהל 7 סוכנים מקצועיים:
1. 🔭 סוכן סריקה      — מוצא מניות חמות
2. 🌍 סוכן מאקרו      — VIX, Fear&Greed, סקטורים
3. 📰 סוכן חדשות      — סנטימנט חדשות
4. 🧠 סוכן סנטימנט    — Finnhub, Stocktwits, SEC Insider
5. 🕯️  סוכן טכני      — RSI, MACD, נרות יפניים
6. 📊 סוכן פונדמנטלי  — דוחות, אנליסטים, יעד מחיר
7. ⚖️  סוכן סיכון     — כניסה, עצירה, יעד
"""

import concurrent.futures
from datetime import datetime

import agent_scanner
import agent_macro
import agent_news
import agent_sentiment
import agent_technical
import agent_fundamental
import agent_risk


def _safe(fn, *args, name="סוכן"):
    try:
        return fn(*args)
    except Exception as e:
        print(f"⚠️  [{name}] שגיאה: {e}")
        return {}


def _score_one(ticker, macro, news_r, sent_r, tech_r, fund_r, risk_r):
    """
    מחשב ציון כולל למניה אחת ממכלול הסוכנים.

    משקלות:
    - טכני:        35% (הכי חשוב למסחר יומי)
    - מאקרו:       15% (תנאי שוק כלליים)
    - חדשות:       20%
    - סנטימנט:     10%
    - פונדמנטלי:   15%
    - סיכון:        5%
    """
    tech = tech_r.get(ticker, {})
    news = news_r.get(ticker, {})
    sent = sent_r.get(ticker, {})
    fund = fund_r.get(ticker, {})
    risk = risk_r.get(ticker, {})

    macro_score = macro.get("macro_score", 0)
    tech_score  = tech.get("score", 0)
    news_score  = news.get("sentiment_score", 0) * 0.5
    sent_score  = sent.get("combined_score", 0)
    fund_score  = fund.get("score", 0)
    risk_score  = risk.get("score", 0)

    total = (
        tech_score  * 0.35 +
        macro_score * 0.15 +
        news_score  * 0.20 +
        sent_score  * 0.10 +
        fund_score  * 0.15 +
        risk_score  * 0.05
    )

    # בונוסים
    if news.get("catalyst"):          total += 15
    if sent.get("insider", {}) and sent.get("insider", {}).get("buys", 0) > 1:
        total += 10   # בעלי תפקידים קונים — אות חזק
    days = fund.get("earnings_days_away")
    if days is not None and 0 <= days <= 3:
        total += 10   # דוח קרוב = תנועה צפויה

    # עונשים
    vix = macro.get("vix", {})
    if vix and vix.get("value", 0) > 30:
        total -= 15   # שוק בפאניקה — לא זמן לסחור

    total = round(max(-100, min(100, total)), 1)

    if total >= 60:
        decision = "🟢 קנייה חזקה"
    elif total >= 35:
        decision = "🟡 בחן מקרוב"
    elif total >= 10:
        decision = "⚪ המתן"
    else:
        decision = "🔴 הימנע"

    all_signals  = tech.get("signals", []) + fund.get("signals", [])
    all_warnings = tech.get("warnings", []) + fund.get("warnings", [])

    return {
        "ticker":       ticker,
        "total_score":  total,
        "decision":     decision,
        "tech":         tech,
        "news":         news,
        "sent":         sent,
        "fund":         fund,
        "risk":         risk,
        "macro":        macro,
        "all_signals":  all_signals,
        "all_warnings": all_warnings,
        "entry":        risk.get("entry_price"),
        "stop_loss":    risk.get("stop_loss"),
        "stop_pct":     risk.get("stop_loss_pct"),
        "target_1":     risk.get("target_1"),
        "target_2":     risk.get("target_2"),
        "shares":       risk.get("shares"),
        "max_loss":     risk.get("max_loss_usd"),
    }


def run():
    print("\n" + "╔" + "═"*60 + "╗")
    print("║  👑 ראש הצוות — מפעיל 7 סוכני ניתוח מקצועיים         ║")
    print("╚" + "═"*60 + "╝\n")

    # ── שלב 1: מאקרו — בודקים את מצב השוק לפני הכל ──
    print("📋 שלב 1: בדיקת מצב השוק הכללי...")
    macro = _safe(agent_macro.run, name="מאקרו")

    vix_val = macro.get("vix", {}).get("value", 18) if macro else 18
    fg_val  = macro.get("fear_greed", {}).get("value", 50) if macro else 50
    mkt_mood = macro.get("market", {}).get("mood", "") if macro else ""

    print(f"   🌡️  VIX: {vix_val} | Fear&Greed: {fg_val} | שוק: {mkt_mood}")

    # אזהרה אם השוק בפאניקה
    if vix_val > 35:
        print("   🚨 VIX גבוה מאוד! ראש הצוות ממליץ זהירות מרבית היום!")

    # ── שלב 2: סריקה ──
    print("\n📋 שלב 2: סריקת השוק למציאת מועמדות...")
    scan_results = _safe(agent_scanner.run, name="סורק")
    candidates = [r["ticker"] for r in scan_results] if scan_results else [
        "TSLA","NVDA","AMD","COIN","PLTR","META","AAPL","MSFT","MARA","SOFI"
    ]
    print(f"   נבחרו {len(candidates)} מועמדות")

    # ── שלב 3: כל שאר הסוכנים במקביל ──
    print("\n📋 שלב 3: ניתוח מקביל — 5 סוכנים עובדים יחד...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        f_news = ex.submit(_safe, agent_news.run, candidates, "חדשות")
        f_sent = ex.submit(_safe, agent_sentiment.run, candidates, "סנטימנט")
        f_tech = ex.submit(_safe, agent_technical.run, candidates, "טכני")
        f_fund = ex.submit(_safe, agent_fundamental.run, candidates, "פונדמנטלי")
        f_risk = ex.submit(_safe, agent_risk.run, {t: None for t in candidates}, "סיכון")

        news_r = f_news.result()
        sent_r = f_sent.result()
        tech_r = f_tech.result()
        fund_r = f_fund.result()
        risk_r = f_risk.result()

    # ── שלב 4: ציון כולל ──
    print("\n📋 שלב 4: ראש הצוות מסכם ומדרג...")
    all_analyzed = []
    for ticker in candidates:
        s = _score_one(ticker, macro, news_r, sent_r, tech_r, fund_r, risk_r)
        all_analyzed.append(s)

    all_analyzed.sort(key=lambda x: x["total_score"], reverse=True)
    top5 = all_analyzed[:5]

    # ── דוח סיום ──
    print("\n" + "╔" + "═"*60 + "╗")
    print("║  📊 TOP 5 להיום                                         ║")
    print("╚" + "═"*60 + "╝")
    for i, s in enumerate(top5, 1):
        print(f"\n  #{i} {s['ticker']} | {s['decision']} | ציון {s['total_score']:.0f}")
        if s["entry"]:
            print(f"      כניסה ${s['entry']} | Stop ${s['stop_loss']} (-{s['stop_pct']}%) | יעד ${s['target_2']}")

    print(f"\n✅ ראש הצוות סיים | {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    return top5, all_analyzed


def get_full_team_report():
    top5, all_stocks = run()
    return {
        "top5":        top5,
        "all_stocks":  all_stocks,
        "generated_at": datetime.now().isoformat()
    }


if __name__ == "__main__":
    run()
