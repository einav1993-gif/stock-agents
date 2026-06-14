#!/usr/bin/env python3
"""
🌍 מיכל — סוכנת ההקשר
=======================
אחראית על התמונה הגדולה:
VIX, S&P500, ריבית, earnings, StockTwits,
Reddit, חדשות אמיתיות ואופציות Put/Call.
מזינה את המידע שלה לאורי לפני כל ניתוח.
"""

import yfinance as yf
import urllib.request
import json
from datetime import datetime, timedelta


# ==============================
# VIX — מדד הפחד בשוק
# ==============================
def get_vix():
    """
    VIX = מדד שמראה כמה הסוחרים בשוק 'מפוחדים'.
    מתחת ל-15 = שקט. מעל 30 = פאניקה.
    """
    try:
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="2d")
        if hist.empty:
            return None
        level = round(float(hist.iloc[-1]['Close']), 2)

        if level < 15:
            mood, risk, emoji = "שוק רגוע ושקט", "נמוך", "😌"
        elif level < 20:
            mood, risk, emoji = "שוק מתון", "בינוני-נמוך", "🙂"
        elif level < 25:
            mood, risk, emoji = "יש קצת חרדה בשוק", "בינוני", "😐"
        elif level < 35:
            mood, risk, emoji = "שוק חרד — זהירות", "גבוה", "😰"
        else:
            mood, risk, emoji = "פאניקה! סוחרים מפחדים מאוד", "מאוד גבוה", "😱"

        return {'level': level, 'mood': mood, 'risk': risk, 'emoji': emoji}
    except Exception:
        return None


# ==============================
# S&P 500 — מגמת השוק הכללית
# ==============================
def get_market_trend():
    """
    בודק האם השוק הכללי עולה או יורד היום.
    חשוב: אם השוק יורד — קשה יותר להרוויח על מניות בודדות.
    """
    try:
        spy = yf.Ticker("^GSPC")
        hist = spy.history(period="3d")
        if len(hist) < 2:
            return None

        today     = float(hist.iloc[-1]['Close'])
        yesterday = float(hist.iloc[-2]['Close'])
        change    = round(((today - yesterday) / yesterday) * 100, 2)

        if change > 1:
            trend, emoji = f"עולה חזק {change:+.1f}%", "🚀"
        elif change > 0.3:
            trend, emoji = f"עולה {change:+.1f}%", "📈"
        elif change > -0.3:
            trend, emoji = f"יציב {change:+.1f}%", "➡️"
        elif change > -1:
            trend, emoji = f"יורד {change:+.1f}%", "📉"
        else:
            trend, emoji = f"יורד חזק {change:+.1f}%", "🔻"

        return {
            'change': change,
            'trend':  trend,
            'emoji':  emoji,
            'price':  round(today, 2),
            'favorable': change > -0.5  # האם השוק מאפשר מסחר
        }
    except Exception:
        return None


# ==============================
# ריבית ואג"ח — מאקרו
# ==============================
def get_macro():
    """
    תשואת אג"ח 10 שנים = מדד ריבית מרכזי.
    כשהיא גבוהה — מניות טכנולוגיה סובלות יותר.
    """
    try:
        tnx = yf.Ticker("^TNX")  # תשואת אג"ח 10 שנים
        hist = tnx.history(period="2d")
        if hist.empty:
            return None

        rate = round(float(hist.iloc[-1]['Close']), 2)

        if rate > 5:
            note = "ריבית גבוהה מאוד — מניות צמיחה בלחץ"
        elif rate > 4:
            note = "ריבית גבוהה — שוק זהיר"
        elif rate > 3:
            note = "ריבית מתונה"
        else:
            note = "ריבית נמוכה — טובה למניות"

        return {'rate': rate, 'note': note}
    except Exception:
        return None


# ==============================
# Earnings — דוחות רבעוניים
# ==============================
def get_earnings_warning(ticker):
    """
    דוח רבעוני = חברה מפרסמת תוצאות כספיות.
    בדרך כלל גורם לתנודתיות גדולה — סיכון גבוה יותר.
    """
    try:
        stock = yf.Ticker(ticker)
        cal   = stock.calendar

        if cal is None:
            return None

        # יש שתי צורות שונות שמחזיר yfinance
        if hasattr(cal, 'empty') and cal.empty:
            return None

        earnings_date = None

        # dict format
        if isinstance(cal, dict):
            ed = cal.get('Earnings Date')
            if ed and len(ed) > 0:
                earnings_date = ed[0]

        # DataFrame format
        elif hasattr(cal, 'loc'):
            try:
                ed = cal.loc['Earnings Date']
                if hasattr(ed, '__iter__'):
                    earnings_date = list(ed)[0]
                else:
                    earnings_date = ed
            except Exception:
                pass

        if earnings_date is None:
            return None

        if hasattr(earnings_date, 'date'):
            earnings_date = earnings_date.date()
        elif hasattr(earnings_date, 'to_pydatetime'):
            earnings_date = earnings_date.to_pydatetime().date()

        days = (earnings_date - datetime.now().date()).days

        if 0 <= days <= 3:
            return f"🚨 דוח רבעוני בעוד {days} ימים ({earnings_date}) — סיכון גבוה מאוד!"
        elif 4 <= days <= 7:
            return f"⚠️ דוח רבעוני בעוד {days} ימים ({earnings_date})"
        elif days < 0 and days >= -2:
            return f"📋 דוח רבעוני היה לפני {abs(days)} ימים"

        return None

    except Exception:
        return None


# ==============================
# StockTwits — סנטימנט ברשת
# ==============================
def get_stocktwits_sentiment(ticker):
    """
    StockTwits = רשת חברתית של סוחרים.
    בודק כמה אחוז חיוביים (שוריים) vs שליליים (דוביים).
    """
    try:
        url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())

        messages = data.get('messages', [])
        if not messages:
            return None

        bullish = sum(1 for m in messages
                     if m.get('entities', {}).get('sentiment') and
                     m['entities']['sentiment'].get('basic') == 'Bullish')
        bearish = sum(1 for m in messages
                     if m.get('entities', {}).get('sentiment') and
                     m['entities']['sentiment'].get('basic') == 'Bearish')
        total = bullish + bearish

        if total < 5:
            return None

        bull_pct = round(bullish / total * 100)

        if bull_pct >= 70:
            mood, emoji = f"חיובי מאוד ({bull_pct}% שוריים)", "🐂🐂"
        elif bull_pct >= 55:
            mood, emoji = f"חיובי ({bull_pct}% שוריים)", "🐂"
        elif bull_pct >= 45:
            mood, emoji = f"מאוזן", "⚖️"
        elif bull_pct >= 30:
            mood, emoji = f"שלילי ({100-bull_pct}% דוביים)", "🐻"
        else:
            mood, emoji = f"שלילי מאוד ({100-bull_pct}% דוביים)", "🐻🐻"

        return {'bull_pct': bull_pct, 'mood': mood, 'emoji': emoji, 'total': total}

    except Exception:
        return None


# ==============================
# חדשות אמיתיות — Yahoo Finance News
# ==============================
def get_real_news(ticker):
    """חדשות אמיתיות ועדכניות — ממש מה שפורסם היום"""
    try:
        stock = yf.Ticker(ticker)
        news  = stock.news
        if not news:
            return []
        now    = datetime.now().timestamp()
        result = []
        for item in news[:5]:
            pub_time  = item.get('providerPublishTime', 0)
            hours_ago = (now - pub_time) / 3600
            if hours_ago < 1:
                time_str = "לפני פחות משעה 🔥"
            elif hours_ago < 24:
                time_str = f"לפני {int(hours_ago)} שעות"
            elif hours_ago < 48:
                time_str = "אתמול"
            else:
                time_str = f"לפני {int(hours_ago / 24)} ימים"
            result.append({
                'title':     item.get('title', ''),
                'publisher': item.get('publisher', ''),
                'time_str':  time_str,
                'hours_ago': round(hours_ago, 1),
                'link':      item.get('link', '')
            })
        return result
    except Exception:
        return []


# ==============================
# Reddit r/wallstreetbets — סנטימנט הקהילה
# ==============================
def get_reddit_sentiment(ticker):
    """מחפש אזכורים ב-r/wallstreetbets — הקהילה הכי גדולה של סוחרים"""
    try:
        url = (f"https://www.reddit.com/r/wallstreetbets/search.json"
               f"?q={ticker}&sort=new&limit=25&t=day")
        req = urllib.request.Request(
            url, headers={'User-Agent': 'StockBot/1.0 (personal use)'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        posts = data.get('data', {}).get('children', [])
        if not posts:
            return {'mentions': 0, 'sentiment': 'אין אזכורים היום', 'emoji': '😶', 'posts': []}

        bullish_words = ['buy', 'bull', 'calls', 'moon', '🚀', 'long', 'bullish',
                         'squeeze', 'rocket', 'rally', 'yolo', 'pump']
        bearish_words = ['sell', 'bear', 'puts', 'short', 'bearish', 'dump',
                         'crash', 'drop', 'dead', 'overvalued']

        bullish_count = 0
        bearish_count = 0
        sample_posts  = []

        for post in posts:
            d    = post.get('data', {})
            text = (d.get('title', '') + ' ' + d.get('selftext', '')).lower()
            if any(w in text for w in bullish_words):
                bullish_count += 1
            if any(w in text for w in bearish_words):
                bearish_count += 1
            if len(sample_posts) < 3 and d.get('title'):
                sample_posts.append({'title': d['title'][:90], 'score': d.get('score', 0)})

        total = bullish_count + bearish_count
        if total == 0:
            mood, emoji, bull_pct = "ניטרלי", "⚖️", 50
        else:
            bull_pct = round(bullish_count / total * 100)
            if bull_pct >= 70:   mood, emoji = f"חיובי מאוד ({bull_pct}% שוריים)", "🚀🚀"
            elif bull_pct >= 55: mood, emoji = f"חיובי ({bull_pct}% שוריים)", "🚀"
            elif bull_pct >= 45: mood, emoji = "מאוזן", "⚖️"
            elif bull_pct >= 30: mood, emoji = f"שלילי ({100-bull_pct}% דוביים)", "🐻"
            else:                mood, emoji = f"שלילי מאוד ({100-bull_pct}% דוביים)", "🐻🐻"

        return {'mentions': len(posts), 'bull_pct': bull_pct,
                'sentiment': mood, 'emoji': emoji, 'posts': sample_posts}
    except Exception:
        return None


# ==============================
# אופציות — יחס Put/Call
# ==============================
def get_options_data(ticker):
    """
    Put/Call Ratio — כלי חזק מאוד!
    Calls = הימור שהמניה תעלה | Puts = הימור שתרד
    יחס < 0.7 = שוק שורי | יחס > 1.3 = שוק דובי
    """
    try:
        stock       = yf.Ticker(ticker)
        expirations = stock.options
        if not expirations:
            return None

        calls_oi = 0
        puts_oi  = 0
        for exp in expirations[:3]:
            try:
                chain     = stock.option_chain(exp)
                calls_oi += chain.calls['openInterest'].fillna(0).sum()
                puts_oi  += chain.puts['openInterest'].fillna(0).sum()
            except Exception:
                continue

        if calls_oi == 0:
            return None

        ratio = round(puts_oi / calls_oi, 2)

        if ratio < 0.5:    signal, emoji, score_add = "שוריים מאוד — הרבה Calls", "🐂🐂", +10
        elif ratio < 0.7:  signal, emoji, score_add = "נוטה לשוריות", "🐂", +5
        elif ratio < 1.0:  signal, emoji, score_add = "מעט שורי", "📈", +3
        elif ratio < 1.3:  signal, emoji, score_add = "מאוזן", "⚖️", 0
        elif ratio < 2.0:  signal, emoji, score_add = "נוטה לדוביות — זהירות", "🐻", -5
        else:              signal, emoji, score_add = "דוביים מאוד — הרבה Puts", "🐻🐻", -10

        return {
            'ratio': ratio, 'signal': signal, 'emoji': emoji,
            'score_add': score_add,
            'calls_oi': int(calls_oi), 'puts_oi': int(puts_oi),
            'expiration': expirations[0]
        }
    except Exception:
        return None


# ==============================
# סיכום שוק מלא
# ==============================
def get_full_market_context():
    """מחזיר תמונה מלאה של מצב השוק הכללי"""
    return {
        'vix':    get_vix(),
        'market': get_market_trend(),
        'macro':  get_macro(),
    }


def get_stock_context(ticker):
    """מחזיר הקשר ספציפי למניה — כולל חדשות, Reddit ואופציות"""
    return {
        'earnings':  get_earnings_warning(ticker),
        'sentiment': get_stocktwits_sentiment(ticker),
        'news':      get_real_news(ticker),
        'reddit':    get_reddit_sentiment(ticker),
        'options':   get_options_data(ticker),
    }


def format_market_summary(ctx):
    """מייצר סיכום טקסטואלי של מצב השוק לדוח"""
    lines = []

    vix = ctx.get('vix')
    if vix:
        lines.append(f"  מדד פחד VIX: {vix['level']} — {vix['emoji']} {vix['mood']}")

    market = ctx.get('market')
    if market:
        lines.append(f"  S&P 500: {market['emoji']} {market['trend']}")
        if not market['favorable']:
            lines.append(f"  ⚠️  השוק יורד היום — שקלי כניסה בזהירות!")

    macro = ctx.get('macro')
    if macro:
        lines.append(f"  ריבית אג\"ח 10Y: {macro['rate']}% — {macro['note']}")

    return "\n".join(lines) if lines else "  נתוני מאקרו לא זמינים"
