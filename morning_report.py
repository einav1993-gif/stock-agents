#!/usr/bin/env python3
"""
🌅 אורי — סוכן הבוקר
=====================
מתעורר כל שני-שישי ב-15:30 שעון ישראל.
מנתח את כל המניות ברשימה, מחשב ציון לכל אחת,
ומחליט מי ה-TOP 3 להיום.
שולח דוח לטלגרם ופותח את הדשבורד.
"""

import yfinance as yf
import pandas as pd
import ta as ta_lib
from datetime import datetime
import json
import os
from market_context import (
    get_full_market_context, get_stock_context,
    format_market_summary
)
from intelligence_layer import (
    get_full_intelligence, calc_intelligence_score,
    get_economic_calendar
)

# ==============================
# הגדרות
# ==============================
VIRTUAL_CAPITAL = 10_000  # דולר וירטואלי לדמו

WATCHLIST = [
    "TSLA", "NVDA", "AMD", "AAPL", "META",
    "AMZN", "GOOGL", "MSFT", "COIN", "PLTR",
    "SOFI", "RIVN", "MARA", "SMCI", "IONQ"
]

# ==============================
# שליפת נתונים
# ==============================
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        df_hourly = stock.history(period="5d", interval="1h")
        df_daily  = stock.history(period="60d", interval="1d")
        info  = stock.info or {}
        news  = stock.news[:3] if stock.news else []
        return df_hourly, df_daily, info, news
    except Exception:
        return None, None, {}, []


# ==============================
# ניתוח טכני
# ==============================
def calculate_technicals(df_hourly, df_daily):
    if df_hourly is None or len(df_hourly) < 14:
        return {}
    if df_daily is None or len(df_daily) < 21:
        return {}

    # אינדיקטורים על גרף שעתי
    df = df_hourly.copy()
    df['RSI']   = ta_lib.momentum.RSIIndicator(df['Close'], window=14).rsi()
    df['EMA9']  = ta_lib.trend.EMAIndicator(df['Close'], window=9).ema_indicator()
    df['EMA21'] = ta_lib.trend.EMAIndicator(df['Close'], window=21).ema_indicator()

    macd_obj = ta_lib.trend.MACD(df['Close'])
    df['MACD_line']   = macd_obj.macd()
    df['MACD_signal'] = macd_obj.macd_signal()

    df['Vol_Avg']   = df['Volume'].rolling(20).mean()
    df['Vol_Ratio'] = df['Volume'] / df['Vol_Avg'].replace(0, 1)

    # Bollinger Bands
    bb = ta_lib.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
    df['BB_upper'] = bb.bollinger_hband()
    df['BB_lower'] = bb.bollinger_lband()
    df['BB_pct']   = bb.bollinger_pband()  # 0=בתחתית, 1=בפסגה

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last

    # מגמה יומית (EMA על גרף יומי)
    dd = df_daily.copy()
    dd['EMA50'] = ta_lib.trend.EMAIndicator(dd['Close'], window=50).ema_indicator()
    daily_last = dd.iloc[-1]

    price      = float(last['Close'])
    prev_close = float(prev['Close'])
    gap_pct    = round(((price - prev_close) / prev_close) * 100, 2)

    return {
        'price':       round(price, 2),
        'prev_close':  round(prev_close, 2),
        'gap_pct':     gap_pct,
        'rsi':         round(float(last.get('RSI', 50) or 50), 1),
        'macd_line':   float(last.get('MACD_line', 0) or 0),
        'macd_signal': float(last.get('MACD_signal', 0) or 0),
        'ema9':        float(last.get('EMA9', 0) or 0),
        'ema21':       float(last.get('EMA21', 0) or 0),
        'ema50_daily': float(daily_last.get('EMA50', 0) or 0),
        'volume_ratio':round(float(last.get('Vol_Ratio', 1) or 1), 2),
        'day_high':    round(float(df_daily.iloc[-1]['High']), 2),
        'day_low':     round(float(df_daily.iloc[-1]['Low']), 2),
        'bb_pct':      round(float(last.get('BB_pct', 0.5) or 0.5), 2),
        'bb_upper':    round(float(last.get('BB_upper', 0) or 0), 2),
        'bb_lower':    round(float(last.get('BB_lower', 0) or 0), 2),
    }


# ==============================
# ציון הזדמנות
# ==============================
def score_stock(t):
    score = 0
    reasons  = []
    warnings = []

    rsi         = t.get('rsi', 50)
    macd_line   = t.get('macd_line', 0)
    macd_signal = t.get('macd_signal', 0)
    vol_ratio   = t.get('volume_ratio', 1)
    gap_pct     = t.get('gap_pct', 0)
    price       = t.get('price', 0)
    ema9        = t.get('ema9', 0)
    ema21       = t.get('ema21', 0)
    ema50d      = t.get('ema50_daily', 0)

    # ── RSI (25 נק׳) ──
    if rsi < 35:
        score += 22
        reasons.append(f"RSI {rsi} — מניה קנויה מעט מדי, פוטנציאל לקפיצה ⬆️")
    elif 40 <= rsi <= 60:
        score += 15
        reasons.append(f"RSI {rsi} — מאוזן, אין קיצוניות")
    elif rsi > 72:
        score += 5
        warnings.append(f"RSI {rsi} — קנויה יתר, עלול לרדת ⚠️")
    else:
        score += 10

    # ── MACD (25 נק׳) ──
    if macd_line > macd_signal and macd_line > 0:
        score += 25
        reasons.append("MACD ↑ חיובי וחוצה מעלה — תנופה עולה 📈")
    elif macd_line > macd_signal:
        score += 15
        reasons.append("MACD מתחיל להתאושש")
    else:
        score += 5
        warnings.append("MACD שלילי — מומנטום יורד 📉")

    # ── נפח (20 נק׳) ──
    if vol_ratio >= 2.5:
        score += 20
        reasons.append(f"נפח חריג ×{vol_ratio} — הרבה סוחרים פעילים! 🔥")
    elif vol_ratio >= 1.5:
        score += 12
        reasons.append(f"נפח גבוה ×{vol_ratio}")
    elif vol_ratio < 0.7:
        warnings.append("נפח נמוך — שוק רדום, פחות הזדמנויות")
        score += 2
    else:
        score += 8

    # ── גאפ / תנועת מחיר (15 נק׳) ──
    if 2 <= gap_pct <= 7:
        score += 15
        reasons.append(f"פתיחה עם עלייה של {gap_pct}% — מומנטום חיובי ☀️")
    elif -7 <= gap_pct <= -2:
        score += 10
        reasons.append(f"ירידה של {gap_pct}% — הזדמנות שורט או המתנה לשפל")
    elif abs(gap_pct) > 8:
        warnings.append(f"תנועה חדה מאוד ({gap_pct}%) — סיכון גבוה!")
        score += 5
    else:
        score += 8

    # ── מגמה EMA (15 נק׳) ──
    if ema9 > ema21 and price > ema9:
        score += 15
        reasons.append("מחיר מעל ממוצעי EMA — מגמה עולה ✅")
    elif ema9 < ema21 and price < ema9:
        score += 4
        warnings.append("מחיר מתחת לממוצעים — מגמה יורדת")
    else:
        score += 8

    # ── בונוס: מגמה יומית ──
    if ema50d > 0 and price > ema50d:
        score += 5
        reasons.append("מעל ממוצע 50 יום — רקע טוב לטווח קצר")

    # ── Bollinger Bands (5 נק') ──
    bb_pct = t.get('bb_pct', 0.5)
    if bb_pct <= 0.15:
        score += 5
        reasons.append(f"Bollinger Band: מחיר קרוב לחלק התחתון — פוטנציאל לקפיצה 📊")
    elif bb_pct >= 0.85:
        score = max(0, score - 3)
        warnings.append(f"Bollinger Band: מחיר קרוב לחלק העליון — קנוי יתר ⚠️")

    return min(score, 100), reasons, warnings


# ==============================
# גודל פוזיציה
# ==============================
def calc_position(price, capital=VIRTUAL_CAPITAL):
    risk          = capital * 0.02          # 2% מההון לסיכון
    stop_pct      = 0.015                   # 1.5% סטופ לוס
    stop_amount   = price * stop_pct
    shares        = max(1, int(risk / stop_amount))
    investment    = round(shares * price, 2)
    target        = round(price * 1.03, 2)  # יעד 3%
    stop          = round(price * (1 - stop_pct), 2)
    profit        = round(shares * (target - price), 2)
    loss          = round(shares * stop_amount, 2)
    return dict(shares=shares, investment=investment,
                target=target, stop=stop,
                profit=profit, loss=loss)


# ==============================
# חדשות
# ==============================
def format_news(articles):
    """הופך רשימת כתבות לטקסט קריא"""
    if not articles:
        return "לא נמצאו חדשות"
    lines = []
    for a in articles[:3]:
        title     = a.get('title', '')
        publisher = a.get('publisher', '')
        time_str  = a.get('time_str', '')
        if title:
            lines.append(f"• [{time_str}] {title} ({publisher})")
    return "\n  ".join(lines) if lines else "לא נמצאו חדשות"


# ==============================
# ניתוח מניה בודדת
# ==============================
def analyze_stock(ticker):
    df_h, df_d, info, _ = get_stock_data(ticker)
    if df_h is None or df_h.empty:
        return None

    t = calculate_technicals(df_h, df_d)
    if not t:
        return None

    score, reasons, warnings = score_stock(t)
    position = calc_position(t['price'])
    name     = info.get('shortName', ticker)

    # הקשר ספציפי למניה: earnings, sentiment, חדשות, Reddit, אופציות
    stock_ctx = get_stock_context(ticker)

    # ── Earnings: מורידים ציון ↓ ──
    if stock_ctx.get('earnings'):
        warnings.insert(0, stock_ctx['earnings'])
        score = max(0, score - 15)

    # ── Put/Call Ratio: מתאמים ציון ↑↓ ──
    options = stock_ctx.get('options')
    if options:
        adj = options['score_add']
        score = max(0, min(100, score + adj))
        if adj > 0:
            reasons.append(f"Put/Call {options['ratio']} — {options['emoji']} {options['signal']}")
        elif adj < 0:
            warnings.append(f"Put/Call {options['ratio']} — {options['emoji']} {options['signal']}")

    # ── שכבת אינטליגנציה מתקדמת ──
    intel        = get_full_intelligence(ticker, df_d)
    i_delta, i_reasons, i_warnings = calc_intelligence_score(intel)
    score        = max(0, min(100, score + i_delta))
    reasons     += i_reasons
    warnings    += i_warnings

    # ── חדשות: מחשבים כמה שעות ישנות ──
    news_articles = stock_ctx.get('news', [])
    news_text     = format_news(news_articles)

    return dict(
        ticker=ticker, name=name, score=score,
        technicals=t, reasons=reasons, warnings=warnings,
        position=position,
        news=news_text,
        news_articles=news_articles,
        sentiment=stock_ctx.get('sentiment'),
        reddit=stock_ctx.get('reddit'),
        options=options,
        earnings=stock_ctx.get('earnings'),
        insider=intel.get('insider'),
        short=intel.get('short'),
        analyst=intel.get('analyst'),
        premarket=intel.get('premarket'),
        sr=intel.get('sr'),
        sector=intel.get('sector'),
    )


# ==============================
# יצירת הדוח
# ==============================
EMOJI_SCORE = {70: "🟢 כדאי לבדוק!", 50: "🟡 ממתין לאישור", 0: "🔴 לא מומלץ היום"}

def rec_emoji(score):
    for threshold, label in EMOJI_SCORE.items():
        if score >= threshold:
            return label
    return "🔴 לא מומלץ"


def generate_report(results):
    now  = datetime.now().strftime("%d/%m/%Y %H:%M")
    top3 = sorted(results, key=lambda x: x['score'], reverse=True)[:3]

    # מצב השוק הכללי
    market_ctx     = get_full_market_context()
    market_summary = format_market_summary(market_ctx)

    market_ok = True
    if market_ctx.get('market') and not market_ctx['market']['favorable']:
        market_ok = False

    # לוח כלכלי
    econ_events = get_economic_calendar()

    lines = [
        "=" * 52,
        f"  🤖 דוח בוקר — סוכני המניות של עינב",
        f"  📅 {now}",
        f"  💰 הון וירטואלי: ${VIRTUAL_CAPITAL:,}",
        "=" * 52,
        "",
        "🌍 מצב השוק הכללי:",
        market_summary,
        "" if market_ok else "  ⚠️  יום יורד בשוק — שקלי האם לסחור בכלל!",
        "",
    ]

    if econ_events:
        lines.append("📅 אירועים כלכליים השבוע:")
        for ev in econ_events[:3]:
            lines.append(f"  ⚡ {ev['time']} — {ev['title']}")
        lines.append("")

    lines += [
        "🏆 TOP 3 הזדמנויות להיום:",
        "",
    ]

    for i, s in enumerate(top3, 1):
        t   = s['technicals']
        p   = s['position']
        rec = rec_emoji(s['score'])

        # פריקמרקט
        pre = s.get('premarket')
        pre_str = f"  פריקמרקט: {pre['emoji']} {pre['signal']}\n" if pre else ""

        lines += [
            "─" * 52,
            f"  #{i}  {s['ticker']}  —  {s['name']}",
            f"  ציון: {s['score']}/100    {rec}",
            f"  מחיר: ${t['price']}    שינוי: {t['gap_pct']:+.1f}%    RSI: {t['rsi']}    נפח: ×{t['volume_ratio']}",
        ]
        if pre:
            lines.append(f"  {pre['emoji']} {pre['signal']}")
        lines.append("")

        if s['reasons']:
            lines.append("  ✅ למה כן:")
            for r in s['reasons']:
                lines.append(f"     {r}")
            lines.append("")

        if s['warnings']:
            lines.append("  ⚠️  סיכונים:")
            for w in s['warnings']:
                lines.append(f"     {w}")
            lines.append("")

        lines += [
            "  📰 חדשות אחרונות:",
            f"  {s['news']}",
            "",
        ]

        # סנטימנט StockTwits
        sent = s.get('sentiment')
        if sent:
            lines += [
                f"  💬 StockTwits: {sent['emoji']} {sent['mood']} ({sent['total']} פוסטים)",
                "",
            ]

        # Reddit r/wallstreetbets
        reddit = s.get('reddit')
        if reddit and reddit.get('mentions', 0) > 0:
            lines += [
                f"  🔴 Reddit WSB: {reddit['emoji']} {reddit['sentiment']} ({reddit['mentions']} פוסטים היום)",
                "",
            ]

        # Put/Call Ratio
        opts = s.get('options')
        if opts:
            lines += [
                f"  📊 Put/Call: {opts['ratio']} — {opts['emoji']} {opts['signal']}",
                "",
            ]

        # Short Interest
        short = s.get('short')
        if short:
            lines.append(f"  📉 Short: {short['emoji']} {short['signal']}")
            lines.append("")

        # אנליסטים
        analyst = s.get('analyst')
        if analyst and analyst.get('target_mean'):
            up = f" | יעד: ${analyst['target_mean']}" + (f" (+{analyst['upside']}%)" if analyst.get('upside') else "")
            lines.append(f"  🎯 אנליסטים: {analyst['emoji']} {analyst['recommendation']}{up}")
            lines.append("")

        # מגזר
        sector = s.get('sector')
        if sector:
            lines.append(f"  🏭 מגזר: {sector['emoji']} {sector['mood']}")
            lines.append("")

        # תמיכה/התנגדות
        sr = s.get('sr')
        if sr and (sr.get('resistances') or sr.get('supports')):
            res_str = f"התנגדות: ${sr['resistances'][0]}" if sr.get('resistances') else ""
            sup_str = f"תמיכה: ${sr['supports'][0]}" if sr.get('supports') else ""
            sep = " | " if res_str and sup_str else ""
            lines.append(f"  📏 {res_str}{sep}{sup_str}")
            lines.append("")

        if s['score'] >= 50:
            lines += [
                "  💼 תוכנית מסחר (דמו בלבד!):",
                f"     כמות:         {p['shares']} מניות",
                f"     השקעה:         ${p['investment']:,}",
                f"     יעד מחיר:     ${p['target']}  (+3%)",
                f"     סטופ לוס:     ${p['stop']}  (-1.5%)",
                f"     רווח פוטנציאלי: +${p['profit']}",
                f"     הפסד מקסימלי:  -${p['loss']}",
                "",
            ]

    # מניות שהפסידו
    rest = sorted(results, key=lambda x: x['score'], reverse=True)[3:]
    avoided = [s for s in rest if s['score'] < 50]
    if avoided:
        lines += ["─" * 52, "  ❌ לא מומלצות היום:"]
        for s in avoided:
            lines.append(f"     {s['ticker']}: ציון {s['score']}/100")
        lines.append("")

    lines += [
        "=" * 52,
        "  ⚠️  תזכורת: זה מסחר דמו בלבד!",
        "  אל תסחרי עם כסף אמיתי לפני 3 שבועות רצופים",
        "  עם תוצאות חיוביות בדמו.",
        "=" * 52,
    ]

    return "\n".join(lines)


# ==============================
# שמירה ומעקב
# ==============================
def save_report(report_text, results):
    os.makedirs("reports", exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")

    txt_path = f"reports/report_{date_str}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    top3 = sorted(results, key=lambda x: x['score'], reverse=True)[:3]
    tracking = []
    for s in top3:
        tracking.append({
            "date":            date_str,
            "ticker":          s['ticker'],
            "score":           s['score'],
            "price_at_report": s['technicals']['price'],
            "target":          s['position']['target'],
            "stop":            s['position']['stop'],
            "potential_profit":s['position']['profit'],
            "actual_result":   None   # יתמלא ע"י end_of_day_tracker.py
        })

    track_path = "reports/tracking.json"
    existing = []
    if os.path.exists(track_path):
        with open(track_path, "r") as f:
            existing = json.load(f)
    existing.extend(tracking)
    with open(track_path, "w") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    # שמירת נתונים גולמיים לממשק HTML
    latest_path = "reports/latest_results.json"
    with open(latest_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n✅ דוח נשמר ב: {txt_path}")


# ==============================
# שליחת וואטסאפ
# ==============================
def send_whatsapp(top_results):
    pass  # לא בשימוש, עברנו ל-Telegram


def send_telegram(top_results):
    """שולח הודעת Telegram עם סיכום הדוח"""
    import urllib.request, urllib.parse

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

    if not top_results:
        return

    best  = top_results[0]
    score = best['score']
    price = best['technicals']['price']
    gap   = best['technicals']['gap_pct']
    t     = best['position']['target']
    stop  = best['position']['stop']
    profit = best['position']['profit']

    emoji = "🟢" if score >= 70 else ("🟡" if score >= 50 else "🔴")

    lines = [
        f"🤖 *דוח מניות בוקר — עינב*",
        f"",
        f"{emoji} *{best['ticker']}* — ציון {score}/100",
        f"💵 מחיר: ${price}   שינוי: {gap:+.1f}%",
        f"🎯 יעד: ${t}   🛑 סטופ: ${stop}",
        f"💰 רווח פוטנציאלי: +${profit}",
    ]

    if best['reasons']:
        lines.append("")
        lines.append("✅ " + " | ".join(best['reasons'][:2]))

    if best['warnings']:
        lines.append("⚠️ " + best['warnings'][0])

    # סנטימנט StockTwits
    sent = best.get('sentiment')
    if sent:
        lines.append(f"💬 StockTwits: {sent['emoji']} {sent['mood']}")

    # Reddit
    reddit = best.get('reddit')
    if reddit and reddit.get('mentions', 0) > 0:
        lines.append(f"🔴 Reddit WSB: {reddit['emoji']} {reddit['sentiment']} ({reddit['mentions']} פוסטים)")

    # Put/Call Ratio
    opts = best.get('options')
    if opts:
        lines.append(f"📊 Put/Call: {opts['ratio']} {opts['emoji']} {opts['signal']}")

    # פריקמרקט
    pre = best.get('premarket')
    if pre:
        lines.append(f"🌅 {pre['emoji']} {pre['signal']}")

    # Short Interest
    short = best.get('short')
    if short and short.get('pct', 0) >= 10:
        lines.append(f"📉 Short: {short['emoji']} {short['signal']}")

    # אנליסטים
    analyst = best.get('analyst')
    if analyst and analyst.get('upside') and analyst['upside'] > 5:
        lines.append(f"🎯 אנליסטים: {analyst['emoji']} {analyst['recommendation']} | יעד +{analyst['upside']}%")

    # מצב שוק כללי
    try:
        from market_context import get_full_market_context
        mkt = get_full_market_context()
        if mkt.get('vix'):
            lines.append(f"😨 VIX: {mkt['vix']['level']} — {mkt['vix']['mood']}")
        if mkt.get('market'):
            lines.append(f"📊 S&P: {mkt['market']['emoji']} {mkt['market']['trend']}")
    except Exception:
        pass

    lines += ["", "_(דמו בלבד — לא כסף אמיתי)_"]

    msg = "\n".join(lines)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id":    chat_id,
        "text":       msg,
        "parse_mode": "Markdown"
    }).encode()

    try:
        urllib.request.urlopen(url, data=data, timeout=10)
        print("📱 הודעת Telegram נשלחה!")
    except Exception as e:
        print(f"(Telegram לא נשלח: {e})")


# ==============================
# התראת Mac
# ==============================
def send_mac_notification(top_results):
    """שולח התראת desktop על Mac"""
    import subprocess, platform
    if platform.system() != "Darwin":
        return

    if not top_results:
        return

    best  = top_results[0]
    score = best['score']
    ticker = best['ticker']

    if score >= 70:
        subtitle = f"🟢 {ticker} — ציון {score}/100 — כדאי לבדוק!"
    elif score >= 50:
        subtitle = f"🟡 {ticker} — ציון {score}/100 — ממתין לאישור"
    else:
        subtitle = f"🔴 אין הזדמנויות חזקות היום"

    script = f'''
    display notification "{subtitle}" ¬
        with title "🤖 דוח מניות בוקר מוכן!" ¬
        sound name "Glass"
    '''
    try:
        subprocess.run(["osascript", "-e", script], check=False)
    except Exception:
        pass  # אם ה-notification לא עובד, הכל בסדר


# ==============================
# main
# ==============================
def main():
    from datetime import datetime
    # בדיקה שהיום יום מסחר (שני-שישי)
    weekday = datetime.now().weekday()  # 0=שני, 6=ראשון
    if weekday >= 5:  # שבת (5) או ראשון (6)
        print("⛔ היום אין מסחר בארה\"ב (סוף שבוע). הסוכן ישן 😴")
        return

    print("🔍 סוכני המניות מתחילים לעבוד...\n")
    results = []
    for ticker in WATCHLIST:
        print(f"  📡 בודק {ticker}...", end=" ", flush=True)
        r = analyze_stock(ticker)
        if r:
            results.append(r)
            print(f"ציון {r['score']}/100")
        else:
            print("לא הצליח")

    if not results:
        print("\n❌ לא הצלחתי למשוך נתונים. בדקי חיבור לאינטרנט.")
        return

    top3 = sorted(results, key=lambda x: x['score'], reverse=True)[:3]
    report = generate_report(results)
    print("\n" + report)
    save_report(report, results)

    # פתיחת Dashboard בדפדפן
    try:
        from generate_html_report import save_html
        from end_of_day_tracker import load_tracking_data
        tracking = load_tracking_data()
        html_path = save_html(results, tracking)
        import subprocess
        subprocess.run(["open", html_path])
        print(f"🌐 Dashboard נפתח בדפדפן!")
    except Exception as e:
        print(f"(לא הצלחתי לפתוח dashboard: {e})")

    # שליחת Telegram + התראת Mac
    send_telegram(top3)
    send_mac_notification(top3)
    print("\n🔔 נשלחה התראה!")


if __name__ == "__main__":
    main()
