#!/usr/bin/env python3
"""
🔌 data_layer.py — שכבת הנתונים המרכזית
==========================================
כל הסוכנים מושכים נתוני מחירים דרך הקובץ הזה בלבד.

למה זה קיים?
Yahoo Finance חוסמת בקשות משרתים של GitHub Actions,
ולכן הסוכנים נכשלו בשקט וקיבלנו דוחות ריקים.

הפתרון: שרשרת גיבויים —
  1. yfinance (עם ניסיונות חוזרים)
  2. Stooq — מקור חינמי שלא חוסם שרתים

בנוסף: מעקב בריאות (HEALTH) — כמה משיכות הצליחו ומאיפה,
כדי שראש הצוות ידע אם אפשר לסמוך על הנתונים של היום.
"""

import io
import time

import pandas as pd
import requests

# ── מעקב בריאות: מי הצליח, מי נכשל ──
HEALTH = {
    "yfinance_ok": 0,
    "stooq_ok": 0,
    "failed": [],       # טיקרים שלא הצלחנו למשוך בכלל
    "sources": {},      # ticker -> "yfinance" / "stooq"
}

_CACHE = {}  # ticker -> DataFrame (נמשך פעם אחת לריצה)

_PERIOD_DAYS = {
    "5d": 7, "1mo": 31, "2mo": 62, "3mo": 92,
    "6mo": 183, "1y": 366, "2y": 730,
}


def _flatten(df):
    """yfinance חדש מחזיר עמודות דו-שכבתיות (Close, TSLA) — משטחים לשכבה אחת."""
    if df is None:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    return df


def _from_yfinance(ticker, period):
    for attempt in range(2):
        try:
            import yfinance as yf
            df = yf.download(ticker, period=period, interval="1d",
                             auto_adjust=True, progress=False, threads=False)
            df = _flatten(df)
            if df is not None and not df.empty and len(df) >= 3:
                df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
                if not df.empty:
                    return df
        except Exception:
            pass
        time.sleep(1 + attempt)  # המתנה לפני ניסיון נוסף
    return None


def _from_stooq(ticker, period):
    """Stooq — נתוני OHLCV יומיים בחינם, עובד מצוין משרתים."""
    try:
        sym = ticker.lower().replace("-", ".") + ".us"
        url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
        r = requests.get(url, timeout=12,
                         headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200 or not r.text.startswith("Date"):
            return None
        df = pd.read_csv(io.StringIO(r.text),
                         parse_dates=["Date"], index_col="Date")
        if df.empty:
            return None
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        days = _PERIOD_DAYS.get(period, 183)
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
        df = df[df.index >= cutoff]
        return df if len(df) >= 3 else None
    except Exception:
        return None


def get_daily(ticker, period="6mo"):
    """
    מחזיר DataFrame יומי (Open/High/Low/Close/Volume) עבור מניה.
    מנסה yfinance, ואם נכשל — Stooq. מחזיר None רק אם שניהם נכשלו.
    """
    cache_key = f"{ticker}:{period}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    df = _from_yfinance(ticker, period)
    if df is not None:
        HEALTH["yfinance_ok"] += 1
        HEALTH["sources"][ticker] = "yfinance"
    else:
        df = _from_stooq(ticker, period)
        if df is not None:
            HEALTH["stooq_ok"] += 1
            HEALTH["sources"][ticker] = "stooq"
        else:
            if ticker not in HEALTH["failed"]:
                HEALTH["failed"].append(ticker)

    _CACHE[cache_key] = df
    return df


def get_daily_bulk(tickers, period="5d"):
    """
    משיכה מרוכזת: מנסה yfinance בבקשה אחת (מהיר),
    ומשלים חורים ב-Stooq טיקר-טיקר.
    מחזיר dict: ticker -> DataFrame (או None).
    """
    out = {t: None for t in tickers}

    # ניסיון ראשון: הכל בבת אחת דרך yfinance
    try:
        import yfinance as yf
        raw = yf.download(list(tickers), period=period, interval="1d",
                          auto_adjust=True, progress=False, threads=True)
        if raw is not None and not raw.empty:
            if isinstance(raw.columns, pd.MultiIndex):
                for t in tickers:
                    try:
                        df = raw.xs(t, axis=1, level=1).dropna()
                        if len(df) >= 2:
                            out[t] = df
                            HEALTH["yfinance_ok"] += 1
                            HEALTH["sources"][t] = "yfinance"
                    except Exception:
                        continue
            elif len(tickers) == 1:
                t = list(tickers)[0]
                df = raw.dropna()
                if len(df) >= 2:
                    out[t] = df
                    HEALTH["yfinance_ok"] += 1
                    HEALTH["sources"][t] = "yfinance"
    except Exception:
        pass

    # השלמת חורים דרך Stooq
    missing = [t for t, df in out.items() if df is None]
    for t in missing:
        df = _from_stooq(t, period)
        if df is not None:
            out[t] = df
            HEALTH["stooq_ok"] += 1
            HEALTH["sources"][t] = "stooq"
        else:
            if t not in HEALTH["failed"]:
                HEALTH["failed"].append(t)
        time.sleep(0.15)  # נימוס כלפי השרת

    return out


def get_last_price(ticker):
    """מחיר סגירה אחרון (לא בזמן אמת) — מהנתונים היומיים."""
    df = get_daily(ticker, "5d")
    if df is None or df.empty:
        return None
    return float(df["Close"].iloc[-1])


def coverage(tickers):
    """אחוז הטיקרים שיש להם נתונים — מדד אמינות לריצה הנוכחית."""
    if not tickers:
        return 0.0
    ok = sum(1 for t in tickers if HEALTH["sources"].get(t))
    return round(ok / len(tickers) * 100, 1)


def health_summary():
    total = HEALTH["yfinance_ok"] + HEALTH["stooq_ok"] + len(HEALTH["failed"])
    return {
        "yfinance_ok": HEALTH["yfinance_ok"],
        "stooq_ok": HEALTH["stooq_ok"],
        "failed": list(HEALTH["failed"]),
        "total_requests": total,
    }


if __name__ == "__main__":
    for t in ["AAPL", "TSLA"]:
        df = get_daily(t, "1mo")
        src = HEALTH["sources"].get(t, "נכשל")
        print(f"{t}: {'✅ ' + str(len(df)) + ' ימים' if df is not None else '❌'} (מקור: {src})")
    print(health_summary())
