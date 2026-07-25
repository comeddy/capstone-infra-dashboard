# Bluesky 스레드 초안 — CHANGELOG v1.0.0 (@pai-playbook.bsky.social)

`---` 구분선으로 나뉜 각 블록이 스레드의 포스트 1개가 됩니다 (각 300자 이내).

---

📦 My Infra Dashboard v1.0.0 릴리스

AWS 계정을 읽기 전용으로 스캔해 단일 HTML 대시보드로 시각화하는 캡스톤 프로젝트입니다.

• VPC·서브넷·보안그룹·EC2·IGW/NAT·라우트 테이블 수집 (계정 ID 기본 마스킹)
• Claude Code 서브에이전트 + 스킬로 구동

🧵 이어서 ↓

---

✨ 주요 기능

• VPC별 in/out 토폴로지 SVG — public/private/isolated 라우트 판정
• AWS Pricing API 기반 월 비용 추정 (부분합 마커)
• S3 + CloudFront(OAC) 호스팅 스택
• 자격 증명 없어도 샘플 데이터 폴백으로 체험 가능
• 3개 모듈 워크샵 가이드 포함

---

🛠 개선 & 보안

• 다크 테마 UI: 도넛 요약 카드, 접이식 VPC 섹션, pill 배지
• 보안그룹 egress 병합 버그, 부분 비용 합계 표시 수정
• 스크린샷은 샘플 데이터 전용으로 교체 — 실계정 토폴로지 비노출
• 데모 후 스택 정리 필수 (대시보드 공개 접근 가능)

https://github.com/comeddy/capstone-infra-dashboard
