#!/usr/bin/env python3
"""Publish both native architectures together without replacing existing assets."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


REPOSITORY = "andrearagao/desktop-releases"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", choices=("folio", "vereda", "vitals"))
    parser.add_argument("version")
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    args = parser.parse_args()
    tag = f"{args.app}-v{args.version}"
    assets = []
    manifests = []
    sums = []
    for system in ("aarch64-linux", "x86_64-linux"):
        name = f"{args.app}-{args.version}-{system}"
        archive = args.dist / f"{name}.tar.gz"
        with tarfile.open(archive) as tar:
            manifest = json.load(tar.extractfile(f"{name}/share/release.json"))
        for key, expected in (("application", args.app), ("version", args.version), ("system", system)):
            if manifest[key] != expected:
                parser.error(f"unexpected {key} in {archive}")
        manifests.append(manifest)
        assets.append(str(archive))
        sums.append(f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n")
    if manifests[0]["sourceRevision"] != manifests[1]["sourceRevision"]:
        parser.error("architectures were built from different source revisions")
    release_dir = args.dist / tag
    release_dir.mkdir(exist_ok=True)
    checksum_file = release_dir / "SHA256SUMS"
    checksum_file.write_text("".join(sums))
    metadata_file = release_dir / "release.json"
    metadata_file.write_text(json.dumps(manifests, indent=2) + "\n")
    notes = release_dir / "notes.md"
    notes.write_text(f"{args.app.title()} {args.version} for ARM64 and x86-64 NixOS.\n\n"
                     f"Source revision: `{manifests[0]['sourceRevision']}`. Application source remains private. "
                     "Nix supplies runtime libraries and patches the ELF interpreter. "
                     "These archives are not standalone installers for other distributions.\n")
    existing = subprocess.run(["gh", "release", "view", tag, "--repo", REPOSITORY], capture_output=True)
    if existing.returncode == 0:
        parser.error(f"release {tag} already exists; publish a new version instead")
    subprocess.run(["gh", "release", "create", tag, "--repo", REPOSITORY, "--draft",
                    "--title", f"{args.app.title()} {args.version}", "--notes-file", str(notes),
                    *assets, str(checksum_file), str(metadata_file)], check=True)
    subprocess.run(["gh", "release", "edit", tag, "--repo", REPOSITORY, "--draft=false"], check=True)
    subprocess.run(["gh", "release", "view", tag, "--repo", REPOSITORY,
                    "--json", "url,isDraft,assets"], check=True)


if __name__ == "__main__":
    main()
