#!/usr/bin/env python3
"""
📅 agent_calendar.py — סוכן לוח הדוחות והאירועים
===================================================
הימים עם התנועות הכי גדולות הם ימי אירועים:
- דוח רבעוני של החברה (לפני/אחרי) — תנועות של 5-15%
- אירועי מאקרו (פד, אינפלציה, תעסוקה) — מזיזים את כל השוק

הסוכן בודק לכל מניה מתי הדוח הקרוב, ומתריע על אירועי
מאקרו גדולים היום — כי ביום כזה גם ניתוח מושלם יכול להימחק.
"""

import json
import urllib.request
from datetime import datetime, timedelta, timezone

import yfinance as yf

FF_CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

_macro_cache = {"events": None}


def get_macro_events_today():
    """אירועי מאקרו אמריקאיים בהשפעה גבוהה — היום ומחר."""
    if _macro_cache["events"] is not None:
        return _macro_cache["events"]
    events = []
    try:
        req = urllib.request.Request(
            FF_CALENDAR_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        today = datetime.now(timezone.utc).date()
        for ev in data:
            if str(ev.get("country", "")).upper() != "USD":
                continue
            if str(ev.get("impact", "")).lower() != "high":
                continue
            date_str = str(ev.get("date", ""))[:10]
            try:
                ev_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except Exception:
                continue
            if today <= ev_date <= today + timedelta(days=1):
                events.append({
                    "title": ev.get("title", ""),
                    "date": date_str,
                    "is_today": ev_date == today,
                })
    except Exception:
        pass
    _macro_cache["events"] = events
    return events


def analyze(ticker, macro_events):
    result = {
        "ticker": ticker,
        "earnings_date": None,
        "earnings_days_away": None,
        "macro_events": [e["title"] for e in macro_events if e["is_today"]],
        "signal": "",
        "score": 0,
        "signals": [],
        "warnings": [],
    }

    # ── דוח רבעוני קרוב ──
    try:
        cal = yf.Ticker(ticker).calendar
        ed = None
        if isinstance(cal, dict):
            dates = cal.get("Earnings Date") or []
            if dates:
                ed = dates[0]
        if ed is not None:
            if hasattr(ed, "date"):
                ed = ed.date() if callable(getattr(ed, "date", None)) else ed
            days = (ed - datetime.now().date()).days
            result["earnings_date"] = str(ed)
            result["earnings_days_away"] = days

            if days == 0:
                result["score"] = -10
                result["warnings"].append(
                    "דוח רבעוני היום! תנועה חדה צפויה לכל כיוון — סיכון גבוה")
            elif 1 <= days <= 2:
                result["score"] = 8
                result["signals"].append(
                    f"דוח בעוד {days} ימים — צפויה תנועה, מומנטום לפני דוח")
            elif 3 <= days <= 5:
                result["score"] = 4
                result["signals"].append(f"דוח בעוד {days} ימים")
    except Exception:
        pass

    # ── אירועי מאקרו היום ──
    today_events = [e for e in macro_events if e["is_today"]]
    if today_events:
        result["score"] -= 5
        names = ", ".join(e["title"] for e in today_events[:2])
        result["warnings"].append(f"אירוע מאקרו היום: {names} — השוק כולו עלול לזוז")

    parts = []
    if result["earnings_days_away"] is not None:
        parts.append(f"דוח בעוד {result['earnings_days_away']} ימים")
    if today_events:
        parts.append(f"{len(today_events)} אירועי מאקרו היום")
    result["signal"] = " | ".join(parts) if parts else "אין אירועים קרובים"

    return result


def run(tickers):
    print(f"📅 [סוכן לוח אירועים] בודק דוחות ואירועי מאקרו עבור {len(tickers)} מניות...")
    macro_events = get_macro_events_today()
    if macro_events:
        print(f"   ⚠️ {len(macro_events)} אירועי מאקרו בהשפעה גבוהה היום/מחר")

    results = {t: analyze(t, macro_events) for t in tickers}
    with_earnings = sum(1 for r in results.values()
                        if r["earnings_days_away"] is not None
                        and 0 <= r["earnings_days_away"] <= 5)
    print(f"✅ [סוכן לוח אירועים] {with_earnings} מניות עם דוח בשבוע הקרוב")
    return results


if __name__ == "__main__":
    for t, r in run(["TSLA", "NVDA"]).items():
        print(t, r["signal"], r["score"])
