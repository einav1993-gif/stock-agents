#!/usr/bin/env python3
"""
🧠 דניאל — סוכן האינטליגנציה
==============================
הסוכן המתוחכם ביותר בצוות.
בודק: Insider Trading, Short Interest, דירוגי אנליסטים,
פריקמרקט, תמיכה/התנגדות, ניתוח מגזר ולוח כלכלי.
מעשיר את הניתוח של אורי בשכבת מידע עמוקה.

🧠 Intelligence Layer — שכבת אינטליגנציה מתקדמת
=================================================
מקורות מידע:
  • מסחר מקורבים (Insider Trading)
  • Short Interest — כמה אחוז בשורט
  • דירוגי אנליסטים + יעד מחיר
  • פריקמרקט — מה קורה לפני הפתיחה
  • תמיכה/התנגדות — רמות מחיר קריטיות
  • ניתוח מגזר — האם כל הסקטור עולה/יורד?
  • לוח כלכלי — אירועים מאקרו קריטיים השבוע
"""

import yfinance as yf
import urllib.request
import json
from datetime import datetime, timedelta

# ──────────────────────────────────────────
# מיפוי מניות ← מגזר ETF
# ──────────────────────────────────────────
SECTOR_ETFS = {
    "TSLA": ("XLY", "צרכנות שיקולית"),
    "NVDA": ("XLK", "טכנולוגיה"),
    "AMD":  ("XLK", "טכנולוגיה"),
    "AAPL": ("XLK", "טכנולוגיה"),
    "META": ("XLC", "תקשורת"),
    "AMZN": ("XLY", "צרכנות שיקולית"),
    "GOOGL":("XLC", "תקשורת"),
    "MSFT": ("XLK", "טכנולוגיה"),
    "COIN": ("XLK", "טכנולוגיה"),
    "PLTR": ("XLK", "טכנולוגיה"),
    "SOFI": ("XLF", "פיננסים"),
    "RIVN": ("XLY", "צרכנות שיקולית"),
    "MARA": ("XLK", "טכנולוגיה"),
    "SMCI": ("XLK", "טכנולוגיה"),
    "IONQ": ("XLK", "טכנולוגיה"),
}


# ══════════════════════════════════════════
# 1. מסחר מקורבים — Insider Trading
# ══════════════════════════════════════════
def get_insider_activity(ticker):
    """
    כשמנכ"ל או דירקטור קונה מניות של החברה שלו עם כסף אישי —
    זה סימן חזק מאוד שהוא מאמין בה. ולהפך — אם הוא מוכר הרבה.
    """
    try:
        stock = yf.Ticker(ticker)
        insiders = stock.insider_transactions

        if insiders is None or (hasattr(insiders, 'empty') and insiders.empty):
            return None

        # מסננים ל-90 ימים אחרונים
        cutoff = datetime.now() - timedelta(days=90)
        recent = []

        for _, row in insiders.iterrows():
            try:
                date = row.get('Start Date') or row.get('Date') or row.get('startDate')
                if date is None:
                    continue
                if hasattr(date, 'to_pydatetime'):
                    date = date.to_pydatetime()
                if hasattr(date, 'replace'):
                    date = date.replace(tzinfo=None)
                if date < cutoff:
                    continue

                shares = row.get('Shares') or row.get('shares', 0)
                value  = row.get('Value') or row.get('value', 0)
                tx_type = str(row.get('Transaction') or row.get('transaction', '')).lower()
                name   = row.get('Insider') or row.get('insider', 'מקורב')

                is_buy = any(w in tx_type for w in ['buy', 'purchase', 'acquisition'])
                is_sell = any(w in tx_type for w in ['sell', 'sale', 'disposition'])

                recent.append({
                    'date':    str(date)[:10],
                    'name':    str(name),
                    'is_buy':  is_buy,
                    'is_sell': is_sell,
                    'shares':  int(shares) if shares else 0,
                    'value':   int(value) if value else 0,
                })
            except Exception:
                continue

        if not recent:
            return None

        buys  = sum(1 for r in recent if r['is_buy'])
        sells = sum(1 for r in recent if r['is_sell'])
        total = buys + sells

        if total == 0:
            return None

        if buys > sells * 2:
            signal, emoji, score_add = "מקורבים קונים!", "🟢", +8
        elif buys > sells:
            signal, emoji, score_add = "יותר קנייה מאשר מכירה", "📈", +4
        elif sells > buys * 2:
            signal, emoji, score_add = "מקורבים מוכרים הרבה", "🔴", -6
        elif sells > buys:
            signal, emoji, score_add = "יותר מכירה מאשר קנייה", "📉", -3
        else:
            signal, emoji, score_add = "מאוזן", "⚖️", 0

        return {
            'buys':      buys,
            'sells':     sells,
            'signal':    signal,
            'emoji':     emoji,
            'score_add': score_add,
            'recent':    recent[:3],
        }

    except Exception:
        return None


# ══════════════════════════════════════════
# 2. Short Interest — כמה אחוז בשורט
# ══════════════════════════════════════════
def get_short_interest(ticker):
    """
    שורט = סוחרים שמהמרים שהמניה תרד.
    שורט גבוה + חדשות טובות = Short Squeeze = עלייה חדה מאוד!
    """
    try:
        info = yf.Ticker(ticker).info
        short_pct = info.get('shortPercentOfFloat', None)
        short_ratio = info.get('shortRatio', None)  # ימים לכסות שורט

        if short_pct is None:
            return None

        short_pct_display = round(short_pct * 100, 1) if short_pct < 1 else round(short_pct, 1)

        if short_pct_display >= 25:
            signal, emoji, score_add = f"שורט גבוה מאוד ({short_pct_display}%) — פוטנציאל squeeze!", "💥", +10
        elif short_pct_display >= 15:
            signal, emoji, score_add = f"שורט גבוה ({short_pct_display}%) — עלייה תגרום לsqueeze", "⚡", +5
        elif short_pct_display >= 8:
            signal, emoji, score_add = f"שורט בינוני ({short_pct_display}%)", "⚠️", 0
        elif short_pct_display >= 3:
            signal, emoji, score_add = f"שורט נמוך ({short_pct_display}%)", "✅", +2
        else:
            signal, emoji, score_add = f"כמעט אין שורט ({short_pct_display}%)", "✅", +3

        return {
            'pct':       short_pct_display,
            'ratio':     round(float(short_ratio), 1) if short_ratio else None,
            'signal':    signal,
            'emoji':     emoji,
            'score_add': score_add,
        }

    except Exception:
        return None


# ══════════════════════════════════════════
# 3. דירוגי אנליסטים + יעד מחיר
# ══════════════════════════════════════════
def get_analyst_data(ticker):
    """
    אנליסטים מוול סטריט עוקבים אחרי המניות ומפרסמים המלצות:
    Buy / Hold / Sell — ויעד מחיר.
    """
    try:
        stock = yf.Ticker(ticker)
        info  = stock.info

        # יעד מחיר
        target_mean = info.get('targetMeanPrice')
        target_high = info.get('targetHighPrice')
        target_low  = info.get('targetLowPrice')
        curr_price  = info.get('currentPrice') or info.get('regularMarketPrice', 0)
        num_analysts = info.get('numberOfAnalystOpinions', 0)

        # המלצה
        recommendation = info.get('recommendationKey', '')
        rec_map = {
            'strong_buy':  ('קנייה חזקה', '🟢🟢', +12),
            'buy':         ('קנייה',       '🟢',   +8),
            'hold':        ('המתנה',       '🟡',    0),
            'underperform':('ביצוע נמוך', '🔴',   -5),
            'sell':        ('מכירה',       '🔴🔴', -10),
        }

        rec_label, rec_emoji, score_add = rec_map.get(
            recommendation, ('אין המלצה', '⚪', 0)
        )

        upside = None
        if target_mean and curr_price and curr_price > 0:
            upside = round(((target_mean - curr_price) / curr_price) * 100, 1)

        return {
            'recommendation': rec_label,
            'emoji':          rec_emoji,
            'score_add':      score_add,
            'target_mean':    round(target_mean, 2) if target_mean else None,
            'target_high':    round(target_high, 2) if target_high else None,
            'target_low':     round(target_low, 2) if target_low else None,
            'upside':         upside,
            'num_analysts':   num_analysts,
        }

    except Exception:
        return None


# ══════════════════════════════════════════
# 4. פריקמרקט — מה קורה לפני הפתיחה
# ══════════════════════════════════════════
def get_premarket_data(ticker):
    """
    פריקמרקט = מסחר שמתחיל ב-4:00 בוקר שעון ניו יורק (11:00 ישראל).
    עוזר לדעת לאן המניה הולכת עוד לפני הפתיחה הרשמית.
    """
    try:
        stock = yf.Ticker(ticker)
        # מנסים לקבל נתוני premarket
        info = stock.info
        pre_price  = info.get('preMarketPrice')
        pre_change = info.get('preMarketChangePercent')
        reg_price  = info.get('regularMarketPrice') or info.get('currentPrice')

        if not pre_price or not reg_price:
            return None

        change_pct = round(float(pre_change) * 100, 2) if pre_change else \
                     round(((pre_price - reg_price) / reg_price) * 100, 2)

        if change_pct >= 3:
            signal, emoji = f"עולה חזק בפריקמרקט {change_pct:+.1f}%", "🚀"
        elif change_pct >= 1:
            signal, emoji = f"עולה בפריקמרקט {change_pct:+.1f}%", "📈"
        elif change_pct > -1:
            signal, emoji = f"יציב בפריקמרקט {change_pct:+.1f}%", "➡️"
        elif change_pct > -3:
            signal, emoji = f"יורד בפריקמרקט {change_pct:+.1f}%", "📉"
        else:
            signal, emoji = f"יורד חזק בפריקמרקט {change_pct:+.1f}%", "🔻"

        return {
            'price':      round(float(pre_price), 2),
            'change_pct': change_pct,
            'signal':     signal,
            'emoji':      emoji,
        }

    except Exception:
        return None


# ══════════════════════════════════════════
# 5. תמיכה והתנגדות — רמות מחיר קריטיות
# ══════════════════════════════════════════
def get_support_resistance(df_daily):
    """
    רמות תמיכה = מחירים שהמניה קפצה מהם כלפי מעלה בעבר.
    רמות התנגדות = מחירים שהמניה נתקעה בהם ולא הצליחה לפרוץ.
    חשוב לדעת: אם המניה מעל תמיכה — טוב. אם קרובה להתנגדות — זהירות.
    """
    try:
        if df_daily is None or len(df_daily) < 20:
            return None

        closes = df_daily['Close'].values
        highs  = df_daily['High'].values
        lows   = df_daily['Low'].values
        curr   = float(closes[-1])

        # מצא שיאים מקומיים (התנגדויות)
        resistances = []
        supports    = []

        window = 5
        for i in range(window, len(highs) - window):
            if highs[i] == max(highs[i-window:i+window+1]):
                resistances.append(float(highs[i]))
            if lows[i] == min(lows[i-window:i+window+1]):
                supports.append(float(lows[i]))

        # קיבוץ רמות קרובות (±1.5%)
        def cluster(levels, threshold=0.015):
            if not levels:
                return []
            levels = sorted(set(levels))
            clustered = [levels[0]]
            for lvl in levels[1:]:
                if abs(lvl - clustered[-1]) / clustered[-1] > threshold:
                    clustered.append(lvl)
            return clustered

        resistances = cluster(resistances)
        supports    = cluster(supports)

        # מסנן: התנגדויות מעל המחיר הנוכחי, תמיכות מתחתיו
        near_res = [r for r in resistances if r > curr * 1.005][:2]
        near_sup = [s for s in supports    if s < curr * 0.995][::-1][:2]

        if not near_res and not near_sup:
            return None

        # מרחק מהתנגדות הקרובה
        dist_to_res = round(((near_res[0] - curr) / curr) * 100, 1) if near_res else None
        dist_to_sup = round(((curr - near_sup[0]) / curr) * 100, 1) if near_sup else None

        return {
            'current':      round(curr, 2),
            'resistances':  [round(r, 2) for r in near_res],
            'supports':     [round(s, 2) for s in near_sup],
            'dist_to_res':  dist_to_res,
            'dist_to_sup':  dist_to_sup,
        }

    except Exception:
        return None


# ══════════════════════════════════════════
# 6. ניתוח מגזר
# ══════════════════════════════════════════
def get_sector_trend(ticker):
    """
    כשכל מגזר הטכנולוגיה עולה — קל יותר לנצח.
    אם המגזר יורד אבל המניה עולה — זה סימן חזק מאוד.
    """
    try:
        etf_info = SECTOR_ETFS.get(ticker)
        if not etf_info:
            return None

        etf_symbol, sector_name = etf_info
        etf = yf.Ticker(etf_symbol)
        hist = etf.history(period="3d")

        if len(hist) < 2:
            return None

        today_close = float(hist.iloc[-1]['Close'])
        prev_close  = float(hist.iloc[-2]['Close'])
        change_pct  = round(((today_close - prev_close) / prev_close) * 100, 2)

        if change_pct >= 1:
            mood, emoji = f"מגזר {sector_name} עולה {change_pct:+.1f}%", "🟢"
        elif change_pct >= 0.2:
            mood, emoji = f"מגזר {sector_name} עולה מעט {change_pct:+.1f}%", "📈"
        elif change_pct > -0.2:
            mood, emoji = f"מגזר {sector_name} יציב", "➡️"
        elif change_pct > -1:
            mood, emoji = f"מגזר {sector_name} יורד מעט {change_pct:+.1f}%", "📉"
        else:
            mood, emoji = f"מגזר {sector_name} יורד {change_pct:+.1f}%", "🔻"

        return {
            'etf':         etf_symbol,
            'sector':      sector_name,
            'change_pct':  change_pct,
            'mood':        mood,
            'emoji':       emoji,
            'favorable':   change_pct > -0.5,
        }

    except Exception:
        return None


# ══════════════════════════════════════════
# 7. לוח כלכלי — אירועים מאקרו השבוע
# ══════════════════════════════════════════
def get_economic_calendar():
    """
    אירועים כלכליים גדולים כמו ישיבת הפד, נתוני אינפלציה, תעסוקה —
    יכולים לזעזע את כל השוק ביום שהם יוצאים. חשוב לדעת מראש!
    """
    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        req = urllib.request.Request(
            url, headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            events = json.loads(resp.read())

        # מסנן: רק אירועים של ארה"ב, השפעה גבוהה, מהיום ומהלאה
        today = datetime.now().strftime("%Y-%m-%d")
        high_impact = []

        for ev in events:
            country = str(ev.get('country', '')).upper()
            impact  = str(ev.get('impact', '')).lower()
            date    = str(ev.get('date', ''))[:10]
            title   = ev.get('title', '')

            if country != 'USD':
                continue
            if impact != 'high':
                continue
            if date < today:
                continue

            time_str = str(ev.get('date', ''))
            try:
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                # ממיר ל-Israel time (UTC+3)
                from datetime import timezone
                israel_dt = dt.astimezone(timezone(timedelta(hours=3)))
                display_time = israel_dt.strftime("%a %d/%m %H:%M")
            except Exception:
                display_time = date

            high_impact.append({
                'title':   title,
                'date':    date,
                'time':    display_time,
                'forecast': ev.get('forecast', ''),
                'previous': ev.get('previous', ''),
            })

        return high_impact[:5]  # עד 5 אירועים קרובים

    except Exception:
        return []


# ══════════════════════════════════════════
# 8. ניתוח היסטורי — ביצועים לאורך זמן
# ══════════════════════════════════════════
def get_historical_analysis(ticker, df_daily=None):
    """
    מנתח את ההיסטוריה של המניה: שנה שלמה אחורה.
    מחשב: טווח 52 שבועות, ATR (תנועה יומית ממוצעת),
    אחוז ניצחון היסטורי, ביצועים אחרי ימי עלייה חזקים.
    """
    try:
        stock = yf.Ticker(ticker)

        # שנה שלמה אחורה
        if df_daily is None or len(df_daily) < 50:
            df_daily = stock.history(period="1y")

        if df_daily is None or len(df_daily) < 20:
            return None

        closes = df_daily['Close']
        highs  = df_daily['High']
        lows   = df_daily['Low']
        curr   = float(closes.iloc[-1])

        # ── 52 שבועות גבוה / נמוך ──
        high_52w = float(highs.max())
        low_52w  = float(lows.min())
        pct_from_high = round(((curr - high_52w) / high_52w) * 100, 1)  # שלילי = מתחת לשיא
        pct_from_low  = round(((curr - low_52w)  / low_52w)  * 100, 1)  # חיובי = מעל לשפל

        # מיקום בתוך טווח 52 שבועות (0% = שפל, 100% = שיא)
        if high_52w != low_52w:
            position_in_range = round(((curr - low_52w) / (high_52w - low_52w)) * 100, 0)
        else:
            position_in_range = 50

        # ── ATR — תנועה יומית ממוצעת (Average True Range) ──
        # כמה דולר זזה המניה ביום ממוצע
        tr_list = []
        for i in range(1, len(df_daily)):
            h = float(highs.iloc[i])
            l = float(lows.iloc[i])
            pc = float(closes.iloc[i-1])
            tr = max(h - l, abs(h - pc), abs(l - pc))
            tr_list.append(tr)

        atr_14 = round(sum(tr_list[-14:]) / 14, 2) if len(tr_list) >= 14 else None
        atr_pct = round((atr_14 / curr) * 100, 2) if atr_14 and curr else None

        # ── אחוז ימי עלייה — 30 ימים אחרונים ──
        last_30 = closes.tail(31)
        daily_returns_30 = last_30.pct_change().dropna()
        win_rate_30d = round((daily_returns_30 > 0).mean() * 100, 1)
        avg_return_30d = round(daily_returns_30.mean() * 100, 2)
        best_day_30d  = round(daily_returns_30.max() * 100, 1)
        worst_day_30d = round(daily_returns_30.min() * 100, 1)

        # ── מחזוריות — ממוצע יום שני/שלישי וכו' ──
        df_copy = df_daily.copy()
        df_copy['return'] = df_copy['Close'].pct_change()
        df_copy['weekday'] = df_copy.index.dayofweek  # 0=Mon, 4=Fri
        weekday_avg = df_copy.groupby('weekday')['return'].mean() * 100
        days_he = {0: 'שני', 1: 'שלישי', 2: 'רביעי', 3: 'חמישי', 4: 'שישי'}
        best_weekday = days_he.get(int(weekday_avg.idxmax()), '?')
        worst_weekday = days_he.get(int(weekday_avg.idxmin()), '?')

        # ── ביצועים אחרי ימים עם נפח גבוה ──
        if 'Volume' in df_daily.columns:
            avg_vol = df_daily['Volume'].mean()
            high_vol_days = df_daily[df_daily['Volume'] > avg_vol * 1.5]
            if len(high_vol_days) > 5:
                # מה קרה יום אחרי נפח גבוה?
                high_vol_indices = df_daily.index.get_indexer(high_vol_days.index)
                next_day_returns = []
                for idx in high_vol_indices:
                    if idx + 1 < len(df_daily):
                        next_ret = float(closes.iloc[idx+1]) / float(closes.iloc[idx]) - 1
                        next_day_returns.append(next_ret * 100)
                after_volume_win_rate = round(
                    sum(1 for r in next_day_returns if r > 0) / len(next_day_returns) * 100, 1
                ) if next_day_returns else None
            else:
                after_volume_win_rate = None
        else:
            after_volume_win_rate = None

        # ── מגמה: 3 חודשים vs 1 חודש ──
        if len(closes) >= 63:
            ret_3m = round(((curr - float(closes.iloc[-63])) / float(closes.iloc[-63])) * 100, 1)
        else:
            ret_3m = None
        if len(closes) >= 21:
            ret_1m = round(((curr - float(closes.iloc[-21])) / float(closes.iloc[-21])) * 100, 1)
        else:
            ret_1m = None
        if len(closes) >= 5:
            ret_1w = round(((curr - float(closes.iloc[-5])) / float(closes.iloc[-5])) * 100, 1)
        else:
            ret_1w = None

        # ── סיגנל כולל מהניתוח ההיסטורי ──
        score_add = 0
        signals   = []
        warnings  = []

        # קרוב לשיא 52 שבועות — חיובי (מומנטום)
        if pct_from_high >= -5:
            score_add += 5
            signals.append(f"קרוב לשיא 52 שבועות ({pct_from_high:.1f}% מהשיא)")
        elif pct_from_high <= -30:
            score_add -= 3
            warnings.append(f"רחוק מהשיא השנתי ({pct_from_high:.1f}%)")

        # מיקום בטווח: מניה בתחתית הטווח — פוטנציאל rebound
        if position_in_range <= 20:
            score_add += 4
            signals.append(f"מניה בתחתית הטווח השנתי ({position_in_range:.0f}%) — פוטנציאל rebound")
        elif position_in_range >= 80:
            score_add += 3
            signals.append(f"מניה בחלק העליון של הטווח ({position_in_range:.0f}%) — מומנטום חזק")

        # win rate 30 יום
        if win_rate_30d >= 60:
            score_add += 4
            signals.append(f"אחוז ניצחון 30 יום: {win_rate_30d}% (חזק!)")
        elif win_rate_30d <= 35:
            score_add -= 3
            warnings.append(f"אחוז ניצחון 30 יום נמוך: {win_rate_30d}%")

        # מגמה חיובית
        if ret_1m and ret_1m > 5:
            score_add += 3
            signals.append(f"מגמה חיובית: +{ret_1m}% בחודש האחרון")
        elif ret_1m and ret_1m < -10:
            score_add -= 4
            warnings.append(f"מגמה שלילית: {ret_1m}% בחודש האחרון")

        return {
            # טווח 52 שבועות
            'high_52w':          round(high_52w, 2),
            'low_52w':           round(low_52w, 2),
            'pct_from_high':     pct_from_high,
            'pct_from_low':      pct_from_low,
            'position_in_range': int(position_in_range),

            # ATR
            'atr_14':   atr_14,
            'atr_pct':  atr_pct,

            # ביצועים 30 יום
            'win_rate_30d':   win_rate_30d,
            'avg_return_30d': avg_return_30d,
            'best_day_30d':   best_day_30d,
            'worst_day_30d':  worst_day_30d,

            # מגמות
            'ret_1w':  ret_1w,
            'ret_1m':  ret_1m,
            'ret_3m':  ret_3m,

            # מחזוריות
            'best_weekday':  best_weekday,
            'worst_weekday': worst_weekday,

            # נפח
            'after_volume_win_rate': after_volume_win_rate,

            # ציון
            'score_add': score_add,
            'signals':   signals,
            'warnings':  warnings,
        }

    except Exception as e:
        return None


# ══════════════════════════════════════════
# פונקציית ראשית — כל הניתוח יחד
# ══════════════════════════════════════════
def get_full_intelligence(ticker, df_daily=None):
    """מחזיר את כל שכבת האינטליגנציה עבור מניה"""
    return {
        'insider':   get_insider_activity(ticker),
        'short':     get_short_interest(ticker),
        'analyst':   get_analyst_data(ticker),
        'premarket': get_premarket_data(ticker),
        'sr':        get_support_resistance(df_daily) if df_daily is not None else None,
        'sector':    get_sector_trend(ticker),
        'historical': get_historical_analysis(ticker, df_daily),
    }


def calc_intelligence_score(intel):
    """
    מחשב השפעת שכבת האינטליגנציה על הציון הכולל.
    מחזיר: (score_delta, extra_reasons, extra_warnings)
    """
    delta    = 0
    reasons  = []
    warnings = []

    # Insider
    ins = intel.get('insider')
    if ins:
        delta += ins['score_add']
        if ins['score_add'] > 0:
            reasons.append(f"מסחר מקורבים: {ins['emoji']} {ins['signal']} (קניות: {ins['buys']}, מכירות: {ins['sells']})")
        elif ins['score_add'] < 0:
            warnings.append(f"מסחר מקורבים: {ins['emoji']} {ins['signal']}")

    # Short Interest
    short = intel.get('short')
    if short:
        delta += short['score_add']
        if short['score_add'] >= 5:
            reasons.append(f"Short Interest: {short['emoji']} {short['signal']}")
        elif short['score_add'] < 0:
            warnings.append(f"Short Interest: {short['emoji']} {short['signal']}")

    # Analyst
    analyst = intel.get('analyst')
    if analyst:
        delta += analyst['score_add']
        if analyst['score_add'] > 0:
            up_str = f" | פוטנציאל עלייה: +{analyst['upside']}%" if analyst.get('upside') and analyst['upside'] > 0 else ""
            reasons.append(f"אנליסטים: {analyst['emoji']} {analyst['recommendation']}{up_str} ({analyst['num_analysts']} אנליסטים)")
        elif analyst['score_add'] < 0:
            warnings.append(f"אנליסטים: {analyst['emoji']} {analyst['recommendation']}")

    # Sector
    sector = intel.get('sector')
    if sector:
        if not sector['favorable']:
            warnings.append(f"מגזר: {sector['emoji']} {sector['mood']}")
        elif sector['change_pct'] >= 1:
            reasons.append(f"מגזר: {sector['emoji']} {sector['mood']}")

    # Support/Resistance
    sr = intel.get('sr')
    if sr:
        if sr.get('dist_to_res') and sr['dist_to_res'] <= 2:
            warnings.append(f"📏 קרוב להתנגדות: ${sr['resistances'][0]} (מרחק {sr['dist_to_res']}%)")
        elif sr.get('dist_to_sup') and sr['dist_to_sup'] <= 1.5:
            reasons.append(f"📏 קרוב לתמיכה חזקה: ${sr['supports'][0]}")

    # Historical analysis
    hist = intel.get('historical')
    if hist:
        delta += hist.get('score_add', 0)
        for s in hist.get('signals', []):
            reasons.append(f"📊 {s}")
        for w in hist.get('warnings', []):
            warnings.append(f"📊 {w}")

    return delta, reasons, warnings
