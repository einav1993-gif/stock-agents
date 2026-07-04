#!/usr/bin/env python3
"""
🪞 self_review.py — הביקורת העצמית של המערכת
================================================
רץ כל ערב אחרי סגירת המסחר (workflow: end_of_day.yml).

מה הוא עושה:
1. פותח את data/tracking.json — כל ההמלצות שנרשמו בבוקר.
2. מושך את נתוני היום בפועל (גבוה/נמוך/סגירה) ובודק:
   פגע ביעד? פגע בסטופ? לאן המניה באמת הלכה?
   (הבדיקה על הגבוה/נמוך של היום — לא רק על הסגירה!)
3. ניתוח טעויות: עבור כל סוכן (טכני, חדשות, פונדמנטלי...)
   בודק אם הכיוון שהוא הצביע עליו תאם את מה שקרה בפועל.
   שומר סטטיסטיקה מצטברת ב-data/agent_performance.json.
4. למידה: מעדכן את המשקלות ב-data/weights.json —
   סוכן שצודק יותר מקבל משקל גבוה יותר מחר.
5. כותב "יומן למידה" ב-data/learning_log.json ושולח סיכום לטלגרם.

כל הקבצים נשמרים בתיקיית data/ שמקומטת (committed) לריפו —
כך ההיסטוריה שורדת בין ריצות, וזה מה שמאפשר למידה אמיתית.
"""

import json
import os
from datetime import datetime

import data_layer

DATA_DIR = "data"
TRACKING_PATH = os.path.join(DATA_DIR, "tracking.json")
WEIGHTS_PATH = os.path.join(DATA_DIR, "weights.json")
PERF_PATH = os.path.join(DATA_DIR, "agent_performance.json")
LOG_PATH = os.path.join(DATA_DIR, "learning_log.json")

# משקלות ברירת מחדל (כמו שהיו קבועים בקוד עד עכשיו)
DEFAULT_WEIGHTS = {
    "tech": 0.35, "macro": 0.15, "news": 0.20,
    "sent": 0.10, "fund": 0.15, "risk": 0.05,
}

AGENT_NAMES_HE = {
    "tech": "הסוכן הטכני", "macro": "סוכן המאקרו", "news": "סוכן החדשות",
    "sent": "סוכן הסנטימנט", "fund": "הסוכן הפונדמנטלי", "risk": "סוכן הסיכון",
}

MIN_SAMPLES_TO_LEARN = 10   # לא משנים משקלות לפני שיש מספיק דוגמאות
LEARNING_RATE = 0.25        # כמה מהר המשקלות זזים (0=בכלל לא, 1=מיד)
OPINION_THRESHOLD = 5       # ציון סוכן מעל/מתחת לזה נחשב "הבעת דעה"


def _load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path, obj):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


# ══════════════════════════════════════════
# שלב 1: בדיקת תוצאות היום מול ההמלצות
# ══════════════════════════════════════════
def check_outcomes(records):
    """ממלא actual_result לכל המלצה פתוחה שהתאריך שלה הגיע."""
    today = datetime.now().strftime("%Y-%m-%d")
    checked = []

    for rec in records:
        if rec.get("actual_result") is not None:
            continue
        if rec.get("date", "") > today:
            continue

        ticker = rec["ticker"]
        df = data_layer.get_daily(ticker, "1mo")
        if df is None or df.empty:
            continue

        # מאתרים את הבר של יום ההמלצה
        day_rows = df[df.index.strftime("%Y-%m-%d") == rec["date"]]
        if day_rows.empty:
            # אין עדיין בר לאותו יום (חג? עיכוב נתונים?) — נבדוק מחר
            continue

        bar = day_rows.iloc[-1]
        day_high = float(bar["High"])
        day_low = float(bar["Low"])
        close = float(bar["Close"])

        entry = rec.get("entry") or rec.get("price_at_report")
        if not entry:
            continue

        change_pct = round((close - entry) / entry * 100, 2)
        trade_type = rec.get("trade_type", "long")
        target = rec.get("target_1") or rec.get("target")
        stop = rec.get("stop_loss") or rec.get("stop")

        outcome = "open"
        pnl_pct = change_pct

        if trade_type == "long" and target and stop:
            hit_stop = day_low <= stop
            hit_target = day_high >= target
            if hit_stop and hit_target:
                # שניהם נגעו באותו יום — לא יודעים מה קרה קודם.
                # שמרנות: מניחים שהסטופ נתפס קודם.
                outcome = "stop"
                pnl_pct = round((stop - entry) / entry * 100, 2)
            elif hit_stop:
                outcome = "stop"
                pnl_pct = round((stop - entry) / entry * 100, 2)
            elif hit_target:
                outcome = "target"
                pnl_pct = round((target - entry) / entry * 100, 2)
            else:
                outcome = "neither"
        elif trade_type == "short" and target and stop:
            hit_stop = day_high >= stop
            hit_target = day_low <= target
            if hit_stop:
                outcome = "stop"
                pnl_pct = round((entry - stop) / entry * 100, 2)
            elif hit_target:
                outcome = "target"
                pnl_pct = round((entry - target) / entry * 100, 2)
            else:
                outcome = "neither"
                pnl_pct = -change_pct
        else:
            outcome = "no_trade"  # המלצת "המתן" — בודקים רק כיוון

        rec["actual_result"] = outcome
        rec["close_price"] = round(close, 2)
        rec["day_high"] = round(day_high, 2)
        rec["day_low"] = round(day_low, 2)
        rec["change_pct"] = change_pct
        rec["pnl_pct"] = pnl_pct
        checked.append(rec)

    return checked


# ══════════════════════════════════════════
# שלב 2: ניתוח טעויות — איזה סוכן צדק?
# ══════════════════════════════════════════
def attribute_agents(checked, perf):
    """
    לכל המלצה שנסגרה: בודק כל סוכן שהביע דעה (ציון מעל/מתחת לסף)
    האם הכיוון שלו תאם את התנועה בפועל.
    """
    for rec in checked:
        comps = rec.get("components")
        if not comps:
            continue
        actual_up = (rec.get("change_pct") or 0) > 0

        for agent, score in comps.items():
            if score is None:
                continue
            if score > OPINION_THRESHOLD:
                said_up = True
            elif score < -OPINION_THRESHOLD:
                said_up = False
            else:
                continue  # הסוכן לא הביע דעה ברורה — לא נספר

            stats = perf.setdefault(agent, {"correct": 0, "wrong": 0})
            if said_up == actual_up:
                stats["correct"] += 1
            else:
                stats["wrong"] += 1

    return perf


# ══════════════════════════════════════════
# שלב 3: למידה — עדכון משקלות
# ══════════════════════════════════════════
def update_weights(weights, perf):
    """
    סוכן מדויק יותר → משקל גבוה יותר.
    עדכון הדרגתי (LEARNING_RATE) כדי שיום חריג אחד לא יהפוך את המערכת.
    """
    total_samples = sum(s["correct"] + s["wrong"] for s in perf.values())
    if total_samples < MIN_SAMPLES_TO_LEARN:
        return weights, [f"עדיין אין מספיק דוגמאות ללמידה ({total_samples}/{MIN_SAMPLES_TO_LEARN}) — המשקלות לא שונו"]

    # דיוק מוחלק (Laplace) לכל סוכן
    accuracy = {}
    for agent in DEFAULT_WEIGHTS:
        s = perf.get(agent, {"correct": 0, "wrong": 0})
        accuracy[agent] = (s["correct"] + 1) / (s["correct"] + s["wrong"] + 2)

    # משקל מוצע: פרופורציונלי לדיוק
    acc_sum = sum(accuracy.values())
    proposed = {a: accuracy[a] / acc_sum for a in accuracy}

    changes = []
    new_weights = {}
    for agent in DEFAULT_WEIGHTS:
        old = weights.get(agent, DEFAULT_WEIGHTS[agent])
        new = old * (1 - LEARNING_RATE) + proposed[agent] * LEARNING_RATE
        new = max(0.05, min(0.45, new))  # גבולות בטיחות
        new_weights[agent] = new
        if abs(new - old) >= 0.005:
            direction = "עלה" if new > old else "ירד"
            changes.append(
                f"{AGENT_NAMES_HE[agent]}: דיוק {accuracy[agent]*100:.0f}% → המשקל {direction} "
                f"מ-{old*100:.0f}% ל-{new*100:.0f}%"
            )

    # נרמול לסכום 1
    total = sum(new_weights.values())
    new_weights = {a: round(w / total, 4) for a, w in new_weights.items()}

    if not changes:
        changes.append("המשקלות יציבים — אין שינוי מהותי היום")
    return new_weights, changes


# ══════════════════════════════════════════
# שלב 4: יומן למידה + טלגרם
# ══════════════════════════════════════════
def summarize(checked, perf, weight_changes):
    trades = [r for r in checked if r["actual_result"] in ("target", "stop", "neither")]
    hits = sum(1 for r in trades if r["actual_result"] == "target")
    stops = sum(1 for r in trades if r["actual_result"] == "stop")
    neither = sum(1 for r in trades if r["actual_result"] == "neither")

    # גם המלצות "המתן" נבדקות על כיוון בלבד
    direction_checks = [r for r in checked if r.get("components")]
    dir_correct = sum(
        1 for r in direction_checks
        if ((r.get("total_score") or 0) > 0) == ((r.get("change_pct") or 0) > 0)
    )

    lessons = []
    # מי הסוכן הכי חלש/חזק עד כה?
    scored = {
        a: s["correct"] / (s["correct"] + s["wrong"])
        for a, s in perf.items() if (s["correct"] + s["wrong"]) >= 5
    }
    if scored:
        best = max(scored, key=scored.get)
        worst = min(scored, key=scored.get)
        lessons.append(f"הסוכן המדויק ביותר עד כה: {AGENT_NAMES_HE.get(best, best)} ({scored[best]*100:.0f}%)")
        lessons.append(f"הסוכן החלש ביותר עד כה: {AGENT_NAMES_HE.get(worst, worst)} ({scored[worst]*100:.0f}%)")

    for r in trades:
        if r["actual_result"] == "stop":
            lessons.append(
                f"{r['ticker']}: נעצר בסטופ ({r['pnl_pct']:+.1f}%). "
                f"ציון הבוקר היה {r.get('total_score', '?')} — נבדוק אילו סוכנים דחפו אותו למעלה."
            )

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "checked": len(checked),
        "hits": hits,
        "stops": stops,
        "neither": neither,
        "direction_correct": dir_correct,
        "direction_total": len(direction_checks),
        "weight_changes": weight_changes,
        "lessons": lessons,
    }


def send_telegram(entry, records):
    token = os.environ.get("TELEGRAM_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("⚠️  אין פרטי טלגרם — מדלגים על שליחה")
        return
    try:
        import requests

        completed = [r for r in records if r.get("actual_result")
                     and r.get("actual_result") != "open"]
        total_hits = sum(1 for r in completed if r["actual_result"] == "target")
        total_stops = sum(1 for r in completed if r["actual_result"] == "stop")

        msg = f"🪞 *ביקורת עצמית — {datetime.now().strftime('%d/%m/%Y')}*\n\n"
        msg += f"נבדקו היום: {entry['checked']} המלצות\n"
        msg += f"✅ פגעו ביעד: {entry['hits']} | 🛑 סטופ: {entry['stops']} | ⏳ באמצע: {entry['neither']}\n"
        if entry["direction_total"]:
            msg += f"🎯 דיוק כיוון: {entry['direction_correct']}/{entry['direction_total']}\n"
        msg += f"\n📊 *מצטבר:* {total_hits} יעדים / {total_stops} סטופים מתוך {len(completed)}\n"
        if entry["weight_changes"]:
            msg += "\n🧠 *למידה:*\n" + "\n".join(f"• {c}" for c in entry["weight_changes"][:4])
        if entry["lessons"]:
            msg += "\n\n📝 *לקחים:*\n" + "\n".join(f"• {l}" for l in entry["lessons"][:4])

        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
            timeout=15,
        )
        print("✅ סיכום ביקורת נשלח לטלגרם")
    except Exception as e:
        print(f"⚠️  שגיאת טלגרם: {e}")


# ══════════════════════════════════════════
# ראשי
# ══════════════════════════════════════════
def main():
    print("🪞 ביקורת עצמית — בודקת את המלצות הבוקר מול המציאות")
    print("=" * 55)

    records = _load_json(TRACKING_PATH, [])
    if not records:
        print("ℹ️  אין עדיין המלצות במעקב (data/tracking.json ריק)")
        return

    weights = _load_json(WEIGHTS_PATH, dict(DEFAULT_WEIGHTS))
    perf = _load_json(PERF_PATH, {})
    log = _load_json(LOG_PATH, [])

    # 1. בדיקת תוצאות
    checked = check_outcomes(records)
    print(f"📊 נבדקו {len(checked)} המלצות חדשות")

    # 2. ניתוח טעויות per-agent
    perf = attribute_agents(checked, perf)

    # 3. עדכון משקלות
    new_weights, changes = update_weights(
        {k: v for k, v in weights.items() if k in DEFAULT_WEIGHTS}, perf
    )
    new_weights["updated"] = datetime.now().isoformat()

    # 4. יומן + שמירה
    entry = summarize(checked, perf, changes)
    log.append(entry)

    _save_json(TRACKING_PATH, records)
    _save_json(WEIGHTS_PATH, new_weights)
    _save_json(PERF_PATH, perf)
    _save_json(LOG_PATH, log)

    for c in changes:
        print(f"🧠 {c}")
    for l in entry["lessons"]:
        print(f"📝 {l}")

    # 5. טלגרם
    send_telegram(entry, records)
    print("\n✅ הביקורת העצמית הסתיימה — המערכת מוכנה למחר")


if __name__ == "__main__":
    main()
