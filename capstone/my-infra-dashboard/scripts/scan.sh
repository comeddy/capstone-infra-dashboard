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
