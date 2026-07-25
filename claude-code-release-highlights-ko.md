# Claude Code 릴리스 하이라이트 (한글 정리)

> Claude Code 0.2.x 초기 버전부터 최신 2.1.207까지의 주요 변화를 한눈에.
> 세부 버그픽스는 생략하고, 사용 흐름을 바꾼 굵직한 기능과 모델 출시 위주로 정리했습니다.

---

## 🤖 모델 출시 타임라인

| 시점 | 모델 | 메모 |
|------|------|------|
| v1.0.0 | **Sonnet 4 / Opus 4** | Claude Code 정식 출시(GA)와 함께 |
| v1.0.69 | Opus 4.1 | |
| v2.0.17 | **Haiku 4.5** | Explore 서브에이전트 도입 |
| v2.0.51 | **Opus 4.5** | 데스크톱 앱 출시, 사용량 한도 개편 |
| v2.1.32 | **Opus 4.6** | Agent Teams(리서치 프리뷰) |
| v2.1.45 | Sonnet 4.6 | 1M 컨텍스트 |
| v2.1.111 | **Opus 4.7** | `xhigh` effort 레벨 추가, Auto 모드 |
| v2.1.154 | **Opus 4.8** | 동적 워크플로우(dynamic workflows) 도입 |
| v2.1.170 | **Fable 5 (Mythos)** | Mythos급 신규 모델 |
| v2.1.197 | **Sonnet 5** | 1M 컨텍스트, Claude Code 기본 모델로 |

---

## 🚀 핵심 기능 진화

### 커맨드 · 스킬 · 플러그인
- **커스텀 슬래시 커맨드** (v0.2.31): `.claude/commands/`의 마크다운을 커맨드로
- **커스텀 서브에이전트** (v1.0.60): `/agents`로 전문화된 에이전트 생성
- **Skills** (v2.0.20) → 이후 슬래시 커맨드와 통합(v2.1.3), 핫 리로드(v2.1.0)
- **플러그인 시스템** (v2.0.12): 마켓플레이스에서 커맨드·에이전트·훅·MCP 설치
- **AskUserQuestion** 인터랙티브 질문 도구 (v2.0.21)

### 계획 · 실행 흐름
- **Thinking 모드** (v0.2.44): "think" / "think harder" / "ultrathink"
- **Todo 리스트** (v0.2.93): 작업 추적으로 조직화
- **Plan 모드 · Plan 서브에이전트** (v2.0.28)
- **`/rewind`** 대화·코드 되돌리기 (v2.0.0)
- **자동 컨텍스트 압축(compaction)** (v0.2.47): 무한 대화 길이

### 백그라운드 · 멀티 에이전트
- **백그라운드 bash 명령** (v1.0.71, Ctrl-b)
- **백그라운드 에이전트** (v2.0.60): 작업 중에도 에이전트 실행
- **Agent Teams**(리서치 프리뷰, v2.1.32): 멀티 에이전트 협업
- **동적 워크플로우 / ultracode** (v2.1.154~2.1.160): 수십~수백 에이전트 오케스트레이션
- **`claude agents` 에이전트 뷰** (v2.1.139): 모든 세션을 한 목록에서 관리

### 훅(Hooks)
- **훅 출시** (v1.0.38): PreToolUse, PostToolUse 등
- SessionStart / SessionEnd / UserPromptSubmit / PreCompact 등 이벤트 지속 확장
- PreToolUse가 입력 수정 가능 (v2.0.10), HTTP 훅 (v2.1.63)

### 세션 · 재개
- **`--continue` / `--resume`** 대화 재개 (v0.2.93)
- **명명된 세션** (v2.0.64): `/rename`, `/resume <name>`
- **`/stats`, `/usage`, `/context`** 사용량·컨텍스트 진단

### 권한 · 자동화
- **`/permissions`** 도구 권한 관리
- **Auto 모드** (v2.1.111~): 분류기 기반 자동 승인, 안전장치 지속 강화
- **샌드박스 모드** (v2.0.24): Bash 도구 샌드박싱 (Linux/Mac)

---

## 🌐 플랫폼 · 통합

- **네이티브 VS Code 확장** (v2.0.0), JetBrains, 데스크톱 앱, 웹(claude.ai/code)
- **Remote Control** (v2.1.58~): 모바일·웹에서 세션 이어받기
- **Claude in Chrome** (v2.1.72 베타 → v2.1.198 GA): 브라우저 제어
- **음성 입력(Voice)** 지원, 다국어 STT 확대 (v2.1.69)
- **MCP** 전방위 지원: OAuth, HTTP/SSE, 리소스 @멘션, 툴 검색(ToolSearch) 자동화
- **3rd-party**: Amazon Bedrock, Google Vertex AI, Microsoft Foundry, Mantle 지원

---

## 🎨 사용성 · 렌더링

- **버터처럼 부드러운 터미널 렌더러** 재작성 (v2.0.10~)
- **커스텀 상태줄(statusline)** (v1.0.71), **커스텀 테마** (v2.1.118)
- **커스텀 키바인딩** (`/keybindings`, v2.1.18)
- **풀스크린 모드** (`/tui fullscreen`), 마우스 지원, 선택 시 자동 복사
- **Vim 모드** 대폭 확장 (visual 모드, 텍스트 오브젝트 등)
- 한글·CJK, RTL, 이모지 렌더링 다수 개선

---

## 📌 요약 한 줄

> CLI 자동완성 도구에서 시작해 **멀티 에이전트 오케스트레이션 플랫폼**으로 진화 —
> 모델은 Sonnet/Opus 4 → Opus 4.8 → Fable 5 → Sonnet 5로, 실행은 단일 세션에서
> 백그라운드·병렬·원격까지 확장되었습니다.
