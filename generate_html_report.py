#!/usr/bin/env python3
"""
📊 רון — סוכן הדשבורד
======================
הצייר של הצוות.
לוקח את כל הנתונים מאורי ויוצר דף HTML
ויזואלי ויפה שאפשר לפתוח בדפדפן.
"""
import json, os
from datetime import datetime

def load_tracking():
    path = "reports/tracking.json"
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_latest_results():
    path = "reports/latest_results.json"
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def score_color(score):
    if score >= 70: return "#00d4aa"
    if score >= 50: return "#f5a623"
    return "#ff4d6d"

def score_label(score):
    if score >= 70: return "כדאי לבדוק! 🟢"
    if score >= 50: return "ממתין לאישור 🟡"
    return "לא מומלץ היום 🔴"

def _build_news_section(s):
    articles = s.get('news_articles', [])
    if not articles:
        # fallback לטקסט הישן
        return f"""
      <div class="news-section">
        <div class="news-title">📰 חדשות</div>
        <div class="news-text">{s.get('news', 'לא נמצאו חדשות')}</div>
      </div>"""
    items_html = ""
    for a in articles[:4]:
        title     = a.get('title', '')
        publisher = a.get('publisher', '')
        time_str  = a.get('time_str', '')
        link      = a.get('link', '#')
        if not title:
            continue
        items_html += f"""
        <a class="news-item" href="{link}" target="_blank" rel="noopener">
          <span class="news-meta">{publisher} · {time_str}</span>
          <span class="news-headline">{title}</span>
        </a>"""
    return f"""
      <div class="news-section">
        <div class="news-title">📰 חדשות אחרונות</div>
        {items_html if items_html else '<div class="news-text">לא נמצאו חדשות</div>'}
      </div>"""


def _build_reddit_section(s):
    reddit = s.get('reddit')
    if not reddit or reddit.get('mentions', 0) == 0:
        return ""
    posts_html = ""
    for p in reddit.get('posts', [])[:2]:
        posts_html += f'<div class="reddit-post">▸ {p["title"]} <span class="reddit-score">↑{p["score"]}</span></div>'
    bull_pct = reddit.get('bull_pct', 50)
    bear_pct = 100 - bull_pct
    return f"""
      <div class="reddit-section">
        <div class="reddit-title">🔴 Reddit r/wallstreetbets — {reddit['mentions']} פוסטים היום</div>
        <div class="sentiment-bar">
          <div class="bar-bull" style="width:{bull_pct}%">{bull_pct}% 🐂</div>
          <div class="bar-bear" style="width:{bear_pct}%">{bear_pct}% 🐻</div>
        </div>
        <div class="reddit-mood">{reddit['emoji']} {reddit['sentiment']}</div>
        {posts_html}
      </div>"""


def _build_options_section(s):
    opts = s.get('options')
    if not opts:
        return ""
    ratio     = opts['ratio']
    calls_oi  = opts['calls_oi']
    puts_oi   = opts['puts_oi']
    signal    = opts['signal']
    emoji     = opts['emoji']
    total     = calls_oi + puts_oi or 1
    calls_pct = round(calls_oi / total * 100)
    puts_pct  = 100 - calls_pct
    color     = "#00d4aa" if ratio < 1.0 else ("#f5a623" if ratio < 1.3 else "#ff4d6d")
    return f"""
      <div class="options-section">
        <div class="options-title">📊 Put/Call Ratio: <span style="color:{color}">{ratio}</span> — {emoji} {signal}</div>
        <div class="options-bar">
          <div class="bar-calls" style="width:{calls_pct}%">Calls {calls_pct}%</div>
          <div class="bar-puts" style="width:{puts_pct}%">Puts {puts_pct}%</div>
        </div>
        <div class="options-note">Open Interest: Calls {calls_oi:,} | Puts {puts_oi:,}</div>
      </div>"""


def _build_historical_section(s):
    hist = s.get('historical')
    if not hist:
        return ""

    # פס טווח שנתי
    pos  = hist.get('position_in_range', 50)
    h52  = hist.get('high_52w', '?')
    l52  = hist.get('low_52w', '?')
    pct_high = hist.get('pct_from_high', 0)
    win  = hist.get('win_rate_30d', '?')
    atr  = hist.get('atr_pct', '?')
    r1w  = hist.get('ret_1w')
    r1m  = hist.get('ret_1m')
    r3m  = hist.get('ret_3m')
    bwd  = hist.get('best_weekday', '?')

    def color_ret(v):
        if v is None: return '#94a3b8', '—'
        c = '#00d4aa' if v >= 0 else '#ff4d6d'
        sign = '+' if v >= 0 else ''
        return c, f"{sign}{v}%"

    c1w, s1w = color_ret(r1w)
    c1m, s1m = color_ret(r1m)
    c3m, s3m = color_ret(r3m)

    bar_color = "#00d4aa" if pos >= 50 else "#f5a623"

    return f"""
      <div class="historical-section">
        <div class="hist-title">📅 ניתוח היסטורי (שנה אחורה)</div>

        <div class="year-range-bar">
          <span class="range-label">${l52}</span>
          <div class="range-track">
            <div class="range-fill" style="width:{pos}%; background:{bar_color}"></div>
            <div class="range-marker" style="left:{pos}%"></div>
          </div>
          <span class="range-label">${h52}</span>
        </div>
        <div class="range-pos-text">מיקום בטווח השנתי: {pos}% | {pct_high:+.1f}% מהשיא</div>

        <div class="hist-stats">
          <div class="hist-stat">
            <span class="hs-label">שבוע</span>
            <span class="hs-val" style="color:{c1w}">{s1w}</span>
          </div>
          <div class="hist-stat">
            <span class="hs-label">חודש</span>
            <span class="hs-val" style="color:{c1m}">{s1m}</span>
          </div>
          <div class="hist-stat">
            <span class="hs-label">3 חודשים</span>
            <span class="hs-val" style="color:{c3m}">{s3m}</span>
          </div>
          <div class="hist-stat">
            <span class="hs-label">ניצחון 30י</span>
            <span class="hs-val" style="color:{'#00d4aa' if isinstance(win,float) and win>=55 else '#f5a623'}">{win}%</span>
          </div>
          <div class="hist-stat">
            <span class="hs-label">ATR יומי</span>
            <span class="hs-val">{atr}%</span>
          </div>
          <div class="hist-stat">
            <span class="hs-label">יום טוב</span>
            <span class="hs-val" style="color:#00d4aa">{bwd}</span>
          </div>
        </div>
      </div>"""


def build_stock_card(s, rank):
    t   = s['technicals']
    p   = s['position']
    sc  = s['score']
    col = score_color(sc)
    lbl = score_label(sc)

    reasons_html  = "".join(f'<li class="reason">✅ {r}</li>' for r in s['reasons'])
    warnings_html = "".join(f'<li class="warning">⚠️ {w}</li>' for w in s['warnings'])

    trade_plan = ""
    if sc >= 50:
        trade_plan = f"""
        <div class="trade-plan">
          <div class="plan-title">💼 תוכנית מסחר (דמו)</div>
          <div class="plan-grid">
            <div class="plan-item"><span class="plan-label">כמות</span><span class="plan-val">{p['shares']} מניות</span></div>
            <div class="plan-item"><span class="plan-label">השקעה</span><span class="plan-val">${p['investment']:,}</span></div>
            <div class="plan-item green"><span class="plan-label">יעד</span><span class="plan-val">${p['target']} (+3%)</span></div>
            <div class="plan-item red"><span class="plan-label">סטופ לוס</span><span class="plan-val">${p['stop']} (-1.5%)</span></div>
            <div class="plan-item green"><span class="plan-label">רווח פוטנציאלי</span><span class="plan-val">+${p['profit']}</span></div>
            <div class="plan-item red"><span class="plan-label">הפסד מקסימלי</span><span class="plan-val">-${p['loss']}</span></div>
          </div>
        </div>"""

    gap_class = "positive" if t['gap_pct'] >= 0 else "negative"
    gap_arrow = "▲" if t['gap_pct'] >= 0 else "▼"

    return f"""
    <div class="stock-card rank-{rank}">
      <div class="card-header">
        <div class="rank-badge">#{rank}</div>
        <div class="ticker-info">
          <span class="ticker">{s['ticker']}</span>
          <span class="company">{s['name']}</span>
        </div>
        <div class="score-circle" style="--score-color:{col}">
          <span class="score-num">{sc}</span>
          <span class="score-max">/100</span>
        </div>
      </div>

      <div class="recommendation-badge" style="background:{col}20; border:1px solid {col}; color:{col}">
        {lbl}
      </div>

      <div class="indicators">
        <div class="indicator">
          <span class="ind-label">מחיר</span>
          <span class="ind-val">${t['price']}</span>
        </div>
        <div class="indicator">
          <span class="ind-label">שינוי</span>
          <span class="ind-val {gap_class}">{gap_arrow} {abs(t['gap_pct'])}%</span>
        </div>
        <div class="indicator">
          <span class="ind-label">RSI</span>
          <span class="ind-val">{t['rsi']}</span>
        </div>
        <div class="indicator">
          <span class="ind-label">נפח</span>
          <span class="ind-val">×{t['volume_ratio']}</span>
        </div>
      </div>

      <div class="score-bar-wrap">
        <div class="score-bar" style="width:{sc}%; background:{col}"></div>
      </div>

      <ul class="analysis-list">
        {reasons_html}
        {warnings_html}
      </ul>

      {_build_news_section(s)}
      {_build_reddit_section(s)}
      {_build_options_section(s)}
      {_build_historical_section(s)}

      {trade_plan}
    </div>"""

def build_history_table(records):
    if not records:
        return "<p class='no-data'>עדיין אין היסטוריה. הפעלת הסוכן ביום המסחר הראשון תתחיל את המעקב.</p>"

    rows = ""
    for r in reversed(records[-20:]):
        result = r.get('actual_result') or "⏳ ממתין"
        if "פגע ביעד" in result:
            row_class = "win"
        elif "פגע בסטופ" in result:
            row_class = "loss"
        else:
            row_class = ""

        rows += f"""
        <tr class="{row_class}">
          <td>{r['date']}</td>
          <td><strong>{r['ticker']}</strong></td>
          <td>{r['score']}/100</td>
          <td>${r['price_at_report']}</td>
          <td>{result}</td>
        </tr>"""

    # סטטיסטיקות
    completed = [r for r in records if r.get('actual_result') and "%" in str(r.get('actual_result',''))]
    stats_html = ""
    if completed:
        wins   = sum(1 for r in completed if "פגע ביעד" in str(r.get('actual_result','')))
        losses = sum(1 for r in completed if "פגע בסטופ" in str(r.get('actual_result','')))
        total  = len(completed)
        pct    = round(wins/total*100)
        stats_html = f"""
        <div class="stats-row">
          <div class="stat green">✅ פגעו ביעד<br><strong>{wins}</strong> ({pct}%)</div>
          <div class="stat red">🛑 פגעו בסטופ<br><strong>{losses}</strong></div>
          <div class="stat">📊 סה"כ<br><strong>{total}</strong> המלצות</div>
        </div>"""

    return f"""
    {stats_html}
    <table class="history-table">
      <thead><tr><th>תאריך</th><th>מניה</th><th>ציון</th><th>מחיר כניסה</th><th>תוצאה</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>"""

def generate_html(results, tracking):
    now   = datetime.now().strftime("%d/%m/%Y %H:%M")
    today = datetime.now().strftime("%A, %d/%m/%Y")
    top3  = sorted(results, key=lambda x: x['score'], reverse=True)[:3]

    cards_html = "".join(build_stock_card(s, i+1) for i, s in enumerate(top3))
    history_html = build_history_table(tracking)

    return f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🤖 סוכני המניות של עינב</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #0a0f1e;
    color: #e2e8f0;
    direction: rtl;
    min-height: 100vh;
  }}

  .header {{
    background: linear-gradient(135deg, #0d1b2a 0%, #1a2744 100%);
    border-bottom: 1px solid #1e3a5f;
    padding: 24px 32px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .header h1 {{ font-size: 24px; font-weight: 700; color: #00d4aa; }}
  .header .subtitle {{ font-size: 13px; color: #64748b; margin-top: 4px; }}
  .header .time {{ font-size: 13px; color: #94a3b8; background: #1e293b; padding: 6px 14px; border-radius: 20px; }}

  .demo-banner {{
    background: linear-gradient(90deg, #1e3a5f, #1a2744);
    border: 1px solid #f5a62350;
    color: #f5a623;
    text-align: center;
    padding: 10px;
    font-size: 13px;
    letter-spacing: 0.5px;
  }}

  .container {{ max-width: 1100px; margin: 0 auto; padding: 32px 20px; }}

  .section-title {{
    font-size: 18px;
    font-weight: 600;
    color: #94a3b8;
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 1px solid #1e293b;
  }}

  .cards-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 20px;
    margin-bottom: 48px;
  }}

  .stock-card {{
    background: #111827;
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 24px;
    transition: transform 0.2s, border-color 0.2s;
  }}
  .stock-card:hover {{ transform: translateY(-2px); border-color: #334155; }}
  .stock-card.rank-1 {{ border-top: 3px solid #00d4aa; }}
  .stock-card.rank-2 {{ border-top: 3px solid #f5a623; }}
  .stock-card.rank-3 {{ border-top: 3px solid #64748b; }}

  .card-header {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
  }}
  .rank-badge {{
    width: 32px; height: 32px;
    border-radius: 50%;
    background: #1e293b;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; font-weight: 700; color: #94a3b8;
    flex-shrink: 0;
  }}
  .ticker-info {{ flex: 1; }}
  .ticker {{ font-size: 20px; font-weight: 800; color: #f1f5f9; display: block; }}
  .company {{ font-size: 12px; color: #64748b; }}

  .score-circle {{
    text-align: center;
    background: color-mix(in srgb, var(--score-color) 15%, transparent);
    border: 2px solid var(--score-color);
    border-radius: 12px;
    padding: 8px 14px;
    flex-shrink: 0;
  }}
  .score-num {{ font-size: 24px; font-weight: 800; color: var(--score-color); display: block; line-height: 1; }}
  .score-max {{ font-size: 11px; color: #64748b; }}

  .recommendation-badge {{
    display: inline-block;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 16px;
  }}

  .indicators {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    margin-bottom: 12px;
  }}
  .indicator {{
    background: #1e293b;
    border-radius: 8px;
    padding: 8px;
    text-align: center;
  }}
  .ind-label {{ font-size: 10px; color: #64748b; display: block; margin-bottom: 2px; }}
  .ind-val {{ font-size: 14px; font-weight: 700; color: #e2e8f0; }}
  .ind-val.positive {{ color: #00d4aa; }}
  .ind-val.negative {{ color: #ff4d6d; }}

  .score-bar-wrap {{
    height: 4px; background: #1e293b; border-radius: 2px; margin-bottom: 16px;
  }}
  .score-bar {{ height: 4px; border-radius: 2px; transition: width 1s ease; }}

  .analysis-list {{ list-style: none; margin-bottom: 16px; }}
  .analysis-list li {{ font-size: 13px; padding: 4px 0; border-bottom: 1px solid #1e293b10; }}
  .reason {{ color: #86efac; }}
  .warning {{ color: #fbbf24; }}

  .news-section {{ background: #0f172a; border-radius: 10px; padding: 12px; margin-bottom: 16px; }}
  .news-title {{ font-size: 12px; color: #64748b; margin-bottom: 6px; }}
  .news-text {{ font-size: 12px; color: #94a3b8; line-height: 1.6; }}

  .trade-plan {{
    background: linear-gradient(135deg, #0d2137, #0f172a);
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    padding: 16px;
  }}
  .plan-title {{ font-size: 13px; font-weight: 600; color: #60a5fa; margin-bottom: 12px; }}
  .plan-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
  .plan-item {{ display: flex; flex-direction: column; }}
  .plan-item.green .plan-val {{ color: #00d4aa; }}
  .plan-item.red .plan-val {{ color: #ff4d6d; }}
  .plan-label {{ font-size: 10px; color: #64748b; }}
  .plan-val {{ font-size: 14px; font-weight: 700; }}

  /* היסטוריה */
  .history-section {{ margin-top: 16px; }}
  .stats-row {{
    display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap;
  }}
  .stat {{
    flex: 1; min-width: 120px;
    background: #111827; border: 1px solid #1e293b;
    border-radius: 12px; padding: 16px; text-align: center;
    font-size: 13px; color: #94a3b8;
  }}
  .stat strong {{ display: block; font-size: 24px; margin-top: 4px; color: #f1f5f9; }}
  .stat.green strong {{ color: #00d4aa; }}
  .stat.red strong {{ color: #ff4d6d; }}

  .history-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  .history-table th {{
    background: #1e293b; color: #64748b;
    padding: 10px 12px; text-align: right; font-weight: 600;
  }}
  .history-table td {{ padding: 10px 12px; border-bottom: 1px solid #1e293b; }}
  .history-table tr.win td {{ background: #00d4aa08; }}
  .history-table tr.loss td {{ background: #ff4d6d08; }}
  .history-table tr:hover td {{ background: #1e293b30; }}

  .no-data {{ color: #64748b; font-size: 14px; padding: 24px; text-align: center; }}

  /* ── חדשות ── */
  .news-section {{ margin-top: 16px; }}
  .news-title {{ font-size: 12px; font-weight: 600; color: #64748b; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }}
  .news-item {{
    display: block; text-decoration: none; padding: 8px 10px;
    border-radius: 8px; border: 1px solid #1e293b; margin-bottom: 6px;
    transition: background 0.15s;
  }}
  .news-item:hover {{ background: #1e293b; }}
  .news-meta {{ display: block; font-size: 10px; color: #64748b; margin-bottom: 3px; }}
  .news-headline {{ display: block; font-size: 12px; color: #cbd5e1; line-height: 1.4; }}
  .news-text {{ font-size: 12px; color: #64748b; line-height: 1.6; white-space: pre-line; }}

  /* ── Reddit ── */
  .reddit-section {{
    margin-top: 14px; padding: 12px;
    background: #1a0a0a; border: 1px solid #ff450030; border-radius: 10px;
  }}
  .reddit-title {{ font-size: 12px; font-weight: 600; color: #ff6b35; margin-bottom: 8px; }}
  .reddit-mood {{ font-size: 12px; color: #94a3b8; margin: 6px 0 4px; }}
  .reddit-post {{ font-size: 11px; color: #64748b; padding: 3px 0; }}
  .reddit-score {{ color: #ff6b35; font-weight: 600; }}
  .sentiment-bar {{
    display: flex; height: 14px; border-radius: 7px; overflow: hidden; margin: 6px 0;
    font-size: 10px; font-weight: 600;
  }}
  .bar-bull {{ background: #00d4aa; color: #0a0f1e; display: flex; align-items: center; padding: 0 5px; white-space: nowrap; overflow: hidden; }}
  .bar-bear {{ background: #ff4d6d; color: white; display: flex; align-items: center; padding: 0 5px; white-space: nowrap; overflow: hidden; }}

  /* ── אופציות ── */
  .options-section {{
    margin-top: 14px; padding: 12px;
    background: #0d1f1a; border: 1px solid #00d4aa20; border-radius: 10px;
  }}
  .options-title {{ font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 8px; }}
  .options-bar {{
    display: flex; height: 14px; border-radius: 7px; overflow: hidden; margin: 6px 0;
    font-size: 10px; font-weight: 600;
  }}
  .bar-calls {{ background: #00d4aa; color: #0a0f1e; display: flex; align-items: center; padding: 0 5px; white-space: nowrap; overflow: hidden; }}
  .bar-puts  {{ background: #ff4d6d; color: white; display: flex; align-items: center; padding: 0 5px; white-space: nowrap; overflow: hidden; }}
  .options-note {{ font-size: 11px; color: #64748b; margin-top: 4px; }}

  /* ── ניתוח היסטורי ── */
  .historical-section {{ margin-top: 16px; padding: 14px; background: #0d1929; border-radius: 10px; border: 1px solid #1e293b; }}
  .hist-title {{ font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 10px; }}
  .year-range-bar {{ display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }}
  .range-label {{ font-size: 11px; color: #64748b; min-width: 48px; }}
  .range-track {{ flex: 1; height: 8px; background: #1e293b; border-radius: 4px; position: relative; overflow: visible; }}
  .range-fill {{ height: 100%; border-radius: 4px; opacity: 0.7; }}
  .range-marker {{ position: absolute; top: -3px; width: 14px; height: 14px; background: white; border-radius: 50%; transform: translateX(-50%); border: 2px solid #334155; }}
  .range-pos-text {{ font-size: 11px; color: #64748b; margin-bottom: 10px; text-align: center; }}
  .hist-stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }}
  .hist-stat {{ background: #111827; border-radius: 8px; padding: 8px; text-align: center; }}
  .hs-label {{ display: block; font-size: 10px; color: #64748b; margin-bottom: 4px; }}
  .hs-val {{ display: block; font-size: 14px; font-weight: 700; }}

  .footer {{
    text-align: center; color: #334155; font-size: 12px;
    padding: 32px; border-top: 1px solid #1e293b; margin-top: 48px;
  }}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>🤖 סוכני המניות של עינב</h1>
    <div class="subtitle">{today}</div>
  </div>
  <div class="time">עודכן: {now}</div>
</div>

<div class="demo-banner">
  ⚠️ &nbsp; גרסת דמו — כל ההמלצות הן לצורך תרגול בלבד, לא מסחר אמיתי
</div>

<div class="container">

  <div class="section-title">🏆 המניות המומלצות להיום</div>
  <div class="cards-grid">
    {cards_html}
  </div>

  <div class="section-title">📊 היסטוריית המלצות</div>
  <div class="history-section">
    {history_html}
  </div>

</div>

<div class="footer">
  🤖 סוכני המניות של עינב &nbsp;|&nbsp; גרסת דמו &nbsp;|&nbsp; לא ייעוץ השקעות
</div>

</body>
</html>"""

def save_html(results, tracking):
    os.makedirs("reports", exist_ok=True)
    html = generate_html(results, tracking)
    path = "reports/dashboard.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path

if __name__ == "__main__":
    results  = load_latest_results()
    tracking = load_tracking()
    if not results:
        print("❌ לא נמצאו נתונים. הרץ קודם את morning_report.py")
    else:
        path = save_html(results, tracking)
        print(f"✅ Dashboard נשמר: {path}")
        import subprocess
        subprocess.run(["open", path])
