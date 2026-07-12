# Changelog

<a href="#english"><img src="https://img.shields.io/badge/lang-English-blue.svg" alt="English"></a>
<a href="#korean"><img src="https://img.shields.io/badge/lang-한국어-red.svg" alt="Korean"></a>

---

<a id="english"></a>

# English

All notable changes to this project are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-07-12

### Added

- Add read-only AWS account scanner (`scan.sh`) collecting VPCs, subnets, security groups, EC2, IGW/NAT, and route tables with account-ID masking by default
- Add `infra-scanner` subagent and `dashboard-builder` skill for Claude Code, with a read-only permission allowlist
- Add single-file HTML dashboard builder (`build_dashboard.py`) with sample-data fallback for accounts without credentials
- Add S3 + CloudFront (OAC) CloudFormation hosting stack and a sample-VPC fallback template for empty accounts
- Add per-VPC in/out topology SVG diagrams with public/private/isolated route judgment
- Add monthly cost estimates from the AWS Pricing API with null fallback and partial-sum markers
- Add three-module workshop guide: design specs and step-by-step implementation plans (base dashboard, topology + cost, UI restyle)

### Changed

- Change dashboard visual language to a dark theme with donut summary cards, collapsible per-VPC sections, and pill status badges

### Fixed

- Fix security-group egress merge contaminating port lists with a literal "none" token
- Fix silent partial cost totals by marking them with an asterisk when some resources are unpriced

### Security

- Replace the committed screenshot with a sample-data-only version to avoid exposing real account topology
- Document mandatory stack teardown after demos, since the deployed dashboard is publicly reachable

[Unreleased]: https://github.com/comeddy/capstone-infra-dashboard/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/comeddy/capstone-infra-dashboard/releases/tag/v1.0.0

---

<a id="korean"></a>

# 한국어

이 프로젝트의 주요 변경 사항을 이 파일에 기록합니다. 형식은 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)를 따르며, [Semantic Versioning](https://semver.org/spec/v2.0.0.html)을 준수합니다.

## [Unreleased]

## [1.0.0] - 2026-07-12

### Added

- VPC, 서브넷, 보안그룹, EC2, IGW/NAT, 라우트 테이블을 수집하고 계정 ID를 기본 마스킹하는 읽기 전용 AWS 계정 스캐너(`scan.sh`) 추가
- Claude Code용 `infra-scanner` 서브에이전트와 `dashboard-builder` 스킬, 읽기 전용 권한 allowlist 추가
- 자격 증명 없는 계정을 위한 샘플 데이터 폴백을 갖춘 단일 파일 HTML 대시보드 빌더(`build_dashboard.py`) 추가
- S3 + CloudFront(OAC) CloudFormation 호스팅 스택과 빈 계정용 샘플 VPC 폴백 템플릿 추가
- public/private/isolated 라우트 판정을 포함한 VPC별 in/out 토폴로지 SVG 다이어그램 추가
- null 폴백과 부분합 마커를 갖춘 AWS Pricing API 기반 월 비용 추정 추가
- 3개 모듈 워크샵 가이드(설계 스펙 + 단계별 실습 가이드: 기본 대시보드, 토폴로지 + 비용, UI 리스타일) 추가

### Changed

- 대시보드 시각 언어를 도넛 요약 카드, 접이식 VPC 섹션, pill 상태 배지를 갖춘 다크 테마로 변경

### Fixed

- 보안그룹 egress 병합 시 포트 목록에 "none" 토큰이 섞이는 문제 수정
- 일부 리소스 단가 미조회 시 부분 합계에 별표 마커를 표시하도록 수정

### Security

- 실계정 토폴로지 노출을 막기 위해 커밋된 스크린샷을 샘플 데이터 전용 버전으로 교체
- 배포된 대시보드가 공개 접근 가능하므로 데모 후 스택 정리 필수 사항을 문서화

[Unreleased]: https://github.com/comeddy/capstone-infra-dashboard/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/comeddy/capstone-infra-dashboard/releases/tag/v1.0.0
