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
