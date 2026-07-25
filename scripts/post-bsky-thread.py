#!/usr/bin/env python3
"""Bluesky에 마크다운 초안을 스레드로 게시한다.

사용법:
    BSKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx python3 scripts/post-bsky-thread.py bsky-news-draft.md
    python3 scripts/post-bsky-thread.py bsky-news-draft.md --dry-run   # 게시 없이 미리보기

초안 형식: '---' 구분선으로 나뉜 각 블록이 포스트 1개.
'#'으로 시작하는 첫 블록(머리말)은 건너뛴다.
"""

import json
import os
import re
import sys
import urllib.request

HANDLE = "pai-playbook.bsky.social"
PDS = "https://bsky.social"
MAX_LEN = 300


def api(path, payload, token=None):
    req = urllib.request.Request(
        f"{PDS}/xrpc/{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 **({"Authorization": f"Bearer {token}"} if token else {})},
    )
    with urllib.request.urlopen(req) as res:
        return json.load(res)


def parse_draft(path):
    raw = open(path, encoding="utf-8").read()
    blocks = [b.strip() for b in re.split(r"^---\s*$", raw, flags=re.M) if b.strip()]
    posts = [b for b in blocks if not b.startswith("#")]
    for i, p in enumerate(posts, 1):
        if len(p) > MAX_LEN:
            sys.exit(f"오류: {i}번째 포스트가 {len(p)}자로 300자를 초과합니다.")
    return posts


def url_facets(text):
    """본문 속 URL을 클릭 가능한 링크 facet으로 변환 (오프셋은 UTF-8 바이트 기준)."""
    facets = []
    for m in re.finditer(r"https?://[^\s)]+", text):
        facets.append({
            "index": {"byteStart": len(text[:m.start()].encode()),
                      "byteEnd": len(text[:m.end()].encode())},
            "features": [{"$type": "app.bsky.richtext.facet#link", "uri": m.group()}],
        })
    return facets


def main():
    draft = sys.argv[1] if len(sys.argv) > 1 else "bsky-news-draft.md"
    dry_run = "--dry-run" in sys.argv
    posts = parse_draft(draft)

    print(f"{len(posts)}개 포스트 스레드:")
    for i, p in enumerate(posts, 1):
        print(f"\n--- [{i}/{len(posts)}] ({len(p)}자) ---\n{p}")
    if dry_run:
        return

    password = os.environ.get("BSKY_APP_PASSWORD") or sys.exit(
        "\n오류: BSKY_APP_PASSWORD 환경변수가 필요합니다 (Bluesky 설정 → App Passwords)."
    )
    session = api("com.atproto.server.createSession",
                  {"identifier": HANDLE, "password": password})
    token, did = session["accessJwt"], session["did"]

    root = parent = None
    for i, text in enumerate(posts, 1):
        record = {
            "$type": "app.bsky.feed.post",
            "text": text,
            "createdAt": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc).isoformat().replace("+00:00", "Z"),
            "langs": ["ko"],
        }
        if facets := url_facets(text):
            record["facets"] = facets
        if parent:
            record["reply"] = {"root": root, "parent": parent}
        res = api("com.atproto.repo.createRecord",
                  {"repo": did, "collection": "app.bsky.feed.post", "record": record},
                  token)
        ref = {"uri": res["uri"], "cid": res["cid"]}
        root = root or ref
        parent = ref
        print(f"게시 완료 [{i}/{len(posts)}]: {res['uri']}")

    rkey = root["uri"].rsplit("/", 1)[-1]
    print(f"\n✅ 스레드: https://bsky.app/profile/{HANDLE}/post/{rkey}")


if __name__ == "__main__":
    main()
