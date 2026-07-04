#!/usr/bin/env python3
"""
🌐 generate_team_report.py — דוח HTML מקצועי לצוות הסוכנים
============================================================
בונה אתר יפה ומפורט שמציג את ניתוח כל הסוכנים.
"""

import json
from datetime import datetime


def _score_color(score):
    if score >= 60:
        return "#00c853"
    elif score >= 35:
        return "#ffd600"
    elif score >= 10:
        return "#ff9800"
    else:
        return "#f44336"


def _sentiment_color(score):
    if score > 20:
        return "#00c853"
    elif score > 0:
        return "#69f0ae"
    elif score > -20:
        return "#90a4ae"
    else:
        return "#f44336"



def _build_performance_section():
    """טבלת ביצועים היסטורית + יומן הלמידה — מ-data/."""
    try:
        with open("data/tracking.json", "r", encoding="utf-8") as f:
            records = json.load(f)
    except Exception:
        records = []

    completed = [r for r in records if r.get("actual_result")
                 and r.get("actual_result") not in (None, "open")]
    if not completed:
        return ""

    hits  = sum(1 for r in completed if r["actual_result"] == "target")
    stops = sum(1 for r in completed if r["actual_result"] == "stop")
    win_rate = round(hits / max(1, hits + stops) * 100) if (hits + stops) else 0

    rows = ""
    outcome_he = {"target": "✅ פגע ביעד", "stop": "🛑 סטופ",
                  "neither": "⏳ בלי פגיעה", "no_trade": "⚪ המתנה"}
    for r in list(reversed(completed))[:15]:
        color = "#00c853" if (r.get("pnl_pct") or 0) > 0 else "#f44336"
        rows += f"""<tr>
          <td>{r.get('date','')}</td><td><b>{r.get('ticker','')}</b></td>
          <td>{r.get('total_score','')}</td>
          <td>{outcome_he.get(r.get('actual_result'), r.get('actual_result'))}</td>
          <td style="color:{color}">{(r.get('pnl_pct') or 0):+.1f}%</td>
        </tr>"""

    # יומן למידה אחרון
    lessons_html = ""
    try:
        with open("data/learning_log.json", "r", encoding="utf-8") as f:
            log = json.load(f)
        if log:
            last = log[-1]
            items = (last.get("weight_changes", [])[:3] + last.get("lessons", [])[:3])
            if items:
                lis = "".join(f"<div style='margin:4px 0;color:#b0bec5'>• {i}</div>" for i in items)
                lessons_html = f"""
<div style="max-width:900px;margin:10px auto;padding:14px;background:#111827;
     border:1px solid #1e2a4a;border-radius:10px;font-size:0.85rem">
  <b style="color:#90caf9">🧠 מה המערכת למדה אתמול ({last.get('date','')}):</b>
  {lis}
</div>"""
    except Exception:
        pass

    return f"""
<div class="section-title">🪞 ביקורת עצמית — ביצועי ההמלצות עד כה</div>
<div style="max-width:900px;margin:0 auto;text-align:center;color:#b0bec5;font-size:0.95rem">
  סה"כ נבדקו: {len(completed)} המלצות |
  ✅ יעדים: {hits} | 🛑 סטופים: {stops} |
  🎯 אחוז הצלחה (יעד מול סטופ): <b style="color:#90caf9">{win_rate}%</b>
</div>
{lessons_html}
<div class="table-wrap" style="margin-top:15px">
  <table>
    <thead><tr><th>תאריך</th><th>מניה</th><th>ציון בוקר</th><th>תוצאה</th><th>רווח/הפסד</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>"""


def build_html(top5, all_stocks, health=None):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    # ── באנר בריאות: אם הנתונים חלקיים, אומרים את זה ביושר ──
    health_banner = ""
    if health:
        if health.get("degraded"):
            health_banner = f"""
<div style="max-width:900px;margin:20px auto;padding:16px;background:#4a1500;
     border:2px solid #ff5722;border-radius:12px;text-align:center;color:#ffab91">
  🚨 <b>אזהרה: כיסוי הנתונים היום נמוך!</b><br>
  ניתוח טכני: {health.get('tech_coverage', '?')}% מהמניות |
  נתוני סיכון: {health.get('risk_coverage', '?')}% |
  פונדמנטלי: {health.get('fund_coverage', '?')}%<br>
  <b>ההמלצות בדוח זה אינן אמינות — לא לסחור לפיהן היום.</b>
</div>"""
        else:
            src_info = health.get("data_sources", {})
            health_banner = f"""
<div style="max-width:900px;margin:15px auto;padding:10px;background:#0d2818;
     border:1px solid #1b5e20;border-radius:10px;text-align:center;color:#a5d6a7;font-size:0.85rem">
  🩺 בריאות המערכת: טכני {health.get('tech_coverage', '?')}% |
  סיכון {health.get('risk_coverage', '?')}% |
  פונדמנטלי {health.get('fund_coverage', '?')}%
  &nbsp;·&nbsp; מקורות: yfinance {src_info.get('yfinance_ok', 0)} · Stooq {src_info.get('stooq_ok', 0)}
</div>"""

    # ── סקציית ביצועים: מה קרה להמלצות הקודמות + מה המערכת למדה ──
    performance_html = _build_performance_section()

    # ── כרטיס מניה ──
    def stock_card(s, rank):
        sc = s["total_score"]
        color = _score_color(sc)
        tech = s.get("tech", {})
        news = s.get("news", {})
        fund = s.get("fund", {})
        risk = s.get("risk", {})

        # תבניות נרות
        candles_html = ""
        for p in tech.get("candle_patterns", []):
            candles_html += f'<div class="candle-tag">🕯️ {p}</div>'

        # כותרות חדשות
        headlines_html = ""
        for h in (news.get("headlines") or [])[:3]:
            headlines_html += f'<div class="headline">📰 {h}</div>'

        # אותות
        signals_html = ""
        for sig in s.get("all_signals", [])[:5]:
            signals_html += f'<div class="signal-tag">✅ {sig}</div>'

        # אזהרות
        warnings_html = ""
        for w in s.get("all_warnings", [])[:3]:
            warnings_html += f'<div class="warning-tag">⚠️ {w}</div>'

        # ניהול סיכון — לונג או שורט
        risk_html = ""
        trade_type = s.get("trade_type", "long")

        if trade_type == "short" and s.get("short_entry"):
            sp = s.get("short_stop_pct", 0)
            risk_html = f"""
            <div class="risk-box" style="border:1px solid #f44336">
                <div class="risk-title">⚖️ ניהול סיכון — שורט 📉</div>
                <div style="font-size:0.78rem;color:#ff8a80;margin-bottom:8px">
                    שורט = מוכרים בחסר, מרוויחים כשהמחיר יורד
                </div>
                <div class="risk-grid">
                    <div class="risk-item">
                        <div class="risk-label">כניסה (מכירה)</div>
                        <div class="risk-val red">${s['short_entry']}</div>
                    </div>
                    <div class="risk-item">
                        <div class="risk-label">Stop Loss (מעל)</div>
                        <div class="risk-val" style="color:#ff9800">${s['short_stop']} <span class="small">(+{sp}%)</span></div>
                    </div>
                    <div class="risk-item">
                        <div class="risk-label">יעד 1 (מתחת)</div>
                        <div class="risk-val green">${s['short_target_1']}</div>
                    </div>
                    <div class="risk-item">
                        <div class="risk-label">יעד 2 (מתחת)</div>
                        <div class="risk-val green">${s['short_target_2']}</div>
                    </div>
                    <div class="risk-item">
                        <div class="risk-label">כמות</div>
                        <div class="risk-val">{s['shares']} מניות</div>
                    </div>
                    <div class="risk-item">
                        <div class="risk-label">סיכון מקס׳</div>
                        <div class="risk-val red">${s['max_loss']}</div>
                    </div>
                </div>
            </div>"""
        elif s.get("entry"):
            stop_pct = s.get("stop_pct", 0)
            risk_html = f"""
            <div class="risk-box">
                <div class="risk-title">⚖️ ניהול סיכון — לונג 📈</div>
                <div class="risk-grid">
                    <div class="risk-item">
                        <div class="risk-label">כניסה</div>
                        <div class="risk-val green">${s['entry']}</div>
                    </div>
                    <div class="risk-item">
                        <div class="risk-label">Stop Loss</div>
                        <div class="risk-val red">${s['stop_loss']} <span class="small">(-{stop_pct}%)</span></div>
                    </div>
                    <div class="risk-item">
                        <div class="risk-label">יעד 1</div>
                        <div class="risk-val blue">${s['target_1']}</div>
                    </div>
                    <div class="risk-item">
                        <div class="risk-label">יעד 2</div>
                        <div class="risk-val blue">${s['target_2']}</div>
                    </div>
                    <div class="risk-item">
                        <div class="risk-label">כמות</div>
                        <div class="risk-val">{s['shares']} מניות</div>
                    </div>
                    <div class="risk-item">
                        <div class="risk-label">סיכון מקס׳</div>
                        <div class="risk-val red">${s['max_loss']}</div>
                    </div>
                </div>
            </div>"""

        rank_badge = ["🥇","🥈","🥉","4️⃣","5️⃣"][rank-1] if rank <= 5 else f"#{rank}"

        return f"""
        <div class="stock-card" style="border-top: 4px solid {color}">
            <div class="card-header">
                <div class="rank-badge">{rank_badge}</div>
                <div class="ticker-name">{s['ticker']}</div>
                <div class="score-circle" style="background:{color}">{sc:.0f}</div>
                <div class="decision-badge">{s['decision']}</div>
            </div>

            <div class="agents-grid">
                <div class="agent-box">
                    <div class="agent-title">🕯️ ניתוח טכני</div>
                    <div class="agent-detail">{tech.get('ema_signal','—')}</div>
                    <div class="agent-detail">{tech.get('rsi_signal','—')}</div>
                    <div class="agent-detail">{tech.get('macd_signal','—')}</div>
                    <div class="agent-detail">{tech.get('bb_signal','—')}</div>
                    <div class="agent-detail">{tech.get('volume_signal','—')}</div>
                    {candles_html}
                </div>

                <div class="agent-box">
                    <div class="agent-title">📰 חדשות וסנטימנט</div>
                    <div class="sentiment-badge" style="background:{_sentiment_color(news.get('sentiment_score',0))}">
                        {news.get('sentiment_label','—')}
                    </div>
                    <div class="agent-detail">{news.get('summary','—')}</div>
                    {headlines_html}
                </div>

                <div class="agent-box">
                    <div class="agent-title">📊 ניתוח פונדמנטלי</div>
                    <div class="agent-detail">אנליסטים: {fund.get('analyst_rating','—')}</div>
                    {'<div class="agent-detail">יעד: $' + str(fund.get('analyst_target','—')) + ' (פוטנציאל +' + str(fund.get('upside_pct','—')) + '%)</div>' if fund.get('analyst_target') else ''}
                    {'<div class="agent-detail earnings-tag">📅 דוח בעוד ' + str(fund.get('earnings_days_away')) + ' ימים!</div>' if fund.get('earnings_days_away') is not None and 0 <= fund.get('earnings_days_away',99) <= 7 else ''}
                    {'<div class="agent-detail">הפתעת EPS: ' + str(fund.get('last_eps_surprise','')) + '%</div>' if fund.get('last_eps_surprise') else ''}
                    {'<div class="agent-detail">Short: ' + str(fund.get('short_interest','')) + '%</div>' if fund.get('short_interest') else ''}
                </div>
            </div>

            <div class="signals-row">
                {signals_html}
                {warnings_html}
            </div>

            {risk_html}
        </div>
        """

    # ── טבלת כל המניות ──
    all_rows = ""
    for s in all_stocks:
        sc = s["total_score"]
        color = _score_color(sc)
        all_rows += f"""
        <tr>
            <td><strong>{s['ticker']}</strong></td>
            <td style="color:{color};font-weight:bold">{sc:.0f}</td>
            <td>{s['decision']}</td>
            <td>{s['tech'].get('trend','—')}</td>
            <td>{s['tech'].get('rsi','—')}</td>
            <td>{s['news'].get('sentiment_label','—')}</td>
            <td>{'🔥 ' + s['news'].get('catalyst_type','') if s['news'].get('catalyst') else '—'}</td>
            <td>{'$' + str(s.get('entry','')) if s.get('entry') else '—'}</td>
            <td>{'$' + str(s.get('stop_loss','')) if s.get('stop_loss') else '—'}</td>
        </tr>"""

    # ── כרטיסי TOP 5 ──
    top_cards = ""
    for i, s in enumerate(top5, 1):
        top_cards += stock_card(s, i)

    return f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>צוות סוכני המניות — {now}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Segoe UI', Arial, sans-serif;
    background: #0a0e1a;
    color: #e0e0e0;
    direction: rtl;
  }}

  /* ── Header ── */
  .header {{
    background: linear-gradient(135deg, #0d47a1, #1a237e, #311b92);
    padding: 30px 20px;
    text-align: center;
    border-bottom: 2px solid #3949ab;
  }}
  .header h1 {{ font-size: 2rem; color: #fff; margin-bottom: 8px; }}
  .header .subtitle {{ color: #90caf9; font-size: 1rem; }}
  .header .time {{ color: #b39ddb; font-size: 0.85rem; margin-top: 6px; }}

  /* ── Section title ── */
  .section-title {{
    text-align: center;
    font-size: 1.4rem;
    color: #90caf9;
    margin: 30px 0 15px;
    padding: 10px;
    border-bottom: 1px solid #1e2a4a;
  }}

  /* ── Stock Card ── */
  .stock-card {{
    background: #111827;
    border-radius: 12px;
    margin: 20px auto;
    max-width: 900px;
    padding: 20px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  }}
  .card-header {{
    display: flex;
    align-items: center;
    gap: 15px;
    margin-bottom: 20px;
    flex-wrap: wrap;
  }}
  .rank-badge {{ font-size: 2rem; }}
  .ticker-name {{
    font-size: 2rem;
    font-weight: bold;
    color: #fff;
    flex: 1;
  }}
  .score-circle {{
    width: 60px; height: 60px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.3rem; font-weight: bold; color: #000;
  }}
  .decision-badge {{
    background: #1e2a4a;
    padding: 8px 16px;
    border-radius: 20px;
    font-size: 1rem;
    color: #fff;
  }}

  /* ── Agents Grid ── */
  .agents-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 15px;
    margin-bottom: 15px;
  }}
  .agent-box {{
    background: #0d1525;
    border-radius: 10px;
    padding: 14px;
    border: 1px solid #1e2a4a;
  }}
  .agent-title {{
    font-size: 0.9rem;
    color: #90caf9;
    font-weight: bold;
    margin-bottom: 10px;
    padding-bottom: 6px;
    border-bottom: 1px solid #1e2a4a;
  }}
  .agent-detail {{
    font-size: 0.82rem;
    color: #b0bec5;
    margin: 4px 0;
    line-height: 1.4;
  }}
  .candle-tag, .signal-tag, .warning-tag, .headline {{
    font-size: 0.8rem;
    padding: 4px 8px;
    border-radius: 6px;
    margin: 3px 2px;
    display: inline-block;
  }}
  .candle-tag  {{ background: #1a237e; color: #90caf9; }}
  .signal-tag  {{ background: #1b5e20; color: #a5d6a7; }}
  .warning-tag {{ background: #4a1500; color: #ffab91; }}
  .headline    {{ background: #1c2331; color: #90a4ae; display: block; }}

  .sentiment-badge {{
    display: inline-block;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.85rem;
    font-weight: bold;
    color: #000;
    margin-bottom: 8px;
  }}
  .earnings-tag {{ color: #ffd600 !important; font-weight: bold; }}

  .signals-row {{
    margin: 10px 0;
    min-height: 10px;
  }}

  /* ── Risk Box ── */
  .risk-box {{
    background: #0d1525;
    border-radius: 10px;
    padding: 16px;
    margin-top: 15px;
    border: 1px solid #263238;
  }}
  .risk-title {{
    color: #90caf9;
    font-weight: bold;
    margin-bottom: 12px;
  }}
  .risk-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
  }}
  .risk-item {{
    text-align: center;
    background: #111827;
    padding: 10px;
    border-radius: 8px;
  }}
  .risk-label {{ font-size: 0.75rem; color: #78909c; margin-bottom: 4px; }}
  .risk-val {{ font-size: 1rem; font-weight: bold; }}
  .risk-val.green {{ color: #00c853; }}
  .risk-val.red   {{ color: #f44336; }}
  .risk-val.blue  {{ color: #40c4ff; }}
  .risk-val .small {{ font-size: 0.75rem; font-weight: normal; }}

  /* ── All Stocks Table ── */
  .table-wrap {{
    max-width: 960px;
    margin: 0 auto 40px;
    overflow-x: auto;
    padding: 0 15px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }}
  th {{
    background: #1a237e;
    color: #90caf9;
    padding: 10px 8px;
    text-align: center;
  }}
  td {{
    padding: 8px;
    text-align: center;
    border-bottom: 1px solid #1e2a4a;
    color: #b0bec5;
  }}
  tr:hover td {{ background: #0d1525; }}

  /* ── Footer ── */
  .footer {{
    text-align: center;
    padding: 20px;
    color: #546e7a;
    font-size: 0.8rem;
    border-top: 1px solid #1e2a4a;
    margin-top: 30px;
  }}
</style>
</head>
<body>

<div class="header">
  <h1>👑 צוות סוכני המניות</h1>
  <div class="subtitle">ניתוח יומי מקצועי — טכני · חדשות · פונדמנטלי · סיכון</div>
  <div class="time">📅 {now} | {len(all_stocks)} מניות נסרקו</div>
</div>

{health_banner}

<div class="section-title">🏆 TOP 5 המניות להיום — ניתוח מלא</div>
<div style="padding: 0 15px">
  {top_cards}
</div>

<div class="section-title">📋 כל המניות שנסרקו</div>
<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th>מניה</th><th>ציון</th><th>המלצה</th><th>טרנד</th>
        <th>RSI</th><th>סנטימנט</th><th>קטליסט</th>
        <th>כניסה</th><th>Stop</th>
      </tr>
    </thead>
    <tbody>{all_rows}</tbody>
  </table>
</div>

{performance_html}

<div class="footer">
  🤖 הופק אוטומטית על ידי צוות סוכני AI | לא ייעוץ פיננסי | אינטרקטיב ישראל
</div>

</body>
</html>"""


if __name__ == "__main__":
    # בדיקה עם נתוני דמה
    sample = [{
        "ticker": "TSLA",
        "total_score": 72,
        "decision": "🟢 קנייה חזקה",
        "priority": "גבוה",
        "tech": {"summary": "טרנד עולה", "ema_signal": "EMA bullish", "rsi_signal": "RSI 45",
                 "macd_signal": "MACD חיובי", "bb_signal": "בחצי עליון",
                 "volume_signal": "נפח x2.3", "candle_patterns": ["Hammer 🔨"]},
        "news": {"sentiment_label": "חיובי 🟢", "sentiment_score": 30,
                 "summary": "3 חדשות היום", "catalyst": True, "catalyst_type": "earnings",
                 "headlines": ["Tesla beats Q2 estimates", "New model announced"]},
        "fund": {"analyst_rating": "Strong Buy (8/10)", "analyst_target": 350,
                 "upside_pct": 18, "earnings_days_away": 2, "last_eps_surprise": 12, "short_interest": 8, "summary": ""},
        "risk": {},
        "all_signals": ["EMA bullish alignment", "MACD crossover"],
        "all_warnings": [],
        "entry": 297.50, "stop_loss": 289.00, "stop_pct": 2.9,
        "target_1": 310.0, "target_2": 323.0,
        "shares": 5, "max_loss": 42.50
    }]
    html = build_html(sample, sample)
    with open("/tmp/test_report.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("נוצר /tmp/test_report.html")
