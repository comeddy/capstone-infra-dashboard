# Topology + Cost Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 My Infra Dashboard에 VPC별 in/out 연결관계 SVG 다이어그램과 월 비용 추정(Pricing API)을 추가한다.

**Architecture:** scan.sh가 IGW/NAT/라우트테이블/인스턴스-SG 매핑/단가를 추가 수집해 inventory.json 스키마를 확장(기존 필드 불변)하고, build_dashboard.py가 VPC마다 인라인 SVG 토폴로지와 비용 배지를 렌더한다. JS 없음, 외부 리소스 없음.

**Tech Stack:** bash + AWS CLI + jq (스캔·단가), Python 3 표준 라이브러리 (SVG 생성), 기존 S3+CloudFront 스택 재사용 (인프라 변경 없음)

## Global Constraints

- 기반 캡스톤의 Global Constraints 전부 유지 (프로젝트 루트 `capstone/my-infra-dashboard/`, 단일 index.html, 인라인 CSS/JS만, Python 표준 라이브러리만, 계정 마스킹 기본)
- **기존 inventory.json 필드는 이름·형태 불변** — 새 필드만 추가 (구버전 빌더와 하위 호환)
- Pricing API는 항상 `--region us-east-1` 엔드포인트, 단가는 스캔 리전(`regionCode=$REGION`) 기준
- 모든 Pricing 조회는 실패 시 `null` 폴백 — 스캔 전체가 죽지 않아야 함
- 비용 = 온디맨드 단가 × 730h, 소수 1자리 반올림. running 인스턴스만 계산(stopped는 0). NAT는 시간당 요금만(데이터 처리 제외)
- route 판정: 0.0.0.0/0 라우트가 igw-* → `public`, nat-* → `private`, 그 외 → `isolated` (명시 연결 없는 서브넷은 VPC main 라우트 테이블 상속) (igw/nat 이외의 기본 라우트 — VGW/TGW/피어링/어플라이언스 ENI 등 — 는 설계상 전부 isolated로 표시된다. "인터넷 경로 없음"이 아니라 "igw/nat 경로 아님"의 의미)
- in 화살표 색 `#38bdf8`, out 화살표 색 `#fb923c`

---

### Task 1: 샘플 인벤토리 확장 (스키마 계약 선행 고정)

**Files:**
- Modify: `capstone/my-infra-dashboard/data/sample-inventory.json` (전체 교체)

**Interfaces:**
- Produces: 확장 스키마의 레퍼런스 인스턴스. Task 2의 scan.sh와 Task 3의 빌더가 이 스키마를 따른다. 추가 필드: `pricing_note`(최상위), `vpcs[].igw_id`, `vpcs[].subnets[].route`, `nat_gateways[]`(최상위 배열), `security_groups[].out`, `ec2_instances[].{sg_ids,in_ports,out,monthly_usd}`

- [ ] **Step 1: sample-inventory.json 전체 교체**

```json
{
  "account_id": "1234********",
  "region": "ap-northeast-2",
  "scanned_at": "2026-07-11T00:00:00Z",
  "pricing_note": "on-demand estimate, 730h/mo, data transfer excluded",
  "vpcs": [
    {
      "id": "vpc-0sample000000001",
      "cidr": "10.0.0.0/16",
      "name": "sample-prod-vpc",
      "igw_id": "igw-0sample000000001",
      "subnets": [
        { "id": "subnet-0sample0000000a1", "cidr": "10.0.1.0/24", "az": "ap-northeast-2a", "vpc_id": "vpc-0sample000000001", "route": "public" },
        { "id": "subnet-0sample0000000c1", "cidr": "10.0.2.0/24", "az": "ap-northeast-2c", "vpc_id": "vpc-0sample000000001", "route": "private" }
      ]
    }
  ],
  "nat_gateways": [
    { "id": "nat-0sample000000001", "subnet_id": "subnet-0sample0000000a1", "vpc_id": "vpc-0sample000000001", "monthly_usd": 43.1 }
  ],
  "security_groups": [
    { "id": "sg-0sample000000001", "name": "web-sg", "vpc_id": "vpc-0sample000000001", "open_ports": [80, 443], "out": "all" },
    { "id": "sg-0sample000000002", "name": "internal-sg", "vpc_id": "vpc-0sample000000001", "open_ports": [], "out": "all" }
  ],
  "ec2_instances": [
    { "id": "i-0sample0000000001", "type": "t3.micro", "state": "running", "subnet_id": "subnet-0sample0000000a1", "sg_ids": ["sg-0sample000000001"], "in_ports": [80, 443], "out": "all", "monthly_usd": 9.5 },
    { "id": "i-0sample0000000002", "type": "t3.small", "state": "running", "subnet_id": "subnet-0sample0000000c1", "sg_ids": ["sg-0sample000000002"], "in_ports": [], "out": "all", "monthly_usd": 19.0 }
  ]
}
```

- [ ] **Step 2: 유효성 + 하위 호환 검증**

Run: `jq -e '.vpcs[0].igw_id and .nat_gateways[0].monthly_usd and (.ec2_instances[1].subnet_id == "subnet-0sample0000000c1")' capstone/my-infra-dashboard/data/sample-inventory.json`
Expected: `true`

Run (기존 빌더가 확장 샘플로도 여전히 동작하는지 — inventory.json이 없는 상태에서):
```bash
python3 capstone/my-infra-dashboard/scripts/build_dashboard.py
```
Expected: `OK: ... (source=sample-inventory.json)` — 기존 빌더는 새 필드를 무시하므로 성공해야 함 (실패 시 하위 호환이 깨진 것)

- [ ] **Step 3: Commit**

```bash
git add capstone/my-infra-dashboard/data/sample-inventory.json
git commit -m "feat(capstone-ext): extend sample inventory with topology and cost fields"
```

---

### Task 2: scan.sh 확장 (토폴로지 수집 + Pricing)

**Files:**
- Modify: `capstone/my-infra-dashboard/scripts/scan.sh` (전체 교체)
- Modify: `capstone/my-infra-dashboard/.claude/settings.local.json` (allow 4개 추가)

**Interfaces:**
- Consumes: AWS 자격 증명, `AWS_REGION`/`MASK_ACCOUNT` 환경변수 (기존과 동일)
- Produces: Task 1 스키마의 `data/inventory.json`. 파생 규칙: `route`(Global Constraints 참조), `in_ports` = 연결 SG들의 open_ports 합집합, `out` = 연결 SG 중 하나라도 egress 전체 허용이면 `"all"`, 없으면 `"none"`, 그 외 포트 목록 문자열, `monthly_usd` = 단가×730 반올림(소수1) 또는 null(단가 조회 실패)/0(stopped)

- [ ] **Step 1: settings.local.json의 allow 배열에 4개 항목 추가** (`"Bash(aws ec2 describe-instances:*)"` 항목 바로 뒤에)

```json
      "Bash(aws ec2 describe-internet-gateways:*)",
      "Bash(aws ec2 describe-nat-gateways:*)",
      "Bash(aws ec2 describe-route-tables:*)",
      "Bash(aws pricing get-products:*)",
```

참고: Pricing 조회에는 IAM 액션 pricing:GetProducts가 필요하다(ec2:Describe*와 별개). 권한이 없으면 스캔은 죽지 않고 pricing_note가 "pricing unavailable", 비용이 "$—"로 표시된다.

- [ ] **Step 2: scan.sh 전체 교체**

```bash
#!/usr/bin/env bash
# AWS 계정 읽기 전용 스캔 → data/inventory.json (토폴로지 + 비용 확장판)
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
  --query 'SecurityGroups[].{id:GroupId,name:GroupName,vpc_id:VpcId,ingress:IpPermissions,egress:IpPermissionsEgress}')
EC2=$(aws ec2 describe-instances --region "$REGION" --output json \
  --query 'Reservations[].Instances[].{id:InstanceId,type:InstanceType,state:State.Name,subnet_id:SubnetId,sg_ids:SecurityGroups[].GroupId}')
IGWS=$(aws ec2 describe-internet-gateways --region "$REGION" --output json \
  --query 'InternetGateways[].{id:InternetGatewayId,vpc_id:(Attachments[0].VpcId)}')
NATS=$(aws ec2 describe-nat-gateways --region "$REGION" --output json \
  --query 'NatGateways[?State==`available`].{id:NatGatewayId,subnet_id:SubnetId,vpc_id:VpcId}')
RTBS=$(aws ec2 describe-route-tables --region "$REGION" --output json \
  --query 'RouteTables[].{vpc_id:VpcId,main:(Associations[?Main]|[0].Main),subnet_ids:Associations[].SubnetId,gw:(Routes[?DestinationCidrBlock==`0.0.0.0/0`]|[0].GatewayId),nat:(Routes[?DestinationCidrBlock==`0.0.0.0/0`]|[0].NatGatewayId)}')

# ---- 비용 단가 (Pricing API, us-east-1 엔드포인트; 실패 시 null 폴백) ----
price_ec2() {
  aws pricing get-products --region us-east-1 --service-code AmazonEC2 --max-results 1 \
    --filters "Type=TERM_MATCH,Field=instanceType,Value=$1" \
              "Type=TERM_MATCH,Field=regionCode,Value=$REGION" \
              "Type=TERM_MATCH,Field=operatingSystem,Value=Linux" \
              "Type=TERM_MATCH,Field=tenancy,Value=Shared" \
              "Type=TERM_MATCH,Field=preInstalledSw,Value=NA" \
              "Type=TERM_MATCH,Field=capacitystatus,Value=Used" \
    --output json 2>/dev/null \
  | jq -r '.PriceList[0] // empty | fromjson | .terms.OnDemand
           | to_entries[0].value.priceDimensions | to_entries[0].value.pricePerUnit.USD' \
    2>/dev/null || true
}

PRICES='{}'
for t in $(jq -r '[.[].type] | unique | .[]' <<<"$EC2"); do
  p=$(price_ec2 "$t")
  PRICES=$(jq --arg t "$t" --argjson p "${p:-null}" '. + {($t): $p}' <<<"$PRICES")
done

NAT_HOURLY=$(aws pricing get-products --region us-east-1 --service-code AmazonEC2 --max-results 100 \
  --filters "Type=TERM_MATCH,Field=productFamily,Value=NAT Gateway" \
            "Type=TERM_MATCH,Field=regionCode,Value=$REGION" \
  --output json 2>/dev/null \
  | jq -r '[.PriceList[] | fromjson
            | select(.product.attributes.usagetype | endswith("NatGateway-Hours"))][0] // empty
           | .terms.OnDemand | to_entries[0].value.priceDimensions
           | to_entries[0].value.pricePerUnit.USD' 2>/dev/null || true)

NOTE="on-demand estimate, 730h/mo, data transfer excluded"
if [ -z "$NAT_HOURLY" ] && jq -e 'length == 0 or all(.[]; . == null)' <<<"$PRICES" >/dev/null; then
  NOTE="pricing unavailable"
fi

# ---- 조립: 파생 필드 계산 후 inventory.json 생성 ----
jq -n \
  --arg account_id "$ACCOUNT" --arg region "$REGION" \
  --arg scanned_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg pricing_note "$NOTE" \
  --argjson vpcs "$VPCS" --argjson subnets "$SUBNETS" --argjson sgs_raw "$SGS_RAW" \
  --argjson ec2 "$EC2" --argjson igws "$IGWS" --argjson nats "$NATS" --argjson rtbs "$RTBS" \
  --argjson prices "$PRICES" --argjson nat_hourly "${NAT_HOURLY:-null}" '

  def openports(rules): [rules[]? | select(any(.IpRanges[]?; .CidrIp == "0.0.0.0/0")) | (.FromPort // "all")] | unique;

  def egress_out(rules):
    if any(rules[]?; .IpProtocol == "-1" and any(.IpRanges[]?; .CidrIp == "0.0.0.0/0")) then "all"
    else ([rules[]? | select(any(.IpRanges[]?; .CidrIp == "0.0.0.0/0")) | (.FromPort // "all") | tostring]
          | unique | join(",") | if . == "" then "none" else . end)
    end;

  def route_of($sid; $vid):
    ([$rtbs[] | select((.subnet_ids // []) | index($sid))] | first) as $ex
    | ($ex // ([$rtbs[] | select(.vpc_id == $vid and .main == true)] | first)) as $rtb
    | if $rtb == null then "isolated"
      elif (($rtb.gw // "") | startswith("igw-")) then "public"
      elif (($rtb.nat // "") | startswith("nat-")) then "private"
      else "isolated" end;

  def monthly($hourly): if $hourly == null then null else (($hourly | tonumber) * 7300 | round / 10) end;

  ($sgs_raw | map({id, name, vpc_id, open_ports: openports(.ingress), out: egress_out(.egress)})) as $sgs
  | {
    account_id: $account_id, region: $region, scanned_at: $scanned_at, pricing_note: $pricing_note,
    vpcs: ($vpcs | map(. as $v | $v + {
      igw_id: (([$igws[] | select(.vpc_id == $v.id)] | first | .id) // null),
      subnets: ($subnets | map(select(.vpc_id == $v.id) | . + {route: route_of(.id; $v.id)}))
    })),
    nat_gateways: ($nats | map(. + {monthly_usd: monthly($nat_hourly)})),
    security_groups: $sgs,
    ec2_instances: ($ec2 | map(. as $i | $i + {
      in_ports: ([$sgs[] | select(. as $g | ($i.sg_ids // []) | index($g.id)) | .open_ports[]] | unique),
      out: (([$sgs[] | select(. as $g | ($i.sg_ids // []) | index($g.id)) | .out]) as $outs
            | ([$outs[] | split(",")[] | select(. != "none")] | unique) as $toks
            | if ($toks | index("all")) then "all"
              elif ($toks | length) == 0 then "none"
              else ($toks | join(",")) end),
      monthly_usd: (if .state == "running" then monthly($prices[.type] // null) else 0 end)
    }))
  }' > data/inventory.json

echo "OK: data/inventory.json ($(jq '.vpcs|length' data/inventory.json) VPCs, $(jq '.ec2_instances|length' data/inventory.json) EC2, $(jq '.nat_gateways|length' data/inventory.json) NAT)"
```

- [ ] **Step 3: 문법 검증**

Run: `bash -n capstone/my-infra-dashboard/scripts/scan.sh`
Expected: exit 0

- [ ] **Step 4: jq 파생 로직 스텁 검증** (스크래치 디렉토리에 임시 스크립트 — 커밋 금지)

스텁 입력으로 route/egress/in_ports/monthly 파생만 검증한다. scan.sh의 jq 프로그램(assembly 부분)을 파일로 추출해 재사용하거나 동일 내용을 복사하고, 다음을 커버하는 스텁을 만든다:
- 명시 연결 rtb가 igw 라우트 → public / main rtb가 nat 라우트인 미연결 서브넷 → private / 0.0.0.0/0 없음 → isolated
- egress `-1`+0.0.0.0/0 → "all", egress 규칙 없음 → "none"
- 인스턴스에 SG 2개 연결 시 in_ports 합집합
- prices에 있는 타입(running) → 단가×730 소수1, 없는 타입 → null, stopped → 0
- NAT monthly = nat_hourly×730 소수1

각 항목을 `jq -e` 종료코드로 단언. Expected: 전부 PASS

- [ ] **Step 5: 실계정 스캔 검증** (권한 있는 환경에서; 없으면 이 단계는 보류로 기록)

Run: `AWS_REGION=us-east-1 bash capstone/my-infra-dashboard/scripts/scan.sh`
Expected: `OK: data/inventory.json (N VPCs, M EC2, K NAT)`

Run:
```bash
jq -e '[.vpcs[].subnets[].route] | all(. == "public" or . == "private" or . == "isolated")' capstone/my-infra-dashboard/data/inventory.json
jq -r '.pricing_note' capstone/my-infra-dashboard/data/inventory.json
jq '[.ec2_instances[] | select(.state == "running") | .monthly_usd] | map(type)' capstone/my-infra-dashboard/data/inventory.json
```
Expected: `true` / `on-demand estimate...` (권한 없으면 `pricing unavailable`) / running 인스턴스 전부 `"number"` (pricing 실패 시 `"null"` 허용)

- [ ] **Step 6: Commit**

```bash
git add capstone/my-infra-dashboard/scripts/scan.sh capstone/my-infra-dashboard/.claude/settings.local.json
git commit -m "feat(capstone-ext): scan topology (igw/nat/routes) and pricing"
```

---

### Task 3: build_dashboard.py — SVG 토폴로지 + 비용

**Files:**
- Modify: `capstone/my-infra-dashboard/scripts/build_dashboard.py`

**Interfaces:**
- Consumes: Task 1/2의 확장 inventory 스키마 (필드 부재 시에도 동작해야 함 — `.get()` 폴백)
- Produces: `site/index.html`에 (a) 5번째 요약 카드 "월 추정 비용", (b) "네트워크 토폴로지 (in/out) & 비용" 섹션 — VPC마다 `<svg>` + VPC별 비용 합계 헤더, (c) 푸터에 pricing_note. CLI 계약(stdout `OK: ...`) 불변

- [ ] **Step 1: 다음 코드를 build_dashboard.py에 추가** — `esc()` 함수 정의 바로 뒤에 삽입:

```python
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


def has_unpriced(items):
    return any(x.get("monthly_usd") is None for x in items)


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
```

주의: private→NAT 화살표는 NAT 노드가 나중 행에서 그려질 수 있어 좌표 미확정일 수 있다.
위 코드는 public 행을 먼저 그리므로(rows 순서), NAT는 public 서브넷 안에서 먼저 배치되어
좌표가 확정된 후 private 행이 그려진다 — rows 순서 `(pub, rest)`가 이 가정을 보장한다.

또한 NAT가 첫 칼럼이 아닌 경우 private→NAT 화살표가 중간 서브넷 박스 위를 가로지른다 — 다이어그램이 복잡한 멀티 AZ VPC에서는 시각적으로 겹칠 수 있으며, 이는 알려진 표시 한계다(정확성에는 영향 없음).

- [ ] **Step 2: render() 확장** — 기존 `render()` 함수에서 세 곳 수정:

(a) `cards` 리스트를 다음으로 교체 (비용 카드 추가):

```python
    nats = d.get("nat_gateways", [])
    total = monthly_sum(ec2 + nats)
    if total is None:
        total_label = "$—"
    elif has_unpriced(ec2 + nats):
        total_label = f"${total:,.1f}*"
    else:
        total_label = f"${total:,.1f}"
    cards = [("VPC", len(vpcs)), ("서브넷", len(subnets)),
             ("EC2", len(ec2)), ("⚠ 오픈 SG", len(open_sgs)),
             ("월 추정 비용(USD)", total_label)]
```

(b) 토폴로지 섹션 생성 — `sg_rows` 계산 블록 다음, `return` 직전에 추가:

```python
    topo = []
    for v in vpcs:
        sub_ids = {s.get("id") for s in v.get("subnets", [])}
        v_ec2 = [i for i in ec2 if i.get("subnet_id") in sub_ids]
        v_nats = [n for n in nats if n.get("vpc_id") == v.get("id")]
        svg = svg_topology(v, nats, v_ec2)
        if not svg:
            continue
        vtotal = monthly_sum(v_ec2 + v_nats)
        vtotal_label = fmt_usd(vtotal)
        if vtotal is not None and has_unpriced(v_ec2 + v_nats):
            vtotal_label += "*"
        topo.append(f'<h3>{esc(v.get("name"))} · {esc(v.get("id"))} · '
                    f'월 추정 {vtotal_label}</h3>{svg}')
    topo_section = ""
    if topo:
        note = esc(d.get("pricing_note", ""))
        topo_section = ('<section><h2>네트워크 토폴로지 (in/out) &amp; 비용</h2>'
                        + "".join(topo)
                        + f'<p class="meta">비용 기준: {note} · * = 일부 리소스 단가 미조회</p></section>')
```

(c) f-string 본문에서 `<section class="cards">{card_html}</section>` 바로 다음 줄에 `{topo_section}` 삽입. CSS의 `h2` 규칙 아래에 다음 추가:

```css
h3 { font-size:.95rem; color:var(--sub); margin:.8rem 0 .2rem; }
```

- [ ] **Step 3: 샘플 폴백 렌더 검증** (data/inventory.json을 스크래치로 임시 이동 후)

```bash
python3 capstone/my-infra-dashboard/scripts/build_dashboard.py
grep -o "네트워크 토폴로지" capstone/my-infra-dashboard/site/index.html | head -1
grep -o 'marker-end="url(#ain)"' capstone/my-infra-dashboard/site/index.html | wc -l
grep -o 'marker-end="url(#aout)"' capstone/my-infra-dashboard/site/index.html | wc -l
grep -o 'NAT nat-0sample000000001' capstone/my-infra-dashboard/site/index.html | head -1
grep -o '\$9\.5/월' capstone/my-infra-dashboard/site/index.html | head -1
grep -o '월 추정 비용(USD)' capstone/my-infra-dashboard/site/index.html | head -1
```
Expected: 섹션 존재 / in 화살표 ≥ 2 (Internet→IGW, IGW→public) / out 화살표 ≥ 3 (IGW→Internet, private→NAT, NAT→IGW) / NAT 노드 존재 / EC2 비용 배지 존재 / 비용 카드 존재. 샘플 총합 카드는 $71.6 (9.5+19.0+43.1)

- [ ] **Step 4: 실데이터 렌더 검증** (inventory.json 복원 후)

Run: `python3 capstone/my-infra-dashboard/scripts/build_dashboard.py`
Expected: `OK: ... (source=inventory.json)`. IGW 없는 VPC는 레인 없이, isolated 서브넷은 회색 테두리로 렌더되는지 grep/육안 확인

- [ ] **Step 5: Commit**

```bash
git add capstone/my-infra-dashboard/scripts/build_dashboard.py
git commit -m "feat(capstone-ext): render per-VPC in/out topology SVG with cost badges"
```

---

### Task 4: 배포 + 검증 + 교재 연결

**Files:**
- Modify: `docs/superpowers/plans/2026-07-11-my-infra-dashboard.md` (스트레치 골 문단 1곳)
- Modify: `capstone/my-infra-dashboard/docs/final-screenshot.png` (샘플 데이터 버전으로 갱신)

**Interfaces:**
- Consumes: Task 5 스택 Outputs (기존 배포 재사용 — 인프라 변경 없음), Task 3의 site/index.html

- [ ] **Step 1: 업로드 + 무효화 + 검증** (배포된 환경에서; 스택 없으면 보류 기록)

```bash
BUCKET=$(aws cloudformation describe-stacks --stack-name my-infra-dashboard --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" --output text)
URL=$(aws cloudformation describe-stacks --stack-name my-infra-dashboard --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='DashboardURL'].OutputValue" --output text)
DIST=$(aws cloudformation describe-stack-resources --stack-name my-infra-dashboard --region us-east-1 \
  --query "StackResources[?LogicalResourceId=='Distribution'].PhysicalResourceId" --output text)
aws s3 sync capstone/my-infra-dashboard/site/ "s3://$BUCKET"
aws cloudfront create-invalidation --distribution-id "$DIST" --paths "/*"
sleep 30 && curl -s "$URL" | grep -o "네트워크 토폴로지" | head -1
```
Expected: `네트워크 토폴로지` — 라이브 반영 확인

- [ ] **Step 2: 커밋용 스크린샷 갱신 (반드시 샘플 데이터 버전)** — inventory.json을 스크래치로 이동 → 재빌드(source=sample) → 로컬 `file://` 렌더를 스크린샷해 `docs/final-screenshot.png` 교체 → inventory.json 복원 + 재빌드. 스크린샷에 토폴로지 SVG와 비용 배지가 보여야 함

- [ ] **Step 3: 메인 플랜의 스트레치 문단 교체** — 파일 끝 "빨리 끝낸 참가자:" 문단의 마지막 문장을 다음으로 교체:

기존: `Lambda Refresh·비용 위젯 스트레치는 진행자 재량으로 별도 안내.`
신규: `정식 확장 모듈(VPC 토폴로지 in/out 다이어그램 + 비용 추정)은 [2026-07-11-topology-cost-extension.md](./2026-07-11-topology-cost-extension.md) 참조. Lambda Refresh 스트레치는 진행자 재량으로 별도 안내.`

- [ ] **Step 4: Commit**

```bash
git add capstone/my-infra-dashboard/docs/final-screenshot.png docs/superpowers/plans/2026-07-11-my-infra-dashboard.md
git commit -m "feat(capstone-ext): deploy topology+cost dashboard, refresh sample screenshot"
```

보안 주의: 배포된 대시보드는 인증 없이 공개되며, 이제 실계정의 라우팅 구조·오픈 포트·비용까지 노출한다. 리허설/데모 후 반드시 스택을 정리한다(버킷 비우기 → aws cloudformation delete-stack --stack-name my-infra-dashboard). 계정 마스킹(MASK_ACCOUNT=true 기본)은 유지한다.
