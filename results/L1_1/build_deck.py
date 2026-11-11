"""분기실적 덱 생성: samples/04_분기실적.csv -> 분기실적.html (PDF는 브라우저 headless 인쇄)."""
import csv
import html
import math
import pathlib

BASE = pathlib.Path(__file__).resolve().parent
SRC = BASE.parent / "samples" / "04_분기실적.csv"
OUT = BASE / "분기실적.html"

with open(SRC, encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

months = [r["월"] for r in rows]
mlabel = [f"{int(m[5:])}월" for m in months]
rev = [int(r["매출_만원"]) for r in rows]
new = [int(r["신규고객"]) for r in rows]
churn = [int(r["해지고객"]) for r in rows]
active = [int(r["월말_활성고객"]) for r in rows]
mkt = [int(r["마케팅비_만원"]) for r in rows]

start_active = active[0] - new[0] + churn[0]  # 1월 초 활성고객 (역산)
begin = [start_active] + active[:-1]
churn_rate = [c / b * 100 for c, b in zip(churn, begin)]  # 월 해지율 = 해지 / 월초 활성
arpu = [r / ((b + e) / 2) * 10000 for r, b, e in zip(rev, begin, active)]  # 원, 평균 활성 기준

Q = {1: [0, 1, 2], 2: [3, 4, 5], 3: [6, 7, 8]}


def qs(a, q):
    return sum(a[i] for i in Q[q])


q = {}
for k in (1, 2, 3):
    i0, i2 = Q[k][0], Q[k][-1]
    q[k] = dict(
        rev=qs(rev, k), new=qs(new, k), churn=qs(churn, k), mkt=qs(mkt, k),
        end=active[i2], begin=begin[i0],
        net=active[i2] - begin[i0],
        churn_rate=sum(churn_rate[i] for i in Q[k]) / 3,
        arpu=qs(rev, k) * 10000 / sum((begin[i] + active[i]) / 2 for i in Q[k]),
        cac=qs(mkt, k) * 10000 / qs(new, k),
        roas=qs(rev, k) / qs(mkt, k),
    )


def pct(a, b):
    return (a - b) / b * 100


def fp(x, d=1):
    return f"{x:+.{d}f}%"


def fn(x):
    return f"{x:,.0f}"


def won_to_man(x):
    return f"{x/10000:.2f}만원"


q3, q2, q1 = q[3], q[2], q[1]
print("Q1", q1)
print("Q2", q2)
print("Q3", q3)

# ---------------------------------------------------------------- SVG charts
C_BLUE = "#2a78d6"
C_BLUE_LT = "#86b6ef"
C_ORANGE = "#eb6834"
GRID = "#e4e3df"
INK2 = "#52514e"
INK3 = "#7a7974"
SURF = "#fcfcfb"


def nice_step(span, n=4):
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def ticks(lo, hi, n=4):
    s = nice_step(hi - lo, n)
    t0 = math.floor(lo / s) * s
    out = []
    v = t0
    while v <= hi + s * 0.999:
        out.append(round(v, 6))
        v += s
    return out


def bar_path(x, y, w, h, r=4):
    if h <= 0:
        return ""
    r = min(r, w / 2, h)
    return (f"M{x:.1f},{y+h:.1f} L{x:.1f},{y+r:.1f} Q{x:.1f},{y:.1f} {x+r:.1f},{y:.1f} "
            f"L{x+w-r:.1f},{y:.1f} Q{x+w:.1f},{y:.1f} {x+w:.1f},{y+r:.1f} L{x+w:.1f},{y+h:.1f} Z")


def frame(w, h, ml, mr, mt, mb, ytk, ymap, yfmt, labels, xc, band=None):
    """축·그리드·x 라벨·Q3 밴드."""
    parts = []
    if band:
        i0, i1, step = band
        x0 = xc(i0) - step / 2
        x1 = xc(i1) + step / 2
        parts.append(f'<rect x="{x0:.1f}" y="{mt-6}" width="{x1-x0:.1f}" height="{h-mt-mb+6}" fill="#f1f0ec" rx="6"/>')
        parts.append(f'<text x="{(x0+x1)/2:.1f}" y="{mt+8}" text-anchor="middle" class="band">3분기</text>')
    for t in ytk:
        y = ymap(t)
        parts.append(f'<line x1="{ml}" x2="{w-mr}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>')
        parts.append(f'<text x="{ml-10}" y="{y+4:.1f}" text-anchor="end" class="ax">{yfmt(t)}</text>')
    for i, lb in enumerate(labels):
        parts.append(f'<text x="{xc(i):.1f}" y="{h-mb+22}" text-anchor="middle" class="ax">{lb}</text>')
    return parts


def bar_chart(labels, series, colors, names, *, w=1100, h=420, yfmt=fn, vfmt=fn,
              label_idx=(), band=None, unit=""):
    ml, mr, mt, mb = 70, 20, 30, 40
    ymax = max(max(s) for s in series)
    ytk = ticks(0, ymax * 1.08)
    top = ytk[-1]
    ph = h - mt - mb
    ymap = lambda v: mt + ph * (1 - v / top)
    n = len(labels)
    step = (w - ml - mr) / n
    xc = lambda i: ml + step * (i + 0.5)
    parts = frame(w, h, ml, mr, mt, mb, ytk, ymap, yfmt, labels, xc,
                  band=(band[0], band[1], step) if band else None)
    k = len(series)
    group_w = step * 0.62
    gap = 2
    bw = (group_w - gap * (k - 1)) / k
    for si, s in enumerate(series):
        for i, v in enumerate(s):
            x = xc(i) - group_w / 2 + si * (bw + gap)
            y = ymap(v)
            col = colors[si][i] if isinstance(colors[si], list) else colors[si]
            tip = html.escape(f"{labels[i]} · {names[si]}: {vfmt(v)}{unit}")
            parts.append(f'<g class="hit"><title>{tip}</title>'
                         f'<rect x="{x-2:.1f}" y="{mt}" width="{bw+4:.1f}" height="{ph}" fill="transparent"/>'
                         f'<path d="{bar_path(x, y, bw, ymap(0)-y)}" fill="{col}"/></g>')
            if (si, i) in label_idx or i in label_idx:
                parts.append(f'<text x="{x+bw/2:.1f}" y="{y-8:.1f}" text-anchor="middle" class="val">{vfmt(v)}</text>')
    parts.append(f'<line x1="{ml}" x2="{w-mr}" y1="{ymap(0):.1f}" y2="{ymap(0):.1f}" stroke="{INK3}" stroke-width="1"/>')
    return f'<svg viewBox="0 0 {w} {h}" class="chart" role="img">{"".join(parts)}</svg>'


def line_chart(labels, values, color, *, w=1100, h=420, yfmt=fn, vfmt=fn, label_idx=(),
               band=None, lo=None, hi=None, unit="", name=""):
    ml, mr, mt, mb = 70, 30, 30, 40
    lo = min(values) if lo is None else lo
    hi = max(values) if hi is None else hi
    ytk = ticks(lo, hi)
    bot, top = ytk[0], ytk[-1]
    ph = h - mt - mb
    ymap = lambda v: mt + ph * (1 - (v - bot) / (top - bot))
    n = len(labels)
    step = (w - ml - mr) / n
    xc = lambda i: ml + step * (i + 0.5)
    parts = frame(w, h, ml, mr, mt, mb, ytk, ymap, yfmt, labels, xc,
                  band=(band[0], band[1], step) if band else None)
    pts = " ".join(f"{xc(i):.1f},{ymap(v):.1f}" for i, v in enumerate(values))
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>')
    for i, v in enumerate(values):
        tip = html.escape(f"{labels[i]} · {name}: {vfmt(v)}{unit}")
        parts.append(f'<g class="hit"><title>{tip}</title>'
                     f'<rect x="{xc(i)-step/2:.1f}" y="{mt}" width="{step:.1f}" height="{ph}" fill="transparent"/>'
                     f'<circle cx="{xc(i):.1f}" cy="{ymap(v):.1f}" r="5" fill="{color}" stroke="{SURF}" stroke-width="2"/></g>')
        if i in label_idx:
            parts.append(f'<text x="{xc(i):.1f}" y="{ymap(v)-14:.1f}" text-anchor="middle" class="val">{vfmt(v)}</text>')
    return f'<svg viewBox="0 0 {w} {h}" class="chart" role="img">{"".join(parts)}</svg>'


# ---------------------------------------------------------------- slides
def kpi(label, value, delta, note="", tone=""):
    return (f'<div class="kpi"><div class="kl">{label}</div><div class="kv">{value}</div>'
            f'<div class="kd {tone}">{delta}</div><div class="kn">{note}</div></div>')


def arrow(x, good_when_up=True):
    up = x >= 0
    good = up == good_when_up
    sym = "▲" if up else "▼"
    return f'{sym} {abs(x):.1f}%', ("good" if good else "bad")


def slide(title, body, kicker="", num=None):
    k = f'<div class="kicker">{kicker}</div>' if kicker else ""
    pg = f'<div class="pg">{num}</div>' if num else ""
    return f'<section class="slide">{k}<h2>{title}</h2>{body}{pg}<div class="foot">2026년 3분기 실적 리뷰</div></section>'


slides = []

# 1. 표지
slides.append(f'''<section class="slide cover">
  <div class="cover-k">QUARTERLY BUSINESS REVIEW</div>
  <h1>2026년 3분기 실적 리뷰</h1>
  <p class="sub">매출 · 고객 · 마케팅 효율 (기간: 2026년 7–9월, 비교: 1–2분기)</p>
  <div class="cover-meta">데이터 출처: 04_분기실적.csv (월별 집계) · 금액 단위: 만원</div>
</section>''')

# 2. 요약
d_rev, t_rev = arrow(pct(q3['rev'], q2['rev']))
d_new, t_new = arrow(pct(q3['new'], q2['new']))
d_act, t_act = arrow(pct(q3['end'], q2['end']))
d_arpu, t_arpu = arrow(pct(q3['arpu'], q2['arpu']))
body = f'''<div class="kpis">
  {kpi("3분기 매출", fn(q3['rev']) + '<small>만원</small>', d_rev + ' 전분기 대비', f"2분기 {fn(q2['rev'])}만원", t_rev)}
  {kpi("신규 고객", fn(q3['new']) + '<small>명</small>', d_new + ' 전분기 대비', f"2분기 {fn(q2['new'])}명", t_new)}
  {kpi("9월 말 활성 고객", fn(q3['end']) + '<small>명</small>', d_act + ' 전분기 말 대비', f"분기 순증 +{fn(q3['net'])}명", t_act)}
  {kpi("고객당 월매출", won_to_man(q3['arpu']).replace('만원', '<small>만원</small>'), d_arpu + ' 전분기 대비', f"2분기 {won_to_man(q2['arpu'])}", t_arpu)}
</div>
<ul class="msgs">
  <li><b>성장 지속:</b> 매출 {fn(q3['rev'])}만원으로 3개 분기 연속 증가, 7월에 처음으로 월매출 1억원을 넘겼습니다.</li>
  <li><b>고객 기반 확대:</b> 신규 {fn(q3['new'])}명으로 분기 최대, 활성 고객은 6,000명대에 진입했습니다.</li>
  <li><b>점검 필요:</b> 매출 증가율({fp(pct(q3['rev'], q2['rev']))})이 고객 증가율({fp(pct(q3['end'], q2['end']))})에 못 미쳐 고객당 매출이 하락했고, 8월 해지가 {churn[7]}명으로 연중 최고였습니다.</li>
</ul>'''
slides.append(slide("요약: 외형은 커졌고, 고객당 매출은 낮아졌다", body, "EXECUTIVE SUMMARY"))

# 3. 매출 추이
colors = [[C_BLUE if i >= 6 else C_BLUE_LT for i in range(9)]]
ch = bar_chart(mlabel, [rev], colors, ["매출"], yfmt=fn, unit="만원", label_idx=(0, 5, 6, 7, 8), band=(6, 8), h=400)
qrow = "".join(
    f'<div class="qcell{" on" if k == 3 else ""}"><span>{k}분기</span><b>{fn(q[k]["rev"])}</b>'
    f'<em>{fp(pct(q[k]["rev"], q[k-1]["rev"])) + " QoQ" if k > 1 else "기준"}</em></div>' for k in (1, 2, 3))
body = f'''<div class="cap">월별 매출 (만원)</div>{ch}<div class="qrow">{qrow}</div>
<p class="note">8월은 전월 대비 {abs(pct(rev[7], rev[6])):.1f}% 감소했으나 9월 {fn(rev[8])}만원으로 연중 최고를 기록. 분기 성장률은 2분기 {fp(pct(q2['rev'], q1['rev']))} → 3분기 {fp(pct(q3['rev'], q2['rev']))}로 둔화.</p>'''
slides.append(slide(f"매출: 3분기 {fn(q3['rev'])}만원, 전분기 대비 {fp(pct(q3['rev'], q2['rev']))}", body, "REVENUE", 3))

# 4. 신규 vs 해지
ch = bar_chart(mlabel, [new, churn], [C_BLUE, C_ORANGE], ["신규 고객", "해지 고객"], unit="명",
               label_idx={(0, 8), (1, 7), (0, 6), (1, 8), (1, 6), (0, 7)}, band=(6, 8), h=380)
legend = (f'<div class="legend"><span><i style="background:{C_BLUE}"></i>신규 고객</span>'
          f'<span><i style="background:{C_ORANGE}"></i>해지 고객</span></div>')
body = f'''<div class="cap">월별 신규·해지 고객 (명)</div>{legend}{ch}
<div class="two">
  <p class="note"><b>신규</b> 분기 {fn(q3['new'])}명 ({fp(pct(q3['new'], q2['new']))}). 7월 {new[6]}명, 9월 {new[8]}명으로 월 최고치를 연달아 경신.</p>
  <p class="note"><b>해지</b> 분기 {fn(q3['churn'])}명 ({fp(pct(q3['churn'], q2['churn']))}). 8월 {churn[7]}명은 1–7월 평균({sum(churn[:7])/7:.0f}명)보다 {churn[7]-sum(churn[:7])/7:.0f}명 많음 — 원인 확인 필요.</p>
</div>'''
slides.append(slide("고객 유입: 신규는 분기 최대, 8월 해지가 튀었다", body, "CUSTOMERS", 4))

# 5. 활성 고객 & 해지율 (두 차트로 분리 — 이중축 금지)
ch1 = line_chart(mlabel, active, C_BLUE, w=540, h=360, lo=3500, hi=6500, label_idx=(0, 5, 8), band=(6, 8), unit="명", name="월말 활성 고객")
ch2 = line_chart(mlabel, churn_rate, C_ORANGE, w=540, h=360, lo=1.5, hi=2.5, yfmt=lambda v: f"{v:.2f}%",
                 vfmt=lambda v: f"{v:.2f}%", label_idx=(0, 7, 8), band=(6, 8), name="월 해지율")
body = f'''<div class="two">
  <div><div class="cap">월말 활성 고객 (명)</div>{ch1}
    <p class="note">분기 순증 {fn(q1['net'])} → {fn(q2['net'])} → <b>{fn(q3['net'])}명</b>. 9월 말 {fn(active[8])}명 (연초 대비 {fp(pct(active[8], start_active), 0)}).</p></div>
  <div><div class="cap">월 해지율 (해지 ÷ 월초 활성)</div>{ch2}
    <p class="note">분기 평균 {q1['churn_rate']:.2f}% → {q2['churn_rate']:.2f}% → <b>{q3['churn_rate']:.2f}%</b>. 추세는 개선 중이나 8월만 {churn_rate[7]:.2f}%로 반등.</p></div>
</div>'''
slides.append(slide("활성 고객: 분기 순증 875명, 해지율은 대체로 안정", body, "RETENTION", 5))

# 6. 마케팅 효율
d1 = pct(q3['mkt'], q2['mkt'])
body = f'''<div class="kpis three">
  {kpi("3분기 마케팅비", fn(q3['mkt']) + '<small>만원</small>', arrow(d1, False)[0] + ' 전분기 대비', f"2분기 {fn(q2['mkt'])}만원", "")}
  {kpi("신규 1명당 마케팅비", won_to_man(q3['cac']).replace('만원', '<small>만원</small>'), arrow(pct(q3['cac'], q2['cac']), False)[0] + ' 전분기 대비', f"2분기 {won_to_man(q2['cac'])}", arrow(pct(q3['cac'], q2['cac']), False)[1])}
  {kpi("마케팅비 1원당 매출", f"{q3['roas']:.2f}<small>원</small>", arrow(pct(q3['roas'], q2['roas']))[0] + ' 전분기 대비', f"2분기 {q2['roas']:.2f}원", arrow(pct(q3['roas'], q2['roas']))[1])}
</div>
<table class="tbl">
  <thead><tr><th></th><th>1분기</th><th>2분기</th><th class="on">3분기</th></tr></thead>
  <tbody>
    <tr><td>마케팅비 (만원)</td>{''.join(f'<td{" class=on" if k==3 else ""}>{fn(q[k]["mkt"])}</td>' for k in (1,2,3))}</tr>
    <tr><td>신규 고객 (명)</td>{''.join(f'<td{" class=on" if k==3 else ""}>{fn(q[k]["new"])}</td>' for k in (1,2,3))}</tr>
    <tr><td>신규 1명당 마케팅비</td>{''.join(f'<td{" class=on" if k==3 else ""}>{won_to_man(q[k]["cac"])}</td>' for k in (1,2,3))}</tr>
    <tr><td>마케팅비 1원당 매출</td>{''.join(f'<td{" class=on" if k==3 else ""}>{q[k]["roas"]:.2f}원</td>' for k in (1,2,3))}</tr>
  </tbody>
</table>
<p class="note">신규 유치 단가는 3개 분기 동안 3.7~3.8만원대로 안정적 — 마케팅비 증액({fp(d1)})이 신규 증가({fp(pct(q3['new'], q2['new']))})로 비례해 이어졌습니다. 반면 매출 대비 효율은 고객당 매출 하락 영향으로 낮아졌습니다.</p>'''
slides.append(slide("마케팅: 유치 단가는 유지, 매출 효율은 하락", body, "EFFICIENCY", 6))

# 7. ARPU
ch = line_chart(mlabel, arpu, C_BLUE, h=360, lo=16000, hi=21000, yfmt=lambda v: f"{v/10000:.1f}만", vfmt=won_to_man,
                label_idx=(0, 2, 7, 8), band=(6, 8), name="고객당 월매출")
body = f'''<div class="cap">고객당 월매출 (월매출 ÷ 월평균 활성 고객)</div>{ch}
<p class="note">분기 평균 {won_to_man(q1['arpu'])} → {won_to_man(q2['arpu'])} → <b>{won_to_man(q3['arpu'])}</b> ({fp(pct(q3['arpu'], q2['arpu']))} QoQ). 신규 고객이 많을수록 저가 요금제·체험 비중이 커졌을 가능성이 있으나 이 데이터로는 판단할 수 없어, 요금제·코호트별 매출 확인이 필요합니다.</p>'''
slides.append(slide("고객당 매출: 3월 이후 하락 추세", body, "WATCH POINT", 7))

# 8. 분기 비교표
def row(label, key, f, good_up=True):
    cells = "".join(f'<td{" class=on" if k==3 else ""}>{f(q[k][key])}</td>' for k in (1, 2, 3))
    d = pct(q3[key], q2[key])
    s, tone = arrow(d, good_up)
    return f'<tr><td>{label}</td>{cells}<td class="{tone}">{s}</td></tr>'

body = f'''<table class="tbl big">
  <thead><tr><th>지표</th><th>1분기</th><th>2분기</th><th class="on">3분기</th><th>QoQ</th></tr></thead>
  <tbody>
    {row("매출 (만원)", "rev", fn)}
    {row("신규 고객 (명)", "new", fn)}
    {row("해지 고객 (명)", "churn", fn, False)}
    {row("분기 순증 (명)", "net", fn)}
    {row("분기 말 활성 고객 (명)", "end", fn)}
    {row("평균 월 해지율", "churn_rate", lambda v: f"{v:.2f}%", False)}
    {row("고객당 월매출", "arpu", won_to_man)}
    {row("마케팅비 (만원)", "mkt", fn, False)}
    {row("신규 1명당 마케팅비", "cac", won_to_man, False)}
  </tbody>
</table>
<p class="note">QoQ = 3분기 ÷ 2분기. ▲▼ 색상은 지표 성격 기준(비용·해지는 감소가 긍정). 해지율·고객당 매출은 1월 초 활성 고객 {fn(start_active)}명(1월 말 활성 − 신규 + 해지로 역산)을 기준으로 계산.</p>'''
slides.append(slide("분기 비교 한눈에 보기", body, "APPENDIX · SCORECARD", 8))

# 9. 시사점
body = f'''<div class="cards">
  <div class="card"><div class="ct">잘한 점</div><ul>
    <li>매출 {fp(pct(q3['rev'], q2['rev']))}, 3개 분기 연속 성장</li>
    <li>신규 {fn(q3['new'])}명으로 분기 최대</li>
    <li>신규 1명당 마케팅비 {won_to_man(q3['cac'])}로 유지</li></ul></div>
  <div class="card warn"><div class="ct">우려 사항</div><ul>
    <li>고객당 월매출 {fp(pct(q3['arpu'], q2['arpu']))} — 매출 성장이 고객 성장을 못 따라감</li>
    <li>8월 해지 {churn[7]}명 급증(해지율 {churn_rate[7]:.2f}%)</li>
    <li>매출 성장률 둔화 ({fp(pct(q2['rev'], q1['rev']))} → {fp(pct(q3['rev'], q2['rev']))})</li></ul></div>
  <div class="card next"><div class="ct">4분기 확인·실행 제안</div><ul>
    <li>요금제·코호트별 매출 분해로 고객당 매출 하락 원인 규명</li>
    <li>8월 해지 고객 사유 조사 (일회성 여부 판단)</li>
    <li>신규 유입 고객의 업셀·유료 전환 지표 추가 관리</li></ul></div>
</div>'''
slides.append(slide("시사점과 4분기 과제", body, "NEXT STEPS", 9))

# 2번 슬라이드 번호
slides[1] = slides[1].replace('<div class="foot">', '<div class="pg">2</div><div class="foot">', 1)

CSS = """
@page { size: 1280px 720px; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; background: #d9d8d3; }
body { font-family: "Pretendard", "Malgun Gothic", "Apple SD Gothic Neo", sans-serif; color: #0b0b0b;
       -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.slide { width: 1280px; height: 720px; margin: 24px auto; background: #fcfcfb; position: relative;
         padding: 52px 72px 60px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,.12); }
.kicker { font-size: 13px; letter-spacing: .14em; color: #2a78d6; font-weight: 700; }
h2 { font-size: 32px; margin: 8px 0 22px; letter-spacing: -.02em; }
.foot { position: absolute; left: 72px; bottom: 24px; font-size: 12px; color: #7a7974; }
.pg { position: absolute; right: 72px; bottom: 24px; font-size: 12px; color: #7a7974; }
.cover { display: flex; flex-direction: column; justify-content: center; padding-left: 96px;
         background: linear-gradient(135deg, #0d366b 0%, #1c5cab 100%); color: #fff; }
.cover-k { letter-spacing: .2em; font-size: 15px; opacity: .8; }
.cover h1 { font-size: 64px; margin: 14px 0 12px; letter-spacing: -.03em; }
.cover .sub { font-size: 22px; opacity: .92; margin: 0; }
.cover-meta { position: absolute; bottom: 48px; left: 96px; font-size: 14px; opacity: .7; }
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; margin-bottom: 30px; }
.kpis.three { grid-template-columns: repeat(3, 1fr); margin-bottom: 22px; }
.kpi { background: #f3f2ee; border-radius: 12px; padding: 20px 22px; }
.kl { font-size: 15px; color: #52514e; }
.kv { font-size: 38px; font-weight: 800; margin: 6px 0 4px; letter-spacing: -.02em; }
.kv small { font-size: 17px; font-weight: 600; margin-left: 3px; color: #52514e; }
.kd { font-size: 15px; font-weight: 700; color: #52514e; }
.kd.good, td.good { color: #1a7f37; } .kd.bad, td.bad { color: #c4372f; }
.kn { font-size: 13px; color: #7a7974; margin-top: 4px; }
.msgs { margin: 0; padding-left: 22px; font-size: 20px; line-height: 1.7; }
.msgs li { margin-bottom: 6px; }
.cap { font-size: 15px; color: #52514e; font-weight: 600; margin-bottom: 4px; }
.chart { width: 100%; height: auto; display: block; }
.chart .ax { font-size: 13px; fill: #52514e; }
.chart .val { font-size: 14px; font-weight: 700; fill: #0b0b0b; }
.chart .band { font-size: 13px; fill: #7a7974; font-weight: 700; }
.chart .hit:hover path, .chart .hit:hover circle { opacity: .75; }
.qrow { display: flex; gap: 14px; margin-top: 6px; }
.qcell { flex: 1; background: #f3f2ee; border-radius: 10px; padding: 10px 16px; display: flex; gap: 12px; align-items: baseline; }
.qcell span { color: #52514e; font-size: 14px; } .qcell b { font-size: 22px; } .qcell em { font-style: normal; font-size: 14px; color: #52514e; margin-left: auto; }
.qcell.on { background: #e3eefc; }
.note { font-size: 16px; line-height: 1.6; color: #2c2b29; margin: 12px 0 0; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 36px; }
.legend { display: flex; gap: 22px; font-size: 14px; color: #52514e; margin: 2px 0 -6px; }
.legend i { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }
.tbl { width: 100%; border-collapse: collapse; font-size: 16px; }
.tbl th, .tbl td { padding: 9px 14px; text-align: right; border-bottom: 1px solid #e4e3df; }
.tbl th:first-child, .tbl td:first-child { text-align: left; color: #2c2b29; }
.tbl th { color: #52514e; font-weight: 600; font-size: 14px; }
.tbl .on { background: #eef4fd; font-weight: 700; }
.tbl.big { font-size: 17px; } .tbl.big td { padding: 10px 16px; }
.cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
.card { background: #f3f2ee; border-radius: 14px; padding: 24px 24px; border-top: 5px solid #1a7f37; min-height: 400px; }
.card.warn { border-top-color: #c4372f; } .card.next { border-top-color: #2a78d6; }
.ct { font-size: 21px; font-weight: 800; margin-bottom: 12px; }
.card ul { margin: 0; padding-left: 20px; font-size: 17px; line-height: 1.65; } .card li { margin-bottom: 12px; }
@media print {
  html, body { background: #fcfcfb; }
  .slide { margin: 0; box-shadow: none; page-break-after: always; break-after: page; }
  .slide:last-child { page-break-after: auto; break-after: auto; }
}
"""

doc = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>분기실적 — 2026년 3분기 실적 리뷰</title>
<meta name="viewport" content="width=1280">
<style>{CSS}</style></head>
<body>
{chr(10).join(slides)}
</body></html>"""
OUT.write_text(doc, encoding="utf-8")
print("wrote", OUT)
