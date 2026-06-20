#!/usr/bin/env python3
"""
☁️ cloud_runner.py — מריץ את צוות הסוכנים בענן (GitHub Actions)
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
except Exception as e:
    print(f"❌ שגיאה בהרצת הצוות: {e}")
    import traceback
    traceback.print_exc()
    # fallback לדוח הישן
    from morning_report import main as old_main
    old_main(force=True)
    sys.exit(0)

# ── יצירת דוח HTML ──
print("\n📄 יוצר דוח HTML...")
try:
    from generate_team_report import build_html
    html = build_html(top5, all_stocks)
    with open("reports/report.html", "w", encoding="utf-8") as f:
        f.write(html)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ דוח HTML נוצר")
except Exception as e:
    print(f"⚠️  שגיאה ביצירת HTML: {e}")
    # fallback
    try:
        from generate_html_report import build_report_html
        html = build_report_html([s for s in all_stocks])
        with open("reports/report.html", "w", encoding="utf-8") as f:
            f.write(html)
        with open("docs/index.html", "w", encoding="utf-8") as f:
            f.write(html)
    except Exception as e2:
        print(f"⚠️  fallback HTML נכשל: {e2}")

# ── שליחת טלגרם ──
print("\n📱 שולח עדכון לטלגרם...")
try:
    import requests
    date_str = datetime.now().strftime("%d/%m/%Y")

    msg = f"📊 *דוח בוקר — {date_str}*\n\n"
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
    msg += f"\n_הופק על ידי צוות {len(all_stocks)} סוכני AI_"

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
