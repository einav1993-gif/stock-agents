#!/usr/bin/env python3
"""בדיקת מערכת מלאה עם נתונים סינתטיים — בלי תלות ברשת."""
import json, os, shutil, sys
import numpy as np
import pandas as pd
from datetime import datetime

# ── נתונים סינתטיים דטרמיניסטיים ──
def make_df(ticker, days=130, trend=0.001):
    rng = np.random.default_rng(abs(hash(ticker)) % 2**32)
    idx = pd.bdate_range(end=pd.Timestamp.now().normalize(), periods=days)
    ret = rng.normal(trend, 0.02, days)
    close = 100 * np.cumprod(1 + ret)
    high = close * (1 + np.abs(rng.normal(0, 0.01, days)))
    low = close * (1 - np.abs(rng.normal(0, 0.01, days)))
    open_ = close * (1 + rng.normal(0, 0.005, days))
    vol = rng.integers(5_000_000, 50_000_000, days).astype(float)
    vol[-1] *= 3  # נפח חריג היום
    return pd.DataFrame({"Open": open_, "High": high, "Low": low,
                         "Close": close, "Volume": vol}, index=idx)

import data_layer
data_layer._from_yfinance = lambda t, p: make_df(t)
data_layer._from_stooq = lambda t, p: None

_orig_bulk = data_layer.get_daily_bulk
def fake_bulk(tickers, period="5d"):
    out = {}
    for t in tickers:
        out[t] = make_df(t, 10)
        data_layer.HEALTH["yfinance_ok"] += 1
        data_layer.HEALTH["sources"][t] = "yfinance"
    return out
data_layer.get_daily_bulk = fake_bulk

# ── 1. ראש הצוות ──
print("═"*55, "\n[1] מריץ את ראש הצוות...")
from team_lead import get_full_team_report
report = get_full_team_report()
top5, all_stocks, health = report["top5"], report["all_stocks"], report["health"]
assert len(top5) == 5, "top5 חסר"
assert health["tech_coverage"] > 80, f"כיסוי טכני נמוך: {health}"
assert not health["degraded"], "לא אמור להיות degraded עם נתונים מלאים"
assert all("components" in s for s in top5), "חסרים components"
assert top5[0]["entry"] is not None, "אין מחיר כניסה"
print(f"\n✔ ראש הצוות: 5 המלצות, כיסוי טכני {health['tech_coverage']}%, entry=${top5[0]['entry']}")

# ── 2. רישום מעקב (כמו cloud_runner) ──
print("\n[2] רושם המלצות למעקב...")
os.makedirs("data", exist_ok=True)
date_str = make_df("X").index[-1].strftime("%Y-%m-%d")  # יום המסחר האחרון
tracking = []
for s in top5:
    tracking.append({
        "date": date_str, "ticker": s["ticker"], "total_score": s["total_score"],
        "decision": s["decision"], "trade_type": s["trade_type"] if s["trade_type"] != "none" else "long",
        "components": s["components"], "entry": s["entry"], "stop_loss": s["stop_loss"],
        "target_1": s["target_1"], "target_2": s["target_2"],
        "degraded_data": False, "actual_result": None,
    })
with open("data/tracking.json", "w", encoding="utf-8") as f:
    json.dump(tracking, f, ensure_ascii=False)
print(f"✔ נרשמו {len(tracking)} המלצות")

# ── 3. ביקורת עצמית ──
print("\n[3] מריץ ביקורת עצמית...")
import self_review
self_review.MIN_SAMPLES_TO_LEARN = 3  # להדגמה בבדיקה
self_review.main()

records = json.load(open("data/tracking.json", encoding="utf-8"))
closed = [r for r in records if r["actual_result"] is not None]
assert closed, "הביקורת לא סגרה אף המלצה"
weights = json.load(open("data/weights.json", encoding="utf-8"))
w_sum = sum(v for k, v in weights.items() if k != "updated")
assert 0.99 < w_sum < 1.01, f"משקלות לא מנורמלים: {w_sum}"
log = json.load(open("data/learning_log.json", encoding="utf-8"))
assert log and log[-1]["checked"] == len(closed)
perf = json.load(open("data/agent_performance.json", encoding="utf-8"))
print(f"✔ ביקורת: {len(closed)} נבדקו | תוצאות: {[r['actual_result'] for r in closed]}")
print(f"✔ משקלות חדשים: { {k: round(v,3) for k,v in weights.items() if k!='updated'} }")
print(f"✔ ביצועי סוכנים: {perf}")

# ── 4. דוח HTML עם באנר בריאות וביצועים ──
print("\n[4] בונה דוח HTML...")
from generate_team_report import build_html
html = build_html(top5, all_stocks, health=health)
assert "בריאות המערכת" in html, "אין באנר בריאות"
assert "ביקורת עצמית" in html, "אין סקציית ביצועים"
with open("/tmp/test_report.html", "w", encoding="utf-8") as f:
    f.write(html)
print(f"✔ HTML נוצר ({len(html)} תווים) כולל באנר בריאות וסקציית ביצועים")

# ── 5. תרחיש degraded ──
print("\n[5] בודק תרחיש נתונים חסרים (degraded)...")
data_layer._CACHE.clear()
data_layer._from_yfinance = lambda t, p: None
data_layer.get_daily_bulk = lambda ts, period="5d": {t: None for t in ts}
import importlib, team_lead
importlib.reload(team_lead)
r2 = team_lead.get_full_team_report()
assert r2["health"]["degraded"], "מערכת בלי נתונים חייבת לסמן degraded"
assert all(s["decision"] == "⚫ אין נתונים" for s in r2["top5"]), \
    f"בלי נתונים אסור להמליץ: {[s['decision'] for s in r2['top5']]}"
html2 = build_html(r2["top5"], r2["all_stocks"], health=r2["health"])
assert "אזהרה: כיסוי הנתונים היום נמוך" in html2
print("✔ degraded: המערכת מזהירה במקום להמציא המלצות")

print("\n" + "═"*55)
print("✅ כל הבדיקות עברו — הצינור המלא עובד: בוקר → מעקב → ביקורת → למידה → דוח")
