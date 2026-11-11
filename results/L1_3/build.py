"""분기실적 덱 생성: samples/04_분기실적.csv -> 분기실적.html (PDF는 Chrome headless로 인쇄)."""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV = ROOT.parent / "samples" / "04_분기실적.csv"

rows = []
with open(CSV, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        rows.append({
            "m": r["월"], "rev": int(r["매출_만원"]), "new": int(r["신규고객"]),
            "churn": int(r["해지고객"]), "active": int(r["월말_활성고객"]),
            "mkt": int(r["마케팅비_만원"]),
        })

# 월초 활성 = 전월 말 활성 (1월은 역산: 월말 - 신규 + 해지)
for i, r in enumerate(rows):
    r["start"] = rows[i - 1]["active"] if i else r["active"] - r["new"] + r["churn"]
    r["churn_rate"] = r["churn"] / r["start"]
    r["avg_active"] = (r["start"] + r["active"]) / 2
    r["label"] = f"{int(r['m'][5:])}월"

# 데이터 정합성: 월말 활성 = 월초 + 신규 - 해지
for r in rows[1:]:
    assert r["start"] + r["new"] - r["churn"] == r["active"], r["m"]

Q = {}
for qi in range(3):
    ms = rows[qi * 3:(qi + 1) * 3]
    rev = sum(r["rev"] for r in ms)
    new = sum(r["new"] for r in ms)
    churn = sum(r["churn"] for r in ms)
    mkt = sum(r["mkt"] for r in ms)
    Q[qi + 1] = dict(
        rev=rev, new=new, churn=churn, mkt=mkt,
        end=ms[-1]["active"], start=ms[0]["start"],
        net=ms[-1]["active"] - ms[0]["start"],
        churn_rate=churn / sum(r["start"] for r in ms),
        arpu=rev / sum(r["avg_active"] for r in ms) * 10000,  # 원/월
        cac=mkt / new * 10000,  # 원
    )
q1, q2, q3 = Q[1], Q[2], Q[3]


def pct(a, b):
    return (a / b - 1) * 100


def sgn(v, d=1, unit="%"):
    return f"{'+' if v >= 0 else '−'}{abs(v):.{d}f}{unit}"


def won(v):  # 만원 -> 억원 표기
    return f"{v / 10000:.2f}억"


# ---------- SVG 차트 ----------
C = dict(ink="#0b0b0b", ink2="#52514e", muted="#8a8984", grid="#e6e5e1",
         s1="#2a78d6", s2="#eb6834", base="#c9c8c2", surface="#fcfcfb")


def bar_chart(values, labels, w, h, hi_from=None, fmt=str, tips=None, color=None):
    """단일 계열 세로 막대. hi_from 이후 인덱스는 강조색, 이전은 회색."""
    pl, pr, pt, pb = 8, 8, 28, 28
    iw, ih = w - pl - pr, h - pt - pb
    vmax = max(values) * 1.12
    n = len(values)
    slot = iw / n
    bw = min(slot - 2, slot * 0.62)
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img">']
    out.append(f'<line x1="{pl}" x2="{w - pr}" y1="{pt + ih}" y2="{pt + ih}" stroke="{C["grid"]}" stroke-width="1"/>')
    for i, v in enumerate(values):
        bh = ih * v / vmax
        x = pl + i * slot + (slot - bw) / 2
        y = pt + ih - bh
        col = color or (C["s1"] if hi_from is None or i >= hi_from else C["base"])
        r = 4
        # 위쪽만 둥근 막대 (기준선에 붙음)
        d = (f"M{x},{pt + ih} L{x},{y + r} Q{x},{y} {x + r},{y} L{x + bw - r},{y} "
             f"Q{x + bw},{y} {x + bw},{y + r} L{x + bw},{pt + ih} Z")
        tip = tips[i] if tips else f"{labels[i]}: {fmt(v)}"
        out.append(f'<g class="mark"><title>{tip}</title>'
                   f'<rect x="{pl + i * slot}" y="{pt}" width="{slot}" height="{ih}" fill="transparent"/>'
                   f'<path d="{d}" fill="{col}"/></g>')
        emph = hi_from is not None and i >= hi_from
        out.append(f'<text x="{x + bw / 2}" y="{y - 8}" text-anchor="middle" font-size="13" '
                   f'fill="{C["ink"] if emph or hi_from is None else C["ink2"]}" '
                   f'font-weight="{600 if emph else 400}">{fmt(v)}</text>')
        out.append(f'<text x="{x + bw / 2}" y="{h - 8}" text-anchor="middle" font-size="13" fill="{C["ink2"]}">{labels[i]}</text>')
    out.append("</svg>")
    return "".join(out)


def line_chart(values, labels, w, h, fmt=str, ymin=None, ymax=None, label_idx=(), color=None,
               band_from=None, tips=None):
    pl, pr, pt, pb = 12, 12, 30, 28
    iw, ih = w - pl - pr, h - pt - pb
    lo = ymin if ymin is not None else min(values) * 0.9
    hi = ymax if ymax is not None else max(values) * 1.08
    n = len(values)
    xs = [pl + iw * (i + 0.5) / n for i in range(n)]
    ys = [pt + ih * (1 - (v - lo) / (hi - lo)) for v in values]
    col = color or C["s1"]
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img">']
    if band_from is not None:
        bx = pl + iw * band_from / n
        out.append(f'<rect x="{bx}" y="{pt - 18}" width="{pl + iw - bx}" height="{ih + 18}" fill="#f1f0ec"/>')
        out.append(f'<text x="{bx + 8}" y="{pt - 5}" font-size="12" fill="{C["ink2"]}">3분기</text>')
    for k in range(4):
        gy = pt + ih * k / 3
        out.append(f'<line x1="{pl}" x2="{w - pr}" y1="{gy}" y2="{gy}" stroke="{C["grid"]}" stroke-width="1"/>')
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    out.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2" stroke-linejoin="round"/>')
    for i, (x, y, v) in enumerate(zip(xs, ys, values)):
        tip = tips[i] if tips else f"{labels[i]}: {fmt(v)}"
        out.append(f'<g class="mark"><title>{tip}</title>'
                   f'<rect x="{x - iw / n / 2}" y="{pt}" width="{iw / n}" height="{ih}" fill="transparent"/>'
                   f'<circle cx="{x}" cy="{y}" r="4.5" fill="{col}" stroke="{C["surface"]}" stroke-width="2"/></g>')
        if i in label_idx:
            below = 0 < i and values[i] < values[i - 1] and (i == n - 1 or values[i + 1] > values[i])
            ty = y + 24 if below else y - 12
            out.append(f'<text x="{x}" y="{ty}" text-anchor="middle" font-size="13" font-weight="600" fill="{C["ink"]}">{fmt(v)}</text>')
        out.append(f'<text x="{x}" y="{h - 8}" text-anchor="middle" font-size="13" fill="{C["ink2"]}">{labels[i]}</text>')
    out.append("</svg>")
    return "".join(out)


labels = [r["label"] for r in rows]

# 슬라이드 3: 월별 매출
rev_chart = bar_chart([r["rev"] for r in rows], labels, 760, 380, hi_from=6,
                      fmt=lambda v: f"{v:,}")
# 분기 매출
qrev_chart = bar_chart([q1["rev"], q2["rev"], q3["rev"]], ["1분기", "2분기", "3분기"], 360, 380,
                       hi_from=2, fmt=won)
# 슬라이드 4: 활성 고객
active_chart = line_chart([r["active"] for r in rows], labels, 600, 340, fmt=lambda v: f"{v:,}",
                          ymin=3500, ymax=6800, label_idx=(0, 2, 5, 8), band_from=6)
net_chart = bar_chart([r["new"] - r["churn"] for r in rows], labels, 560, 340, hi_from=6,
                      fmt=lambda v: f"+{v}",
                      tips=[f"{r['label']}: 신규 {r['new']} − 해지 {r['churn']} = 순증 {r['new'] - r['churn']}" for r in rows])
# 슬라이드 5: 해지율
churn_chart = line_chart([r["churn_rate"] * 100 for r in rows], labels, 700, 360,
                         fmt=lambda v: f"{v:.2f}%", ymin=1.4, ymax=2.6, label_idx=(1, 5, 6, 7, 8),
                         color=C["s2"], band_from=6,
                         tips=[f"{r['label']}: 해지 {r['churn']}명 / 월초 {r['start']:,}명 = {r['churn_rate'] * 100:.2f}%" for r in rows])
# 슬라이드 6: CAC
cac_chart = bar_chart([q1["cac"], q2["cac"], q3["cac"]], ["1분기", "2분기", "3분기"], 420, 340,
                      hi_from=2, fmt=lambda v: f"{v:,.0f}원")
# 슬라이드 7: ARPU
arpu_chart = bar_chart([q1["arpu"], q2["arpu"], q3["arpu"]], ["1분기", "2분기", "3분기"], 420, 340,
                       hi_from=2, fmt=lambda v: f"{v:,.0f}원")

aug, jul, sep = rows[7], rows[6], rows[8]
rev_growth = pct(q3["rev"], q2["rev"])
avg_act_growth = pct(sum(r["avg_active"] for r in rows[6:9]), sum(r["avg_active"] for r in rows[3:6]))


def kpi(label, value, delta, note, good=True):
    cls = "up" if good else "down"
    return (f'<div class="kpi"><div class="kpi-l">{label}</div><div class="kpi-v">{value}</div>'
            f'<div class="kpi-d {cls}">{delta}</div><div class="kpi-n">{note}</div></div>')


table_rows = "".join(
    f"<tr{' class=hl' if i >= 6 else ''}><td>{r['m']}</td><td>{r['rev']:,}</td><td>{r['new']:,}</td>"
    f"<td>{r['churn']:,}</td><td>{r['active']:,}</td><td>{r['churn_rate'] * 100:.2f}%</td><td>{r['mkt']:,}</td></tr>"
    for i, r in enumerate(rows))
qtable_rows = "".join(
    f"<tr{' class=hl' if k == 3 else ''}><td>{k}분기</td><td>{q['rev']:,}</td><td>{q['new']:,}</td><td>{q['churn']:,}</td>"
    f"<td>{q['end']:,}</td><td>{q['churn_rate'] * 100:.2f}%</td><td>{q['mkt']:,}</td><td>{q['cac']:,.0f}</td><td>{q['arpu']:,.0f}</td></tr>"
    for k, q in Q.items())

slides = []

slides.append(f"""
<section class="slide title">
  <div class="eyebrow">2026년 3분기 실적 리뷰</div>
  <h1>매출 3.09억, 전분기 대비 {sgn(rev_growth)}<br>고객은 더 빠르게 늘었지만 객단가는 낮아졌다</h1>
  <div class="meta">기간 2026.07 – 2026.09 · 비교 기준 2분기(2026.04 – 06) · 자료 04_분기실적.csv</div>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="eyebrow">요약</div>
  <h2>3분기 핵심 지표</h2>
  <div class="kpis">
    {kpi("분기 매출", won(q3["rev"]) + "원", sgn(rev_growth) + " QoQ", f"2분기 {won(q2['rev'])}원")}
    {kpi("신규 고객", f"{q3['new']:,}명", sgn(pct(q3['new'], q2['new'])) + " QoQ", f"2분기 {q2['new']:,}명")}
    {kpi("월말 활성 고객", f"{q3['end']:,}명", sgn(pct(q3['end'], q2['end'])) + " QoQ", f"분기 순증 +{q3['net']:,}명")}
    {kpi("월평균 해지율", f"{q3['churn_rate'] * 100:.2f}%", sgn((q3['churn_rate'] - q2['churn_rate']) * 100, 2, '%p') + " QoQ", f"2분기 {q2['churn_rate'] * 100:.2f}%")}
  </div>
  <ul class="points">
    <li><b>성장 가속.</b> 매출·신규·활성 고객 모두 1분기부터 매 분기 증가했고, 9월 매출 {sep['rev']:,}만원으로 월 최고치.</li>
    <li><b>8월이 유일한 흔들림.</b> 매출이 전월 대비 {sgn(pct(aug['rev'], jul['rev']))}, 해지 {aug['churn']}명으로 9개월 중 최다. 9월에 회복.</li>
    <li><b>객단가 하락.</b> 고객당 월매출(ARPU)이 {q3['arpu']:,.0f}원으로 전분기 대비 {sgn(pct(q3['arpu'], q2['arpu']))} — 매출 성장({sgn(rev_growth)})이 고객 성장({sgn(avg_act_growth)})을 따라가지 못함.</li>
  </ul>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="eyebrow">매출</div>
  <h2>3분기 매출 {won(q3['rev'])}원, 2분기보다 {sgn(rev_growth)} · 1분기보다 {sgn(pct(q3['rev'], q1['rev']))}</h2>
  <div class="row">
    <figure class="grow"><figcaption>월별 매출 (만원)</figcaption>{rev_chart}</figure>
    <figure style="width:360px"><figcaption>분기 매출 (원)</figcaption>{qrev_chart}</figure>
  </div>
  <p class="note">8월 {aug['rev']:,}만원으로 전월 대비 {sgn(pct(aug['rev'], jul['rev']))} 후퇴, 9월 {sep['rev']:,}만원으로 반등해 최고치 경신.</p>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="eyebrow">고객</div>
  <h2>활성 고객 {q3['end']:,}명 — 3분기 순증 +{q3['net']:,}명으로 2분기(+{q2['net']:,}명)보다 많다</h2>
  <div class="row">
    <figure class="grow"><figcaption>월말 활성 고객 (명)</figcaption>{active_chart}</figure>
    <figure class="grow"><figcaption>월 순증 고객 = 신규 − 해지 (명)</figcaption>{net_chart}</figure>
  </div>
  <p class="note">신규 {q3['new']:,}명({sgn(pct(q3['new'], q2['new']))} QoQ) · 해지 {q3['churn']:,}명({sgn(pct(q3['churn'], q2['churn']))} QoQ). 8월은 신규 감소와 해지 증가가 겹쳐 순증 +{aug['new'] - aug['churn']}명에 그침.</p>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="eyebrow">해지</div>
  <h2>해지율은 내려가는 추세, 8월 {aug['churn_rate'] * 100:.2f}%만 튀었다</h2>
  <div class="row">
    <figure class="grow"><figcaption>월 해지율 = 해지 고객 ÷ 월초 활성 고객</figcaption>{churn_chart}</figure>
    <div class="side">
      <div class="stat"><div class="stat-l">1분기 평균</div><div class="stat-v">{q1['churn_rate'] * 100:.2f}%</div></div>
      <div class="stat"><div class="stat-l">2분기 평균</div><div class="stat-v">{q2['churn_rate'] * 100:.2f}%</div></div>
      <div class="stat hl"><div class="stat-l">3분기 평균</div><div class="stat-v">{q3['churn_rate'] * 100:.2f}%</div></div>
      <p class="small">해지 고객 수 자체는 늘었지만({q2['churn']} → {q3['churn']}명) 고객 기반이 더 크게 늘어 비율은 하락.</p>
    </div>
  </div>
  <p class="note">8월 해지 {aug['churn']}명은 9개월 중 최다. 원인은 이 자료로 확인할 수 없음 — 해지 사유 데이터로 점검 필요.</p>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="eyebrow">마케팅 효율</div>
  <h2>마케팅비 {sgn(pct(q3['mkt'], q2['mkt']))} 늘렸고, 신규는 {sgn(pct(q3['new'], q2['new']))} 늘어 획득비용이 낮아졌다</h2>
  <div class="row">
    <figure style="width:460px"><figcaption>신규 고객 1명당 마케팅비 (CAC)</figcaption>{cac_chart}</figure>
    <div class="side wide">
      <table class="mini">
        <tr><th></th><th>2분기</th><th>3분기</th><th>증감</th></tr>
        <tr><td>마케팅비</td><td>{q2['mkt']:,}만원</td><td>{q3['mkt']:,}만원</td><td>{sgn(pct(q3['mkt'], q2['mkt']))}</td></tr>
        <tr><td>신규 고객</td><td>{q2['new']:,}명</td><td>{q3['new']:,}명</td><td>{sgn(pct(q3['new'], q2['new']))}</td></tr>
        <tr><td>CAC</td><td>{q2['cac']:,.0f}원</td><td>{q3['cac']:,.0f}원</td><td>{sgn(pct(q3['cac'], q2['cac']))}</td></tr>
      </table>
      <p class="small">CAC = 분기 마케팅비 ÷ 분기 신규 고객. 마케팅비 외 획득 비용은 자료에 없어 제외.</p>
    </div>
  </div>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="eyebrow">주의 신호</div>
  <h2>고객당 월매출(ARPU)이 두 분기 연속 하락 — 3분기 {q3['arpu']:,.0f}원, {sgn(pct(q3['arpu'], q2['arpu']))}</h2>
  <div class="row">
    <figure style="width:460px"><figcaption>ARPU = 분기 매출 ÷ 월평균 활성 고객 합</figcaption>{arpu_chart}</figure>
    <div class="side wide">
      <div class="compare">
        <div><div class="stat-l">매출 성장 (QoQ)</div><div class="stat-v">{sgn(rev_growth)}</div></div>
        <div class="vs">vs</div>
        <div><div class="stat-l">평균 활성 고객 성장 (QoQ)</div><div class="stat-v">{sgn(avg_act_growth)}</div></div>
      </div>
      <p class="small">고객 수가 매출보다 빠르게 늘고 있다. 저가 요금제·할인 유입 비중 확대, 기존 고객 이용 감소 등이 후보지만 이 자료만으로는 원인을 가릴 수 없음.</p>
      <p class="small">월평균 활성 고객 = (월초 + 월말) ÷ 2. 1월 월초 값은 월말 − 신규 + 해지로 역산.</p>
    </div>
  </div>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="eyebrow">정리</div>
  <h2>4분기에 확인할 것</h2>
  <ol class="next">
    <li><b>ARPU 하락 원인 분해</b><span>요금제·상품별 매출과 신규 고객 구성을 보고, 객단가 하락이 신규 유입 구성 때문인지 기존 고객 변화 때문인지 구분</span></li>
    <li><b>8월 해지 급증 원인</b><span>8월 해지 {aug['churn']}명의 해지 사유·가입 시기 확인. 일회성인지 계절성인지 판단</span></li>
    <li><b>마케팅 확대 여력 판단</b><span>CAC가 {q3['cac']:,.0f}원으로 안정적이므로 증액 시에도 효율이 유지되는지 채널별로 점검</span></li>
  </ol>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="eyebrow">부록</div>
  <h2>원자료와 분기 집계</h2>
  <div class="row top">
    <table class="data">
      <tr><th>월</th><th>매출(만원)</th><th>신규</th><th>해지</th><th>월말 활성</th><th>해지율</th><th>마케팅비(만원)</th></tr>
      {table_rows}
    </table>
    <table class="data">
      <tr><th>분기</th><th>매출(만원)</th><th>신규</th><th>해지</th><th>기말 활성</th><th>해지율</th><th>마케팅비</th><th>CAC(원)</th><th>ARPU(원)</th></tr>
      {qtable_rows}
    </table>
  </div>
  <p class="small">해지율 = 해지 ÷ 월초 활성(분기는 월초 활성 합 기준). 월말 활성 = 월초 + 신규 − 해지 로 8개월 모두 검산 일치.</p>
</section>""")

total = len(slides)
body = "".join(s.replace('</section>', f'<div class="pg">{i + 1} / {total}</div></section>', 1)
               for i, s in enumerate(slides))

html = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<title>분기실적 — 2026년 3분기 실적 리뷰</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{ --ink:{C['ink']}; --ink2:{C['ink2']}; --muted:{C['muted']}; --grid:{C['grid']};
  --s1:{C['s1']}; --s2:{C['s2']}; --surface:{C['surface']}; --good:#008300; --bad:#c43c3b; }}
* {{ box-sizing:border-box; margin:0; padding:0; }}
@page {{ size:1280px 720px; margin:0; }}
html {{ background:#e9e8e4; }}
body {{ font-family:"Pretendard","Malgun Gothic","Apple SD Gothic Neo",sans-serif; color:var(--ink);
  -webkit-print-color-adjust:exact; print-color-adjust:exact; word-break:keep-all; }}
.slide {{ width:1280px; height:720px; background:var(--surface); position:relative; overflow:hidden;
  padding:56px 72px; margin:24px auto; box-shadow:0 1px 4px rgba(0,0,0,.08); display:flex; flex-direction:column; }}
@media print {{ html {{ background:none; }} .slide {{ margin:0; box-shadow:none; break-after:page; }} }}
.eyebrow {{ font-size:15px; font-weight:600; color:var(--s1); letter-spacing:.02em; margin-bottom:10px; }}
h1 {{ font-size:46px; line-height:1.3; font-weight:700; letter-spacing:-.02em; }}
h2 {{ font-size:30px; line-height:1.35; font-weight:700; letter-spacing:-.015em; margin-bottom:28px; }}
.title {{ justify-content:center; padding-left:96px; }}
.title .eyebrow {{ font-size:18px; margin-bottom:20px; }}
.title .meta {{ margin-top:40px; color:var(--ink2); font-size:16px; }}
.pg {{ position:absolute; right:40px; bottom:24px; font-size:12px; color:var(--muted); }}
.row {{ display:flex; gap:40px; align-items:flex-end; flex:1; min-height:0; }}
.row.top {{ align-items:flex-start; gap:28px; }}
.grow {{ flex:1; min-width:0; }}
figure figcaption {{ font-size:14px; color:var(--ink2); margin-bottom:6px; }}
svg {{ font-family:inherit; display:block; overflow:visible; }}
svg .mark:hover path, svg .mark:hover circle {{ opacity:.8; }}
.note {{ margin-top:18px; font-size:16px; color:var(--ink2); border-left:3px solid var(--grid); padding-left:12px; }}
.small {{ font-size:14px; color:var(--ink2); line-height:1.6; margin-top:14px; }}
.kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:20px; margin-bottom:40px; }}
.kpi {{ border:1px solid var(--grid); border-radius:10px; padding:22px 24px; }}
.kpi-l {{ font-size:14px; color:var(--ink2); }}
.kpi-v {{ font-size:36px; font-weight:700; margin:8px 0 6px; letter-spacing:-.02em; }}
.kpi-d {{ font-size:15px; font-weight:600; }}
.kpi-d.up {{ color:var(--good); }} .kpi-d.down {{ color:var(--bad); }}
.kpi-n {{ font-size:13px; color:var(--muted); margin-top:4px; }}
.points {{ list-style:none; display:flex; flex-direction:column; gap:16px; font-size:19px; line-height:1.55; }}
.points li {{ padding-left:18px; position:relative; }}
.points li::before {{ content:""; position:absolute; left:0; top:12px; width:6px; height:6px; border-radius:50%; background:var(--ink2); }}
.side {{ width:300px; align-self:center; }}
.side.wide {{ width:auto; flex:1; }}
.stat {{ padding:12px 0; border-bottom:1px solid var(--grid); display:flex; justify-content:space-between; align-items:baseline; }}
.stat.hl .stat-v {{ color:var(--s2); }}
.stat-l {{ font-size:14px; color:var(--ink2); }}
.stat-v {{ font-size:28px; font-weight:700; }}
table {{ border-collapse:collapse; font-variant-numeric:tabular-nums; }}
.mini {{ width:100%; font-size:17px; }}
.mini th, .mini td {{ padding:12px 10px; text-align:right; border-bottom:1px solid var(--grid); }}
.mini th {{ font-size:14px; color:var(--ink2); font-weight:500; }}
.mini td:first-child {{ text-align:left; color:var(--ink2); }}
.mini tr:last-child td {{ font-weight:700; }}
.compare {{ display:flex; align-items:center; gap:28px; padding:20px 0; border-bottom:1px solid var(--grid); }}
.compare .vs {{ color:var(--muted); font-size:16px; }}
.compare .stat-v {{ font-size:40px; }}
.next {{ list-style:none; counter-reset:n; display:flex; flex-direction:column; gap:22px; }}
.next li {{ counter-increment:n; display:grid; grid-template-columns:56px 1fr; row-gap:6px; }}
.next li::before {{ content:counter(n); grid-row:span 2; width:40px; height:40px; border-radius:50%;
  background:var(--s1); color:#fff; font-weight:700; font-size:18px; display:flex; align-items:center; justify-content:center; }}
.next b {{ font-size:22px; }}
.next span {{ font-size:17px; color:var(--ink2); line-height:1.55; }}
.data {{ font-size:14px; }}
.data th, .data td {{ padding:7px 10px; text-align:right; border-bottom:1px solid var(--grid); white-space:nowrap; }}
.data th {{ color:var(--ink2); font-weight:500; font-size:13px; }}
.data td:first-child, .data th:first-child {{ text-align:left; }}
.data tr.hl td {{ background:#eef4fc; }}
</style></head>
<body>
{body}
</body></html>
"""

out = ROOT / "분기실적.html"
out.write_text(html, encoding="utf-8")
print("wrote", out)
for k, q in Q.items():
    print(k, {a: round(b, 4) for a, b in q.items()})
print("avg_act_growth", round(avg_act_growth, 2))
