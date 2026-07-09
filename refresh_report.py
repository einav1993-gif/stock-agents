#!/usr/bin/env python3
"""
🔄 refresh_report.py — ריענון האתר כל שעה
============================================
רץ כל שעה עגולה בשעות המסחר (workflow: refresh.yml).

מה הוא עושה:
  • מריץ מחדש את ניתוח 11 הסוכנים עם מחירים עדכניים.
  • בונה מחדש את דוח ה-HTML (docs/index.html) — כך האתר מתעדכן כל שעה.

מה הוא *לא* עושה (בכוונה!):
  • לא רושם המלצות חדשות ל-tracking.json
  • לא קונה/מוכר בסימולטור
  • לא נוגע בלמידה או במשקלות
ההחלטות המסחריות והלמידה נשארות בדוח הבוקר (16:00) ובביקורת הערב (00:30) בלבד.
כך האתר "חי" ומתעדכן, בלי לשבש את מקורות האמת של המערכת.
"""

import os
from datetime import datetime

print("🔄 ריענון אתר —", datetime.now().strftime("%H:%M UTC"))

os.makedirs("docs", exist_ok=True)
os.makedirs("reports", exist_ok=True)

# בונים config.json כדי שסוכן הסיכון ידע את גודל התיק
import json
token = os.environ.get("TELEGRAM_TOKEN", "")
chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
with open("config.json", "w", encoding="utf-8") as f:
    json.dump({"telegram": {"enabled": False, "token": token, "chat_id": chat_id},
               "virtual_capital": 1000}, f, ensure_ascii=False)

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
    raise SystemExit(1)

# בונים HTML בלבד — בלי לגעת ב-tracking / portfolio / weights
try:
    from generate_team_report import build_html
    html = build_html(top5, all_stocks, health=health)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ האתר עודכן (docs/index.html)")
except Exception as e:
    print(f"⚠️  שגיאה ביצירת HTML: {e}")
    raise SystemExit(1)

print("✅ ריענון הסתיים — האתר מציג ניתוח עדכני")
