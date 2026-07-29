#!/usr/bin/env bash
# capstone-infra-dashboard의 drafts/bsky/ 에서 아직 게시하지 않은 초안을 Bluesky에 게시한다.
# 클라우드 루틴이 초안을 커밋하면(매일 00:00 UTC), 이 스크립트가 01:00 UTC systemd 타이머로 게시한다.
# 게시 이력은 ~/.local/state/bsky-poster/posted.log 에 기록 (성공한 초안만 — 실패 시 다음 실행 때 재시도).
set -euo pipefail

REPO=/home/ec2-user/capstone-infra-dashboard
STATE_DIR="$HOME/.local/state/bsky-poster"
STATE="$STATE_DIR/posted.log"
PW_FILE="$HOME/.config/bsky/app-password"

mkdir -p "$STATE_DIR"
touch "$STATE"

if [[ ! -s "$PW_FILE" ]]; then
  echo "오류: $PW_FILE 이 비어 있거나 없습니다 — Bluesky 앱 비밀번호를 넣어주세요 (chmod 600)." >&2
  exit 1
fi

cd "$REPO"
git pull --ff-only --quiet

shopt -s nullglob
posted=0
for draft in drafts/bsky/*.md; do
  name=$(basename "$draft")
  grep -qxF "$name" "$STATE" && continue
  echo "[$(date -u +%FT%TZ)] 게시 시도: $name"
  if BSKY_APP_PASSWORD=$(cat "$PW_FILE") python3 scripts/post-bsky-thread.py "$draft"; then
    echo "$name" >> "$STATE"
    posted=$((posted + 1))
    echo "[$(date -u +%FT%TZ)] 게시 완료: $name"
  else
    # state 미기록 → 다음 타이머 실행 때 재시도. 스레드 일부만 올라간 경우 중복 가능성 있음(로그 확인).
    echo "[$(date -u +%FT%TZ)] 게시 실패: $name" >&2
    exit 1
  fi
done
echo "[$(date -u +%FT%TZ)] 완료 — 신규 게시 ${posted}건"
