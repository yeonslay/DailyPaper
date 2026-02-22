#!/usr/bin/env python3
"""
화~토 매일 09:30에 실행할 때 사용.
오늘이 화~토가 아니면 아무것도 하지 않음.
Task Scheduler에서 이 스크립트를 매일 09:30에 실행하도록 등록하면 됨.
"""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 화(1)~토(5): Python weekday() 기준
WEEKDAYS_RUN = (1, 2, 3, 4, 5)

def main():
    today = datetime.now()
    if today.weekday() not in WEEKDAYS_RUN:
        print(f"[{today:%Y-%m-%d}] {today.strftime('%A')} - skip")
        return 0

    root = Path(__file__).resolve().parent.parent
    env = {**os.environ, "PYTHONPATH": str(root / "src")}

    cmd = [sys.executable, "-m", "dailypaper.cli", "run-yesterday"]
    print(f"[{today:%Y-%m-%d %H:%M}] run-yesterday ...")
    result = subprocess.run(cmd, cwd=str(root), env=env)
    if result.returncode != 0:
        print(f"Failed: exit code {result.returncode}", file=sys.stderr)
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
