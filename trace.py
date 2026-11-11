"""stream-json 로그를 도구 호출 순서로 짧게 편다. build.py 결과의 ✗ 줄과 Stop 훅 응답도 같이.

    python trace.py <runs 폴더>/L3_1.jsonl
"""
import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
i = 0
for line in open(sys.argv[1], encoding="utf-8"):
    m = json.loads(line)
    if m.get("type") == "system" and m.get("subtype") == "hook_response":
        print(f"    [{m.get('hook_event')} 훅] exit {m.get('exit_code')} {(m.get('stderr') or '').strip()[:200]}")
    for c in (m.get("message") or {}).get("content") or []:
        if not isinstance(c, dict):
            continue
        if c.get("type") == "tool_use":
            i += 1
            inp = c.get("input") or {}
            arg = inp.get("command") or inp.get("file_path") or inp.get("skill") or inp.get("pattern") or ""
            arg = re.sub(r"cd \"?[^\"&]+\"? && ", "", arg)  # 절대 경로(사용자 이름) 지우기
            print(f"{i:>2} {c['name']:<6} {arg.splitlines()[0][:120] if arg else ''}")
        if c.get("type") == "tool_result":
            body = c.get("content")
            text = body if isinstance(body, str) else " ".join(x.get("text", "") for x in body or [] if isinstance(x, dict))
            for l in text.splitlines():
                if "✗" in l or "통과" in l or "문제" in l:
                    print("     ", l.strip()[:150])
