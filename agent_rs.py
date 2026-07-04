#!/usr/bin/env python3
"""
💪 agent_rs.py — סוכן החוזק היחסי (Relative Strength)
=======================================================
עיקרון ותיק של סוחרים מקצועיים: אל תשאל "האם המניה עולה?"
אלא "האם היא חזקה מהשוק?".
מניה שעולה כשהשוק (SPY) יורד — יש בה כוח קנייה אמיתי.
מניה שעולה רק כי הכול עולה — אין לה שום יתרון.
"""

import data_layer


def _pct_change(series, days):
    if len(series) <= days:
        return None
    return (float(series.iloc[-1]) / float(series.iloc[-1 - days]) - 1) * 100


def run(tickers):
    print(f"💪 [סוכן חוזק יחסי] משווה {len(tickers)} מניות מול SPY...")
    results = {}

    spy = data_layer.get_daily("SPY", "3mo")
    if spy is None or len(spy) < 21:
        print("⚠️  [סוכן חוזק יחסי] אין נתוני SPY — מדלג")
        return {t: {"ticker": t, "score": 0, "signal": "אין נתוני שוק",
                    "signals": [], "warnings": []} for t in tickers}

    spy_1d  = _pct_change(spy["Close"], 1)
    spy_5d  = _pct_change(spy["Close"], 5)
    spy_20d = _pct_change(spy["Close"], 20)

    for ticker in tickers:
        result = {
            "ticker": ticker, "score": 0, "signal": "",
            "rs_1d": None, "rs_5d": None, "rs_20d": None,
            "signals": [], "warnings": [],
        }
        try:
            df = data_layer.get_daily(ticker, "3mo")
            if df is None or len(df) < 21:
                result["signal"] = "אין מספיק נתונים"
                results[ticker] = result
                continue

            t_1d  = _pct_change(df["Close"], 1)
            t_5d  = _pct_change(df["Close"], 5)
            t_20d = _pct_change(df["Close"], 20)

            rs_1d  = round(t_1d - spy_1d, 2)   if t_1d  is not None and spy_1d  is not None else None
            rs_5d  = round(t_5d - spy_5d, 2)   if t_5d  is not None and spy_5d  is not None else None
            rs_20d = round(t_20d - spy_20d, 2) if t_20d is not None and spy_20d is not None else None

            result["rs_1d"], result["rs_5d"], result["rs_20d"] = rs_1d, rs_5d, rs_20d

            score = 0
            # חוזק בכל שלושת הטווחים — הסימן החזק ביותר
            if all(v is not None and v > 0 for v in (rs_1d, rs_5d, rs_20d)):
                score += 15
                result["signals"].append(
                    f"חזקה מהשוק בכל הטווחים (יום {rs_1d:+.1f}% | שבוע {rs_5d:+.1f}% | חודש {rs_20d:+.1f}%)")
            elif rs_5d is not None and rs_5d > 3:
                score += 10
                result["signals"].append(f"חזקה מהשוק השבוע ({rs_5d:+.1f}%)")
            elif rs_1d is not None and rs_1d > 2:
                score += 6
                result["signals"].append(f"חזקה מהשוק היום ({rs_1d:+.1f}%)")

            # מניה שעולה כשהשוק יורד — אות מיוחד
            if (spy_1d is not None and t_1d is not None
                    and spy_1d < -0.3 and t_1d > 0.5):
                score += 10
                result["signals"].append("עולה ביום אדום של השוק — כוח קנייה אמיתי 💪")

            # חולשה עקבית מול השוק
            if all(v is not None and v < 0 for v in (rs_1d, rs_5d, rs_20d)):
                score -= 12
                result["warnings"].append(
                    f"חלשה מהשוק בכל הטווחים ({rs_20d:+.1f}% בחודש)")

            result["score"] = score
            result["signal"] = f"RS: יום {rs_1d:+.1f}% | שבוע {rs_5d:+.1f}%" \
                if rs_1d is not None and rs_5d is not None else "RS חלקי"

        except Exception:
            pass
        results[ticker] = result

    strong = sum(1 for r in results.values() if r["score"] >= 10)
    print(f"✅ [סוכן חוזק יחסי] {strong} מניות חזקות מהשוק")
    return results


if __name__ == "__main__":
    for t, r in run(["TSLA", "NVDA"]).items():
        print(t, r["signal"], r["score"])
