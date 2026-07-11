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
