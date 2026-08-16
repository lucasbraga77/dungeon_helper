import os
import subprocess
import sys
from typing import Sequence


def _is_admin() -> bool:
    if os.name != "nt":
        return True
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def build_admin_command(executable: str, args: Sequence[str] | None = None) -> list[str]:
    cmd = ["powershell", "-NoProfile", "-Command"]
    payload = ["Start-Process", "-Verb", "RunAs", "-Wait", "-FilePath", f'"{executable}"']
    extra_args = list(args or []) + ["--already-elevated"]
    if extra_args:
        payload.extend(["-ArgumentList", "\"" + "\",\"".join(extra_args) + "\""])
    cmd.append(" ".join(payload))
    return cmd


def relaunch_as_admin(executable: str, args: Sequence[str] | None = None) -> int:
    if os.name != "nt":
        return 0

    if _is_admin() or (sys.argv and any(a.lower() == "--already-elevated" for a in sys.argv)):
        return 0

    cmd = build_admin_command(executable, [*list(args or [])])
    try:
        return subprocess.call(cmd)
    except OSError:
        return 1


def ensure_admin_launch(executable: str, args: Sequence[str] | None = None) -> None:
    if os.name != "nt":
        return

    if _is_admin() or (sys.argv and any(a.lower() == "--already-elevated" for a in sys.argv)):
        return

    raise SystemExit(relaunch_as_admin(executable, args))
