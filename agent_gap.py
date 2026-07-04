#!/usr/bin/env python3
"""
⚡ agent_gap.py — סוכן הגאפים והפרימרקט
==========================================
המחקר על מסחר יומי ברור: המנבא החזק ביותר לתנועה יומית הוא
פער פתיחה (Gap) של 3%+ עם נפח גבוה וקטליסט אמיתי.
הסוכן הזה מזהה בדיוק את זה:
- פער בין סגירת אתמול למחיר הנוכחי/פרימרקט
- נפח חריג ביום האחרון
- "Gap and Go" — פער שממשיך, מול "Gap Fill" — פער שנסגר
"""

import data_layer


def analyze(ticker):
    result = {
        "ticker": ticker,
        "gap_pct": None,
        "premarket_price": None,
        "volume_ratio": None,
        "signal": "",
        "score": 0,
        "signals": [],
        "warnings": [],
    }

    try:
        df = data_layer.get_daily(ticker, "1mo")
        if df is None or len(df) < 6:
            return result

        prev_close = float(df["Close"].iloc[-2])
        last_close = float(df["Close"].iloc[-1])
        last_open  = float(df["Open"].iloc[-1])
        last_vol   = float(df["Volume"].iloc[-1])
        avg_vol    = float(df["Volume"].iloc[-6:-1].mean())

        vol_ratio = round(last_vol / avg_vol, 2) if avg_vol > 0 else None
        result["volume_ratio"] = vol_ratio

        # ── פרימרקט (אם זמין) — המחיר לפני הפתיחה של היום ──
        pre_price = None
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).fast_info
            pre_price = getattr(info, "pre_market_price", None) or None
        except Exception:
            pass
        if pre_price:
            result["premarket_price"] = round(float(pre_price), 2)
            gap = (float(pre_price) - last_close) / last_close * 100
            gap_basis = "פרימרקט מול סגירה"
        else:
            # אין פרימרקט — משתמשים בפער הפתיחה של הבר האחרון
            gap = (last_open - prev_close) / prev_close * 100
            gap_basis = "פתיחה מול סגירת אתמול"

        gap = round(gap, 2)
        result["gap_pct"] = gap

        # ── ניקוד לפי המחקר: גאפ 3-4%+ עם נפח = הסטאפ הכי חזק ──
        if gap >= 4 and vol_ratio and vol_ratio >= 1.5:
            result["score"] = 30
            result["signals"].append(f"Gap&Go קלאסי: פער {gap:+.1f}% + נפח x{vol_ratio}")
        elif gap >= 4:
            result["score"] = 18
            result["signals"].append(f"פער גדול {gap:+.1f}% ({gap_basis}) — לוודא נפח")
        elif gap >= 2:
            result["score"] = 10
            result["signals"].append(f"פער {gap:+.1f}% ({gap_basis})")
        elif gap <= -4 and vol_ratio and vol_ratio >= 1.5:
            result["score"] = -25
            result["warnings"].append(f"פער שלילי חד {gap:+.1f}% עם נפח — לחץ מכירה")
        elif gap <= -2:
            result["score"] = -12
            result["warnings"].append(f"פער שלילי {gap:+.1f}%")

        # נפח חריג לבדו — עניין במניה
        if vol_ratio and vol_ratio >= 2.5 and abs(gap) < 2:
            result["score"] += 8
            result["signals"].append(f"נפח חריג x{vol_ratio} בלי תנועה — משהו מתבשל")

        result["signal"] = f"פער {gap:+.1f}% | נפח x{vol_ratio}" if vol_ratio else f"פער {gap:+.1f}%"

    except Exception:
        pass

    return result


def run(tickers):
    print(f"⚡ [סוכן גאפים] בודק פערי פתיחה ופרימרקט עבור {len(tickers)} מניות...")
    results = {t: analyze(t) for t in tickers}
    hot = sum(1 for r in results.values() if r["score"] >= 18)
    print(f"✅ [סוכן גאפים] {hot} מניות עם גאפ משמעותי")
    return results


if __name__ == "__main__":
    for t, r in run(["TSLA", "NVDA"]).items():
        print(t, r["signal"], r["score"])
