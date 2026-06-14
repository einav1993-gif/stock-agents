#!/usr/bin/env python3
"""
📈 שירה — סוכנת המעקב
=======================
עובדת בסוף יום המסחר (23:00 ישראל).
בודקת מה קרה למניות שאורי המליץ עליהן:
פגעו ביעד? בסטופ? נשארו פתוחות?
בונה היסטוריה וסטטיסטיקת הצלחה לאורך זמן.
"""

import yfinance as yf
import json
import os
from datetime import datetime

TRACK_PATH = "reports/tracking.json"

def load_tracking_data():
    if not os.path.exists(TRACK_PATH):
        return []
    with open(TRACK_PATH, "r") as f:
        return json.load(f)

def check_results():
    if not os.path.exists(TRACK_PATH):
        print("❌ לא נמצא קובץ מעקב. הרץ קודם את morning_report.py")
        return

    with open(TRACK_PATH, "r") as f:
        records = json.load(f)

    today = datetime.now().strftime("%Y-%m-%d")
    today_records = [r for r in records if r["date"] == today and r["actual_result"] is None]

    if not today_records:
        print("✅ לא נמצאו המלצות פתוחות להיום.")
        return

    print(f"\n📊 בודק תוצאות סוף יום — {today}\n")
    updated = False

    for rec in today_records:
        ticker = rec["ticker"]
        try:
            stock = yf.Ticker(ticker)
            hist  = stock.history(period="1d", interval="1m")
            if hist.empty:
                continue

            close_price = float(hist.iloc[-1]['Close'])
            open_price  = rec["price_at_report"]
            change_pct  = round(((close_price - open_price) / open_price) * 100, 2)

            hit_target  = close_price >= rec["target"]
            hit_stop    = close_price <= rec["stop"]

            if hit_target:
                result = f"✅ פגע ביעד! רווח {change_pct:+.1f}%"
            elif hit_stop:
                result = f"🛑 פגע בסטופ! הפסד {change_pct:+.1f}%"
            else:
                result = f"⏳ לא פגע ביעד ולא בסטופ. שינוי: {change_pct:+.1f}%"

            rec["actual_result"]  = result
            rec["close_price"]    = close_price
            rec["change_pct"]     = change_pct
            updated = True

            print(f"  {ticker}: {result}")
            print(f"    מחיר פתיחה: ${open_price}  |  מחיר סגירה: ${close_price}")

        except Exception as e:
            print(f"  {ticker}: שגיאה — {e}")

    if updated:
        with open(TRACK_PATH, "w") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        print("\n✅ תוצאות נשמרו.")
        print_weekly_summary(records)


def print_weekly_summary(records):
    completed = [r for r in records if r.get("actual_result") and "%" in str(r.get("actual_result",""))]
    if not completed:
        return

    print("\n" + "=" * 50)
    print("📈 סיכום ביצועי סוכן — כל ההמלצות עד כה:")
    hits    = sum(1 for r in completed if "פגע ביעד" in str(r.get("actual_result","")))
    stops   = sum(1 for r in completed if "פגע בסטופ" in str(r.get("actual_result","")))
    neutral = len(completed) - hits - stops

    print(f"  סה\"כ המלצות: {len(completed)}")
    print(f"  ✅ פגעו ביעד:   {hits}  ({round(hits/len(completed)*100)}%)")
    print(f"  🛑 פגעו בסטופ:  {stops}  ({round(stops/len(completed)*100)}%)")
    print(f"  ⏳ ניטרלי:      {neutral}")

    changes = [r.get("change_pct", 0) for r in completed if r.get("change_pct") is not None]
    if changes:
        avg = round(sum(changes) / len(changes), 2)
        print(f"\n  ממוצע שינוי: {avg:+.2f}% להמלצה")

    # המלצה על הגדלת הון
    if len(completed) >= 15 and hits / len(completed) >= 0.6:
        print("\n  🎯 ביצועים מצוינים! שקולי מעבר למסחר אמיתי בסכום קטן.")
    elif len(completed) >= 15 and hits / len(completed) < 0.4:
        print("\n  ⚠️  ביצועים נמוכים. נמשיך לשפר את הסוכנים לפני מסחר אמיתי.")
    print("=" * 50)


if __name__ == "__main__":
    check_results()
