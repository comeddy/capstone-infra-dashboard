---
name: dashboard-builder
description: data/inventory.json을 시각화 HTML 대시보드(site/index.html)로 변환한다. 사용자가 "대시보드 만들어/갱신해", "HTML로 시각화해달라"고 요청하면 사용.
---

# Dashboard Builder

## 절차
1. `python3 scripts/build_dashboard.py` 실행. (대시보드 HTML을 처음부터 다시 작성하지 않는다 — 스크립트가 단일 소스)
2. 출력의 `source=`를 확인해 실데이터인지 샘플 폴백인지 보고한다.
3. `data/inventory.json`이 없어 샘플로 생성됐다면, infra-scanner 서브에이전트로 스캔 후 재실행을 제안한다.
4. 사용자가 위젯 추가/테마 변경을 요청하면 `scripts/build_dashboard.py`를 수정한다:
   - 색상 테마는 CSS 상수의 `:root` 변수만 수정
   - 새 위젯은 `render()`에 `<section>` 블록 추가
5. 수정 후에는 반드시 스크립트를 재실행하고 site/index.html에 기대한 문자열이 있는지 grep으로 검증한다.

## 제약
- site/index.html은 단일 파일 유지. 외부 CDN/스크립트 태그 추가 금지.
- inventory.json 스키마(계약)는 변경하지 않는다. 스키마 변경이 필요하면 scan.sh와 함께 변경해야 함을 사용자에게 알린다.
