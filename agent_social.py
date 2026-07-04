#!/usr/bin/env python3
"""
🗣️ agent_social.py — סוכן הסנטימנט החברתי
=============================================
עוקב אחרי מה שסוחרים קטנים מדברים עליו ב-Reddit
(r/wallstreetbets ועוד) דרך ApeWisdom — API חינמי בלי מפתח.

למה זה חשוב למסחר יומי: מניה שמטפסת בדירוג האזכורים
מושכת כסף קמעונאי — ותנועות חדות מגיעות עם קהל.
אבל זהירות: כשמניה כבר #1 הרבה זמן — לרוב מאוחר מדי.
"""

import json
import urllib.request

APEWISDOM_URL = "https://apewisdom.io/api/v1.0/filter/all-stocks/page/{page}"

_cache = {"data": None}


def _fetch_trending(pages=2):
    """מושך את המניות המדוברות ביותר ברדיט. מחזיר dict: ticker -> נתונים."""
    if _cache["data"] is not None:
        return _cache["data"]

    trending = {}
    for page in range(1, pages + 1):
        try:
            req = urllib.request.Request(
                APEWISDOM_URL.format(page=page),
                headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            for item in data.get("results", []):
                t = item.get("ticker", "")
                if t:
                    trending[t] = {
                        "rank":          int(item.get("rank", 999)),
                        "mentions":      int(item.get("mentions", 0) or 0),
                        "upvotes":       int(item.get("upvotes", 0) or 0),
                        "rank_24h_ago":  int(item.get("rank_24h_ago", 999) or 999),
                        "mentions_24h_ago": int(item.get("mentions_24h_ago", 0) or 0),
                    }
        except Exception:
            break

    _cache["data"] = trending
    return trending


def analyze(ticker, trending):
    result = {
        "ticker": ticker,
        "rank": None,
        "mentions": 0,
        "mention_change_pct": None,
        "signal": "לא מדוברת ברדיט",
        "score": 0,
        "signals": [],
        "warnings": [],
    }

    data = trending.get(ticker)
    if not data:
        return result

    result["rank"] = data["rank"]
    result["mentions"] = data["mentions"]

    prev = data["mentions_24h_ago"]
    if prev > 0:
        change = round((data["mentions"] - prev) / prev * 100)
        result["mention_change_pct"] = change
    else:
        change = None

    rank_jump = data["rank_24h_ago"] - data["rank"]  # חיובי = טיפסה

    # ── ניקוד: זינוק באזכורים = כסף קמעונאי בדרך ──
    if change is not None and change >= 150 and data["mentions"] >= 30:
        result["score"] = 20
        result["signals"].append(
            f"אזכורים ברדיט קפצו {change:+d}% ביממה ({data['mentions']} אזכורים)")
    elif change is not None and change >= 50 and data["mentions"] >= 20:
        result["score"] = 12
        result["signals"].append(f"עניין גובר ברדיט: {change:+d}% אזכורים")
    elif rank_jump >= 20:
        result["score"] = 8
        result["signals"].append(f"טיפסה {rank_jump} מקומות בדירוג רדיט (עכשיו #{data['rank']})")
    elif data["rank"] <= 5 and (change is None or change < 0):
        # כבר בצמרת והעניין דועך — הקהל כבר בפנים
        result["score"] = -8
        result["warnings"].append(f"#{data['rank']} ברדיט אבל העניין דועך — אולי מאוחר מדי")
    elif data["rank"] <= 15:
        result["score"] = 4
        result["signals"].append(f"מדוברת ברדיט (#{data['rank']})")

    result["signal"] = f"רדיט #{data['rank']} | {data['mentions']} אזכורים"
    if change is not None:
        result["signal"] += f" ({change:+d}%)"

    return result


def run(tickers):
    print(f"🗣️  [סוכן חברתי] בודק את Reddit עבור {len(tickers)} מניות...")
    trending = _fetch_trending()
    if not trending:
        print("⚠️  [סוכן חברתי] ApeWisdom לא זמין — מחזיר ריק")
        return {t: analyze(t, {}) for t in tickers}

    results = {t: analyze(t, trending) for t in tickers}
    talked = sum(1 for r in results.values() if r["rank"] is not None)
    print(f"✅ [סוכן חברתי] {talked}/{len(tickers)} מהמועמדות מדוברות ברדיט")
    return results


if __name__ == "__main__":
    for t, r in run(["TSLA", "GME", "NVDA"]).items():
        print(t, r["signal"], r["score"])
