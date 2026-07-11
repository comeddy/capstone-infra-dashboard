# 캡스톤 설계: My Infra Dashboard — 2시간 미니 프로젝트

- **날짜**: 2026-07-11
- **대상 워크샵**: Claude Code Deep Dive Workshop (20260703 에디션) 마지막 세션
- **참가자**: 인프라/네트워크 엔지니어 (코딩 경험 적음, AWS 지식 강함)
- **상태**: 승인됨

## 1. 목표와 성공 기준

각 참가자가 Claude Code를 지휘해 **자기 AWS 계정의 네트워크/인프라 현황을 시각화한
대시보드를 만들고, S3 + CloudFront로 실제 배포**한다.

**성공 기준 (단일)**: 세션 종료 시 CloudFront URL을 브라우저에서 열면
자기 계정의 실제 리소스(VPC, 서브넷, 보안그룹, EC2)가 보이는 대시보드가 표시된다.

참가자마다 계정 내용이 다르므로 결과물은 자연히 각자 고유하다.
추가 개별화 요소로 테마 선택과 스트레치 골 위젯을 제공한다.

## 2. 아키텍처

백엔드 없는 정적 사이트 구조. 배포 실패 지점을 최소화하는 것이 핵심 설계 결정이다.

```
[커스텀 서브에이전트: infra-scanner]
  AWS CLI (describe-* 읽기 전용) → data/inventory.json
        ↓
[커스텀 스킬: dashboard-builder]
  inventory.json → site/index.html (단일 파일, 인라인 CSS/JS)
        ↓
[aws-architecture-diagram 스킬]
  VPC 토폴로지 다이어그램 → site/에 포함
        ↓
[deploy-on-aws 플러그인]
  CloudFormation 1장: S3 버킷 + CloudFront(OAC) → aws s3 sync → 배포
        ↓
[Playwright MCP]
  배포된 URL 스크린샷으로 최종 검증
```

### 컴포넌트

| 컴포넌트 | 역할 | 산출물 |
|---|---|---|
| `infra-scanner` 서브에이전트 | AWS CLI로 계정 리소스 스캔 (읽기 전용) | `data/inventory.json` |
| `dashboard-builder` 스킬 | inventory.json을 시각화 HTML로 변환 | `site/index.html` |
| 배포 스택 (CloudFormation) | S3 버킷 + CloudFront 배포(OAC) | CloudFront URL |
| 검증 단계 | Playwright로 배포 URL 스크린샷 | 성공 증빙 |

### 데이터 계약: inventory.json

스캐너와 대시보드 빌더 사이의 인터페이스. 최소 스키마:

```json
{
  "account_id": "123456789012 (마스킹 옵션)",
  "region": "ap-northeast-2",
  "scanned_at": "ISO8601",
  "vpcs": [{ "id": "", "cidr": "", "name": "", "subnets": [...] }],
  "security_groups": [{ "id": "", "name": "", "open_ports": [...] }],
  "ec2_instances": [{ "id": "", "type": "", "state": "", "subnet_id": "" }]
}
```

## 3. 워크샵 자산 활용 매핑

| 워크샵 챕터 | 캡스톤에서 재사용 |
|---|---|
| Ch2 (Agents & Subagents) | `infra-scanner` 서브에이전트 직접 작성 |
| Ch3/Ch4 (Admin/Settings) | 읽기 전용 permissions 설정 (`Bash(aws ec2 describe-*)` 등 allowlist) |
| Ch4 (Skills) | `dashboard-builder` 스킬 작성 |
| Ch5 (CLI) | 헤드리스 모드 스캔 자동화 (스트레치) |
| 랩 제공 MCP/플러그인 | deploy-on-aws (배포·다이어그램·비용), Playwright (검증) |

## 4. 2시간 타임라인

| 시간 | 단계 | 산출물 |
|---|---|---|
| 0:00–0:15 | 프로젝트 폴더 + CLAUDE.md 작성, IAM 읽기 권한 확인 | CLAUDE.md, settings.local.json |
| 0:15–0:40 | `infra-scanner` 서브에이전트 작성 → 계정 스캔 | data/inventory.json |
| 0:40–1:10 | `dashboard-builder` 스킬로 HTML 생성, 로컬 미리보기 | site/index.html |
| 1:10–1:40 | CloudFormation 배포 + `aws s3 sync` 업로드 | CloudFront URL |
| 1:40–2:00 | 다이어그램 추가, Playwright 검증, 스트레치/결과 공유 | 스크린샷, 발표 |

## 5. 에러 처리와 리스크 대응

- **빈 계정**: 리소스가 거의 없는 참가자용 폴백 2종 — ① 샘플 VPC CloudFormation(1분 배포),
  ② 사전 제공 샘플 inventory.json
- **CloudFront 전파 지연(5~10분)**: 배포는 1:40 이전 시작으로 타임박스.
  대기 중 S3 website endpoint를 1차 확인 URL로 사용
- **민감정보**: 계정 ID 마스킹 옵션 기본 제공. 서브에이전트는 describe-* 읽기 전용
  권한만 allowlist에 등록 (권한 설정 자체가 Ch3/Ch4 복습 실습)
- **속도 편차**: 스트레치 골 3종 — ① Lambda + Function URL "Refresh" 버튼,
  ② 비용 위젯 (awspricing MCP), ③ 보안그룹 오픈 포트 경고 위젯

## 6. 검증 (테스트 전략)

1. **로컬**: `site/index.html`을 브라우저/미리보기로 열어 inventory 데이터 렌더링 확인
2. **배포 후**: Playwright MCP로 CloudFront URL 접속 → 스크린샷 저장 (성공 증빙 겸 발표 자료)
3. **데이터 정합성**: 대시보드의 VPC/서브넷 수가 `aws ec2 describe-vpcs` 결과와 일치하는지 확인

## 7. 검토했던 대안

- **옵션 B — 서버리스 일일 점검 봇**: 실무 직결이지만 결과물이 눈에 덜 보여(리포트/이메일)
  데모 임팩트 약함 → 탈락
- **옵션 C — AgentCore 기반 인프라 Q&A 에이전트**: 가장 화려하지만 코딩 비중이 높아
  인프라 엔지니어에게 2시간이 빠듯 → 스트레치 골의 원형으로만 남김
