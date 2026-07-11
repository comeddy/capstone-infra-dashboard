# 확장 모듈 설계: VPC 토폴로지(in/out) + 비용 대시보드

- **날짜**: 2026-07-11
- **기반**: My Infra Dashboard 캡스톤 (2026-07-11-infra-dashboard-capstone-design.md)
- **성격**: 빨리 끝낸 참가자용 스트레치 골의 정식 확장 모듈. 메인 2시간 플랜은 변경하지 않음
- **상태**: 승인됨

## 1. 목표

기존 대시보드에 VPC마다 **객체 연결관계(in/out) 다이어그램**과 **월 비용 추정**을 추가한다.

성공 기준: 배포된 대시보드에서 각 VPC 카드에 (a) Internet↔IGW↔서브넷↔EC2/NAT의
in/out 경로가 그려진 SVG, (b) EC2·NAT 노드별 월 추정 비용 배지, (c) VPC별·계정 전체
비용 합계가 보인다.

## 2. 데이터 확장 (scan.sh)

추가 스캔 (전부 읽기 전용):

| 호출 | 용도 |
|---|---|
| `ec2 describe-internet-gateways` | VPC별 `igw_id` |
| `ec2 describe-nat-gateways` | `nat_gateways[]` (id, subnet_id, vpc_id) |
| `ec2 describe-route-tables` | 서브넷별 `route` 판정 |
| `describe-instances`의 SG 필드 | EC2별 `sg_ids` |
| `pricing get-products` (us-east-1 엔드포인트) | 인스턴스 타입·NAT 시간당 단가 |

**route 판정 규칙**: 서브넷에 연결된(명시 연결 없으면 VPC main) 라우트 테이블의
0.0.0.0/0 대상이 `igw-*`면 `public`, `nat-*`면 `private`, 그 외/없음이면 `isolated`.
igw/nat 이외의 기본 라우트 — VGW/TGW/피어링/어플라이언스 ENI 등 — 는 설계상 전부 isolated로 표시된다. "인터넷 경로 없음"이 아니라 "igw/nat 경로 아님"의 의미.

**비용 규칙**: 온디맨드 Linux/Shared 단가 × 730h = 월 추정(USD, 소수 1자리).
running 상태 인스턴스만 비용 계산(stopped는 $0 + "stopped" 표기). NAT는 시간당
단가 × 730 (데이터 처리량 제외 — 각주로 명시). Pricing 조회 실패 시 해당 값 `null`.

**inventory.json 스키마 추가분** (기존 필드는 불변 — 하위 호환):

```json
{
  "vpcs": [{ "igw_id": "igw-... | null",
             "subnets": [{ "route": "public|private|isolated" }] }],
  "nat_gateways": [{ "id": "", "subnet_id": "", "vpc_id": "", "monthly_usd": 32.9 }],
  "ec2_instances": [{ "sg_ids": [""], "in_ports": [22], "out": "all|ports",
                      "monthly_usd": 7.6 }],
  "pricing_note": "on-demand estimate, 730h/mo, data transfer excluded | unavailable"
}
```

`in_ports` = 인스턴스에 연결된 SG들의 0.0.0.0/0 오픈 ingress 포트 합집합.
`out` = egress가 전체 허용이면 `"all"`, 아니면 포트 목록 문자열.

## 3. 다이어그램 (build_dashboard.py → 인라인 SVG)

- VPC마다 `<svg>` 하나를 파이썬으로 계산해 삽입. JS 없음, 외부 리소스 없음 (기존
  단일 파일·no-CDN 제약 유지)
- 레이아웃: 좌측 외부 레인(Internet, IGW), 우측 서브넷 그리드(public 행 위,
  private/isolated 행 아래). EC2·NAT 노드는 서브넷 박스 안에 세로 스택
- 화살표: in = 하늘색(--accent), out = 주황색(#fb923c). Internet→IGW→public 서브넷
  (in), private 서브넷→NAT→IGW→Internet (out)
- 노드 주석: EC2 = 타입, `in:22,80`, `out:all`, `$7.6/월`. NAT = `$32.9/월`.
  오픈 포트는 기존 warn(빨강) 스타일 재사용
- 요약 카드 5개로 확장: VPC / 서브넷 / EC2 / ⚠오픈 SG / **$월 추정 합계**
- VPC 섹션 헤더에 VPC별 합계. 페이지 하단에 pricing_note 각주
- 빈 케이스: IGW 없는 VPC는 외부 레인 생략, 리소스 없는 서브넷은 빈 박스,
  pricing null이면 배지에 `$—`

## 4. 산출물 구조

- `capstone/my-infra-dashboard/scripts/scan.sh` 확장 (기존 스키마 필드 불변)
- `capstone/my-infra-dashboard/scripts/build_dashboard.py` 확장 (SVG 생성 함수 추가)
- `data/sample-inventory.json` 확장 (public+private 서브넷, NAT 1개 포함하도록 보강
  — 다이어그램의 모든 요소가 샘플로도 시연되게)
- 플랜: `docs/superpowers/plans/2026-07-11-topology-cost-extension.md` (신규)
- 메인 플랜의 스트레치 골 문단에서 확장 플랜 참조 (한 줄 수정)

## 5. 검증

1. 확장된 샘플 inventory로 빌드 → SVG 노드/화살표/비용 배지 존재를 grep으로 확인
2. 실계정 재스캔(us-east-1) → 재빌드 → 로컬 확인
3. s3 sync + CloudFront `/*` 무효화 → curl 200 + 콘텐츠 확인 → 스크린샷
   (커밋용 스크린샷은 기존 원칙대로 **샘플 데이터** 버전만)

## 6. 리스크

- Pricing API 응답의 PriceList는 문자열화된 JSON — jq `fromjson`으로 파싱, 실패 시
  null 폴백 (기능 전체가 죽지 않게 `|| echo null` 가드)
- 라우트 테이블 명시 연결이 없는 서브넷은 main 라우트 테이블 상속 — 판정 로직에 반영
- 리소스 많은 VPC의 SVG 높이 — 서브넷당 EC2 표시 상한 8개, 초과분 "+N more" 노드
- 라이브 페이지의 실계정 노출 정보가 증가(경로+비용) — 리허설 후 스택 정리 권장 유지
