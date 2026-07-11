# My Infra Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AWS 계정의 인프라(VPC/서브넷/보안그룹/EC2)를 읽기 전용으로 스캔해 정적 HTML 대시보드를 생성하고 S3 + CloudFront로 배포한다.

**Architecture:** 백엔드 없는 정적 사이트. 커스텀 서브에이전트(infra-scanner)가 AWS CLI로 스캔한 `data/inventory.json`을, 커스텀 스킬(dashboard-builder)이 단일 `site/index.html`로 변환하고, CloudFormation 1장(S3+CloudFront OAC)으로 배포한다.

**Tech Stack:** bash + AWS CLI + jq (스캔), Python 3 표준 라이브러리만 (대시보드 생성), CloudFormation (배포), Playwright MCP (검증)

## Global Constraints

- 프로젝트 루트: `capstone/my-infra-dashboard/` (모든 경로는 이 루트 기준 상대 경로)
- AWS 변경(mutating) 작업은 **CloudFormation 스택 `my-infra-dashboard` 배포와 해당 버킷 `aws s3 sync`만** 허용. 그 외 AWS 호출은 전부 `describe-*`/`get-*` 읽기 전용
- 리전 기본값: `ap-northeast-2` (환경변수 `AWS_REGION`으로 재정의 가능)
- 계정 ID는 기본 마스킹 (`MASK_ACCOUNT=false`로 해제)
- 대시보드는 **단일 `site/index.html`** — 인라인 CSS/JS만, 외부 CDN 의존 금지
- Python은 표준 라이브러리만 사용 (pip install 없음)
- `data/inventory.json` 스키마는 스펙 §2 데이터 계약을 따름 (Task 2 Interfaces 참조)
- 스트레치 골(Lambda Refresh, 비용 위젯)은 이 계획의 범위 밖 — 오픈 포트 경고 위젯만 기본 포함

---

### Task 1: 프로젝트 스캐폴드 + 권한 설정

**Files:**
- Create: `capstone/my-infra-dashboard/CLAUDE.md`
- Create: `capstone/my-infra-dashboard/.claude/settings.local.json`
- Create: `capstone/my-infra-dashboard/data/sample-inventory.json`

**Interfaces:**
- Produces: `data/sample-inventory.json` — 빈 계정 폴백 데이터. Task 4의 빌더가 `data/inventory.json` 부재 시 이 파일을 읽는다. 스키마는 Task 2의 inventory 스키마와 동일.

- [ ] **Step 1: 디렉토리 구조 생성**

```bash
mkdir -p capstone/my-infra-dashboard/{.claude/agents,.claude/skills/dashboard-builder,scripts,data,site,infra}
```

- [ ] **Step 2: CLAUDE.md 작성**

`capstone/my-infra-dashboard/CLAUDE.md`:

```markdown
# My Infra Dashboard

AWS 계정 인프라를 스캔해 정적 HTML 대시보드로 시각화하고 S3+CloudFront로 배포하는 캡스톤 프로젝트.

## 구조
- `scripts/scan.sh` — 읽기 전용 AWS 스캔 → `data/inventory.json`
- `scripts/build_dashboard.py` — inventory.json → `site/index.html` (단일 파일)
- `infra/stack.yaml` — S3 + CloudFront(OAC) CloudFormation
- `.claude/agents/infra-scanner.md` — 스캔 전담 서브에이전트
- `.claude/skills/dashboard-builder/` — 대시보드 생성 스킬

## 규칙
- AWS 변경 작업은 CloudFormation 스택 `my-infra-dashboard` 배포와 해당 버킷 `aws s3 sync`만 허용. 그 외는 전부 읽기 전용(describe-*/get-*)
- 계정 ID는 기본 마스킹 (`MASK_ACCOUNT=false`로 해제)
- 대시보드는 단일 `site/index.html`, 외부 CDN 의존 금지
- `data/inventory.json`이 없으면 빌더는 `data/sample-inventory.json`으로 폴백
- .claude/settings.local.json은 보통 로컬 전용이지만, 이 프로젝트에서는 권한 실습 교육 자산으로 의도적으로 git에 커밋한다
```

- [ ] **Step 3: 읽기 전용 권한 allowlist 작성** (Ch3/Ch4 복습 포인트)

`capstone/my-infra-dashboard/.claude/settings.local.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(aws sts get-caller-identity:*)",
      "Bash(aws ec2 describe-vpcs:*)",
      "Bash(aws ec2 describe-subnets:*)",
      "Bash(aws ec2 describe-security-groups:*)",
      "Bash(aws ec2 describe-instances:*)",
      "Bash(aws cloudformation validate-template:*)",
      "Bash(aws cloudformation deploy:*)",
      "Bash(aws cloudformation describe-stacks:*)",
      "Bash(aws s3 sync:*)",
      "Bash(bash scripts/scan.sh:*)",
      "Bash(jq:*)",
      "Bash(python3:*)",
      "Bash(curl:*)"
    ],
    "deny": [
      "Bash(aws ec2 terminate-instances:*)",
      "Bash(aws ec2 delete-*:*)",
      "Bash(aws s3 rm:*)",
      "Bash(aws cloudformation delete-stack:*)"
    ]
  }
}
```

- [ ] **Step 4: 빈 계정 폴백용 샘플 인벤토리 작성**

`capstone/my-infra-dashboard/data/sample-inventory.json`:

```json
{
  "account_id": "1234********",
  "region": "ap-northeast-2",
  "scanned_at": "2026-07-11T00:00:00Z",
  "vpcs": [
    {
      "id": "vpc-0sample000000001",
      "cidr": "10.0.0.0/16",
      "name": "sample-prod-vpc",
      "subnets": [
        { "id": "subnet-0sample0000000a1", "cidr": "10.0.1.0/24", "az": "ap-northeast-2a", "vpc_id": "vpc-0sample000000001" },
        { "id": "subnet-0sample0000000c1", "cidr": "10.0.2.0/24", "az": "ap-northeast-2c", "vpc_id": "vpc-0sample000000001" }
      ]
    }
  ],
  "security_groups": [
    { "id": "sg-0sample000000001", "name": "web-sg", "vpc_id": "vpc-0sample000000001", "open_ports": [80, 443] },
    { "id": "sg-0sample000000002", "name": "internal-sg", "vpc_id": "vpc-0sample000000001", "open_ports": [] }
  ],
  "ec2_instances": [
    { "id": "i-0sample0000000001", "type": "t3.micro", "state": "running", "subnet_id": "subnet-0sample0000000a1" }
  ]
}
```

- [ ] **Step 5: 샘플 JSON 유효성 검증**

Run: `jq -e '.vpcs | length' capstone/my-infra-dashboard/data/sample-inventory.json`
Expected: `1` (exit code 0)

- [ ] **Step 6: 빈 계정용 샘플 VPC 템플릿 작성** (스펙 §5 폴백 ① — 스캔할 리소스가 아예 없는 참가자만 배포)

`capstone/my-infra-dashboard/infra/sample-vpc.yaml`:

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Description: Capstone sample VPC (empty-account fallback)

Resources:
  SampleVpc:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.99.0.0/16
      Tags: [{ Key: Name, Value: capstone-sample-vpc }]
  SubnetA:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref SampleVpc
      CidrBlock: 10.99.1.0/24
      AvailabilityZone: !Select [0, !GetAZs ""]
      Tags: [{ Key: Name, Value: capstone-sample-a }]
  SubnetC:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref SampleVpc
      CidrBlock: 10.99.2.0/24
      AvailabilityZone: !Select [2, !GetAZs ""]
      Tags: [{ Key: Name, Value: capstone-sample-c }]
```

배포(필요한 참가자만):
```bash
aws cloudformation deploy --template-file capstone/my-infra-dashboard/infra/sample-vpc.yaml \
  --stack-name capstone-sample-vpc --region ap-northeast-2
```
Expected: 1분 내 `Successfully created/updated stack - capstone-sample-vpc`

- [ ] **Step 7: Commit**

```bash
git add capstone/my-infra-dashboard/
git commit -m "feat(capstone): scaffold my-infra-dashboard with read-only permissions"
```

주의: 전역 gitignore(`~/.config/git/ignore` 등)에 `**/.claude/settings.local.json` 패턴이 있으면 git이 이 파일을 **조용히 누락**시킨다. 커밋 후 `git show --stat HEAD`로 4개 파일이 모두 들어갔는지 확인하고, `settings.local.json`이 빠졌다면 `git add -f capstone/my-infra-dashboard/.claude/settings.local.json` 후 `git commit --amend --no-edit` 한다. (이 프로젝트에서는 이 파일이 공유 교육 자산이라 의도적으로 커밋한다)

---

### Task 2: 스캔 스크립트 (scan.sh)

**Files:**
- Create: `capstone/my-infra-dashboard/scripts/scan.sh`

**Interfaces:**
- Consumes: AWS CLI 자격 증명 (환경에 설정됨), 환경변수 `AWS_REGION`(기본 ap-northeast-2), `MASK_ACCOUNT`(기본 true)
- Produces: `data/inventory.json` — 스키마:
  - `account_id: string` (마스킹 시 앞 4자리 + `********`)
  - `region: string`, `scanned_at: string` (ISO8601 UTC)
  - `vpcs: [{id, cidr, name, subnets: [{id, cidr, az, vpc_id}]}]`
  - `security_groups: [{id, name, vpc_id, open_ports: [number|"all"]}]` — open_ports는 0.0.0.0/0에 열린 포트만
  - `ec2_instances: [{id, type, state, subnet_id}]`

- [ ] **Step 1: scan.sh 작성**

`capstone/my-infra-dashboard/scripts/scan.sh`:

```bash
#!/usr/bin/env bash
# AWS 계정 읽기 전용 스캔 → data/inventory.json
set -euo pipefail
cd "$(dirname "$0")/.."

REGION="${AWS_REGION:-ap-northeast-2}"
MASK="${MASK_ACCOUNT:-true}"
mkdir -p data

ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
[ "$MASK" = "true" ] && ACCOUNT="${ACCOUNT:0:4}********"

VPCS=$(aws ec2 describe-vpcs --region "$REGION" --output json \
  --query 'Vpcs[].{id:VpcId,cidr:CidrBlock,name:(Tags[?Key==`Name`].Value|[0])}')
SUBNETS=$(aws ec2 describe-subnets --region "$REGION" --output json \
  --query 'Subnets[].{id:SubnetId,cidr:CidrBlock,az:AvailabilityZone,vpc_id:VpcId}')
SGS_RAW=$(aws ec2 describe-security-groups --region "$REGION" --output json \
  --query 'SecurityGroups[].{id:GroupId,name:GroupName,vpc_id:VpcId,ingress:IpPermissions}')
EC2=$(aws ec2 describe-instances --region "$REGION" --output json \
  --query 'Reservations[].Instances[].{id:InstanceId,type:InstanceType,state:State.Name,subnet_id:SubnetId}')

# 0.0.0.0/0 에 열린 포트만 추출
SGS=$(jq '[.[] | {id, name, vpc_id,
  open_ports: ([.ingress[]? | select(any(.IpRanges[]?; .CidrIp == "0.0.0.0/0"))
                | (.FromPort // "all")] | unique)}]' <<<"$SGS_RAW")

jq -n \
  --arg account_id "$ACCOUNT" --arg region "$REGION" \
  --arg scanned_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --argjson vpcs "$VPCS" --argjson subnets "$SUBNETS" \
  --argjson sgs "$SGS" --argjson ec2 "$EC2" '
  {account_id: $account_id, region: $region, scanned_at: $scanned_at,
   vpcs: ($vpcs | map(. as $v | $v + {subnets: ($subnets | map(select(.vpc_id == $v.id)))})),
   security_groups: $sgs,
   ec2_instances: $ec2}' > data/inventory.json

echo "OK: data/inventory.json ($(jq '.vpcs|length' data/inventory.json) VPCs, $(jq '.ec2_instances|length' data/inventory.json) EC2)"
```

- [ ] **Step 2: 실행 권한 부여 후 실행**

Run: `bash capstone/my-infra-dashboard/scripts/scan.sh`
Expected: `OK: data/inventory.json (N VPCs, M EC2)` — N/M은 계정에 따라 다름. 기본 VPC만 있어도 N≥1.

- [ ] **Step 3: 산출물 스키마 검증**

Run:
```bash
jq -e 'has("account_id") and has("vpcs") and has("security_groups") and has("ec2_instances")' \
  capstone/my-infra-dashboard/data/inventory.json
```
Expected: `true`

- [ ] **Step 4: 마스킹 동작 검증**

Run: `jq -r '.account_id' capstone/my-infra-dashboard/data/inventory.json`
Expected: `1234********` 형태 (앞 4자리 + 별표 8개)

- [ ] **Step 5: Commit** (생성물 inventory.json은 커밋하지 않음)

```bash
echo -e "data/inventory.json\nsite/index.html" > capstone/my-infra-dashboard/.gitignore
git add capstone/my-infra-dashboard/scripts/scan.sh capstone/my-infra-dashboard/.gitignore
git commit -m "feat(capstone): add read-only AWS scan script"
```

---

### Task 3: infra-scanner 서브에이전트 (Ch2 복습)

**Files:**
- Create: `capstone/my-infra-dashboard/.claude/agents/infra-scanner.md`

**Interfaces:**
- Consumes: `scripts/scan.sh` (Task 2)
- Produces: "계정 스캔해줘" 류의 요청 시 Claude Code가 자동 위임하는 서브에이전트. 산출물은 Task 2와 동일한 `data/inventory.json`.

- [ ] **Step 1: 서브에이전트 정의 작성**

`capstone/my-infra-dashboard/.claude/agents/infra-scanner.md`:

```markdown
---
name: infra-scanner
description: AWS 계정의 VPC/서브넷/보안그룹/EC2를 읽기 전용으로 스캔해 data/inventory.json을 생성한다. 사용자가 "계정 스캔", "인벤토리 갱신", "인프라 현황 수집"을 요청하면 사용.
tools: Bash, Read
---

너는 AWS 인프라 스캔 전담 에이전트다.

## 임무
1. `bash scripts/scan.sh` 를 실행한다. (다른 방법으로 스캔하지 않는다)
2. 실패하면 에러 메시지를 그대로 보고하고 멈춘다. 임의로 다른 AWS 명령을 시도하지 않는다.
3. 성공하면 `jq` 로 data/inventory.json 을 읽어 요약을 보고한다:
   VPC 수, 서브넷 수, EC2 수, 0.0.0.0/0 오픈 포트가 있는 보안그룹 수와 목록.

## 금지
- 변경(mutating) AWS 명령 절대 금지. describe-*/get-* 외에는 실행하지 않는다.
- inventory.json 을 직접 손으로 수정하지 않는다.
```

- [ ] **Step 2: 서브에이전트 동작 검증**

Claude Code 세션(프로젝트 루트 `capstone/my-infra-dashboard/`)에서 실행:

```
> 계정 스캔해줘
```

Expected: infra-scanner 서브에이전트로 위임되어 scan.sh 실행 후 "VPC N개, 서브넷 M개, EC2 K개, 오픈 SG L개" 형태의 요약 보고. (`/agents` 명령으로 infra-scanner가 목록에 보이는지도 확인)

- [ ] **Step 3: Commit**

```bash
git add capstone/my-infra-dashboard/.claude/agents/infra-scanner.md
git commit -m "feat(capstone): add infra-scanner subagent"
```

---

### Task 4: 대시보드 빌더 (스크립트 + 스킬, Ch4 복습)

**Files:**
- Create: `capstone/my-infra-dashboard/scripts/build_dashboard.py`
- Create: `capstone/my-infra-dashboard/.claude/skills/dashboard-builder/SKILL.md`

**Interfaces:**
- Consumes: `data/inventory.json` (Task 2 스키마). 부재 시 `data/sample-inventory.json` (Task 1) 폴백.
- Produces: `site/index.html` — 단일 파일 대시보드. Task 6이 이 파일을 S3에 업로드.
- CLI 계약: `python3 scripts/build_dashboard.py` → 성공 시 stdout에 `OK: <경로> 생성 (source=<파일명>)`, exit 0.

- [ ] **Step 1: 빌더 실행이 실패하는 것을 먼저 확인** (스크립트 부재 = 실패하는 테스트)

Run: `python3 capstone/my-infra-dashboard/scripts/build_dashboard.py`
Expected: FAIL — `No such file or directory`

- [ ] **Step 2: build_dashboard.py 작성**

`capstone/my-infra-dashboard/scripts/build_dashboard.py`:

```python
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
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(d))
    print(f"OK: {OUT} 생성 (source={d['source']})")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 폴백 경로 검증 (샘플 데이터)**

Run:
```bash
mv capstone/my-infra-dashboard/data/inventory.json /tmp/inv-backup.json 2>/dev/null; \
python3 capstone/my-infra-dashboard/scripts/build_dashboard.py && \
grep -c "vpc-0sample000000001" capstone/my-infra-dashboard/site/index.html
```
Expected: `OK: ... (source=sample-inventory.json)` 그리고 grep 결과 `1` 이상

- [ ] **Step 4: 실데이터 경로 검증**

Run:
```bash
mv /tmp/inv-backup.json capstone/my-infra-dashboard/data/inventory.json 2>/dev/null || \
  bash capstone/my-infra-dashboard/scripts/scan.sh
python3 capstone/my-infra-dashboard/scripts/build_dashboard.py
```
Expected: `OK: ... (source=inventory.json)`. 브라우저/미리보기로 `site/index.html`을 열어 자기 계정 VPC ID가 보이는지 확인.

- [ ] **Step 5: dashboard-builder 스킬 작성**

`capstone/my-infra-dashboard/.claude/skills/dashboard-builder/SKILL.md`:

```markdown
---
name: dashboard-builder
description: data/inventory.json을 시각화 HTML 대시보드(site/index.html)로 변환한다. 사용자가 "대시보드 만들어/갱신해", "HTML로 시각화해달라"고 요청하면 사용.
---

# Dashboard Builder

## 절차
1. `python3 scripts/build_dashboard.py` 실행. (대시보드 HTML을 처음부터 다시 작성하지 않는다 — 스크립트가 단일 소스)
2. 출력의 `source=`를 확인해 실데이터인지 샘플 폴백인지 보고한다.
3. `data/inventory.json`이 없어 샘플로 생성됐다면, infra-scanner 서브에이전트로 스캔 후 재실행을 제안한다.
4. 사용자가 위젯 추가/테마 변경을 요청하면 `scripts/build_dashboard.py`를 수정한다:
   - 색상 테마는 CSS 상수의 `:root` 변수만 수정
   - 새 위젯은 `render()`에 `<section>` 블록 추가
5. 수정 후에는 반드시 스크립트를 재실행하고 site/index.html에 기대한 문자열이 있는지 grep으로 검증한다.

## 제약
- site/index.html은 단일 파일 유지. 외부 CDN/스크립트 태그 추가 금지.
- inventory.json 스키마(계약)는 변경하지 않는다. 스키마 변경이 필요하면 scan.sh와 함께 변경해야 함을 사용자에게 알린다.
```

- [ ] **Step 6: 스킬 동작 검증**

Claude Code 세션에서:

```
> 대시보드 갱신해줘
```

Expected: dashboard-builder 스킬이 트리거되어 스크립트 실행 + source 보고.

- [ ] **Step 7: Commit**

```bash
git add capstone/my-infra-dashboard/scripts/build_dashboard.py \
        capstone/my-infra-dashboard/.claude/skills/dashboard-builder/SKILL.md
git commit -m "feat(capstone): add dashboard builder script and skill"
```

---

### Task 5: 배포 스택 (CloudFormation: S3 + CloudFront OAC)

**Files:**
- Create: `capstone/my-infra-dashboard/infra/stack.yaml`

**Interfaces:**
- Produces: CloudFormation 스택 `my-infra-dashboard` — Outputs:
  - `BucketName: string` — Task 6의 `aws s3 sync` 대상
  - `DashboardURL: string` — `https://<distribution>.cloudfront.net` 형태, 최종 검증 URL

- [ ] **Step 1: stack.yaml 작성**

`capstone/my-infra-dashboard/infra/stack.yaml`:

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Description: My Infra Dashboard - S3 + CloudFront (OAC) static hosting

Resources:
  SiteBucket:
    Type: AWS::S3::Bucket
    Properties:
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true

  OriginAccessControl:
    Type: AWS::CloudFront::OriginAccessControl
    Properties:
      OriginAccessControlConfig:
        Name: !Sub "${AWS::StackName}-oac"
        OriginAccessControlOriginType: s3
        SigningBehavior: always
        SigningProtocol: sigv4

  Distribution:
    Type: AWS::CloudFront::Distribution
    Properties:
      DistributionConfig:
        Enabled: true
        DefaultRootObject: index.html
        Origins:
          - Id: s3origin
            DomainName: !GetAtt SiteBucket.RegionalDomainName
            OriginAccessControlId: !GetAtt OriginAccessControl.Id
            S3OriginConfig:
              OriginAccessIdentity: ""
        DefaultCacheBehavior:
          TargetOriginId: s3origin
          ViewerProtocolPolicy: redirect-to-https
          CachePolicyId: 658327ea-f89d-4fab-a63d-7e88639e58f6  # Managed-CachingOptimized

  BucketPolicy:
    Type: AWS::S3::BucketPolicy
    Properties:
      Bucket: !Ref SiteBucket
      PolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: cloudfront.amazonaws.com
            Action: s3:GetObject
            Resource: !Sub "${SiteBucket.Arn}/*"
            Condition:
              StringEquals:
                AWS:SourceArn: !Sub "arn:aws:cloudfront::${AWS::AccountId}:distribution/${Distribution}"

Outputs:
  BucketName:
    Value: !Ref SiteBucket
  DashboardURL:
    Value: !Sub "https://${Distribution.DomainName}"
```

- [ ] **Step 2: 템플릿 사전 검증** (deploy-on-aws 플러그인의 `validate_cloudformation_template` MCP 도구 또는 CLI)

Run: `aws cloudformation validate-template --template-body file://capstone/my-infra-dashboard/infra/stack.yaml`
Expected: JSON 응답에 `"Description": "My Infra Dashboard - ..."` — 에러 없음

- [ ] **Step 3: 배포** (CloudFront 전파에 5~10분 소요 — 세션 1:40 이전에 반드시 시작)

Run:
```bash
aws cloudformation deploy \
  --template-file capstone/my-infra-dashboard/infra/stack.yaml \
  --stack-name my-infra-dashboard \
  --region ap-northeast-2
```
Expected: `Successfully created/updated stack - my-infra-dashboard`

- [ ] **Step 4: Outputs 확인**

Run:
```bash
aws cloudformation describe-stacks --stack-name my-infra-dashboard --region ap-northeast-2 \
  --query "Stacks[0].Outputs" --output table
```
Expected: `BucketName`과 `DashboardURL` 두 개의 출력값

- [ ] **Step 5: Commit**

```bash
git add capstone/my-infra-dashboard/infra/stack.yaml
git commit -m "feat(capstone): add S3+CloudFront deployment stack"
```

---

### Task 6: 업로드 + 최종 검증

**Files:**
- Modify: 없음 (배포·검증만)

**Interfaces:**
- Consumes: `site/index.html` (Task 4), 스택 Outputs `BucketName`/`DashboardURL` (Task 5)
- Produces: 접속 가능한 CloudFront URL + 검증 스크린샷 (성공 기준 달성)

- [ ] **Step 1: 대시보드 업로드**

Run:
```bash
BUCKET=$(aws cloudformation describe-stacks --stack-name my-infra-dashboard --region ap-northeast-2 \
  --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" --output text)
aws s3 sync capstone/my-infra-dashboard/site/ "s3://$BUCKET"
```
Expected: `upload: .../index.html to s3://.../index.html`

- [ ] **Step 2: HTTP 응답 검증**

Run:
```bash
URL=$(aws cloudformation describe-stacks --stack-name my-infra-dashboard --region ap-northeast-2 \
  --query "Stacks[0].Outputs[?OutputKey=='DashboardURL'].OutputValue" --output text)
echo "$URL" && curl -sI "$URL" | head -1
```
Expected: `HTTP/2 200`. (배포 직후 403/404면 CloudFront 전파 대기 — 2~3분 후 재시도)

참고: 버킷은 OAC로 비공개이므로 스펙에서 언급한 S3 website endpoint 1차 확인은 불가능하다.
대신 로컬 `site/index.html` 미리보기(Task 4 Step 4)가 1차 확인 역할을 하고, 최종 확인은 CloudFront URL로만 한다.

- [ ] **Step 3: 콘텐츠 정합성 검증**

Run: `curl -s "$URL" | grep -o "My Infra Dashboard" | head -1`
Expected: `My Infra Dashboard`

추가로 대시보드의 VPC 수가 실제와 일치하는지 확인:
```bash
aws ec2 describe-vpcs --region ap-northeast-2 --query 'length(Vpcs)'
```
Expected: 대시보드 VPC 카드 숫자와 동일

- [ ] **Step 4: 아키텍처 다이어그램 추가 (스펙 §2 — 시간 부족 시 생략 가능)**

Claude Code 세션에서 deploy-on-aws 플러그인의 다이어그램 스킬 사용:

```
> aws-architecture-diagram 스킬로 data/inventory.json 의 VPC 토폴로지 다이어그램을 만들어서
  site/diagram.png 로 내보내줘
```

그 다음 `scripts/build_dashboard.py`의 `render()` 마지막 `<section>` 뒤에 아래 블록을 추가하고 재실행:

```python
    diagram = ""
    if (ROOT / "site" / "diagram.png").exists():
        diagram = ('<section><h2>네트워크 토폴로지</h2>'
                   '<img src="diagram.png" alt="VPC topology" '
                   'style="max-width:100%;border-radius:12px"></section>')
```

(f-string 본문의 `<footer>` 바로 앞에 `{diagram}` 삽입. 같은 버킷에 함께 배포되는 로컬 이미지이므로 "외부 CDN 금지" 제약 위반 아님)

Run: `python3 capstone/my-infra-dashboard/scripts/build_dashboard.py && aws s3 sync capstone/my-infra-dashboard/site/ "s3://$BUCKET"`
Expected: `OK: ...` 후 diagram.png, index.html 업로드

- [ ] **Step 5: Playwright 스크린샷 (성공 증빙 겸 발표 자료)**

Claude Code 세션에서 Playwright MCP 사용:

```
> Playwright로 $URL 접속해서 전체 페이지 스크린샷을 capstone/my-infra-dashboard/docs/final-screenshot.png 로 저장해줘
```

Expected: 자기 계정 리소스가 렌더링된 대시보드 스크린샷 파일 생성

- [ ] **Step 6: 최종 Commit**

```bash
git add capstone/my-infra-dashboard/docs/
git commit -m "feat(capstone): deploy dashboard and capture verification screenshot"
```

---

## 2시간 타임라인 ↔ 태스크 매핑 (진행자용)

| 시간 | 태스크 |
|---|---|
| 0:00–0:15 | Task 1 |
| 0:15–0:40 | Task 2, Task 3 |
| 0:40–1:10 | Task 4 |
| 1:10–1:40 | Task 5 (Step 3 배포는 1:40 이전 필수 시작) |
| 1:40–2:00 | Task 6 + 결과 공유 |

빨리 끝낸 참가자: dashboard-builder 스킬(Task 4 Step 5)의 위젯 추가 절차를 활용해 자유 확장 (테마 변경, 라우팅 테이블 섹션 추가 등). 정식 확장 모듈(VPC 토폴로지 in/out 다이어그램 + 비용 추정)은 [2026-07-11-topology-cost-extension.md](./2026-07-11-topology-cost-extension.md) 참조. Lambda Refresh 스트레치는 진행자 재량으로 별도 안내.
