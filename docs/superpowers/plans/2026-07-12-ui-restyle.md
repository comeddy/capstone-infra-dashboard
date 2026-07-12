# UI Restyle (LLM Monitor 스타일) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 대시보드 렌더 계층을 LLM Monitor(gray-950 다크, 도넛 카드, 접이식 섹션, pill 배지) 스타일로 전면 교체한다.

**Architecture:** `build_dashboard.py` 단일 파일 전체 교체. 데이터 스키마·scan.sh·CLI 계약 불변. 도넛/세그먼트 바는 인라인 SVG, 접이식은 `<details>`(JS 없음).

**Tech Stack:** Python 3 표준 라이브러리만. 배포는 기존 S3+CloudFront 재사용.

> **모듈 순서 안내:** 이 플랜은 base(my-infra-dashboard) → topology-cost-extension → **ui-restyle** 순서의 3번째이자 최종 모듈이다. 리포지토리에 커밋된 `build_dashboard.py`와 `docs/final-screenshot.png`는 이 플랜까지 적용된 **최종 상태**이며, 앞선 두 플랜만 완료한 참가자의 대시보드는 이와 다른 (구 스타일) 모습이 정상이다. 이 플랜의 스크린샷 갱신 단계는 확장 플랜의 스크린샷 단계를 대체한다.

## Global Constraints

- 스펙: `docs/superpowers/specs/2026-07-12-ui-restyle-design.md`의 토큰·매핑·불변 조건 전부
- 단일 index.html, 인라인 CSS/SVG만, **JS 금지**
- inventory.json 스키마·scan.sh·CLI 계약(`OK: <경로> 생성 (source=<파일명>)`) 불변
- `.get()` 폴백으로 필드 부재 시에도 동작, `$—`/`*` 부분합 마커/계정 마스킹 규칙 유지
- 기존 topology-cost-extension 플랜 문서는 수정 금지

---

### Task 1: build_dashboard.py 전체 교체

**Files:**
- Modify: `capstone/my-infra-dashboard/scripts/build_dashboard.py` (전체 교체 — 아래 리스팅이 파일 전문)

**Interfaces:**
- Consumes: 확장 inventory 스키마 (기존과 동일)
- Produces: `site/index.html` — 도넛 카드 3장(`class="donut"`), VPC별 `<details class="vpc" open>`, pill 배지, 새 팔레트. CLI 계약 불변

- [ ] **Step 1: 파일 전체 교체** — 아래 내용으로 `scripts/build_dashboard.py`를 통째로 교체:

```python
#!/usr/bin/env python3
"""data/inventory.json → site/index.html 단일 파일 대시보드 생성.
inventory.json 부재 시 sample-inventory.json 폴백. LLM Monitor 스타일 다크 테마."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INV = ROOT / "data" / "inventory.json"
SAMPLE = ROOT / "data" / "sample-inventory.json"
OUT = ROOT / "site" / "index.html"

ACCENT = "#3b82f6"
ARROW_IN = "#60a5fa"
ARROW_OUT = "#fb923c"
OK = "#34d399"
WARN = "#fbbf24"
DANGER = "#fb7185"
MUTED = "#6b7280"
ROUTE_COLOR = {"public": OK, "private": WARN, "isolated": MUTED}
ROUTE_PILL = {"public": "emerald", "private": "amber", "isolated": "gray"}

CSS = """
:root { --bg:#030712; --panel:#111827; --line:#1f2937; --text:#f9fafb;
        --sub:#9ca3af; --accent:#3b82f6; --ok:#34d399; --warn:#fbbf24;
        --danger:#fb7185; }
* { box-sizing:border-box; margin:0; }
body { background:var(--bg); color:var(--text);
       font-family:'Segoe UI',Pretendard,sans-serif; padding:2rem;
       font-variant-numeric:tabular-nums; }
header { display:flex; justify-content:space-between; align-items:center;
         flex-wrap:wrap; gap:.6rem; padding-bottom:1rem;
         border-bottom:1px solid var(--line); }
header h1 { font-size:1.35rem; }
header h1 span { color:var(--accent); }
.meta { display:flex; gap:.4rem; flex-wrap:wrap; }
.chip { background:var(--panel); border:1px solid var(--line); color:var(--sub);
        border-radius:999px; padding:.2rem .7rem; font-size:.75rem;
        white-space:nowrap; }
.cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
         gap:1rem; margin:1.4rem 0; }
.scard { background:var(--panel); border:1px solid var(--line);
         border-radius:14px; padding:1.1rem 1.2rem; }
.scard-head { display:flex; justify-content:space-between; align-items:center;
              margin-bottom:.7rem; }
.scard-head h3 { font-size:.95rem; }
.scard-body { display:flex; align-items:center; gap:1.1rem; }
.donut { width:104px; height:104px; flex:none; }
.donut-c { fill:var(--text); font-size:20px; font-weight:700; }
.donut-s { fill:var(--sub); font-size:9px; letter-spacing:.08em; }
.stats { list-style:none; padding:0; font-size:.82rem; color:var(--sub);
         display:flex; flex-direction:column; gap:.35rem; width:100%; }
.stats li { display:flex; align-items:center; gap:.45rem; }
.stats b { color:var(--text); margin-left:auto; padding-left:.8rem;
           font-weight:600; }
.dot { width:8px; height:8px; border-radius:50%; flex:none; }
section { margin-bottom:2rem; }
h2 { font-size:1.02rem; margin:1.6rem 0 .7rem;
     border-left:3px solid var(--accent); padding-left:.55rem; }
details.vpc { background:var(--panel); border:1px solid var(--line);
              border-radius:14px; margin-bottom:.8rem; overflow:hidden; }
details.vpc summary { cursor:pointer; list-style:none; display:flex;
                      align-items:center; gap:.9rem; padding:.85rem 1.1rem;
                      flex-wrap:wrap; }
details.vpc summary::-webkit-details-marker { display:none; }
details.vpc summary::before { content:"▸"; color:var(--sub); }
details.vpc[open] summary::before { content:"▾"; }
.vpc-name { font-weight:600; }
.vpc-id { color:var(--sub); font-size:.78rem; }
.segbar { display:flex; height:6px; border-radius:999px; overflow:hidden;
          background:var(--line); width:180px; }
.vpc-cost { margin-left:auto; color:var(--warn); font-size:.85rem;
            font-weight:600; }
.vpc-body { padding:0 1.1rem 1rem; }
table { width:100%; border-collapse:collapse; background:var(--panel);
        border:1px solid var(--line); border-radius:12px; overflow:hidden;
        font-size:.86rem; }
th, td { padding:.55rem .9rem; text-align:left;
         border-bottom:1px solid var(--line); }
th { color:var(--sub); font-weight:600; font-size:.72rem;
     text-transform:uppercase; letter-spacing:.06em; }
tr:last-child td { border-bottom:none; }
.pill { display:inline-block; border-radius:999px; padding:.12rem .6rem;
        font-size:.74rem; font-weight:600; margin-right:.25rem; }
.pill.rose { background:rgba(251,113,133,.15); color:var(--danger);
             border:1px solid rgba(251,113,133,.35); }
.pill.emerald { background:rgba(52,211,153,.12); color:var(--ok);
                border:1px solid rgba(52,211,153,.3); }
.pill.amber { background:rgba(251,191,36,.12); color:var(--warn);
              border:1px solid rgba(251,191,36,.3); }
.pill.gray { background:rgba(107,114,128,.15); color:var(--sub);
             border:1px solid rgba(107,114,128,.35); }
.empty { color:var(--sub); text-align:center; }
.note { color:var(--sub); font-size:.78rem; margin-top:.6rem; }
footer { color:var(--sub); font-size:.78rem; text-align:center;
         margin-top:2rem; }
"""


def load_inventory():
    src = INV if INV.exists() else SAMPLE
    data = json.loads(src.read_text())
    data["source"] = src.name
    return data


def esc(v):
    return html.escape(str(v if v is not None else "-"))


def fmt_usd(v):
    if v is None:
        return "$—"
    return f"${v:,.1f}/월"


def monthly_sum(items):
    nums = [x.get("monthly_usd") for x in items
            if isinstance(x.get("monthly_usd"), (int, float))]
    return round(sum(nums), 1) if nums else None


def has_unpriced(items):
    return any(x.get("monthly_usd") is None for x in items)


def pill(text, kind):
    return f'<span class="pill {kind}">{esc(text)}</span>'


def table(headers, rows):
    thead = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows
    ) or f'<tr><td colspan="{len(headers)}" class="empty">리소스 없음</td></tr>'
    return f"<table><thead><tr>{thead}</tr></thead><tbody>{body}</tbody></table>"


def donut(segments, center, sub):
    """segments: [(0..1 비율, 색)] — 인라인 SVG 도넛 링."""
    size, stroke = 104, 12
    r = (size - stroke) / 2
    c = 2 * 3.14159265 * r
    parts = [f'<circle cx="{size / 2}" cy="{size / 2}" r="{r}" fill="none" '
             f'stroke="#1f2937" stroke-width="{stroke}"/>']
    off = 0.0
    for frac, color in segments:
        if frac <= 0:
            continue
        parts.append(
            f'<circle cx="{size / 2}" cy="{size / 2}" r="{r}" fill="none" '
            f'stroke="{color}" stroke-width="{stroke}" '
            f'stroke-dasharray="{frac * c:.2f} {c:.2f}" '
            f'stroke-dashoffset="{-off * c:.2f}" '
            f'transform="rotate(-90 {size / 2} {size / 2})"/>')
        off += frac
    parts.append(f'<text x="52" y="50" text-anchor="middle" '
                 f'class="donut-c">{esc(center)}</text>')
    parts.append(f'<text x="52" y="66" text-anchor="middle" '
                 f'class="donut-s">{esc(sub)}</text>')
    return (f'<svg viewBox="0 0 {size} {size}" class="donut">'
            + "".join(parts) + "</svg>")


def stat_card(title, badge, donut_svg, bullets):
    """bullets: [(라벨, 값(안전한 문자열/숫자), 색)]"""
    lis = "".join(
        f'<li><span class="dot" style="background:{c}"></span>{esc(t)}<b>{v}</b></li>'
        for t, v, c in bullets)
    return (f'<div class="scard"><div class="scard-head"><h3>{esc(title)}</h3>'
            f'<span class="chip">{esc(badge)}</span></div>'
            f'<div class="scard-body">{donut_svg}<ul class="stats">{lis}</ul>'
            f'</div></div>')


def svg_node(x, y, w, lines, stroke):
    txt = "".join(
        f'<text x="{x + 8}" y="{y + 16 + n * 14}" font-size="10" '
        f'fill="#e5e7eb">{t}</text>' for n, t in enumerate(lines))
    return (f'<rect x="{x}" y="{y}" width="{w}" height="50" rx="6" '
            f'fill="#1f2937" stroke="{stroke}"/>{txt}')


def svg_arrow(x1, y1, x2, y2, color, marker):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{color}" stroke-width="1.5" marker-end="url(#{marker})"/>')


def svg_topology(vpc, nats, instances):
    """VPC 하나의 in/out 토폴로지 SVG. 서브넷 그리드 + 좌측 Internet/IGW 레인."""
    subs = vpc.get("subnets", [])
    pub = [s for s in subs if s.get("route") == "public"]
    rest = [s for s in subs if s.get("route") != "public"]
    rows = [r for r in (pub, rest) if r]
    if not rows:
        return ""

    by_subnet = {}
    for i in instances:
        by_subnet.setdefault(i.get("subnet_id"), []).append(i)
    vpc_nats = [n for n in nats if n.get("vpc_id") == vpc.get("id")]
    nat_by_subnet = {}
    for n in vpc_nats:
        nat_by_subnet.setdefault(n.get("subnet_id"), []).append(n)

    SUB_W, GAP, LANE, NODE = 280, 24, 150, 58

    def contents(s):
        items = by_subnet.get(s["id"], [])
        return items[:8], max(0, len(items) - 8), nat_by_subnet.get(s["id"], [])

    def sub_h(s):
        items, extra, snats = contents(s)
        return 46 + (len(items) + (1 if extra else 0) + len(snats)) * NODE

    row_hs = [max(sub_h(s) for s in r) for r in rows]
    cols = max(len(r) for r in rows)
    width = LANE + cols * (SUB_W + GAP)
    height = 30 + sum(row_hs) + GAP * len(rows)

    p = [f'<svg viewBox="0 0 {width} {height}" '
         f'xmlns="http://www.w3.org/2000/svg" '
         f'style="width:100%;max-width:{width}px;display:block;margin:.5rem 0">',
         '<defs>'
         f'<marker id="ain" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
         f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" '
         f'fill="{ARROW_IN}"/></marker>'
         f'<marker id="aout" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
         f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" '
         f'fill="{ARROW_OUT}"/></marker>'
         '</defs>']

    igw = vpc.get("igw_id")
    if igw:
        p.append(svg_node(10, 20, 120, ["Internet"], ARROW_IN))
        p.append(svg_node(10, 100, 120, ["IGW", esc(igw)], ARROW_IN))
        p.append(svg_arrow(60, 70, 60, 98, ARROW_IN, "ain"))
        p.append(svg_arrow(80, 100, 80, 72, ARROW_OUT, "aout"))

    nat_pos = {}
    y = 20
    for r, rh in zip(rows, row_hs):
        for j, s in enumerate(r):
            x = LANE + j * (SUB_W + GAP)
            color = ROUTE_COLOR.get(s.get("route"), MUTED)
            p.append(f'<rect x="{x}" y="{y}" width="{SUB_W}" height="{sub_h(s)}" '
                     f'rx="8" fill="#0b1120" stroke="{color}" '
                     f'stroke-dasharray="4 3"/>')
            p.append(f'<text x="{x + 8}" y="{y + 16}" font-size="10" '
                     f'fill="{color}">{esc(s.get("id"))} · {esc(s.get("cidr"))} · '
                     f'{esc(s.get("route"))}</text>')
            ny = y + 26
            items, extra, snats = contents(s)
            for i in items:
                ports = ",".join(str(v) for v in i.get("in_ports", [])) or "-"
                cost = fmt_usd(i.get("monthly_usd"))
                if i.get("state") != "running":
                    cost += f' ({esc(i.get("state"))})'
                p.append(svg_node(x + 10, ny, SUB_W - 20,
                                  [f'{esc(i.get("id"))} · {esc(i.get("type"))}',
                                   f'in:{esc(ports)} out:{esc(i.get("out", "-"))}',
                                   cost],
                                  ARROW_IN))
                ny += NODE
            if extra:
                p.append(f'<text x="{x + 12}" y="{ny + 14}" font-size="10" '
                         f'fill="#9ca3af">+{extra} more</text>')
                ny += NODE
            for n in snats:
                p.append(svg_node(x + 10, ny, SUB_W - 20,
                                  ["NAT " + esc(n.get("id")),
                                   fmt_usd(n.get("monthly_usd"))],
                                  ARROW_OUT))
                nat_pos[n.get("id")] = (x + 10, ny + 25)
                ny += NODE
            if igw and s.get("route") == "public":
                p.append(svg_arrow(130, 120, x - 2, y + 20, ARROW_IN, "ain"))
            if s.get("route") == "private" and vpc_nats:
                tx, ty = nat_pos.get(vpc_nats[0].get("id"), (130, 125))
                p.append(svg_arrow(x - 2, y + 40, tx, ty, ARROW_OUT, "aout"))
        y += rh + GAP
    if igw and vpc_nats and vpc_nats[0].get("id") in nat_pos:
        tx, ty = nat_pos[vpc_nats[0].get("id")]
        p.append(svg_arrow(tx, ty, 132, 125, ARROW_OUT, "aout"))

    p.append("</svg>")
    return "".join(p)


def render(d):
    vpcs = d.get("vpcs", [])
    subnets = [s for v in vpcs for s in v.get("subnets", [])]
    sgs = d.get("security_groups", [])
    ec2 = d.get("ec2_instances", [])
    nats = d.get("nat_gateways", [])
    open_sgs = [g for g in sgs if g.get("open_ports")]

    rc = {"public": 0, "private": 0, "isolated": 0}
    for s in subnets:
        rc[s.get("route") if s.get("route") in rc else "isolated"] += 1
    n_sub = len(subnets)
    net_donut = donut(
        [(rc["public"] / n_sub if n_sub else 0, OK),
         (rc["private"] / n_sub if n_sub else 0, WARN),
         (rc["isolated"] / n_sub if n_sub else 0, MUTED)],
        str(n_sub) if n_sub else "—", "SUBNETS")

    running = [i for i in ec2 if i.get("state") == "running"]
    run_pct = f"{round(100 * len(running) / len(ec2))}%" if ec2 else "—"
    comp_donut = donut(
        [(len(running) / len(ec2) if ec2 else 0, OK)], run_pct, "RUNNING")

    total = monthly_sum(ec2 + nats)
    total_label = ("$—" if total is None
                   else f"${total:,.1f}"
                        + ("*" if has_unpriced(ec2 + nats) else ""))

    closed = len(sgs) - len(open_sgs)
    closed_pct = f"{round(100 * closed / len(sgs))}%" if sgs else "—"
    sec_donut = donut(
        [(closed / len(sgs) if sgs else 0, OK),
         (len(open_sgs) / len(sgs) if sgs else 0, DANGER)],
        closed_pct, "HEALTH")
    open_ports_all = sorted({p for g in open_sgs
                             for p in g.get("open_ports", [])}, key=str)
    ports_label = ", ".join(str(p) for p in open_ports_all[:6]) or "-"

    cards = "".join([
        stat_card("네트워크", f"VPC {len(vpcs)}", net_donut,
                  [("Public", rc["public"], OK),
                   ("Private", rc["private"], WARN),
                   ("Isolated", rc["isolated"], MUTED),
                   ("NAT GW", len(nats), ARROW_OUT)]),
        stat_card("컴퓨트", f"EC2 {len(ec2)}", comp_donut,
                  [("Running", len(running), OK),
                   ("Stopped", len(ec2) - len(running), MUTED),
                   ("월 추정 비용(USD)", total_label, WARN)]),
        stat_card("보안", f"SG {len(sgs)}", sec_donut,
                  [("오픈 SG (0.0.0.0/0)", len(open_sgs), DANGER),
                   ("전체 SG", len(sgs), MUTED),
                   ("오픈 포트", esc(ports_label), WARN)]),
    ])

    topo = []
    for v in vpcs:
        subs = v.get("subnets", [])
        sub_ids = {s.get("id") for s in subs}
        v_ec2 = [i for i in ec2 if i.get("subnet_id") in sub_ids]
        v_nats = [n for n in nats if n.get("vpc_id") == v.get("id")]
        svg = svg_topology(v, nats, v_ec2)
        if not svg:
            continue
        vc = {"public": 0, "private": 0, "isolated": 0}
        for s in subs:
            vc[s.get("route") if s.get("route") in vc else "isolated"] += 1
        seg = "".join(f'<span style="flex:{n};background:{c}"></span>'
                      for n, c in [(vc["public"], OK), (vc["private"], WARN),
                                   (vc["isolated"], MUTED)] if n > 0)
        vtotal = monthly_sum(v_ec2 + v_nats)
        vcost = fmt_usd(vtotal)
        if vtotal is not None and has_unpriced(v_ec2 + v_nats):
            vcost += "*"
        topo.append(
            f'<details class="vpc" open><summary>'
            f'<span class="vpc-name">{esc(v.get("name"))}</span>'
            f'<span class="vpc-id">{esc(v.get("id"))}</span>'
            f'<div class="segbar">{seg}</div>'
            f'<span class="chip">서브넷 {len(subs)} · EC2 {len(v_ec2)} · '
            f'NAT {len(v_nats)}</span>'
            f'<span class="vpc-cost">{vcost}</span></summary>'
            f'<div class="vpc-body">{svg}</div></details>')
    topo_section = ""
    if topo:
        note = esc(d.get("pricing_note", ""))
        topo_section = ('<section><h2>네트워크 토폴로지 (in/out) &amp; 비용</h2>'
                        + "".join(topo)
                        + f'<p class="note">비용 기준: {note} · '
                          f'* = 일부 리소스 단가 미조회</p></section>')

    vpc_rows = [[esc(v.get("name")), esc(v.get("id")), esc(v.get("cidr")),
                 str(len(v.get("subnets", [])))] for v in vpcs]
    subnet_rows = [[esc(s.get("id")), esc(s.get("cidr")), esc(s.get("az")),
                    pill(s.get("route", "-"),
                         ROUTE_PILL.get(s.get("route"), "gray")),
                    esc(s.get("vpc_id"))] for s in subnets]
    ec2_rows = []
    for i in ec2:
        state = i.get("state", "-")
        ec2_rows.append([esc(i.get("id")), esc(i.get("type")),
                         pill(state, "emerald" if state == "running" else "gray"),
                         esc(i.get("subnet_id")),
                         fmt_usd(i.get("monthly_usd"))])
    sg_rows = []
    for g in sgs:
        ports = g.get("open_ports") or []
        badge = "".join(pill(p, "rose") for p in ports) or pill("없음", "emerald")
        sg_rows.append([esc(g.get("name")), esc(g.get("id")),
                        esc(g.get("vpc_id")), badge])

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>My Infra Dashboard</title><style>{CSS}</style></head>
<body>
<header><h1><span>☁</span> My Infra Dashboard</h1>
<div class="meta"><span class="chip">계정 {esc(d.get("account_id"))}</span>
<span class="chip">{esc(d.get("region"))}</span>
<span class="chip">스캔 {esc(d.get("scanned_at"))}</span>
<span class="chip">데이터: {esc(d.get("source"))}</span></div></header>
<div class="cards">{cards}</div>
{topo_section}
<section><h2>VPC</h2>{table(["Name", "VPC ID", "CIDR", "서브넷 수"], vpc_rows)}</section>
<section><h2>서브넷</h2>{table(["Subnet ID", "CIDR", "AZ", "Route", "VPC"], subnet_rows)}</section>
<section><h2>EC2 인스턴스</h2>{table(["Instance ID", "Type", "State", "Subnet", "월 추정"], ec2_rows)}</section>
<section><h2>보안그룹 — 0.0.0.0/0 오픈 포트</h2>{table(["Name", "Group ID", "VPC", "오픈 포트"], sg_rows)}</section>
<footer>Generated with Claude Code · Capstone 2026</footer>
</body></html>"""


def main():
    d = load_inventory()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(d))
    print(f"OK: {OUT} 생성 (source={d['source']})")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 문법 확인**

Run: `python3 -m py_compile capstone/my-infra-dashboard/scripts/build_dashboard.py`
Expected: exit 0, 출력 없음

- [ ] **Step 3: 샘플 렌더 검증** (data/inventory.json을 스크래치로 임시 이동 후)

```bash
python3 capstone/my-infra-dashboard/scripts/build_dashboard.py
H=capstone/my-infra-dashboard/site/index.html
grep -o 'class="donut"' $H | wc -l                     # 3
grep -o '<details class="vpc" open>' $H | wc -l        # 1 (샘플 VPC 1개)
grep -o 'class="pill rose"' $H | wc -l                 # ≥ 2 (포트 80, 443)
grep -o 'class="pill emerald"' $H | wc -l              # ≥ 2 (없음 + running)
grep -o '#030712' $H | wc -l                           # ≥ 1 (새 배경색)
grep -o '\$71\.6' $H | head -1                         # 비용 합계 유지
grep -o 'segbar' $H | wc -l                            # ≥ 2 (CSS + 사용처)
grep -c '<script' $H                                   # 0 (JS 금지)
```
Expected: 주석의 기대값. CLI 출력은 `OK: ... (source=sample-inventory.json)`

- [ ] **Step 4: 실데이터 렌더 검증** (inventory.json 복원 후)

Run: `python3 capstone/my-infra-dashboard/scripts/build_dashboard.py`
Expected: `OK: ... (source=inventory.json)`, `<details` 수 = VPC 수(5)

- [ ] **Step 5: Commit**

```bash
git add capstone/my-infra-dashboard/scripts/build_dashboard.py
git commit -m "feat(capstone-ui): restyle dashboard to LLM Monitor dark theme"
```

---

### Task 2: 배포 + 스크린샷 갱신

**Files:**
- Modify: `capstone/my-infra-dashboard/docs/final-screenshot.png` (샘플 데이터 버전으로 갱신)

- [ ] **Step 1: 업로드 + 무효화 + 라이브 검증** — 기존 확장 Task 4 Step 1과 동일 절차(us-east-1, 스택 `my-infra-dashboard`). 검증 grep: `curl -s "$URL" | grep -o 'class="donut"' | wc -l` → 3, `grep -o '#030712' | wc -l` ≥ 1

- [ ] **Step 2: 커밋용 스크린샷 갱신 (샘플 데이터)** — inventory.json 스크래치 이동 → 재빌드(source=sample) → `file://` 전체 페이지 스크린샷(CJK 폰트 설치됨 — 한글 렌더 확인) → `docs/final-screenshot.png` 교체 → Read 도구로 검증: 도넛 3개·접이식 VPC 행·pill 배지·새 다크 팔레트·샘플 ID만 → inventory.json 복원 + 재빌드

- [ ] **Step 3: Commit**

```bash
git add capstone/my-infra-dashboard/docs/final-screenshot.png
git commit -m "feat(capstone-ui): deploy restyled dashboard, refresh sample screenshot"
```
