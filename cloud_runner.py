#!/usr/bin/env python3
"""
☁️ cloud_runner.py — מריץ את הסוכנים בענן (GitHub Actions)
============================================================
קובץ זה מופעל אוטומטית על ידי GitHub בכל יום מסחר.
לא צריך לגעת בו.
"""

import os
import sys
import json

print("☁️  GitHub Actions — סוכני המניות מתחילים")
print("=" * 50)

# ── יצירת תיקיית reports ──
os.makedirs("reports", exist_ok=True)

# ── בניית config.json מ-Secrets של GitHub ──
token   = os.environ.get("TELEGRAM_TOKEN", "")
chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

if not token or not chat_id:
    print("❌ חסרים TELEGRAM_TOKEN או TELEGRAM_CHAT_ID ב-GitHub Secrets!")
    sys.exit(1)

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
print(f"✅ Telegram מופעל (chat_id: {chat_id})")
print()

# ── הרצת אורי — סוכן הבוקר ──
from morning_report import main
main()
