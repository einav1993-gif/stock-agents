#!/usr/bin/env python3
"""
☁️ cloud_runner.py — מריץ את צוות הסוכנים בענן (GitHub Actions)
=================================================================
חדש:
- כל המלצות ה-TOP 5 נרשמות ב-data/tracking.json (מקומט לריפו!)
  כדי שהביקורת העצמית של הערב (self_review.py) תוכל לבדוק אותן.
- אם כיסוי הנתונים נמוך — הטלגרם והאתר מזהירים במקום להמליץ.
"""

import os
import sys
import json
from datetime import datetime

print("☁️  GitHub Actions — צוות סוכני המניות מתחיל")
print("=" * 55)
print(f"🕐 זמן: {datetime.now().strftime('%d/%m/%Y %H:%M UTC')}")
print()

# ── יצירת תיקיות ──
os.makedirs("reports", exist_ok=True)
os.makedirs("docs", exist_ok=True)
os.makedirs("data", exist_ok=True)

# ── בניית config.json מ-Secrets של GitHub ──
token   = os.environ.get("TELEGRAM_TOKEN", "")
chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

if not token or not chat_id:
    print("⚠️  אזהרה: חסרים TELEGRAM_TOKEN או TELEGRAM_CHAT_ID — ממשיכים בלי טלגרם")

cfg = {
    "telegram": {
        "enabled": True,
        "token":   token,
        "chat_id": chat_id
    },
    "virtual_capital": 10000,
    "stop_loss_pct":   1.5,
    "target_pct":      3.0
}

with open("config.json", "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)

print("✅ config.json נוצר מ-GitHub Secrets")

# ── בדיקת יום מסחר ──
is_manual = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
weekday = datetime.utcnow().weekday()
if weekday >= 5 and not is_manual:
    print("⛔ סוף שבוע — הסוכן ישן 😴")
    sys.exit(0)
if weekday >= 5 and is_manual:
    print("⚠️  סוף שבוע אבל הרצה ידנית — ממשיכים!")

# ── הרצת צוות הסוכנים ──
print("\n🚀 מפעיל את ראש הצוות...")
try:
    from team_lead import get_full_team_report
    report = get_full_team_report()
    top5 = report["top5"]
    all_stocks = report["all_stocks"]
    health = report.get("health", {})
except Exception as e:
    print(f"❌ שגיאה בהרצת הצוות: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

degraded = health.get("degraded", False)

# ── רישום ההמלצות למעקב (הבסיס לביקורת העצמית של הערב) ──
print("\n📝 רושם את המלצות היום למעקב (data/tracking.json)...")
try:
    track_path = os.path.join("data", "tracking.json")
    existing = []
    if os.path.exists(track_path):
        with open(track_path, "r", encoding="utf-8") as f:
            existing = json.load(f)

    date_str = datetime.now().strftime("%Y-%m-%d")
    # לא רושמים פעמיים באותו יום (למשל בהרצה ידנית חוזרת)
    already = {(r["date"], r["ticker"]) for r in existing}

    added = 0
    for s in top5:
        if (date_str, s["ticker"]) in already:
            continue
        existing.append({
            "date":         date_str,
            "ticker":       s["ticker"],
            "total_score":  s["total_score"],
            "decision":     s["decision"],
            "trade_type":   s["trade_type"],
            "components":   s.get("components", {}),
            "entry":        s.get("entry"),
            "stop_loss":    s.get("stop_loss"),
            "target_1":     s.get("target_1"),
            "target_2":     s.get("target_2"),
            "degraded_data": degraded,
            "actual_result": None,
        })
        added += 1

    with open(track_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    print(f"✅ נרשמו {added} המלצות חדשות למעקב")
except Exception as e:
    print(f"⚠️  שגיאה ברישום מעקב: {e}")

# ── יצירת דוח HTML ──
print("\n📄 יוצר דוח HTML...")
try:
    from generate_team_report import build_html
    html = build_html(top5, all_stocks, health=health)
    with open("reports/report.html", "w", encoding="utf-8") as f:
        f.write(html)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ דוח HTML נוצר")
except Exception as e:
    print(f"⚠️  שגיאה ביצירת HTML: {e}")
    import traceback
    traceback.print_exc()

# ── שליחת טלגרם ──
print("\n📱 שולח עדכון לטלגרם...")
try:
    import requests
    date_str = datetime.now().strftime("%d/%m/%Y")

    msg = f"📊 *דוח בוקר — {date_str}*\n\n"

    if degraded:
        msg += "🚨 *אזהרה: כיסוי הנתונים נמוך היום!*\n"
        msg += f"(טכני: {health.get('tech_coverage', '?')}% | סיכון: {health.get('risk_coverage', '?')}%)\n"
        msg += "_ההמלצות היום לא אמינות — עדיף לא לסחור לפיהן._\n\n"

    msg += "🏆 *TOP 5 מניות להיום:*\n\n"

    for i, s in enumerate(top5, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
        msg += f"{emoji} *{s['ticker']}* | {s['decision']} | ציון {s['total_score']:.0f}\n"
        if s.get("entry") and s.get("stop_loss") and s.get("target_2"):
            msg += f"   כניסה ${s['entry']} | Stop ${s['stop_loss']} | יעד ${s['target_2']}\n"
        if s["news"].get("catalyst"):
            msg += f"   🔥 קטליסט: {s['news']['catalyst_type']}\n"
        msg += "\n"

    # קישור לאתר
    msg += "🌐 [דוח מלא באתר](https://einav1993-gif.github.io/stock-agents/)\n"
    msg += f"\n_הופק על ידי צוות {len(all_stocks)} סוכני AI | בערב תגיע הביקורת העצמית_ 🪞"

    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        },
        timeout=15
    )

    if resp.status_code == 200:
        print("✅ טלגרם נשלח בהצלחה!")
    else:
        print(f"❌ שגיאת טלגרם: {resp.status_code} — {resp.text[:200]}")

except Exception as e:
    print(f"⚠️  שגיאה בשליחת טלגרם: {e}")

print("\n✅ צוות הסוכנים סיים את עבודתו!")
