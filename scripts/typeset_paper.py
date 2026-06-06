#!/usr/bin/env python
"""Typeset the manuscript PDF without hard-coding a machine-local TeX path."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
TEX_DIR = REPO / "paper" / "tex"
MAIN = "main.tex"


def run(cmd: list[str]) -> None:
    print(" ".join(cmd))
    subprocess.run(cmd, cwd=TEX_DIR, check=True)


def tectonic_binary() -> str | None:
    env_path = os.environ.get("TECTONIC")
    if env_path:
        return env_path
    return shutil.which("tectonic")


def main() -> int:
    tectonic = tectonic_binary()
    if tectonic:
        env = os.environ.copy()
        env.setdefault("XDG_CACHE_HOME", "/tmp/tectonic-cache")
        print(f"Using tectonic: {tectonic}")
        subprocess.run([tectonic, MAIN], cwd=TEX_DIR, env=env, check=True)
        return 0

    pdflatex = shutil.which("pdflatex")
    bibtex = shutil.which("bibtex")
    if pdflatex and bibtex:
        print(f"Using pdflatex: {pdflatex}")
        run([pdflatex, "-interaction=nonstopmode", MAIN])
        run([bibtex, "main"])
        run([pdflatex, "-interaction=nonstopmode", MAIN])
        run([pdflatex, "-interaction=nonstopmode", MAIN])
        return 0

    print(
        "No TeX engine found. Install tectonic and make it available on PATH, "
        "or set TECTONIC=/path/to/tectonic.",
        file=sys.stderr,
    )
    return 127


if __name__ == "__main__":
    raise SystemExit(main())
