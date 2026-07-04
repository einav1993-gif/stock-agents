#!/usr/bin/env python3
"""
💼 paper_trader.py — הסימולטור: תיק מסחר דמה אוטומטי
=======================================================
"ארנק וירטואלי" של $1,000 שחי בקובץ data/portfolio.json (מקומט לריפו).
אין כסף אמיתי, אין ברוקר, אין סיסמאות — אבל סוחר לפי מחירי שוק אמיתיים.

מחזור יום:
  בוקר (cloud_runner):  open_positions() — קונה מניות שקיבלו איתות
                        לונג חזק (ציון ≥ ENTRY_THRESHOLD), עד MAX_POSITIONS.
  ערב (self_review):    close_positions() — בודק מול גבוה/נמוך של היום:
                        יעד? סטופ? אחרת סוגר בסגירה (מסחר יומי — בלי לילה).

כל עסקה כוללת עמלה מדומה כדי שהמספרים יהיו כנים.
"""

import json
import os
from datetime import datetime

import data_layer

PORTFOLIO_PATH = os.path.join("data", "portfolio.json")

STARTING_CASH   = 1000.0   # הון התחלתי בדולרים
ENTRY_THRESHOLD = 35       # ציון מינימלי לפתיחת עסקה ("לונג — בחן מקרוב" ומעלה)
MAX_POSITIONS   = 3        # מקסימום פוזיציות פתוחות במקביל
COMMISSION      = 1.0      # עמלה מדומה לכל צד (קנייה/מכירה) בדולר


def _default_portfolio():
    return {
        "cash": STARTING_CASH,
        "start_cash": STARTING_CASH,
        "start_date": datetime.now().strftime("%Y-%m-%d"),
        "open_positions": [],   # פוזיציות פתוחות כרגע
        "closed_trades": [],    # היסטוריית עסקאות סגורות
        "equity_curve": [],     # [{date, equity}] לגרף
        "peak_equity": STARTING_CASH,
        "max_drawdown_pct": 0.0,
    }


def load_portfolio():
    if not os.path.exists(PORTFOLIO_PATH):
        return _default_portfolio()
    try:
        with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
            p = json.load(f)
        for k, v in _default_portfolio().items():
            p.setdefault(k, v)
        return p
    except Exception:
        return _default_portfolio()


def save_portfolio(p):
    os.makedirs("data", exist_ok=True)
    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        json.dump(p, f, indent=2, ensure_ascii=False)


# ══════════════════════════════════════════
# בוקר: פתיחת פוזיציות לפי המלצות היום
# ══════════════════════════════════════════
def open_positions(top_stocks, date_str=None):
    """
    קונה מניות שקיבלו איתות לונג חזק. מחזיר רשימת הפקודות שבוצעו
    (כדי לבנות מהן כרטיס פקודה לאינטרקטיב).
    """
    p = load_portfolio()
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")

    held = {pos["ticker"] for pos in p["open_positions"]}
    slots = MAX_POSITIONS - len(p["open_positions"])
    orders = []

    if slots <= 0:
        return p, orders

    # מועמדים: לונג, ציון מספיק, יש מחיר כניסה/סטופ/יעד, לא מוחזק כבר
    picks = [
        s for s in top_stocks
        if s.get("trade_type") == "long"
        and s.get("total_score", 0) >= ENTRY_THRESHOLD
        and s.get("entry") and s.get("stop_loss") and s.get("target_1")
        and s["ticker"] not in held
        and not s.get("degraded_data", False)
    ]
    picks.sort(key=lambda s: s.get("total_score", 0), reverse=True)

    for s in picks[:slots]:
        entry = float(s["entry"])
        shares = int(s.get("shares") or 0)
        # אם סוכן הסיכון לא נתן כמות — מחשבים לפי 30% מהתיק
        if shares < 1:
            shares = int((p["cash"] * 0.30) / entry)
        cost = shares * entry + COMMISSION
        if shares < 1 or cost > p["cash"]:
            continue

        p["cash"] -= cost
        pos = {
            "ticker":     s["ticker"],
            "date_open":  date_str,
            "shares":     shares,
            "entry":      round(entry, 2),
            "stop_loss":  round(float(s["stop_loss"]), 2),
            "target":     round(float(s["target_1"]), 2),
            "score":      s.get("total_score"),
            "cost":       round(cost, 2),
        }
        p["open_positions"].append(pos)
        orders.append(pos)

    save_portfolio(p)
    return p, orders


# ══════════════════════════════════════════
# ערב: סגירת פוזיציות מול תוצאות היום
# ══════════════════════════════════════════
def close_positions(date_str=None):
    """סוגר את כל הפוזיציות הפתוחות מול נתוני היום. מחזיר (portfolio, סיכום)."""
    p = load_portfolio()
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    closed_today = []

    still_open = []
    for pos in p["open_positions"]:
        df = data_layer.get_daily(pos["ticker"], "5d")
        if df is None or df.empty:
            still_open.append(pos)   # אין נתונים — משאירים לבדיקה מחר
            continue

        bar = df.iloc[-1]
        day_high = float(bar["High"])
        day_low  = float(bar["Low"])
        close    = float(bar["Close"])

        entry, stop, target = pos["entry"], pos["stop_loss"], pos["target"]

        # קובעים מחיר יציאה לפי מה שקרה במהלך היום
        if day_low <= stop and day_high >= target:
            exit_price, reason = stop, "🛑 סטופ (יום תנודתי)"  # שמרנות: סטופ קודם
        elif day_low <= stop:
            exit_price, reason = stop, "🛑 סטופ"
        elif day_high >= target:
            exit_price, reason = target, "✅ יעד"
        else:
            exit_price, reason = close, "🔔 סגירת יום"

        proceeds = pos["shares"] * exit_price - COMMISSION
        pnl = round(proceeds - pos["cost"], 2)
        pnl_pct = round(pnl / pos["cost"] * 100, 2)

        p["cash"] += proceeds
        trade = {**pos, "date_close": date_str, "exit": round(exit_price, 2),
                 "reason": reason, "pnl": pnl, "pnl_pct": pnl_pct}
        p["closed_trades"].append(trade)
        closed_today.append(trade)

    p["open_positions"] = still_open

    # עדכון עקומת ההון + drawdown
    equity = p["cash"] + sum(
        pos["shares"] * (data_layer.get_last_price(pos["ticker"]) or pos["entry"])
        for pos in p["open_positions"]
    )
    equity = round(equity, 2)
    p["equity_curve"].append({"date": date_str, "equity": equity})
    p["peak_equity"] = max(p.get("peak_equity", equity), equity)
    if p["peak_equity"] > 0:
        dd = (p["peak_equity"] - equity) / p["peak_equity"] * 100
        p["max_drawdown_pct"] = round(max(p.get("max_drawdown_pct", 0), dd), 2)

    save_portfolio(p)
    return p, closed_today


# ══════════════════════════════════════════
# סטטיסטיקה מסכמת
# ══════════════════════════════════════════
def stats(p=None):
    p = p or load_portfolio()
    trades = p["closed_trades"]
    open_val = sum(
        pos["shares"] * (data_layer.get_last_price(pos["ticker"]) or pos["entry"])
        for pos in p["open_positions"]
    )
    equity = round(p["cash"] + open_val, 2)
    total_return = round((equity - p["start_cash"]) / p["start_cash"] * 100, 2)

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    win_rate = round(len(wins) / len(trades) * 100) if trades else 0
    avg_win = round(sum(t["pnl"] for t in wins) / len(wins), 2) if wins else 0
    avg_loss = round(sum(t["pnl"] for t in losses) / len(losses), 2) if losses else 0

    return {
        "equity": equity,
        "cash": round(p["cash"], 2),
        "start_cash": p["start_cash"],
        "total_return_pct": total_return,
        "open_count": len(p["open_positions"]),
        "closed_count": len(trades),
        "win_rate": win_rate,
        "wins": len(wins),
        "losses": len(losses),
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "max_drawdown_pct": p.get("max_drawdown_pct", 0),
        "start_date": p.get("start_date"),
    }


if __name__ == "__main__":
    import pprint
    pprint.pprint(stats())
