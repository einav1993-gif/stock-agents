#!/usr/bin/env python3
"""
📄 daily_pdf.py — דוח PDF יומי
================================
כל ערב, אחרי הביקורת העצמית, נוצר קובץ PDF מסכם ליום:
  reports/daily_YYYY-MM-DD.pdf
כך נבנית מאליה תיקיית reports/ עם דוח לכל יום מסחר.

הדוח כולל:
  • סיכום היום: אילו המלצות נבדקו, מה קרה (יעד/סטופ/באמצע)
  • מצב תיק הדמה: שווי, תשואה, אחוז הצלחה, נפילה מקסימלית
  • הלקחים שהמערכת למדה היום

עברית מוצגת נכון (מימין לשמאל) בעזרת python-bidi + גופן DejaVuSans.
"""

import json
import os
from datetime import datetime

from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER

DATA_DIR = "data"
REPORTS_DIR = "reports"

# ── גופנים עבריים (זמינים ב-ubuntu / GitHub runner) ──
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
FONT = "Heb"
FONT_BOLD = "HebBold"
try:
    pdfmetrics.registerFont(TTFont(FONT, _FONT_CANDIDATES[0]))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, _FONT_CANDIDATES[1]))
except Exception:
    FONT = FONT_BOLD = "Helvetica"  # גיבוי (בלי עברית, אבל לא קורס)


def he(text):
    """הופך טקסט עברי לסדר תצוגה נכון (RTL)."""
    return get_display(str(text))


def _load(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def build_pdf(date_str=None):
    """בונה את דוח ה-PDF ליום. מחזיר את נתיב הקובץ, או None אם נכשל."""
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    os.makedirs(REPORTS_DIR, exist_ok=True)
    path = os.path.join(REPORTS_DIR, f"daily_{date_str}.pdf")

    tracking = _load(os.path.join(DATA_DIR, "tracking.json"), [])
    portfolio = _load(os.path.join(DATA_DIR, "portfolio.json"), {})
    log = _load(os.path.join(DATA_DIR, "learning_log.json"), [])

    styles = getSampleStyleSheet()
    title_st = ParagraphStyle("t", parent=styles["Title"], fontName=FONT_BOLD,
                              alignment=TA_CENTER, fontSize=20, leading=26)
    h_st = ParagraphStyle("h", parent=styles["Heading2"], fontName=FONT_BOLD,
                          alignment=TA_RIGHT, fontSize=13, leading=18,
                          textColor=colors.HexColor("#1a237e"))
    p_st = ParagraphStyle("p", parent=styles["Normal"], fontName=FONT,
                          alignment=TA_RIGHT, fontSize=10, leading=15)

    doc = SimpleDocTemplate(path, pagesize=A4,
                            rightMargin=18*mm, leftMargin=18*mm,
                            topMargin=18*mm, bottomMargin=18*mm)
    story = []

    # ── כותרת ──
    story.append(Paragraph(he(f"👑 דוח יומי — צוות סוכני המניות"), title_st))
    story.append(Paragraph(he(f"תאריך: {date_str}"),
                           ParagraphStyle("d", parent=p_st, alignment=TA_CENTER,
                                          textColor=colors.grey)))
    story.append(Spacer(1, 8*mm))

    # ── סיכום התיק ──
    start = portfolio.get("start_cash", 1000)
    curve = portfolio.get("equity_curve", [])
    equity = curve[-1]["equity"] if curve else portfolio.get("cash", start)
    ret_pct = round((equity - start) / start * 100, 1) if start else 0
    closed = portfolio.get("closed_trades", [])
    wins = sum(1 for t in closed if t.get("pnl", 0) > 0)
    win_rate = round(wins / len(closed) * 100) if closed else 0
    dd = portfolio.get("max_drawdown_pct", 0)

    story.append(Paragraph(he("💼 מצב תיק הדמה"), h_st))
    kpi = [
        [he("שווי תיק"), he("תשואה"), he("אחוז הצלחה"), he("עסקאות"), he("נפילה מקס'")],
        [he(f"${equity:,.0f}"), he(f"{ret_pct:+.1f}%"), he(f"{win_rate}%"),
         he(str(len(closed))), he(f"{dd:.1f}%")],
    ]
    kt = Table(kpi, colWidths=[34*mm]*5)
    kt.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f0f0f5")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(kt)
    story.append(Spacer(1, 6*mm))

    # ── עסקאות שנסגרו היום ──
    today_trades = [t for t in closed if t.get("date_close") == date_str]
    story.append(Paragraph(he("📊 עסקאות שנסגרו היום"), h_st))
    if today_trades:
        rows = [[he("תוצאה"), he("רווח/הפסד"), he("יציאה"), he("כניסה"), he("מנייה")]]
        for t in today_trades:
            rows.append([
                he(t.get("reason", "")),
                he(f"{t.get('pnl', 0):+.2f}$ ({t.get('pnl_pct', 0):+.1f}%)"),
                he(f"${t.get('exit', '')}"), he(f"${t.get('entry', '')}"),
                he(t.get("ticker", "")),
            ])
        tt = Table(rows, colWidths=[45*mm, 40*mm, 25*mm, 25*mm, 25*mm])
        tt.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f7fa")]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(tt)
    else:
        story.append(Paragraph(he("לא נסגרו עסקאות היום (אין פוזיציות פתוחות או שהמערכת לא זיהתה איתות חזק)."), p_st))
    story.append(Spacer(1, 6*mm))

    # ── לקחים שנלמדו היום ──
    today_log = next((e for e in reversed(log) if e.get("date") == date_str), None)
    story.append(Paragraph(he("🧠 מה המערכת למדה היום"), h_st))
    if today_log:
        stats_line = (f"נבדקו {today_log.get('checked', 0)} המלצות | "
                      f"יעדים: {today_log.get('hits', 0)} | "
                      f"סטופים: {today_log.get('stops', 0)} | "
                      f"דיוק כיוון: {today_log.get('direction_correct', 0)}/{today_log.get('direction_total', 0)}")
        story.append(Paragraph(he(stats_line), p_st))
        story.append(Spacer(1, 2*mm))
        for c in today_log.get("weight_changes", [])[:5]:
            story.append(Paragraph(he("• " + c), p_st))
        for l in today_log.get("lessons", [])[:5]:
            story.append(Paragraph(he("• " + l), p_st))
    else:
        story.append(Paragraph(he("אין עדיין נתוני למידה ליום זה."), p_st))

    story.append(Spacer(1, 10*mm))
    story.append(Paragraph(
        he("הופק אוטומטית על ידי צוות סוכני AI · לא ייעוץ פיננסי · המערכת בשלב מסחר דמה"),
        ParagraphStyle("f", parent=p_st, alignment=TA_CENTER, fontSize=8,
                       textColor=colors.grey)))

    try:
        doc.build(story)
        return path
    except Exception as e:
        print(f"⚠️  שגיאה בבניית PDF: {e}")
        return None


if __name__ == "__main__":
    p = build_pdf()
    print(f"✅ נוצר: {p}" if p else "❌ הבנייה נכשלה")
