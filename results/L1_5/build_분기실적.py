"""samples/04_분기실적.csv -> 분기실적/분기실적.html (16:9 슬라이드 덱)"""
import csv
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "samples" / "04_분기실적.csv"
OUT = ROOT / "분기실적" / "분기실적.html"

rows = []
with open(SRC, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        rows.append({
            "m": r["월"], "mon": int(r["월"][5:]),
            "rev": int(r["매출_만원"]), "new": int(r["신규고객"]),
            "churn": int(r["해지고객"]), "active": int(r["월말_활성고객"]),
            "mkt": int(r["마케팅비_만원"]),
        })

# 데이터 정합성: 전월 활성 + 신규 - 해지 = 당월 활성
for a, b in zip(rows, rows[1:]):
    assert a["active"] + b["new"] - b["churn"] == b["active"], b["m"]

for i, r in enumerate(rows):
    r["arpu"] = r["rev"] / r["active"]                 # 월말 활성고객 1인당 매출(만원)
    r["churn_rate"] = r["churn"] / rows[i - 1]["active"] if i else None

Q = []
for qi in range(3):
    ms = rows[qi * 3:qi * 3 + 3]
    Q.append({
        "name": f"{qi + 1}분기", "rev": sum(x["rev"] for x in ms),
        "new": sum(x["new"] for x in ms), "churn": sum(x["churn"] for x in ms),
        "mkt": sum(x["mkt"] for x in ms), "active": ms[-1]["active"],
        "arpu": ms[-1]["arpu"],
        "start": rows[qi * 3 - 1]["active"] if qi else None,
    })
for q in Q:
    q["cac"] = q["mkt"] / q["new"]
    q["roas"] = q["rev"] / q["mkt"]
q1, q2, q3 = Q


def pct(a, b):
    return (a / b - 1) * 100


def fmt(n):
    return f"{n:,.0f}"


def sgn(p, d=1):
    return f"{'+' if p >= 0 else '−'}{abs(p):.{d}f}%"


def eok(man):  # 만원 -> "3억 940만원"
    e, m = divmod(man, 10000)
    return f"{e}억 {fmt(m)}만원" if e else f"{fmt(m)}만원"


# ---------- SVG 차트 ----------
W, H = 1040, 400


def bar_chart(labels, values, highlight, unit, vmax, w=W, h=H, fmtv=fmt):
    pl, pr, pt, pb = 70, 20, 30, 50
    iw, ih = w - pl - pr, h - pt - pb
    n = len(values)
    slot = iw / n
    bw = min(120, slot * 0.5)
    ticks = [vmax * i / 4 for i in range(5)]
    s = [f'<svg viewBox="0 0 {w} {h}" class="chart" role="img">']
    for t in ticks:
        y = pt + ih - t / vmax * ih
        s.append(f'<line x1="{pl}" x2="{w - pr}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
        s.append(f'<text x="{pl - 10}" y="{y + 4:.1f}" class="tick" text-anchor="end">{fmtv(t)}</text>')
    for i, (lab, v) in enumerate(zip(labels, values)):
        x = pl + slot * i + (slot - bw) / 2
        bh = v / vmax * ih
        y = pt + ih - bh
        cls = "bar hi" if i in highlight else "bar"
        r = 4
        path = (f"M{x:.1f},{pt + ih:.1f} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} "
                f"H{x + bw - r:.1f} Q{x + bw:.1f},{y:.1f} {x + bw:.1f},{y + r:.1f} V{pt + ih:.1f} Z")
        s.append(f'<g class="hit" data-tip="{html.escape(lab)}: {fmtv(v)}{unit}">'
                 f'<rect x="{pl + slot * i:.1f}" y="{pt}" width="{slot:.1f}" height="{ih}" fill="transparent"/>'
                 f'<path d="{path}" class="{cls}"/></g>')
        s.append(f'<text x="{x + bw / 2:.1f}" y="{y - 10:.1f}" class="val{" strong" if i in highlight else ""}" '
                 f'text-anchor="middle">{fmtv(v)}</text>')
        s.append(f'<text x="{x + bw / 2:.1f}" y="{pt + ih + 28:.1f}" class="tick" text-anchor="middle">{html.escape(lab)}</text>')
    s.append(f'<line x1="{pl}" x2="{w - pr}" y1="{pt + ih}" y2="{pt + ih}" class="axis"/>')
    s.append("</svg>")
    return "".join(s)


def line_chart(labels, series, unit, vmin, vmax, w=W, h=H, fmtv=fmt, annotate=None,
               shade_from=None, nticks=4):
    """series: [(name, values, css_class)]"""
    pl, pr, pt, pb = 70, 90, 30, 50
    iw, ih = w - pl - pr, h - pt - pb
    n = len(labels)
    xs = [pl + iw * i / (n - 1) for i in range(n)]

    def Y(v):
        return pt + ih - (v - vmin) / (vmax - vmin) * ih

    s = [f'<svg viewBox="0 0 {w} {h}" class="chart" role="img">']
    if shade_from is not None:
        x0 = (xs[shade_from - 1] + xs[shade_from]) / 2
        s.append(f'<rect x="{x0:.1f}" y="{pt}" width="{w - pr - x0 + 10:.1f}" height="{ih}" class="shade"/>')
        s.append(f'<text x="{x0 + 8:.1f}" y="{pt + 16}" class="shade-label">3분기</text>')
    for i in range(nticks + 1):
        t = vmin + (vmax - vmin) * i / nticks
        y = Y(t)
        s.append(f'<line x1="{pl}" x2="{w - pr}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
        s.append(f'<text x="{pl - 10}" y="{y + 4:.1f}" class="tick" text-anchor="end">{fmtv(t)}</text>')
    for x, lab in zip(xs, labels):
        s.append(f'<text x="{x:.1f}" y="{pt + ih + 28}" class="tick" text-anchor="middle">{lab}</text>')
    for name, vals, cls in series:
        pts = " ".join(f"{x:.1f},{Y(v):.1f}" for x, v in zip(xs, vals) if v is not None)
        s.append(f'<polyline points="{pts}" class="line {cls}"/>')
        for x, v in zip(xs, vals):
            if v is not None:
                s.append(f'<circle cx="{x:.1f}" cy="{Y(v):.1f}" r="4.5" class="dot {cls}"/>')
        last = vals[-1]
        s.append(f'<text x="{xs[-1] + 12:.1f}" y="{Y(last) + 5:.1f}" class="val strong">{fmtv(last)}</text>')
        if len(series) > 1:
            s.append(f'<text x="{xs[-1] + 12:.1f}" y="{Y(last) + 22:.1f}" class="tick">{name}</text>')
    if annotate:
        i, text = annotate
        v = series[0][1][i]
        s.append(f'<line x1="{xs[i]:.1f}" x2="{xs[i]:.1f}" y1="{Y(v) + 10:.1f}" y2="{Y(v) + 46:.1f}" class="axis"/>')
        s.append(f'<text x="{xs[i]:.1f}" y="{Y(v) + 64:.1f}" class="note" text-anchor="middle">{text}</text>')
    # 호버 히트 영역 (월 단위 컬럼)
    step = iw / (n - 1)
    for i, x in enumerate(xs):
        tip = " · ".join(f"{nm} {fmtv(v[i])}{unit}" for nm, v, _ in series if v[i] is not None)
        s.append(f'<rect class="hit col" x="{x - step / 2:.1f}" y="{pt}" width="{step:.1f}" height="{ih}" '
                 f'data-tip="{labels[i]} — {html.escape(tip)}"/>')
    s.append(f'<line x1="{pl}" x2="{w - pr}" y1="{pt + ih}" y2="{pt + ih}" class="axis"/>')
    s.append("</svg>")
    return "".join(s)


def grouped_bars(labels, a, b, names, w=W, h=H, vmax=None, shade_from=None):
    pl, pr, pt, pb = 70, 20, 30, 50
    iw, ih = w - pl - pr, h - pt - pb
    vmax = vmax or max(a + b)
    n = len(labels)
    slot = iw / n
    bw = slot * 0.3
    s = [f'<svg viewBox="0 0 {w} {h}" class="chart" role="img">']
    if shade_from is not None:
        x0 = pl + slot * shade_from
        s.append(f'<rect x="{x0:.1f}" y="{pt}" width="{w - pr - x0:.1f}" height="{ih}" class="shade"/>')
        s.append(f'<text x="{x0 + 8:.1f}" y="{pt + 16}" class="shade-label">3분기</text>')
    for i in range(5):
        t = vmax * i / 4
        y = pt + ih - t / vmax * ih
        s.append(f'<line x1="{pl}" x2="{w - pr}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
        s.append(f'<text x="{pl - 10}" y="{y + 4:.1f}" class="tick" text-anchor="end">{fmt(t)}</text>')
    for i, lab in enumerate(labels):
        cx = pl + slot * i + slot / 2
        for j, (v, cls) in enumerate(((a[i], "s1"), (b[i], "s2"))):
            x = cx - bw - 1 + j * (bw + 2)
            bh = v / vmax * ih
            y = pt + ih - bh
            r = 3
            path = (f"M{x:.1f},{pt + ih:.1f} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} "
                    f"H{x + bw - r:.1f} Q{x + bw:.1f},{y:.1f} {x + bw:.1f},{y + r:.1f} V{pt + ih:.1f} Z")
            s.append(f'<path d="{path}" class="bar {cls}"/>')
        s.append(f'<text x="{cx:.1f}" y="{pt + ih + 28}" class="tick" text-anchor="middle">{lab}</text>')
        s.append(f'<rect class="hit col" x="{pl + slot * i:.1f}" y="{pt}" width="{slot:.1f}" height="{ih}" '
                 f'data-tip="{lab} — {names[0]} {fmt(a[i])}명 · {names[1]} {fmt(b[i])}명"/>')
    # 3분기 마지막 막대만 직접 라벨
    cx = pl + slot * (n - 1) + slot / 2
    for j, v in enumerate((a[-1], b[-1])):
        x = cx - bw - 1 + j * (bw + 2) + bw / 2
        y = pt + ih - v / vmax * ih
        s.append(f'<text x="{x:.1f}" y="{y - 8:.1f}" class="val" text-anchor="middle">{fmt(v)}</text>')
    s.append(f'<line x1="{pl}" x2="{w - pr}" y1="{pt + ih}" y2="{pt + ih}" class="axis"/>')
    s.append("</svg>")
    return "".join(s)


months = [f"{r['mon']}월" for r in rows]
q3m = rows[6:]
aug = rows[7]

# ---------- 슬라이드 ----------
slides = []


def slide(title, body, kicker="", cls=""):
    slides.append((title, body, kicker, cls))


slide("", f"""
<div class="cover">
  <div class="kicker">2026 · Quarterly Business Review</div>
  <h1>3분기 실적 리뷰</h1>
  <p class="sub">2026년 7월 – 9월 · 매출 · 고객 · 마케팅 효율</p>
  <p class="meta">기준 자료: 04_분기실적.csv (2026년 1–9월 월별 실적) · 금액 단위 만원</p>
</div>""", cls="cover-slide")

kpi = [
    ("분기 매출", eok(q3["rev"]), sgn(pct(q3["rev"], q2["rev"])), "직전 분기 대비"),
    ("신규 고객", f"{fmt(q3['new'])}명", sgn(pct(q3["new"], q2["new"])), "직전 분기 대비"),
    ("9월 말 활성 고객", f"{fmt(q3['active'])}명", sgn(pct(q3["active"], q2["active"])), "6월 말 대비"),
    ("마케팅비", eok(q3["mkt"]), sgn(pct(q3["mkt"], q2["mkt"])), "직전 분기 대비"),
]
tiles = "".join(
    f'<div class="tile"><div class="tl">{a}</div><div class="tv">{b}</div>'
    f'<div class="td"><b>{c}</b> {d}</div></div>' for a, b, c, d in kpi)
slide("3분기 한눈에 보기", f"""
<div class="tiles">{tiles}</div>
<ul class="points">
  <li>매출 <b>{eok(q3['rev'])}</b>으로 3개 분기 연속 성장, 9월 월매출 <b>{fmt(rows[8]['rev'])}만원</b>으로 연중 최고</li>
  <li>신규 고객 {fmt(q3['new'])}명으로 분기 최대 — 활성 고객이 분기 동안 <b>{fmt(q3['active'] - q2['active'])}명</b> 순증</li>
  <li>다만 고객 증가율({sgn(pct(q3['active'], q2['active']))})에 비해 매출 증가율({sgn(pct(q3['rev'], q2['rev']))})이 낮아 <b>고객당 매출은 하락</b> 추세</li>
</ul>""", "Executive Summary")

slide("분기 매출: 3분기 연속 성장, 성장 폭은 둔화", f"""
<div class="row">
  <div class="col-chart">{bar_chart([q['name'] for q in Q], [q['rev'] for q in Q], {2}, '만원', 32000, w=640, h=420)}</div>
  <div class="col-text">
    <div class="big">{sgn(pct(q3['rev'], q2['rev']))}</div>
    <div class="cap">3분기 매출 성장률 (QoQ)</div>
    <ul class="points sm">
      <li>(만원) 1분기 {fmt(q1['rev'])} → 2분기 {fmt(q2['rev'])} → 3분기 <b>{fmt(q3['rev'])}</b></li>
      <li>2분기 성장률 {sgn(pct(q2['rev'], q1['rev']))} 대비 성장 폭 <b>{pct(q2['rev'], q1['rev']) - pct(q3['rev'], q2['rev']):.1f}%p 축소</b></li>
      <li>1–9월 누적 매출 <b>{eok(sum(q['rev'] for q in Q))}</b></li>
    </ul>
  </div>
</div>""", "매출")

slide("월별 매출: 8월 일시 하락 후 9월 최고치", f"""
{line_chart(months, [('매출', [r['rev'] for r in rows], 's1')], '만원', 7000, 11000, h=400,
            annotate=(7, f"8월 {sgn(pct(aug['rev'], rows[6]['rev']))} · 해지 {aug['churn']}명(연중 최다)"), shade_from=6)}
<p class="foot">8월 매출은 전월 대비 {fmt(rows[6]['rev'] - aug['rev'])}만원 감소했고, 같은 달 해지 고객이 {aug['churn']}명으로 1–9월 중 가장 많았습니다. 9월에는 {fmt(rows[8]['rev'])}만원으로 반등.</p>
""", "매출")

slide("고객 유입·이탈: 신규는 늘고, 해지는 8월에 튐", f"""
<div class="legend"><span><i class="sw s1"></i>신규 고객</span><span><i class="sw s2"></i>해지 고객</span></div>
{grouped_bars(months, [r['new'] for r in rows], [r['churn'] for r in rows], ('신규', '해지'), h=330, vmax=480, shade_from=6)}
<table class="mini">
  <tr><th></th>{''.join(f'<th>{q["name"]}</th>' for q in Q)}</tr>
  <tr><td>신규 고객</td>{''.join(f'<td>{fmt(q["new"])}</td>' for q in Q)}</tr>
  <tr><td>해지 고객</td>{''.join(f'<td>{fmt(q["churn"])}</td>' for q in Q)}</tr>
  <tr><td>순증</td>{''.join(f'<td><b>{fmt(q["new"] - q["churn"])}</b></td>' for q in Q)}</tr>
</table>""", "고객")

rates = [r["churn_rate"] * 100 if r["churn_rate"] else None for r in rows]
slide("활성 고객은 빠르게 늘었지만, 고객당 매출은 감소", f"""
<div class="row two">
  <div>
    <h3>월말 활성 고객 (명)</h3>
    {line_chart(months, [('활성 고객', [r['active'] for r in rows], 's1')], '명', 4000, 6500, w=600, h=400, nticks=5)}
  </div>
  <div>
    <h3>활성 고객 1인당 월매출 (만원)</h3>
    {line_chart(months, [('1인당 매출', [r['arpu'] for r in rows], 's2')], '만원', 1.6, 2.1, w=600, h=400, fmtv=lambda v: f'{v:.2f}', nticks=5)}
  </div>
</div>
<p class="foot">1인당 월매출 = 월매출 ÷ 월말 활성 고객. 3월 {rows[2]['arpu']:.2f} → 6월 {rows[5]['arpu']:.2f} → 9월 <b>{rows[8]['arpu']:.2f}만원</b>.
월 해지율(해지 ÷ 전월말 활성)은 3분기 {', '.join(f'{r["mon"]}월 {r["churn_rate"] * 100:.2f}%' for r in q3m)}.</p>
""", "고객")

slide("마케팅 효율: 획득 비용은 안정적", f"""
<table class="big-table">
  <tr><th>지표</th>{''.join(f'<th>{q["name"]}</th>' for q in Q)}<th>3분기 QoQ</th></tr>
  <tr><td>마케팅비 (만원)</td>{''.join(f'<td>{fmt(q["mkt"])}</td>' for q in Q)}<td>{sgn(pct(q3['mkt'], q2['mkt']))}</td></tr>
  <tr><td>신규 고객 (명)</td>{''.join(f'<td>{fmt(q["new"])}</td>' for q in Q)}<td>{sgn(pct(q3['new'], q2['new']))}</td></tr>
  <tr class="hl"><td>신규 1명당 마케팅비 (만원)</td>{''.join(f'<td>{q["cac"]:.2f}</td>' for q in Q)}<td>{sgn(pct(q3['cac'], q2['cac']))}</td></tr>
  <tr><td>마케팅비 1만원당 매출 (만원)</td>{''.join(f'<td>{q["roas"]:.2f}</td>' for q in Q)}<td>{sgn(pct(q3['roas'], q2['roas']))}</td></tr>
</table>
<ul class="points sm">
  <li>마케팅비를 {sgn(pct(q3['mkt'], q2['mkt']))} 늘렸고 신규 고객은 {sgn(pct(q3['new'], q2['new']))} 늘어 <b>신규 1명당 비용은 {q3['cac']:.2f}만원으로 소폭 개선</b></li>
  <li>반면 고객당 매출 하락으로 마케팅비 대비 매출은 {q2['roas']:.2f} → {q3['roas']:.2f}로 낮아짐</li>
</ul>""", "마케팅")

slide("시사점과 4분기 점검 과제", f"""
<div class="cards">
  <div class="card"><div class="cn">01</div><h3>고객당 매출 하락 원인 확인</h3>
    <p>활성 고객은 6월 말 대비 {sgn(pct(q3['active'], q2['active']))}인데 매출은 {sgn(pct(q3['rev'], q2['rev']))}. 신규 고객의 요금제·구매 단가 구성을 확인할 필요</p></div>
  <div class="card"><div class="cn">02</div><h3>8월 해지 증가 원인 점검</h3>
    <p>8월 해지 {aug['churn']}명(해지율 {aug['churn_rate'] * 100:.2f}%)으로 연중 최다. 9월 {rows[8]['churn']}명으로 회복했으나 일회성 여부 확인 필요</p></div>
  <div class="card"><div class="cn">03</div><h3>마케팅 효율 유지</h3>
    <p>신규 1명당 비용 {q3['cac']:.2f}만원으로 안정적. 매출 기여 기준(1만원당 매출 {q3['roas']:.2f})도 함께 추적</p></div>
</div>
<p class="foot">※ 원인 해석은 월별 집계 수치만으로 판단할 수 없어 '확인 과제'로 정리했습니다.</p>
""", "Next Steps")

trs = "".join(
    f"<tr{' class=\"hl\"' if r['mon'] >= 7 else ''}><td>{r['m']}</td><td>{fmt(r['rev'])}</td><td>{fmt(r['new'])}</td>"
    f"<td>{fmt(r['churn'])}</td><td>{fmt(r['active'])}</td><td>{fmt(r['mkt'])}</td>"
    f"<td>{r['arpu']:.2f}</td><td>{'' if r['churn_rate'] is None else f'{r['churn_rate'] * 100:.2f}%'}</td></tr>"
    for r in rows)
slide("부록: 월별 원자료", f"""
<table class="data">
  <tr><th>월</th><th>매출(만원)</th><th>신규</th><th>해지</th><th>월말 활성</th><th>마케팅비(만원)</th><th>1인당 매출</th><th>해지율</th></tr>
  {trs}
</table>
<p class="foot">강조 행 = 3분기. 해지율 = 해지 ÷ 전월말 활성 (1월은 전월 자료 없음).</p>
""", "Appendix")

# ---------- HTML ----------
CSS = """
@page { size: 1280px 720px; margin: 0; }
* { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --surface: #fcfcfb; --bg: #e9e8e4; --ink: #0b0b0b; --ink2: #52514e; --muted: #8a8984;
  --grid: #e4e3df; --s1: #2a78d6; --s2: #eb6834; --base: #b9b8b2; --tint: #f1f5fb;
}
html, body { word-break: keep-all; background: var(--bg); font-family: "Pretendard", "Malgun Gothic", "Apple SD Gothic Neo", sans-serif; color: var(--ink); }
.slide { width: 1280px; height: 720px; margin: 24px auto; background: var(--surface); position: relative;
  padding: 56px 72px 48px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,.08); }
.kick { font-size: 15px; font-weight: 600; color: var(--s1); letter-spacing: .04em; text-transform: uppercase; }
h2 { font-size: 36px; font-weight: 700; letter-spacing: -.02em; margin: 6px 0 28px; }
h3 { font-size: 18px; font-weight: 600; color: var(--ink2); margin-bottom: 8px; }
.pg { position: absolute; right: 72px; bottom: 24px; font-size: 13px; color: var(--muted); }
.brand { position: absolute; left: 72px; bottom: 24px; font-size: 13px; color: var(--muted); }
.cover-slide { background: #0f2a4a; color: #fff; display: flex; align-items: center; }
.cover .kicker { font-size: 18px; letter-spacing: .08em; color: #9cc2f0; text-transform: uppercase; }
.cover h1 { font-size: 76px; font-weight: 800; letter-spacing: -.03em; margin: 18px 0 16px; }
.cover .sub { font-size: 26px; color: #d6e3f3; }
.cover .meta { margin-top: 64px; font-size: 15px; color: #8fa8c6; }
.cover-slide .pg, .cover-slide .brand { display: none; }
.tiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 40px; }
.tile { border: 1px solid var(--grid); border-radius: 12px; padding: 22px 24px; background: #fff; }
.tl { font-size: 16px; color: var(--ink2); }
.tv { font-size: 34px; font-weight: 700; margin: 10px 0 8px; letter-spacing: -.02em; }
.td { font-size: 15px; color: var(--ink2); } .td b { color: var(--ink); }
.points { list-style: none; } .points li { font-size: 22px; line-height: 1.5; padding: 10px 0 10px 28px; position: relative; color: var(--ink2); }
.points li::before { content: ""; position: absolute; left: 4px; top: 22px; width: 10px; height: 10px; border-radius: 50%; background: var(--s1); }
.points li b { color: var(--ink); }
.points.sm li { font-size: 19px; padding: 8px 0 8px 26px; } .points.sm li::before { top: 19px; }
.row { display: flex; gap: 48px; align-items: center; } .col-chart { flex: 0 0 640px; } .col-text { flex: 1; }
.row.two { gap: 40px; align-items: flex-start; } .row.two > div { flex: 1; }
.big { font-size: 72px; font-weight: 800; color: var(--s1); letter-spacing: -.03em; }
.cap { font-size: 17px; color: var(--ink2); margin-bottom: 20px; }
.chart { width: 100%; height: auto; display: block; font-family: inherit; }
.grid { stroke: var(--grid); stroke-width: 1; } .axis { stroke: var(--base); stroke-width: 1; }
.tick { font-size: 14px; fill: var(--muted); } .val { font-size: 15px; fill: var(--ink2); font-weight: 600; }
.val.strong { fill: var(--ink); font-weight: 700; font-size: 17px; }
.note { font-size: 15px; fill: var(--ink2); }
.bar { fill: var(--base); } .bar.hi, .bar.s1 { fill: var(--s1); } .bar.s2 { fill: var(--s2); }
.line { fill: none; stroke-width: 2.5; stroke-linejoin: round; } .line.s1 { stroke: var(--s1); } .line.s2 { stroke: var(--s2); }
.dot { stroke: var(--surface); stroke-width: 2; } .dot.s1 { fill: var(--s1); } .dot.s2 { fill: var(--s2); }
.shade { fill: var(--tint); } .shade-label { font-size: 13px; fill: var(--s1); font-weight: 600; }
.hit { cursor: default; } .col { fill: transparent; } .col:hover { fill: rgba(0,0,0,.035); }
.legend { display: flex; gap: 24px; font-size: 15px; color: var(--ink2); margin: -12px 0 4px; }
.sw { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 8px; vertical-align: -1px; }
.sw.s1 { background: var(--s1); } .sw.s2 { background: var(--s2); }
.foot { font-size: 16px; color: var(--ink2); line-height: 1.6; margin-top: 14px; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
th, td { text-align: right; padding: 10px 16px; border-bottom: 1px solid var(--grid); }
th:first-child, td:first-child { text-align: left; } th { color: var(--ink2); font-weight: 600; font-size: 15px; }
.mini { font-size: 15px; margin-top: 6px; } .mini td, .mini th { padding: 5px 16px; }
.big-table { font-size: 20px; margin-bottom: 28px; } .big-table td, .big-table th { padding: 14px 18px; }
tr.hl td { background: var(--tint); font-weight: 600; }
.data { font-size: 16px; } .data td, .data th { padding: 8px 14px; }
.cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.card { border: 1px solid var(--grid); border-radius: 12px; padding: 28px; background: #fff; min-height: 250px; }
.cn { font-size: 15px; font-weight: 700; color: var(--s1); margin-bottom: 14px; }
.card h3 { font-size: 23px; color: var(--ink); margin-bottom: 14px; } .card p { font-size: 18px; line-height: 1.6; color: var(--ink2); }
#tip { position: fixed; pointer-events: none; background: #1a1a19; color: #f0efec; font-size: 14px; padding: 7px 11px;
  border-radius: 6px; opacity: 0; transition: opacity .1s; white-space: nowrap; z-index: 9; }
@media print {
  html, body { background: none; }
  .slide { margin: 0; box-shadow: none; page-break-after: always; break-after: page; }
  #tip { display: none; }
}
"""

JS = """
const tip = document.getElementById('tip');
document.querySelectorAll('[data-tip]').forEach(el => {
  el.addEventListener('mousemove', e => { tip.textContent = el.dataset.tip; tip.style.opacity = 1;
    tip.style.left = (e.clientX + 14) + 'px'; tip.style.top = (e.clientY + 14) + 'px'; });
  el.addEventListener('mouseleave', () => tip.style.opacity = 0);
});
"""

parts = []
for i, (title, body, kicker, cls) in enumerate(slides, 1):
    head = f'<div class="kick">{kicker}</div><h2>{title}</h2>' if title else ""
    parts.append(f'<section class="slide {cls}">{head}{body}'
                 f'<div class="brand">2026년 3분기 실적 리뷰</div><div class="pg">{i} / {len(slides)}</div></section>')

doc = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>분기실적 — 2026년 3분기 실적 리뷰</title>
<style>{CSS}</style></head>
<body>
{''.join(parts)}
<div id="tip"></div>
<script>{JS}</script>
</body></html>"""

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(doc, encoding="utf-8")
print(f"wrote {OUT} ({len(slides)} slides)")
