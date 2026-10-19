"""Entry point for the usbc.exe build: equivalent to `msikvm.py set usbc`.

Built windowed (no console), so errors are shown in a message box instead of stderr.
"""

import contextlib
import ctypes
import io
import os
import sys

# msikvm.py lives in the repo root, one level up.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import msikvm  # noqa: E402


def run():
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        code = msikvm.main(["set", "usbc"])
    if code:
        ctypes.windll.user32.MessageBoxW(None, err.getvalue().strip() or "failed", "msikvm", 0x10)
    return code


if __name__ == "__main__":
    sys.exit(run())
