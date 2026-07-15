#!/usr/bin/env python
"""Typeset the main manuscript and supplementary-information PDFs."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
TEX_DIR = REPO / "paper" / "tex"
DOCUMENTS = ("main.tex", "supplementary_main.tex")


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
        for document in DOCUMENTS:
            subprocess.run([tectonic, document], cwd=TEX_DIR, env=env, check=True)
        return 0

    pdflatex = shutil.which("pdflatex")
    bibtex = shutil.which("bibtex")
    if pdflatex and bibtex:
        print(f"Using pdflatex: {pdflatex}")
        for document in DOCUMENTS:
            stem = Path(document).stem
            run([pdflatex, "-interaction=nonstopmode", document])
            run([bibtex, stem])
            run([pdflatex, "-interaction=nonstopmode", document])
            run([pdflatex, "-interaction=nonstopmode", document])
        return 0

    print(
        "No TeX engine found. Install tectonic and make it available on PATH, "
        "or set TECTONIC=/path/to/tectonic.",
        file=sys.stderr,
    )
    return 127


if __name__ == "__main__":
    raise SystemExit(main())
