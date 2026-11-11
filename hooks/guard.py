"""L4 PreToolUse 훅: 검사기·테마·하네스 설정 파일은 편집 도구로 못 고치게 막는다(가이드가 아니라 차단)."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
data = json.load(sys.stdin)
target = (data.get("tool_input") or {}).get("file_path") or ""
root = Path(data.get("cwd") or ".").resolve()
try:
    rel = Path(target).resolve().relative_to(root).as_posix()
except ValueError:
    rel = ""
if rel == "build.py" or rel.startswith(("theme/", ".claude/")):
    # 종료 코드 2 = 도구 호출 차단, stderr 가 모델에게 간다
    print(f"{rel} 는 검사기·하네스 파일이라 고칠 수 없다. 덱(decks/<이름>/slides.html)만 고친다.", file=sys.stderr)
    sys.exit(2)
