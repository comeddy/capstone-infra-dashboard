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

    cards = [("VPC", len(vpcs)), ("서브넷", len(subnets)),
             ("EC2", len(ec2)), ("⚠ 오픈 SG", len(open_sgs))]
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

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>My Infra Dashboard</title><style>{CSS}</style></head>
<body>
<header><h1>☁ My Infra Dashboard</h1>
<p class="meta">계정 {esc(d.get("account_id"))} · {esc(d.get("region"))} ·
스캔 {esc(d.get("scanned_at"))} · 데이터: {esc(d.get("source"))}</p></header>
<section class="cards">{card_html}</section>
<section><h2>VPC</h2>{table(["Name", "VPC ID", "CIDR", "서브넷 수"], vpc_rows)}</section>
<section><h2>서브넷</h2>{table(["Subnet ID", "CIDR", "AZ", "VPC"], subnet_rows)}</section>
<section><h2>EC2 인스턴스</h2>{table(["Instance ID", "Type", "State", "Subnet"], ec2_rows)}</section>
<section><h2>보안그룹 — 0.0.0.0/0 오픈 포트</h2>{table(["Name", "Group ID", "VPC", "오픈 포트"], sg_rows)}</section>
<footer>Generated with Claude Code · Capstone 2026</footer>
</body></html>"""


def main():
    d = load_inventory()
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(render(d))
    print(f"OK: {OUT} 생성 (source={d['source']})")


if __name__ == "__main__":
    main()
