#!/usr/bin/env python3
"""
👑 team_lead.py — ראש צוות הסוכנים
=====================================
מנהל 11 סוכנים מקצועיים:
1. 🔭 סוכן סריקה      — מוצא מניות חמות
2. 🌍 סוכן מאקרו      — VIX, Fear&Greed, סקטורים
3. 📰 סוכן חדשות      — סנטימנט חדשות
4. 🧠 סוכן סנטימנט    — Finnhub, Stocktwits, SEC Insider
5. 🕯️  סוכן טכני      — RSI, MACD, נרות יפניים
6. 📊 סוכן פונדמנטלי  — דוחות, אנליסטים, יעד מחיר
7. ⚖️  סוכן סיכון     — כניסה, עצירה, יעד
8. ⚡ סוכן גאפים      — פערי פתיחה ופרימרקט (המנבא החזק ביותר)
9. 🗣️  סוכן חברתי     — סנטימנט Reddit דרך ApeWisdom
10. 💪 סוכן חוזק יחסי — חזקה או חלשה מהשוק (מול SPY)
11. 📅 סוכן לוח אירועים — דוחות קרובים ואירועי מאקרו

חדש:
- המשקלות נטענים מ-data/weights.json ומתעדכנים כל ערב
  על ידי self_review.py (הביקורת העצמית).
- ראש הצוות באמת בודק שהסוכנים עובדים: סופר כמה מניות
  קיבלו נתונים אמיתיים, ואם הכיסוי נמוך — מסמן את הדוח
  כ"לא אמין" במקום להעמיד פנים שהכול בסדר.
"""

import concurrent.futures
import json
import os
from datetime import datetime

import agent_scanner
import agent_macro
import agent_news
import agent_sentiment
import agent_technical
import agent_fundamental
import agent_risk
import agent_gap
import agent_social
import agent_rs
import agent_calendar
import data_layer

WEIGHTS_PATH = os.path.join("data", "weights.json")

DEFAULT_WEIGHTS = {
    "tech": 0.22, "news": 0.13, "gap": 0.12, "fund": 0.10,
    "rs": 0.10, "macro": 0.09, "sent": 0.07, "risk": 0.07,
    "social": 0.06, "cal": 0.04,
}

# מתחת לכיסוי נתונים כזה (באחוזים) — הדוח מסומן כלא אמין
MIN_COVERAGE_PCT = 50


def load_weights():
    """טוען את המשקלות שהביקורת העצמית למדה. אם אין — ברירת מחדל."""
    try:
        with open(WEIGHTS_PATH, "r", encoding="utf-8") as f:
            w = json.load(f)
        weights = {k: float(w[k]) for k in DEFAULT_WEIGHTS if k in w}
        if len(weights) == len(DEFAULT_WEIGHTS) and 0.9 < sum(weights.values()) < 1.1:
            return weights
    except Exception:
        pass
    return dict(DEFAULT_WEIGHTS)


def _safe(fn, *args, name="סוכן"):
    try:
        result = fn(*args)
        return result if result is not None else {}
    except Exception as e:
        print(f"🚨 [{name}] נכשל: {e}")
        return {}


def _score_one(ticker, macro, news_r, sent_r, tech_r, fund_r, risk_r,
               gap_r, social_r, rs_r, cal_r, weights):
    """מחשב ציון כולל למניה אחת ממכלול הסוכנים, לפי המשקלות הנלמדים."""
    tech = tech_r.get(ticker, {})
    news = news_r.get(ticker, {})
    sent = sent_r.get(ticker, {})
    fund = fund_r.get(ticker, {})
    risk = risk_r.get(ticker, {})
    gap    = gap_r.get(ticker, {})
    social = social_r.get(ticker, {})
    rs     = rs_r.get(ticker, {})
    cal    = cal_r.get(ticker, {})

    macro_score = macro.get("macro_score", 0)
    tech_score  = tech.get("score", 0)
    news_score  = news.get("sentiment_score", 0) * 0.5
    sent_score  = sent.get("combined_score", 0)
    fund_score  = fund.get("score", 0)
    risk_score  = risk.get("score", 0)

    # הציונים הגולמיים של כל סוכן — נשמרים כדי שהביקורת העצמית
    # תדע בערב מי צדק ומי טעה
    components = {
        "tech": tech_score, "macro": macro_score, "news": news_score,
        "sent": sent_score, "fund": fund_score, "risk": risk_score,
        "gap":    gap.get("score", 0),
        "social": social.get("score", 0),
        "rs":     rs.get("score", 0),
        "cal":    cal.get("score", 0),
    }

    total = sum(components[a] * weights[a] for a in weights)

    # בונוסים
    if news.get("catalyst"):          total += 15
    if sent.get("insider", {}) and sent.get("insider", {}).get("buys", 0) > 1:
        total += 10   # בעלי תפקידים קונים — אות חזק
    days = fund.get("earnings_days_away")
    if days is not None and 0 <= days <= 3:
        total += 10   # דוח קרוב = תנועה צפויה

    # עונשים
    vix = macro.get("vix") or {}
    if vix and vix.get("value", 0) > 30:
        total -= 15   # שוק בפאניקה — לא זמן לסחור

    total = round(max(-100, min(100, total)), 1)

    # האם בכלל היו לנו נתונים על המניה הזו?
    has_data = bool(tech) and tech.get("rsi") is not None

    if not has_data:
        decision = "⚫ אין נתונים"
        trade_type = "none"
    elif total >= 60:
        decision = "🟢 קנייה חזקה"
        trade_type = "long"
    elif total >= 35:
        decision = "🟡 לונג — בחן מקרוב"
        trade_type = "long"
    elif total >= 10:
        decision = "⚪ המתן"
        trade_type = "none"
    elif total <= -50:
        decision = "🔴 שורט חזק"
        trade_type = "short"
    elif total <= -25:
        decision = "🟠 שורט — בחן מקרוב"
        trade_type = "short"
    else:
        decision = "⚪ הימנע"
        trade_type = "none"

    all_signals  = (tech.get("signals", []) + fund.get("signals", [])
                    + gap.get("signals", []) + social.get("signals", [])
                    + rs.get("signals", []) + cal.get("signals", []))
    all_warnings = (tech.get("warnings", []) + fund.get("warnings", [])
                    + gap.get("warnings", []) + social.get("warnings", [])
                    + rs.get("warnings", []) + cal.get("warnings", []))

    return {
        "ticker":       ticker,
        "total_score":  total,
        "decision":     decision,
        "trade_type":   trade_type,
        "has_data":     has_data,
        "components":   components,
        "tech":         tech,
        "news":         news,
        "sent":         sent,
        "fund":         fund,
        "risk":         risk,
        "macro":        macro,
        "gap":          gap,
        "social":       social,
        "rs":           rs,
        "cal":          cal,
        "all_signals":  all_signals,
        "all_warnings": all_warnings,
        # לונג
        "entry":        risk.get("entry_price"),
        "stop_loss":    risk.get("stop_loss"),
        "stop_pct":     risk.get("stop_loss_pct"),
        "target_1":     risk.get("target_1"),
        "target_2":     risk.get("target_2"),
        # שורט
        "short_entry":    risk.get("short_entry"),
        "short_stop":     risk.get("short_stop"),
        "short_stop_pct": risk.get("short_stop_pct"),
        "short_target_1": risk.get("short_target_1"),
        "short_target_2": risk.get("short_target_2"),
        # כללי
        "shares":       risk.get("shares"),
        "max_loss":     risk.get("max_loss_usd"),
    }


def run():
    print("\n" + "╔" + "═"*60 + "╗")
    print("║  👑 ראש הצוות — מפעיל 11 סוכני ניתוח מקצועיים         ║")
    print("╚" + "═"*60 + "╝\n")

    weights = load_weights()
    print("⚖️  משקלות נוכחיים (נלמדים):",
          " | ".join(f"{k}: {v*100:.0f}%" for k, v in weights.items()))

    # ── שלב 1: מאקרו — בודקים את מצב השוק לפני הכל ──
    print("\n📋 שלב 1: בדיקת מצב השוק הכללי...")
    macro = _safe(agent_macro.run, name="מאקרו")

    vix_val = (macro.get("vix") or {}).get("value", 18) if macro else 18
    fg_val  = (macro.get("fear_greed") or {}).get("value", 50) if macro else 50
    mkt_mood = (macro.get("market") or {}).get("mood", "") if macro else ""

    print(f"   🌡️  VIX: {vix_val} | Fear&Greed: {fg_val} | שוק: {mkt_mood}")

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
    print("\n📋 שלב 3: ניתוח מקביל — 9 סוכנים עובדים יחד...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=9) as ex:
        f_news   = ex.submit(_safe, agent_news.run, candidates, name="חדשות")
        f_sent   = ex.submit(_safe, agent_sentiment.run, candidates, name="סנטימנט")
        f_tech   = ex.submit(_safe, agent_technical.run, candidates, name="טכני")
        f_fund   = ex.submit(_safe, agent_fundamental.run, candidates, name="פונדמנטלי")
        f_risk   = ex.submit(_safe, agent_risk.run, {t: None for t in candidates}, name="סיכון")
        f_gap    = ex.submit(_safe, agent_gap.run, candidates, name="גאפים")
        f_social = ex.submit(_safe, agent_social.run, candidates, name="חברתי")
        f_rs     = ex.submit(_safe, agent_rs.run, candidates, name="חוזק יחסי")
        f_cal    = ex.submit(_safe, agent_calendar.run, candidates, name="לוח אירועים")

        news_r   = f_news.result()
        sent_r   = f_sent.result()
        tech_r   = f_tech.result()
        fund_r   = f_fund.result()
        risk_r   = f_risk.result()
        gap_r    = f_gap.result()
        social_r = f_social.result()
        rs_r     = f_rs.result()
        cal_r    = f_cal.result()

    # ── שלב 3.5: ראש הצוות בודק שהסוכנים באמת עבדו ──
    def _agent_coverage(results, key):
        if not results:
            return 0
        ok = sum(1 for t in candidates
                 if results.get(t) and results[t].get(key) is not None)
        return round(ok / len(candidates) * 100)

    news_ok = sum(1 for t in candidates
                  if news_r.get(t) and news_r[t].get("headlines")) if news_r else 0
    health = {
        "tech_coverage":  _agent_coverage(tech_r, "rsi"),
        "risk_coverage":  _agent_coverage(risk_r, "entry_price"),
        "fund_coverage":  _agent_coverage(fund_r, "score"),
        "news_coverage":  round(news_ok / len(candidates) * 100) if candidates else 0,
        "data_sources":   data_layer.health_summary(),
    }
    health["overall"] = round(
        (health["tech_coverage"] + health["risk_coverage"]) / 2
    )
    health["degraded"] = health["overall"] < MIN_COVERAGE_PCT

    print(f"\n🩺 בדיקת בריאות: טכני {health['tech_coverage']}% | "
          f"סיכון {health['risk_coverage']}% | פונדמנטלי {health['fund_coverage']}% | "
          f"חדשות {health['news_coverage']}%")
    if health["degraded"]:
        print("🚨 כיסוי נתונים נמוך! הדוח יסומן כלא אמין — אל תסחרי לפיו היום.")

    # ── שלב 4: ציון כולל ──
    print("\n📋 שלב 4: ראש הצוות מסכם ומדרג...")
    all_analyzed = []
    for ticker in candidates:
        s = _score_one(ticker, macro, news_r, sent_r, tech_r, fund_r, risk_r,
                       gap_r, social_r, rs_r, cal_r, weights)
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
    return top5, all_analyzed, health, weights


def get_full_team_report():
    top5, all_stocks, health, weights = run()
    return {
        "top5":         top5,
        "all_stocks":   all_stocks,
        "health":       health,
        "weights":      weights,
        "generated_at": datetime.now().isoformat()
    }


if __name__ == "__main__":
    run()
