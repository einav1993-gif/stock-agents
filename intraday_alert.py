#!/usr/bin/env python3
"""
⚡ intraday_alert.py — מעקב תוך-יומי בזמן אמת
================================================
רץ כל 20 דקות בשעות המסחר (workflow: intraday.yml).

מה הוא עושה:
1. קורא את המלצות הבוקר הפתוחות מ-data/tracking.json.
2. מושך מחיר בזמן אמת לכל מנייה — דרך Finnhub /quote (עובד משרתים!),
   עם גיבוי ל-yfinance בנתוני דקה.
3. אם מנייה חצתה את היעד או את הסטופ — שולח התראה מיידית לטלגרם.
4. שומר ב-data/alerts_sent.json אילו התראות כבר נשלחו היום,
   כדי לא לשלוח פעמיים (הקובץ מקומט לריפו כדי לשרוד בין ריצות).

הערה: הקובץ הזה שולח התראות בלבד. הוא לא סוגר פוזיציות ולא משנה
את הלמידה — זה נשאר באחריות הביקורת הערבית (self_review.py),
שהיא מקור האמת היחיד. כך אין התנגשויות ולא ספירה כפולה.
"""

import json
import os
from datetime import datetime

import data_layer
import finnhub_source

TRACKING_PATH    = os.path.join("data", "tracking.json")
ALERTS_SENT_PATH = os.path.join("data", "alerts_sent.json")


def _load(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save(path, obj):
    os.makedirs("data", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def get_live_price(ticker):
    """מחיר בזמן אמת: Finnhub /quote קודם, אז yfinance דקה, אז סגירה יומית."""
    q = finnhub_source.quote(ticker)
    if q:
        return q["price"]
    # גיבוי: yfinance נתוני דקה (לרוב חסום בענן, אבל ננסה)
    try:
        import yfinance as yf
        df = yf.download(ticker, period="1d", interval="1m",
                         progress=False, auto_adjust=True)
        if df is not None and not df.empty:
            return round(float(df["Close"].iloc[-1]), 2)
    except Exception:
        pass
    # מוצא אחרון: סגירה יומית (לא בזמן אמת אבל עדיף מכלום)
    return data_layer.get_last_price(ticker)


def send_telegram(msg):
    token = os.environ.get("TELEGRAM_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("⚠️  אין פרטי טלגרם — מדלגים")
        return
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
            timeout=15,
        )
        print("📱 התראה נשלחה!")
    except Exception as e:
        print(f"⚠️  שגיאת טלגרם: {e}")


def check():
    today = datetime.now().strftime("%Y-%m-%d")
    now_str = datetime.now().strftime("%H:%M")

    # עוקבים אחרי הפוזיציות שהסימולטור באמת קנה היום (portfolio.json),
    # כדי שהמעקב יתאים בדיוק למה שמוחזק — 3 המניות המדורגות.
    portfolio = _load(os.path.join("data", "portfolio.json"), {})
    open_today = [
        pos for pos in portfolio.get("open_positions", [])
        if pos.get("date_open") == today
        and pos.get("entry") and pos.get("stop_loss") and pos.get("target")
    ]

    if not open_today:
        print(f"[{now_str}] אין פוזיציות פתוחות למעקב היום")
        return False

    alerts_sent = _load(ALERTS_SENT_PATH, {})
    print(f"[{now_str}] בודק {len(open_today)} מניות בזמן אמת...")
    fired = False

    for rec in open_today:
        ticker = rec["ticker"]
        key_hit  = f"{today}_{ticker}_hit"
        key_warn = f"{today}_{ticker}_warn"
        if key_hit in alerts_sent:
            continue  # כבר התרענו על פגיעה — לא שולחים שוב

        price = get_live_price(ticker)
        if price is None:
            print(f"  {ticker}: אין מחיר")
            continue

        entry  = float(rec["entry"])
        target = float(rec["target"])
        stop   = float(rec["stop_loss"])
        change = round((price - entry) / entry * 100, 2)
        print(f"  {ticker}: ${price} (כניסה ${entry}, {change:+.1f}%)")

        # ── פגע ביעד ──
        if price >= target:
            send_telegram(
                f"🎯 *{ticker} פגע ביעד!*\n\n"
                f"📈 מחיר עכשיו: ${price}\n"
                f"🎯 יעד: ${target}\n"
                f"📊 כניסה: ${entry} ({change:+.1f}%)\n\n"
                f"_שקלי לממש את הפוזיציה בדמו של אינטרקטיב._"
            )
            alerts_sent[key_hit] = now_str
            fired = True

        # ── פגע בסטופ ──
        elif price <= stop:
            send_telegram(
                f"🛑 *{ticker} פגע בסטופ!*\n\n"
                f"📉 מחיר עכשיו: ${price}\n"
                f"🛑 סטופ: ${stop}\n"
                f"📊 כניסה: ${entry} ({change:+.1f}%)\n\n"
                f"_יש לצאת מהפוזיציה — זו בדיוק המטרה של הסטופ: להגביל הפסד._"
            )
            alerts_sent[key_hit] = now_str
            fired = True

        # ── אזהרה: קרוב לסטופ (עד 1%) — פעם אחת ──
        elif price <= stop * 1.01 and key_warn not in alerts_sent:
            dist = round((price - stop) / stop * 100, 1)
            send_telegram(
                f"⚠️ *{ticker} מתקרב לסטופ*\n\n"
                f"📉 מחיר: ${price} | סטופ: ${stop} (מרחק {dist}%)\n"
                f"_עקבי מקרוב._"
            )
            alerts_sent[key_warn] = now_str
            fired = True

    if fired:
        _save(ALERTS_SENT_PATH, alerts_sent)
        print(f"[{now_str}] נשלחו התראות ✅")
    else:
        print(f"[{now_str}] אין התראות חדשות")
    return fired


if __name__ == "__main__":
    # בדיקת שעות מסחר (13:30–20:00 UTC = שוק ניו יורק פתוח)
    now_utc = datetime.utcnow()
    if now_utc.weekday() >= 5:
        print("⛔ סוף שבוע — אין מסחר")
        raise SystemExit(0)
    h, m = now_utc.hour, now_utc.minute
    market_open = (h > 13 or (h == 13 and m >= 30)) and h < 20
    is_manual = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
    if not market_open and not is_manual:
        print(f"⛔ שוק סגור ({now_utc.strftime('%H:%M')} UTC)")
        raise SystemExit(0)
    check()
