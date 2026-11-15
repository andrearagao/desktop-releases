#!/usr/bin/env python3
"""Build and archive one committed private application on the native host."""

import argparse
import io
from pathlib import Path
import platform
import subprocess
import tarfile
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", choices=("folio", "vereda", "vitals"))
    parser.add_argument("source", type=Path)
    parser.add_argument("--version", default="0.1.0")
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    repository = Path(__file__).resolve().parent
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=source, text=True)
    if dirty:
        parser.error("commit the intended application source before building a release")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    archive = subprocess.check_output(["git", "archive", "HEAD"], cwd=source)
    work = repository / "work"
    work.mkdir(exist_ok=True)
    dist = repository / "dist"
    dist.mkdir(exist_ok=True)
    output = dist / f"{args.app}-{platform.machine()}-linux"
    with tempfile.TemporaryDirectory(dir=work) as temp:
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(temp, filter="data")
        subprocess.run(["nix", "build", f".#{args.app}",
                        "--override-input", "app-source", f"path:{temp}",
                        "--no-write-lock-file", "--out-link", str(output)], cwd=repository, check=True)
        subprocess.run(["nix", "run", ".#release-tools", "--", args.app, str(output),
                        "--revision", revision, "--version", args.version], cwd=repository, check=True)


if __name__ == "__main__":
    main()
