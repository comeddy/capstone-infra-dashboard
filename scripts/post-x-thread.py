#!/usr/bin/env python3
"""X(트위터)에 마크다운 초안을 스레드로 게시한다. (post-bsky-thread.py의 X 대응판)

사용법:
    X_API_KEY=... X_API_SECRET=... X_ACCESS_TOKEN=... X_ACCESS_SECRET=... \
        python3 scripts/post-x-thread.py drafts/x/2026-07-30.md
    python3 scripts/post-x-thread.py drafts/x/2026-07-30.md --dry-run   # 게시 없이 검증·미리보기

초안 형식: '---' 구분선으로 나뉜 각 블록이 트윗 1개. '#'으로 시작하는 첫 블록(머리말)은 건너뜀.

길이 규칙(X 가중치): 한글·CJK·이모지 = 2, URL = 23 고정, 그 외 = 1 — 합계 280 이내.
Bluesky(순수 300자)와 달라서 X 전용 초안(drafts/x/)을 쓴다.
인증: OAuth 1.0a user context (developer.x.com 앱의 4개 키) — 표준 라이브러리로 서명.
"""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import time
import urllib.parse
import urllib.request

API_URL = "https://api.x.com/2/tweets"
MAX_WEIGHTED = 280
URL_WEIGHT = 23  # t.co 단축 후 고정 가중치
URL_RE = re.compile(r"https?://[^\s)]+")

# X 문서 기준 '가중치 1' 유니코드 구간 — 이 밖의 문자(한글·CJK·이모지)는 2로 센다
_LIGHT = ((0x0000, 0x10FF), (0x2000, 0x200D), (0x2010, 0x201F), (0x2032, 0x2037))


def weighted_len(text: str) -> int:
    total, pos = 0, 0
    for m in URL_RE.finditer(text):
        for ch in text[pos:m.start()]:
            total += 1 if any(a <= ord(ch) <= b for a, b in _LIGHT) else 2
        total += URL_WEIGHT
        pos = m.end()
    for ch in text[pos:]:
        total += 1 if any(a <= ord(ch) <= b for a, b in _LIGHT) else 2
    return total


def parse_draft(path):
    raw = open(path, encoding="utf-8").read()
    blocks = [b.strip() for b in re.split(r"^---\s*$", raw, flags=re.M) if b.strip()]
    posts = [b for b in blocks if not b.startswith("#")]
    for i, p in enumerate(posts, 1):
        w = weighted_len(p)
        if w > MAX_WEIGHTED:
            sys.exit(f"오류: {i}번째 트윗이 가중 {w}자로 {MAX_WEIGHTED}를 초과합니다 (한글=2, URL=23).")
    return posts


def _enc(s: str) -> str:
    return urllib.parse.quote(str(s), safe="~-._")


def oauth1_header(url: str, creds: dict) -> str:
    """POST + JSON 본문 요청의 OAuth 1.0a HMAC-SHA1 Authorization 헤더 (본문은 서명 제외)."""
    p = {
        "oauth_consumer_key": creds["X_API_KEY"],
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": creds["X_ACCESS_TOKEN"],
        "oauth_version": "1.0",
    }
    param_str = "&".join(f"{_enc(k)}={_enc(v)}" for k, v in sorted(p.items()))
    base = "&".join(["POST", _enc(url), _enc(param_str)])
    key = f'{_enc(creds["X_API_SECRET"])}&{_enc(creds["X_ACCESS_SECRET"])}'
    sig = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    p["oauth_signature"] = sig
    return "OAuth " + ", ".join(f'{_enc(k)}="{_enc(v)}"' for k, v in sorted(p.items()))


def post_tweet(text: str, creds: dict, reply_to=None) -> str:
    payload: dict = {"text": text}
    if reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to}
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": oauth1_header(API_URL, creds)},
    )
    with urllib.request.urlopen(req) as res:
        return json.load(res)["data"]["id"]


def main():
    draft = sys.argv[1] if len(sys.argv) > 1 else "drafts/x/draft.md"
    dry_run = "--dry-run" in sys.argv
    posts = parse_draft(draft)

    print(f"{len(posts)}개 트윗 스레드:")
    for i, p in enumerate(posts, 1):
        print(f"\n--- [{i}/{len(posts)}] (가중 {weighted_len(p)}/280) ---\n{p}")
    if dry_run:
        return

    creds = {}
    for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"):
        creds[k] = os.environ.get(k) or sys.exit(f"\n오류: {k} 환경변수가 필요합니다 (developer.x.com 앱 키).")

    first = parent = None
    for i, text in enumerate(posts, 1):
        tweet_id = post_tweet(text, creds, reply_to=parent)
        first = first or tweet_id
        parent = tweet_id
        print(f"게시 완료 [{i}/{len(posts)}]: https://x.com/paiplaybook/status/{tweet_id}")
        time.sleep(2)  # 연속 게시 rate limit 완화

    print(f"\n✅ 스레드: https://x.com/paiplaybook/status/{first}")


if __name__ == "__main__":
    main()
