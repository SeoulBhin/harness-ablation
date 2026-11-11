"""채점 결과(*.score.json)를 모아 results/ 에 표·덱 사본·도구 순서로 남긴다. 로컬 경로는 지운다.

    python collect.py <runs 폴더>
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "results"
COLS = ["run", "duration_s", "turns", "cost_usd_list", "numbers_shown", "unverifiable", "unexplained",
        "pristine_build_pass", "pdf", "checker_changed"]


def scrub(s, runs):
    s = s.replace(str(runs), "<runs>").replace(str(runs).replace("\\", "/"), "<runs>")
    s = re.sub(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\"' ]+", "<home>", s)
    return re.sub(r"<home>[\\/]+AppData[\\/]+Local[\\/]+Temp[\\/]+claude[\\/]+[^\\/]+[\\/]+[^\\/]+[\\/]+scratchpad", "<scratch>", s)


def main(runs):
    sys.stdout.reconfigure(encoding="utf-8")
    runs = Path(runs).resolve()
    OUT.mkdir(exist_ok=True)
    rows = []
    for p in sorted(runs.glob("L*_*.score.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        name = d["run"]
        rows.append(d)
        dst = OUT / name
        dst.mkdir(exist_ok=True)
        if d.get("deck"):
            shutil.copy(runs / name / d["deck"], dst / Path(d["deck"]).name)
        for f in d["new_files"]:  # L1 이 스스로 짠 생성기도 남긴다
            if f.endswith(".py"):
                (dst / Path(f).name).write_text(scrub((runs / name / f).read_text(encoding="utf-8"), runs), encoding="utf-8")
        trace = subprocess.run([sys.executable, str(HERE / "trace.py"), str(runs / f"{name}.jsonl")],
                               capture_output=True, text=True, encoding="utf-8").stdout
        (dst / "trace.txt").write_text(scrub(trace, runs), encoding="utf-8")
        (dst / "score.json").write_text(scrub(json.dumps(d, ensure_ascii=False, indent=1), runs), encoding="utf-8")
    lines = ["| " + " | ".join(COLS) + " |", "|" + "---|" * len(COLS)]
    for d in rows:
        cell = lambda k: (len(d[k]) if isinstance(d.get(k), list) else d.get(k, "N/A"))
        lines.append("| " + " | ".join(str(cell(k)) for k in COLS) + " |")
    (OUT / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
