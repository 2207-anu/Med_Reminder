"""
MedRemind — Windows Task Scheduler (4 separate .py files)

  python scripts/setup_windows_tasks.py

Tasks:
  morning_8am.py    → 08:00
  afternoon_1pm.py  → 13:00
  evening_6pm.py    → 18:00
  night_9pm.py      → 21:00
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

TASKS = (
    ("MedRemind-Morning-8AM", "08:00", "morning_8am.py"),
    ("MedRemind-Afternoon-1PM", "13:00", "afternoon_1pm.py"),
    ("MedRemind-Evening-6PM", "18:00", "evening_6pm.py"),
    ("MedRemind-Night-9PM", "21:00", "night_9pm.py"),
)


def task_command(script_name: str) -> str:
    python = Path(sys.executable).resolve()
    script = (PROJECT_DIR / "scripts" / script_name).resolve()
    return f'"{python}" "{script}"'


def register_task(name: str, time_hhmm: str, script_name: str) -> None:
    subprocess.run(
        [
            "schtasks",
            "/Create",
            "/TN",
            name,
            "/TR",
            task_command(script_name),
            "/SC",
            "DAILY",
            "/ST",
            time_hhmm,
            "/F",
        ],
        check=True,
        cwd=PROJECT_DIR,
    )


def main() -> int:
    print(f"Project: {PROJECT_DIR}\n")

    for name, time_str, script in TASKS:
        path = PROJECT_DIR / "scripts" / script
        if not path.is_file():
            print(f"Missing: {path}", file=sys.stderr)
            return 1
        try:
            register_task(name, time_str, script)
            print(f"✅ {name} at {time_str} → scripts/{script}")
        except subprocess.CalledProcessError as exc:
            print(f"❌ {name}: {exc}", file=sys.stderr)
            return 1

    print("\nTest:")
    print("  python scripts/morning_8am.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
