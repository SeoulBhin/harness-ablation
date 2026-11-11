"""samples/04_분기실적.csv -> 분기실적/분기실적.html (PDF는 Edge headless로 인쇄)"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT.parent / "samples" / "04_분기실적.csv"

rows = []
with open(SRC, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        rows.append({
            "m": r["월"], "rev": int(r["매출_만원"]), "new": int(r["신규고객"]),
            "churn": int(r["해지고객"]), "active": int(r["월말_활성고객"]),
            "mkt": int(r["마케팅비_만원"]),
        })

# 월초 활성 = 전월 말 (1월은 역산: 말 - 신규 + 해지)
for i, r in enumerate(rows):
    r["start"] = rows[i - 1]["active"] if i else r["active"] - r["new"] + r["churn"]
    r["churn_rate"] = r["churn"] / r["start"] * 100
    r["arpu"] = r["rev"] / ((r["start"] + r["active"]) / 2)  # 만원/평균활성고객
    r["mon"] = int(r["m"][5:])

Q = {}
for q in (1, 2, 3):
    ms = rows[(q - 1) * 3: q * 3]
    Q[q] = {
        "rev": sum(r["rev"] for r in ms), "new": sum(r["new"] for r in ms),
        "churn": sum(r["churn"] for r in ms), "mkt": sum(r["mkt"] for r in ms),
        "end": ms[-1]["active"], "start": ms[0]["start"],
        "churn_rate": sum(r["churn_rate"] for r in ms) / 3,
        "arpu": sum(r["rev"] for r in ms) / sum((r["start"] + r["active"]) / 2 for r in ms),
    }
    Q[q]["net"] = Q[q]["end"] - Q[q]["start"]
    Q[q]["cac"] = Q[q]["mkt"] / Q[q]["new"]
    Q[q]["roas"] = Q[q]["rev"] / Q[q]["mkt"]

q3, q2 = Q[3], Q[2]
pct = lambda a, b: (a - b) / b * 100
eok = lambda man: f"{man / 10000:.2f}억"
sgn = lambda v, d=1: f"{'+' if v >= 0 else '−'}{abs(v):.{d}f}"

# ---------- SVG 차트 ----------
W, H = 1040, 380
PL, PR, PT, PB = 64, 24, 24, 44


def axis(ymax, ticks, fmt):
    out = []
    for t in ticks:
        y = PT + (H - PT - PB) * (1 - t / ymax)
        out.append(f'<line x1="{PL}" x2="{W-PR}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>'
                   f'<text x="{PL-10}" y="{y+4:.1f}" class="tick" text-anchor="end">{fmt(t)}</text>')
    return "".join(out)


def ypos(v, ymax):
    return PT + (H - PT - PB) * (1 - v / ymax)


def bar_revenue():
    ymax = 12000
    n = len(rows)
    slot = (W - PL - PR) / n
    bw = slot * 0.56
    s = [axis(ymax, range(0, 12001, 3000), lambda t: f"{t:,}")]
    for i, r in enumerate(rows):
        x = PL + slot * i + (slot - bw) / 2
        y = ypos(r["rev"], ymax)
        h = H - PB - y
        cls = "bar hl" if r["mon"] >= 7 else "bar mute"
        s.append(f'<g class="hit"><title>{r["mon"]}월 매출 {r["rev"]:,}만원</title>'
                 f'<rect x="{x-6:.1f}" y="{PT}" width="{bw+12:.1f}" height="{H-PT-PB}" fill="transparent"/>'
                 f'<path class="{cls}" d="M{x:.1f},{H-PB} V{y+4:.1f} q0,-4 4,-4 H{x+bw-4:.1f} q4,0 4,4 V{H-PB} Z"/></g>')
        if r["mon"] >= 7:
            s.append(f'<text x="{x+bw/2:.1f}" y="{y-8:.1f}" class="val" text-anchor="middle">{r["rev"]:,}</text>')
        s.append(f'<text x="{x+bw/2:.1f}" y="{H-PB+22}" class="tick" text-anchor="middle">{r["mon"]}월</text>')
    s.append(f'<line x1="{PL}" x2="{W-PR}" y1="{H-PB}" y2="{H-PB}" class="base"/>')
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="월별 매출 막대그래프">{"".join(s)}</svg>'


def bar_customers():
    ymax = 450
    n = len(rows)
    slot = (W - PL - PR) / n
    bw = slot * 0.3
    gap = 2
    s = [axis(ymax, range(0, 451, 150), lambda t: f"{t}")]
    for i, r in enumerate(rows):
        x0 = PL + slot * i + (slot - 2 * bw - gap) / 2
        for k, key, cls, lab in ((0, "new", "s1", "신규"), (1, "churn", "s2", "해지")):
            x = x0 + k * (bw + gap)
            y = ypos(r[key], ymax)
            s.append(f'<g class="hit"><title>{r["mon"]}월 {lab} {r[key]}명</title>'
                     f'<path class="bar {cls}" d="M{x:.1f},{H-PB} V{y+4:.1f} q0,-4 4,-4 H{x+bw-4:.1f} q4,0 4,4 V{H-PB} Z"/></g>')
        if r["mon"] == 8:
            y = ypos(r["churn"], ymax)
            s.append(f'<text x="{x0+bw*1.5+gap:.1f}" y="{y-8:.1f}" class="val" text-anchor="middle">{r["churn"]}</text>')
        if r["mon"] == 9:
            y = ypos(r["new"], ymax)
            s.append(f'<text x="{x0+bw/2:.1f}" y="{y-8:.1f}" class="val" text-anchor="middle">{r["new"]}</text>')
        s.append(f'<text x="{x0+bw+gap/2:.1f}" y="{H-PB+22}" class="tick" text-anchor="middle">{r["mon"]}월</text>')
    # 분기 구분선
    for q in (1, 2):
        x = PL + slot * 3 * q
        s.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{PT}" y2="{H-PB}" class="qdiv"/>')
    s.append(f'<line x1="{PL}" x2="{W-PR}" y1="{H-PB}" y2="{H-PB}" class="base"/>')
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="월별 신규·해지 고객">{"".join(s)}</svg>'


def line_active():
    ymin, ymax = 3000, 7000
    n = len(rows)
    xs = [PL + 30 + (W - PL - PR - 60) * i / (n - 1) for i in range(n)]
    yv = lambda v: PT + (H - PT - PB) * (1 - (v - ymin) / (ymax - ymin))
    s = []
    for t in range(3000, 7001, 1000):
        y = yv(t)
        s.append(f'<line x1="{PL}" x2="{W-PR}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>'
                 f'<text x="{PL-10}" y="{y+4:.1f}" class="tick" text-anchor="end">{t:,}</text>')
    # Q3 음영
    s.append(f'<rect x="{(xs[5]+xs[6])/2:.1f}" y="{PT}" width="{W-PR-(xs[5]+xs[6])/2:.1f}" height="{H-PT-PB}" class="band"/>'
             f'<text x="{W-PR-10}" y="{PT+18}" class="tick" text-anchor="end">3분기</text>')
    pts = " ".join(f"{x:.1f},{yv(r['active']):.1f}" for x, r in zip(xs, rows))
    s.append(f'<polyline points="{pts}" class="line"/>')
    for x, r in zip(xs, rows):
        y = yv(r["active"])
        s.append(f'<g class="hit"><title>{r["mon"]}월 말 활성고객 {r["active"]:,}명</title>'
                 f'<circle cx="{x:.1f}" cy="{y:.1f}" r="14" fill="transparent"/>'
                 f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" class="dot"/></g>')
        if r["mon"] in (1, 6, 9):
            s.append(f'<text x="{x:.1f}" y="{y-14:.1f}" class="val" text-anchor="middle">{r["active"]:,}</text>')
        s.append(f'<text x="{x:.1f}" y="{H-PB+22}" class="tick" text-anchor="middle">{r["mon"]}월</text>')
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="월말 활성고객 추이">{"".join(s)}</svg>'


def eff_table():
    head = "<tr><th>지표</th><th>1분기</th><th>2분기</th><th>3분기</th><th>전분기 대비</th></tr>"
    def row(name, key, fmt, better_low=False, diff_fmt=None):
        vals = [Q[q][key] for q in (1, 2, 3)]
        d = vals[2] - vals[1]
        dtxt = diff_fmt(d, vals[1]) if diff_fmt else f"{sgn(pct(vals[2], vals[1]))}%"
        good = (d < 0) if better_low else (d > 0)
        mark = "▲" if d > 0 else "▼"
        cls = "good" if good else "bad"
        return (f"<tr><td>{name}</td>" + "".join(f"<td>{fmt(v)}</td>" for v in vals)
                + f'<td class="{cls}">{mark} {dtxt}</td></tr>')
    pp = lambda d, _: f"{sgn(d, 2)}%p"
    body = "".join([
        row("마케팅비 (만원)", "mkt", lambda v: f"{v:,}", better_low=True),
        row("신규 1명당 획득비용 (만원)", "cac", lambda v: f"{v:.2f}", better_low=True),
        row("마케팅비 1원당 매출 (배)", "roas", lambda v: f"{v:.2f}"),
        row("월평균 해지율", "churn_rate", lambda v: f"{v:.2f}%", better_low=True, diff_fmt=pp),
        row("고객 1명당 월매출 (만원)", "arpu", lambda v: f"{v:.2f}"),
    ])
    return f'<table class="eff">{head}{body}</table>'


def data_table():
    head = ("<tr><th>월</th><th>매출(만원)</th><th>신규</th><th>해지</th><th>월말 활성</th>"
            "<th>마케팅비(만원)</th><th>해지율</th></tr>")
    body = "".join(
        f'<tr class="{"q3" if r["mon"] >= 7 else ""}"><td>{r["m"]}</td><td>{r["rev"]:,}</td><td>{r["new"]}</td>'
        f'<td>{r["churn"]}</td><td>{r["active"]:,}</td><td>{r["mkt"]:,}</td><td>{r["churn_rate"]:.2f}%</td></tr>'
        for r in rows)
    return f'<table class="data">{head}{body}</table>'


jul, aug, sep = rows[6], rows[7], rows[8]

kpis = [
    ("3분기 매출", eok(q3["rev"]), f"전분기 대비 {sgn(pct(q3['rev'], q2['rev']))}%", "good"),
    ("신규 고객", f"{q3['new']:,}명", f"전분기 대비 {sgn(pct(q3['new'], q2['new']))}%", "good"),
    ("9월 말 활성 고객", f"{q3['end']:,}명", f"분기 순증 {q3['net']:,}명 ({sgn(pct(q3['end'], q2['end']))}%)", "good"),
    ("해지 고객", f"{q3['churn']:,}명", f"전분기 대비 {sgn(pct(q3['churn'], q2['churn']))}%", "bad"),
]
kpi_html = "".join(
    f'<div class="kpi"><div class="kl">{a}</div><div class="kv">{b}</div><div class="kd {c}">{"▲" if "+" in d else "▼"} {d}</div></div>'
    for a, b, d, c in kpis)

slides = []
slides.append(f"""
<section class="slide title">
  <div class="eyebrow">2026년 3분기 (7–9월)</div>
  <h1>3분기 실적 리뷰</h1>
  <p class="sub">매출·고객·효율 지표 점검과 4분기 과제</p>
  <div class="foot">데이터: 04_분기실적.csv · 단위 별도 표기 없으면 만원</div>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="eyebrow">요약</div>
  <h2>매출 {eok(q3['rev'])}로 올해 분기 최고, 활성 고객 6천 명 돌파</h2>
  <div class="kpis">{kpi_html}</div>
  <ul class="points">
    <li>7월 월매출이 처음 1억 원을 넘었고, 9월 {sep['rev']:,}만원으로 연중 최고치</li>
    <li>신규 고객은 분기 기준 최다({q3['new']:,}명). 획득비용은 1명당 {q3['cac']:.2f}만원으로 소폭 개선</li>
    <li>다만 8월 해지가 {aug['churn']}명으로 연중 최다 — 같은 달 매출도 전월보다 {jul['rev']-aug['rev']:,}만원 감소</li>
  </ul>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="eyebrow">매출</div>
  <h2>3분기 매출 {eok(q3['rev'])}, 전분기보다 {sgn(pct(q3['rev'], q2['rev']))}%</h2>
  <p class="cap">월별 매출 (만원) · 진한 막대가 3분기</p>
  <div class="chart">{bar_revenue()}</div>
  <p class="note">8월만 전월 대비 감소({sgn(pct(aug['rev'], jul['rev']))}%)했고, 9월에 {sgn(pct(sep['rev'], aug['rev']))}% 반등했다. 성장 속도는 2분기(+{pct(q2['rev'], Q[1]['rev']):.1f}%)보다 다소 둔화.</p>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="eyebrow">고객 유입·이탈</div>
  <h2>신규는 늘었지만 8월 해지가 튀었다</h2>
  <div class="legend"><span><i class="sw s1"></i>신규 고객</span><span><i class="sw s2"></i>해지 고객</span><span class="muted">(명, 점선은 분기 경계)</span></div>
  <div class="chart">{bar_customers()}</div>
  <p class="note">8월 해지율 {aug['churn_rate']:.2f}% — 3분기 다른 달(7월 {jul['churn_rate']:.2f}%, 9월 {sep['churn_rate']:.2f}%)보다 높다. 9월에 정상 수준으로 돌아왔지만 원인은 이 데이터만으로는 알 수 없어 확인이 필요하다.</p>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="eyebrow">활성 고객</div>
  <h2>분기 순증 {q3['net']:,}명 — 올해 들어 가장 큰 폭</h2>
  <p class="cap">월말 활성 고객 수 (명)</p>
  <div class="chart">{line_active()}</div>
  <p class="note">분기 순증: 1분기 {Q[1]['net']:,} → 2분기 {Q[2]['net']:,} → 3분기 {Q[3]['net']:,}명. 연초 대비 활성 고객 {sgn(pct(sep['active'], rows[0]['start']), 0)}%.</p>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="eyebrow">효율</div>
  <h2>획득 효율은 유지, 고객 1명당 매출은 하락 추세</h2>
  {eff_table()}
  <ul class="points small">
    <li>마케팅비를 {sgn(pct(q3['mkt'], q2['mkt']))}% 늘렸고 신규도 {sgn(pct(q3['new'], q2['new']))}% 늘어 획득비용은 비슷한 수준</li>
    <li>고객 1명당 월매출은 분기마다 낮아지는 중 — 고객 수가 매출보다 빠르게 늘고 있다는 뜻</li>
    <li class="muted">고객 1명당 월매출 = 월매출 ÷ (월초+월말 활성)/2, 해지율 = 해지 ÷ 월초 활성</li>
  </ul>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="eyebrow">4분기 과제</div>
  <h2>성장은 유지하고, 이탈과 단가를 챙긴다</h2>
  <div class="cols">
    <div class="card"><h3>1. 8월 해지 원인 확인</h3><p>해지 {aug['churn']}명이 몰린 배경(가격·서비스 이슈·계절 요인 등)을 해지 사유 데이터로 확인하고 재발 방지책을 정한다.</p></div>
    <div class="card"><h3>2. 고객 1명당 매출 관리</h3><p>{Q[1]['arpu']:.2f} → {q3['arpu']:.2f}만원으로 하락 중. 신규 고객의 요금제 구성과 업셀 여지를 점검한다.</p></div>
    <div class="card"><h3>3. 획득 효율 유지</h3><p>마케팅비가 월 1,500만원 수준까지 올라왔다. 신규 1명당 {q3['cac']:.2f}만원 이하를 기준선으로 집행을 관리한다.</p></div>
  </div>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="eyebrow">부록</div>
  <h2>월별 원자료</h2>
  {data_table()}
  <p class="note">해지율은 월초 활성(전월 말) 기준으로 계산. 1월 월초 활성은 1월 말 − 신규 + 해지로 역산({rows[0]['start']:,}명).</p>
</section>""")

for i, s in enumerate(slides[1:], start=2):
    slides[i - 1] = s.replace("</section>", f'<div class="pno">{i} / {len(slides)}</div></section>')

CSS = """
@page { size: 1280px 720px; margin: 0; }
* { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#8a8984; --line:#e4e3df;
  --s1:#2a78d6; --s2:#eb6834; --mute:#c9d6e6; --good:#0a7d33; --bad:#c2372f;
}
html { background:#d9d9d6; }
body { font-family:"Pretendard","Malgun Gothic","Apple SD Gothic Neo",sans-serif; color:var(--ink);
  -webkit-print-color-adjust:exact; print-color-adjust:exact; }
.slide { width:1280px; height:720px; background:var(--surface); margin:24px auto; padding:56px 120px 48px;
  position:relative; overflow:hidden; box-shadow:0 2px 12px rgba(0,0,0,.12); page-break-after:always; break-after:page; }
@media print { html{background:none} .slide{ margin:0; box-shadow:none; } }
.eyebrow { font-size:15px; font-weight:700; color:var(--s1); letter-spacing:.04em; margin-bottom:10px; }
h1 { font-size:64px; font-weight:800; letter-spacing:-.02em; }
h2 { font-size:34px; font-weight:800; letter-spacing:-.01em; margin-bottom:22px; }
h3 { font-size:20px; margin-bottom:10px; }
.title { display:flex; flex-direction:column; justify-content:center; padding-left:120px;
  border-left:14px solid var(--s1); }
.title .sub { font-size:24px; color:var(--ink2); margin-top:16px; }
.title .foot { position:absolute; bottom:48px; font-size:14px; color:var(--muted); }
.pno { position:absolute; right:40px; bottom:24px; font-size:13px; color:var(--muted); }
.kpis { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:34px; }
.kpi { border:1px solid var(--line); border-radius:12px; padding:20px 22px; background:#fff; }
.kl { font-size:15px; color:var(--ink2); }
.kv { font-size:38px; font-weight:800; margin:6px 0; font-variant-numeric:tabular-nums; }
.kd { font-size:14px; font-weight:600; }
.good { color:var(--good); } .bad { color:var(--bad); } .muted { color:var(--muted); }
.points { list-style:none; font-size:21px; line-height:1.55; color:var(--ink2); }
.points li { padding-left:20px; position:relative; margin-bottom:10px; }
.points li::before { content:""; position:absolute; left:0; top:13px; width:7px; height:7px; border-radius:50%; background:var(--s1); }
.points.small { font-size:17px; margin-top:22px; }
.points li.muted::before { background:var(--line); }
.cap { font-size:15px; color:var(--ink2); margin-bottom:6px; }
.note { font-size:17px; color:var(--ink2); line-height:1.5; margin-top:10px; }
.chart svg { width:100%; height:auto; display:block; }
.legend { display:flex; gap:22px; font-size:15px; color:var(--ink2); margin-bottom:6px; align-items:center; }
.sw { display:inline-block; width:12px; height:12px; border-radius:3px; margin-right:6px; vertical-align:-1px; }
.sw.s1 { background:var(--s1); } .sw.s2 { background:var(--s2); }
svg .grid { stroke:var(--line); stroke-width:1; }
svg .base { stroke:var(--ink2); stroke-width:1; }
svg .qdiv { stroke:var(--muted); stroke-width:1; stroke-dasharray:4 4; }
svg .tick { font-size:14px; fill:var(--ink2); }
svg .val { font-size:15px; font-weight:700; fill:var(--ink); }
svg .bar.hl, svg .bar.s1 { fill:var(--s1); } svg .bar.mute { fill:var(--mute); } svg .bar.s2 { fill:var(--s2); }
svg .line { fill:none; stroke:var(--s1); stroke-width:2.5; stroke-linejoin:round; }
svg .dot { fill:var(--s1); stroke:var(--surface); stroke-width:2; }
svg .band { fill:#2a78d6; opacity:.06; }
svg .hit:hover .bar, svg .hit:hover .dot { opacity:.75; }
table { border-collapse:collapse; width:100%; font-variant-numeric:tabular-nums; }
th, td { padding:11px 14px; text-align:right; border-bottom:1px solid var(--line); }
th:first-child, td:first-child { text-align:left; }
th { font-size:14px; color:var(--ink2); font-weight:600; border-bottom:2px solid var(--ink2); }
.eff td { font-size:18px; } .eff td:nth-child(4) { font-weight:700; background:#f1f6fd; }
.data td { font-size:16px; padding:8px 14px; } .data tr.q3 td { background:#f1f6fd; font-weight:600; }
.cols { display:grid; grid-template-columns:repeat(3,1fr); gap:20px; margin-top:10px; }
.card { border:1px solid var(--line); border-top:5px solid var(--s1); border-radius:12px; padding:26px 24px; background:#fff;
  font-size:17px; line-height:1.6; color:var(--ink2); min-height:300px; }
.card h3 { color:var(--ink); }
"""

html = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>분기실적 — 2026년 3분기 실적 리뷰</title>
<meta name="viewport" content="width=1280"><style>{CSS}</style></head>
<body>{''.join(slides)}</body></html>"""

out = ROOT / "분기실적.html"
out.write_text(html, encoding="utf-8")
print("wrote", out)
for q in (1, 2, 3):
    print(q, {k: round(v, 3) for k, v in Q[q].items()})
