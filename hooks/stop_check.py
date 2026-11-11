"""L4 Stop 훅: 세션이 "끝났다"고 하기 전에 검사를 코드가 다시 돌린다. 통과 못 하면 끝내지 못하게 막는다.

- 덱(decks/*/slides.html)이 없으면 막는다.
- build.py·theme 가 처음과 다르면 막는다(해시는 ablation.py 가 pins.json 에 적어 둠).
- 대화 기록에서 마지막 `python build.py decks/<이름> <자료…>` 명령을 찾아 같은 인자로 다시 돌린다. 실패면 막는다.
"""
import hashlib
import json
import shlex
import subprocess
import sys
from pathlib import Path

MAX_BLOCKS = 5  # ponytail: 무한 루프 방지용 상한. 넘으면 그냥 끝내게 두고 채점에서 실패로 잡힌다

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
data = json.load(sys.stdin)
root = Path(data.get("cwd") or ".").resolve()
here = Path(__file__).parent
counter = here / ".blocks"


def block(msg):
    n = int(counter.read_text()) + 1 if counter.exists() else 1
    if n > MAX_BLOCKS:
        sys.exit(0)
    counter.write_text(str(n))
    print(msg, file=sys.stderr)
    sys.exit(2)  # Stop 훅의 종료 코드 2 = 멈추지 말고 이어서 하라, stderr 가 모델에게 간다


decks = sorted(root.glob("decks/*/slides.html"))
if not decks:
    block("decks/<이름>/slides.html 이 없다. 스킬 순서대로 덱을 만들고 build.py 로 검사해 통과시킨 뒤 끝낸다.")

pins = json.loads((here / "pins.json").read_text(encoding="utf-8"))
changed = [f for f, h in pins.items() if hashlib.sha256((root / f).read_bytes()).hexdigest() != h]
if changed:
    block(f"검사기가 바뀌었다: {', '.join(changed)}. 검사기는 고치지 않는다. 원래대로 되돌리고 덱을 고친다.")

last = None
for line in Path(data["transcript_path"]).read_text(encoding="utf-8").splitlines():
    try:
        msg = json.loads(line).get("message") or {}
    except json.JSONDecodeError:
        continue
    for c in msg.get("content") or []:
        if isinstance(c, dict) and c.get("type") == "tool_use":
            cmd = (c.get("input") or {}).get("command") or ""
            if "build.py" in cmd and "decks/" in cmd:
                last = cmd
if not last:
    block("build.py 를 한 번도 돌리지 않았다. `python build.py decks/<이름> <자료 파일들>` 로 검사해 통과시킨 뒤 끝낸다.")

args = shlex.split(last.split("build.py", 1)[1].split("&&")[0].split("|")[0].split(";")[0])
r = subprocess.run([sys.executable, "build.py", *args], cwd=root, capture_output=True, text=True, encoding="utf-8")
if r.returncode:
    block("Stop 훅이 build.py 를 다시 돌렸더니 통과하지 못했다. slides.html 을 고쳐 통과시킨 뒤 끝낸다.\n" + r.stdout[-2000:])
