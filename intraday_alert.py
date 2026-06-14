#!/usr/bin/env python3
"""
⚡ נועה — סוכנת ההתראות
========================
ערה כל 15 דקות בשעות המסחר (16:30–23:00 ישראל).
שומרת עיניים על המניות שאורי המליץ עליהן.
שולחת התראה מיידית לטלגרם ברגע שמניה
פוגעת ביעד או בסטופ לוס.

⚡ Intraday Alert — התראות בזמן אמת
=====================================
בודק כל 15 דקות האם המניות המומלצות היום פגעו ביעד או בסטופ.
שולח הודעת Telegram מיד כשזה קורה.

cron (עריכת crontab -e):
  */15 14-21 * * 1-5 cd /Users/.../stock_agents && python3 intraday_alert.py
"""

import yfinance as yf
import json, os, urllib.request, urllib.parse
from datetime import datetime


# ─────────────────────────────────
# קובץ מעקב התראות (למנוע כפולות)
# ─────────────────────────────────
ALERTS_SENT_FILE = "reports/alerts_sent.json"

def load_alerts_sent():
    if not os.path.exists(ALERTS_SENT_FILE):
        return {}
    with open(ALERTS_SENT_FILE, "r") as f:
        return json.load(f)

def save_alerts_sent(data):
    os.makedirs("reports", exist_ok=True)
    with open(ALERTS_SENT_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ─────────────────────────────────
# קריאת ההמלצות של היום
# ─────────────────────────────────
def load_todays_recommendations():
    track_path = "reports/tracking.json"
    if not os.path.exists(track_path):
        return []

    today = datetime.now().strftime("%Y-%m-%d")

    with open(track_path, "r") as f:
        all_recs = json.load(f)

    # רק המלצות של היום שעדיין פתוחות
    return [r for r in all_recs
            if r.get('date') == today and r.get('actual_result') is None]


# ─────────────────────────────────
# בדיקת מחיר נוכחי
# ─────────────────────────────────
def get_current_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        info  = stock.info
        price = info.get('regularMarketPrice') or info.get('currentPrice')
        return float(price) if price else None
    except Exception:
        return None


# ─────────────────────────────────
# שליחת Telegram
# ─────────────────────────────────
def send_telegram_alert(message):
    cfg_path = "config.json"
    if not os.path.exists(cfg_path):
        return
    with open(cfg_path, "r") as f:
        cfg = json.load(f)

    tg = cfg.get("telegram", {})
    if not tg.get("enabled"):
        return

    token   = tg.get("token", "")
    chat_id = tg.get("chat_id", "")
    if not token or not chat_id:
        return

    url  = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id":    chat_id,
        "text":       message,
        "parse_mode": "Markdown"
    }).encode()

    try:
        urllib.request.urlopen(url, data=data, timeout=10)
        print(f"📱 התראה נשלחה!")
    except Exception as e:
        print(f"(Telegram error: {e})")


# ─────────────────────────────────
# עדכון תוצאה בקובץ המעקב
# ─────────────────────────────────
def update_tracking_result(ticker, date, result_text):
    track_path = "reports/tracking.json"
    if not os.path.exists(track_path):
        return

    with open(track_path, "r") as f:
        records = json.load(f)

    for r in records:
        if r.get('ticker') == ticker and r.get('date') == date and r.get('actual_result') is None:
            r['actual_result'] = result_text
            break

    with open(track_path, "w") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────
# ניתוח עסקאות
# ─────────────────────────────────
def check_alerts():
    recs         = load_todays_recommendations()
    alerts_sent  = load_alerts_sent()
    today        = datetime.now().strftime("%Y-%m-%d")
    now_str      = datetime.now().strftime("%H:%M")
    any_sent     = False

    if not recs:
        print(f"[{now_str}] אין המלצות פתוחות להיום")
        return

    print(f"[{now_str}] בודק {len(recs)} המלצות...")

    for rec in recs:
        ticker  = rec['ticker']
        target  = rec['target']
        stop    = rec['stop']
        entry   = rec['price_at_report']
        alert_key = f"{today}_{ticker}"

        if alert_key in alerts_sent:
            continue  # כבר שלחנו התראה על זה

        price = get_current_price(ticker)
        if price is None:
            print(f"  {ticker}: לא הצלחתי לקבל מחיר")
            continue

        change_pct = round(((price - entry) / entry) * 100, 2)
        print(f"  {ticker}: ${price} (כניסה ${entry}, שינוי {change_pct:+.1f}%)")

        msg = None
        result_text = None

        # ── פגע ביעד ──
        if price >= target:
            profit = round(rec.get('potential_profit', 0), 2)
            msg = (
                f"🎯 *פגע ביעד! {ticker}*\n\n"
                f"✅ המניה הגיעה ליעד!\n"
                f"📈 מחיר נוכחי: ${price}\n"
                f"🎯 יעד: ${target}\n"
                f"📊 כניסה: ${entry} ({change_pct:+.1f}%)\n"
                f"💰 רווח פוטנציאלי: +${profit}\n\n"
                f"_שקלי לממש חלק מהפוזיציה!_"
            )
            result_text = f"פגע ביעד ${target} ב-{now_str} (+{change_pct}%)"

        # ── פגע בסטופ ──
        elif price <= stop:
            loss = round(rec.get('potential_profit', 0) * 0.5, 2)
            msg = (
                f"🛑 *סטופ לוס! {ticker}*\n\n"
                f"⚠️ המניה ירדה לסטופ לוס!\n"
                f"📉 מחיר נוכחי: ${price}\n"
                f"🛑 סטופ: ${stop}\n"
                f"📊 כניסה: ${entry} ({change_pct:+.1f}%)\n\n"
                f"_יש לצאת מהפוזיציה. הפסד מינימלי!_"
            )
            result_text = f"פגע בסטופ ${stop} ב-{now_str} ({change_pct}%)"

        # ── אזהרה: קרוב לסטופ ──
        elif price <= stop * 1.01 and f"{alert_key}_warning" not in alerts_sent:
            msg = (
                f"⚠️ *אזהרה — {ticker} קרוב לסטופ!*\n\n"
                f"📉 מחיר: ${price}\n"
                f"🛑 סטופ: ${stop} (מרחק {round(((price-stop)/stop)*100, 1)}%)\n\n"
                f"_עקבי מקרוב!_"
            )
            alerts_sent[f"{alert_key}_warning"] = now_str

        if msg:
            send_telegram_alert(msg)
            alerts_sent[alert_key] = now_str
            any_sent = True

            if result_text:
                update_tracking_result(ticker, today, result_text)

    save_alerts_sent(alerts_sent)

    if not any_sent:
        print(f"[{now_str}] אין התראות חדשות")


# ─────────────────────────────────
# main
# ─────────────────────────────────
if __name__ == "__main__":
    # בדיקת שעות מסחר (14:30–21:00 UTC = 16:30–23:00 ישראל בחורף)
    now_utc = datetime.utcnow()
    hour    = now_utc.hour
    minute  = now_utc.minute
    weekday = now_utc.weekday()  # 0=שני

    if weekday >= 5:
        print("⛔ סוף שבוע — אין מסחר")
        exit()

    # שוק פתוח 13:30–20:00 UTC (9:30–16:00 ET)
    market_open  = hour > 13 or (hour == 13 and minute >= 30)
    market_close = hour < 20

    if not (market_open and market_close):
        print(f"⛔ שוק סגור כרגע ({now_utc.strftime('%H:%M')} UTC)")
        exit()

    check_alerts()
