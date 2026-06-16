#!/usr/bin/env python3
"""
👑 team_lead.py — ראש צוות הסוכנים
=====================================
תפקיד: מנהל ומתאם את כל הסוכנים.
מריץ אותם במקביל, אוסף את תוצאותיהם,
ומחליט מהן המניות הטובות ביותר להיום.

פלט סופי: TOP 5 מניות עם כל הניתוח המלא.
"""

import concurrent.futures
import json
import os
from datetime import datetime

import agent_scanner
import agent_news
import agent_technical
import agent_fundamental
import agent_risk


def _run_agent_safe(fn, *args, name="סוכן"):
    """מריץ סוכן ומחזיר תוצאה גם אם יש שגיאה"""
    try:
        return fn(*args)
    except Exception as e:
        print(f"⚠️  [{name}] שגיאה: {e}")
        return {}


def analyze_one_stock(ticker, news_results, tech_results, fund_results, risk_results):
    """מרכז את כל תוצאות הסוכנים עבור מניה אחת לציון כולל"""

    news = news_results.get(ticker, {})
    tech = tech_results.get(ticker, {})
    fund = fund_results.get(ticker, {})
    risk = risk_results.get(ticker, {})

    # ── ציון משוקלל ──
    # טכני:       40% (הכי חשוב למסחר יומי)
    # חדשות:      25%
    # פונדמנטלי:  20%
    # סיכון:      15%

    tech_score = tech.get("score", 0)
    news_score = news.get("sentiment_score", 0) * 0.5   # -100→+100 → -50→+50
    fund_score = fund.get("score", 0)
    risk_score = risk.get("score", 0)

    total = (
        tech_score * 0.40 +
        news_score * 0.25 +
        fund_score * 0.20 +
        risk_score * 0.15
    )

    # בונוס קטליסט (חדשות חמות = +15)
    if news.get("catalyst"):
        total += 15

    # בונוס דוח קרוב (0-3 ימים = +10)
    days = fund.get("earnings_days_away")
    if days is not None and 0 <= days <= 3:
        total += 10

    # עונש: אין נתונים טכניים
    if tech_score == 0 and not tech.get("summary"):
        total -= 20

    # סיגנלים מרוכזים
    all_signals  = tech.get("signals", []) + fund.get("signals", []) + news.get("signals", []) if news.get("signals") else tech.get("signals", []) + fund.get("signals", [])
    all_warnings = tech.get("warnings", []) + fund.get("warnings", [])

    # החלטה סופית
    total = round(max(-100, min(100, total)), 1)

    if total >= 60:
        decision = "🟢 קנייה חזקה"
        priority = "גבוה"
    elif total >= 35:
        decision = "🟡 בחן מקרוב"
        priority = "בינוני"
    elif total >= 10:
        decision = "⚪ המתן"
        priority = "נמוך"
    else:
        decision = "🔴 הימנע"
        priority = "נמוך"

    return {
        "ticker": ticker,
        "total_score": total,
        "decision": decision,
        "priority": priority,
        "tech": tech,
        "news": news,
        "fund": fund,
        "risk": risk,
        "all_signals": all_signals,
        "all_warnings": all_warnings,
        "entry":     risk.get("entry_price"),
        "stop_loss": risk.get("stop_loss"),
        "stop_pct":  risk.get("stop_loss_pct"),
        "target_1":  risk.get("target_1"),
        "target_2":  risk.get("target_2"),
        "shares":    risk.get("shares"),
        "max_loss":  risk.get("max_loss_usd"),
    }


def run():
    """
    הפונקציה הראשית — מריצה את כל הצוות.

    Returns:
        list: TOP 5 המניות מדורגות, כל אחת עם ניתוח מלא.
    """
    print("\n" + "╔" + "═"*58 + "╗")
    print("║  👑 ראש הצוות מפעיל את סוכני הניתוח                   ║")
    print("╚" + "═"*58 + "╝\n")

    # ── שלב 1: סריקה — מי ראוי לניתוח ──
    print("📋 שלב 1: סריקת השוק למציאת מועמדות...")
    scan_results = _run_agent_safe(agent_scanner.run, name="סורק")
    candidates = [r["ticker"] for r in scan_results] if scan_results else [
        "TSLA","NVDA","AMD","COIN","PLTR","META","AAPL","MSFT","MARA","SOFI"
    ]
    print(f"   נבחרו {len(candidates)} מועמדות: {', '.join(candidates[:8])}...")

    # ── שלב 2: ניתוח מקביל — כל הסוכנים רצים בו זמנית ──
    print("\n📋 שלב 2: ניתוח מקביל — כל הסוכנים עובדים יחד...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_news  = executor.submit(_run_agent_safe, agent_news.run, candidates, "חדשות")
        future_tech  = executor.submit(_run_agent_safe, agent_technical.run, candidates, "טכני")
        future_fund  = executor.submit(_run_agent_safe, agent_fundamental.run, candidates, "פונדמנטלי")

        news_results = future_news.result()
        tech_results = future_tech.result()
        fund_results = future_fund.result()

    # ── שלב 3: חישוב סיכונים לכולן ──
    print("\n📋 שלב 3: חישוב כניסה/עצירה/יעד...")
    prices = {}
    for t, r in tech_results.items():
        # ניסיון לשלוף מחיר מהנתונים הקיימים
        pass
    risk_results = _run_agent_safe(
        agent_risk.run,
        {t: None for t in candidates},
        name="סיכון"
    )

    # ── שלב 4: ראש הצוות מרכז ומדרג ──
    print("\n📋 שלב 4: ראש הצוות מסכם ומדרג...")
    all_analyzed = []
    for ticker in candidates:
        a = analyze_one_stock(ticker, news_results, tech_results, fund_results, risk_results)
        all_analyzed.append(a)

    # מיון
    all_analyzed.sort(key=lambda x: x["total_score"], reverse=True)

    # TOP 5 בלבד
    top5 = all_analyzed[:5]

    # ── דוח ראש הצוות ──
    print("\n" + "╔" + "═"*58 + "╗")
    print("║  📊 סיכום ראש הצוות — TOP 5 להיום                      ║")
    print("╚" + "═"*58 + "╝")

    for i, s in enumerate(top5, 1):
        print(f"\n{'='*55}")
        print(f"  #{i} {s['ticker']} | ציון: {s['total_score']:.0f}/100 | {s['decision']}")
        print(f"  טכני: {s['tech'].get('summary','—')}")
        print(f"  חדשות: {s['news'].get('sentiment_label','—')} | {s['news'].get('summary','—')}")
        print(f"  פונדמנטלי: {s['fund'].get('summary','—')}")
        if s['entry']:
            print(f"  כניסה: ${s['entry']} | Stop: ${s['stop_loss']} | יעד: ${s['target_2']}")
            print(f"  קנה {s['shares']} מניות | סיכון מקסימלי: ${s['max_loss']}")

    print(f"\n{'='*55}")
    print(f"✅ ראש הצוות סיים | {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    return top5, all_analyzed


def get_full_team_report():
    """ממשק נוח לקריאה מ-morning_report.py"""
    top5, all_stocks = run()
    return {
        "top5": top5,
        "all_stocks": all_stocks,
        "generated_at": datetime.now().isoformat()
    }


if __name__ == "__main__":
    top5, all_stocks = run()
