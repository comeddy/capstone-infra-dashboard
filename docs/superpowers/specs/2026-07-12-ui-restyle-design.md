# 확장 모듈 설계: LLM Monitor 스타일 UI 리스타일

- **날짜**: 2026-07-12
- **레퍼런스**: https://llm-monitor.whchoi.net/parity (Amazon Bedrock LLM Monitor — Next.js/Tailwind, gray-950 다크 테마)
- **기반**: My Infra Dashboard + topology-cost-extension
- **상태**: 승인됨

## 1. 목표

대시보드의 시각 언어를 레퍼런스와 동일한 계열로 교체한다(풀 리스타일).
**데이터 스키마·scan.sh·CLI 계약은 불변** — `build_dashboard.py`의 렌더 계층만 교체한다.

성공 기준: 배포된 대시보드가 (a) gray-950 다크 팔레트 + 라운드 패널, (b) 도넛 링
요약 카드 3장, (c) VPC별 접이식 섹션 + 세그먼트 바, (d) pill 상태 배지를 보여준다.

## 2. 디자인 토큰

| 토큰 | 값 |
|---|---|
| 배경 / 패널 / 보더 | `#030712` / `#111827` / `#1f2937` |
| 본문 / 보조 텍스트 | `#f9fafb` / `#9ca3af` |
| 액센트 | `#3b82f6` (blue-500) |
| 상태 3단계 | ok `#34d399` (emerald) / warn `#fbbf24` (amber) / danger `#fb7185` (rose) |
| radius | 카드 14px, 배지·칩 999px(pill) |
| 숫자 | `font-variant-numeric: tabular-nums` |

route 색 재매핑: public → emerald, private → amber, isolated → gray(`#6b7280`).
SVG 화살표: in → `#60a5fa`(blue-400), out → `#fb923c`(유지).

## 3. 구조 요소 (레퍼런스 → 대시보드 매핑)

- **헤더**: 좌측 브랜드, 우측 메타(계정/리전/스캔시각/데이터 소스)를 pill 칩으로. 하단 1px 보더
- **요약 카드 5장 → 도넛 링 카드 3장** (인라인 SVG `stroke-dasharray` 링, 라이브러리 없음):
  1. **네트워크** — 도넛: 서브넷 public/private/isolated 구성비, 중앙 서브넷 수. 불릿: Public/Private/Isolated/NAT 수
  2. **컴퓨트** — 도넛: EC2 running 비율(중앙 %). 불릿: Running/Stopped 수 + **월 추정 비용**(`*` 마커 규칙 유지)
  3. **보안** — 도넛: 오픈 포트 없는 SG 비율(중앙 HEALTH %). 불릿: 오픈 SG/전체 SG/대표 오픈 포트
- **VPC 토폴로지 → `<details class="vpc" open>` 접이식** (JS 없음): summary 행 = ▸ 토글 + VPC 이름/ID + **3색 세그먼트 바**(서브넷 구성) + 월 비용. 본문 = 토폴로지 SVG. 기본 전부 열림(스크린샷·인쇄 대응)
- **테이블**: 라운드 컨테이너 + `#1f2937` 구분선, 헤더 uppercase 캡션. 서브넷 테이블에 route pill 열 추가, EC2 테이블에 state pill + 월 추정 열 추가
- **pill 배지**: 오픈 포트 → rose, 없음/running → emerald, stopped/isolated → gray, private route → amber

## 4. 불변 조건

- 단일 index.html, 인라인 CSS/SVG만, **JS 금지**(접이식은 `<details>` 네이티브)
- inventory.json 스키마, scan.sh, CLI 계약(`OK: ... (source=...)`) 불변
- 필드 부재 시 `.get()` 폴백으로 동작(하위 호환), 계정 마스킹·`$—`·`*` 부분합 마커 규칙 유지
- 기존 topology-cost-extension 플랜 문서는 수정하지 않음(참가자는 구 스타일로 완주) — 리스타일은 별도 플랜의 3번째 모듈. `build_dashboard.py`는 플랜에 **전체 교체 리스팅**으로 수록해 드리프트 방지

## 5. 검증·배포

1. 샘플 렌더: 도넛 3개, `<details>` = VPC 수, pill·segbar·`#030712` 존재, `$71.6` 합계 유지, CLI 계약 grep
2. 실데이터 렌더(us-east-1) → 라이브 배포(s3 sync + CloudFront 무효화) → curl 검증
3. 커밋용 스크린샷은 **샘플 데이터** 버전으로 갱신(CJK 폰트 설치됨)

## 6. 리스크

- 도넛 링의 0-분모(EC2 0대, SG 0개) → 중앙 `—` 표시, 링은 트랙만
- `<details>` 기본 마커 브라우저 편차 → `summary::marker`/`list-style:none` 제거 후 커스텀 ▸
- 다크 배경 대비 SVG 노드 가독성 → 노드 fill `#1f2937`, 텍스트 `#e5e7eb`로 조정
