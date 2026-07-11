#!/usr/bin/env python3
"""data/inventory.json → site/index.html 단일 파일 대시보드 생성.
inventory.json 부재 시 sample-inventory.json 폴백."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INV = ROOT / "data" / "inventory.json"
SAMPLE = ROOT / "data" / "sample-inventory.json"
OUT = ROOT / "site" / "index.html"

CSS = """
:root { --bg:#0f172a; --panel:#1e293b; --text:#e2e8f0; --sub:#94a3b8;
        --accent:#38bdf8; --warn:#f87171; --ok:#4ade80; }
* { box-sizing:border-box; margin:0; }
body { background:var(--bg); color:var(--text);
       font-family:'Segoe UI',Pretendard,sans-serif; padding:2rem; }
header h1 { color:var(--accent); font-size:1.6rem; }
.meta { color:var(--sub); font-size:.85rem; margin-top:.3rem; }
.cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
         gap:1rem; margin:1.5rem 0; }
.card { background:var(--panel); border-radius:12px; padding:1.2rem; text-align:center; }
.card .num { font-size:2rem; font-weight:700; color:var(--accent); }
.card .label { color:var(--sub); font-size:.85rem; margin-top:.3rem; }
section { margin-bottom:2rem; }
h2 { font-size:1.1rem; margin-bottom:.6rem; border-left:3px solid var(--accent);
     padding-left:.5rem; }
h3 { font-size:.95rem; color:var(--sub); margin:.8rem 0 .2rem; }
table { width:100%; border-collapse:collapse; background:var(--panel);
        border-radius:8px; overflow:hidden; font-size:.9rem; }
th, td { padding:.55rem .8rem; text-align:left; }
th { background:#334155; color:var(--sub); font-weight:600; }
tr:nth-child(even) td { background:#243449; }
.warn { background:var(--warn); color:#111; border-radius:6px;
        padding:.1rem .5rem; margin-right:.3rem; font-weight:700; }
.ok { color:var(--ok); }
.empty { color:var(--sub); text-align:center; }
footer { color:var(--sub); font-size:.8rem; text-align:center; margin-top:2rem; }
"""


def load_inventory():
    src = INV if INV.exists() else SAMPLE
    data = json.loads(src.read_text())
    data["source"] = src.name
    return data


def esc(v):
    return html.escape(str(v if v is not None else "-"))


ARROW_IN = "#38bdf8"
ARROW_OUT = "#fb923c"
ROUTE_COLOR = {"public": "#4ade80", "private": "#fb923c", "isolated": "#64748b"}


def fmt_usd(v):
    if v is None:
        return "$—"
    return f"${v:,.1f}/월"


def monthly_sum(items):
    nums = [x.get("monthly_usd") for x in items if isinstance(x.get("monthly_usd"), (int, float))]
    return round(sum(nums), 1) if nums else None


def svg_node(x, y, w, lines, stroke):
    txt = "".join(
        f'<text x="{x + 8}" y="{y + 16 + n * 14}" font-size="10" fill="#e2e8f0">{t}</text>'
        for n, t in enumerate(lines))
    return (f'<rect x="{x}" y="{y}" width="{w}" height="50" rx="6" '
            f'fill="#334155" stroke="{stroke}"/>{txt}')


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

    p = [f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
         f'style="width:100%;max-width:{width}px;display:block;margin:.5rem 0">',
         '<defs>'
         f'<marker id="ain" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
         f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{ARROW_IN}"/></marker>'
         f'<marker id="aout" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
         f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{ARROW_OUT}"/></marker>'
         '</defs>']

    igw = vpc.get("igw_id")
    if igw:
        p.append(svg_node(10, 20, 120, ["Internet"], ARROW_IN))
        p.append(svg_node(10, 100, 120, ["IGW", esc(igw)], ARROW_IN))
        p.append(svg_arrow(60, 70, 60, 98, ARROW_IN, "ain"))       # in: Internet→IGW
        p.append(svg_arrow(80, 100, 80, 72, ARROW_OUT, "aout"))    # out: IGW→Internet

    nat_pos = {}
    y = 20
    for r, rh in zip(rows, row_hs):
        for j, s in enumerate(r):
            x = LANE + j * (SUB_W + GAP)
            color = ROUTE_COLOR.get(s.get("route"), "#64748b")
            p.append(f'<rect x="{x}" y="{y}" width="{SUB_W}" height="{sub_h(s)}" rx="8" '
                     f'fill="#1e293b" stroke="{color}" stroke-dasharray="4 3"/>')
            p.append(f'<text x="{x + 8}" y="{y + 16}" font-size="10" fill="{color}">'
                     f'{esc(s.get("id"))} · {esc(s.get("cidr"))} · {esc(s.get("route"))}</text>')
            ny = y + 26
            items, extra, snats = contents(s)
            for i in items:
                ports = ",".join(str(v) for v in i.get("in_ports", [])) or "-"
                cost = fmt_usd(i.get("monthly_usd"))
                if i.get("state") != "running":
                    cost += f' ({esc(i.get("state"))})'
                p.append(svg_node(x + 10, ny, SUB_W - 20,
                                  [f'{esc(i.get("id"))} · {esc(i.get("type"))}',
                                   f'in:{esc(ports)} out:{esc(i.get("out", "-"))}', cost],
                                  "#38bdf8"))
                ny += NODE
            if extra:
                p.append(f'<text x="{x + 12}" y="{ny + 14}" font-size="10" '
                         f'fill="#94a3b8">+{extra} more</text>')
                ny += NODE
            for n in snats:
                p.append(svg_node(x + 10, ny, SUB_W - 20,
                                  ["NAT " + esc(n.get("id")), fmt_usd(n.get("monthly_usd"))],
                                  ARROW_OUT))
                nat_pos[n.get("id")] = (x + 10, ny + 25)
                ny += NODE
            if igw and s.get("route") == "public":
                p.append(svg_arrow(130, 120, x - 2, y + 20, ARROW_IN, "ain"))  # in: IGW→public
            if s.get("route") == "private" and vpc_nats:
                tx, ty = nat_pos.get(vpc_nats[0].get("id"), (130, 125))
                p.append(svg_arrow(x - 2, y + 40, tx, ty, ARROW_OUT, "aout"))  # out: private→NAT
        y += rh + GAP
    if igw and vpc_nats and vpc_nats[0].get("id") in nat_pos:
        tx, ty = nat_pos[vpc_nats[0].get("id")]
        p.append(svg_arrow(tx, ty, 132, 125, ARROW_OUT, "aout"))               # out: NAT→IGW

    p.append("</svg>")
    return "".join(p)


def table(headers, rows):
    thead = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows
    ) or f'<tr><td colspan="{len(headers)}" class="empty">리소스 없음</td></tr>'
    return f"<table><thead><tr>{thead}</tr></thead><tbody>{body}</tbody></table>"


def render(d):
    vpcs = d.get("vpcs", [])
    subnets = [s for v in vpcs for s in v.get("subnets", [])]
    sgs = d.get("security_groups", [])
    ec2 = d.get("ec2_instances", [])
    open_sgs = [g for g in sgs if g.get("open_ports")]

    nats = d.get("nat_gateways", [])
    total = monthly_sum(ec2 + nats)
    total_label = f"${total:,.1f}" if total is not None else "$—"
    cards = [("VPC", len(vpcs)), ("서브넷", len(subnets)),
             ("EC2", len(ec2)), ("⚠ 오픈 SG", len(open_sgs)),
             ("월 추정 비용(USD)", total_label)]
    card_html = "".join(
        f'<div class="card"><div class="num">{n}</div>'
        f'<div class="label">{esc(t)}</div></div>' for t, n in cards)

    vpc_rows = [[esc(v.get("name")), esc(v.get("id")), esc(v.get("cidr")),
                 str(len(v.get("subnets", [])))] for v in vpcs]
    subnet_rows = [[esc(s.get("id")), esc(s.get("cidr")), esc(s.get("az")),
                    esc(s.get("vpc_id"))] for s in subnets]
    ec2_rows = [[esc(i.get("id")), esc(i.get("type")), esc(i.get("state")),
                 esc(i.get("subnet_id"))] for i in ec2]
    sg_rows = []
    for g in sgs:
        ports = g.get("open_ports") or []
        badge = "".join(f'<span class="warn">{esc(p)}</span>' for p in ports) \
            or '<span class="ok">없음</span>'
        sg_rows.append([esc(g.get("name")), esc(g.get("id")),
                        esc(g.get("vpc_id")), badge])

    topo = []
    for v in vpcs:
        sub_ids = {s.get("id") for s in v.get("subnets", [])}
        v_ec2 = [i for i in ec2 if i.get("subnet_id") in sub_ids]
        v_nats = [n for n in nats if n.get("vpc_id") == v.get("id")]
        svg = svg_topology(v, nats, v_ec2)
        if not svg:
            continue
        vtotal = monthly_sum(v_ec2 + v_nats)
        topo.append(f'<h3>{esc(v.get("name"))} · {esc(v.get("id"))} · '
                    f'월 추정 {fmt_usd(vtotal)}</h3>{svg}')
    topo_section = ""
    if topo:
        note = esc(d.get("pricing_note", ""))
        topo_section = ('<section><h2>네트워크 토폴로지 (in/out) &amp; 비용</h2>'
                        + "".join(topo)
                        + f'<p class="meta">비용 기준: {note}</p></section>')

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>My Infra Dashboard</title><style>{CSS}</style></head>
<body>
<header><h1>☁ My Infra Dashboard</h1>
<p class="meta">계정 {esc(d.get("account_id"))} · {esc(d.get("region"))} ·
스캔 {esc(d.get("scanned_at"))} · 데이터: {esc(d.get("source"))}</p></header>
<section class="cards">{card_html}</section>
{topo_section}
<section><h2>VPC</h2>{table(["Name", "VPC ID", "CIDR", "서브넷 수"], vpc_rows)}</section>
<section><h2>서브넷</h2>{table(["Subnet ID", "CIDR", "AZ", "VPC"], subnet_rows)}</section>
<section><h2>EC2 인스턴스</h2>{table(["Instance ID", "Type", "State", "Subnet"], ec2_rows)}</section>
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
