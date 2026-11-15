#!/usr/bin/env python3
"""Create a versioned, relocatable binary archive from a native Nix build."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import tarfile
import tempfile


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def copy_licenses(source, destination):
    for path in source.rglob("*"):
        if not path.is_file() or not path.name.lower().startswith(("license", "copying", "notice")):
            continue
        if path.suffix.lower() not in ("", ".txt", ".md", ".html", ".ofl", ".apache", ".mit", ".bsd"):
            continue
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", choices=("folio", "vereda", "vitals"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    args = parser.parse_args()
    output = args.output.resolve(strict=True)
    data = json.loads(run("nix", "derivation", "show", str(output)))
    derivation = next(iter(data.get("derivations", data).values()))
    system = derivation["system"]
    if system not in ("aarch64-linux", "x86_64-linux"):
        parser.error(f"unsupported system: {system}")
    env = derivation["env"]
    args.dist.mkdir(parents=True, exist_ok=True)
    name = f"{args.app}-{args.version}-{system}"
    archive = args.dist / f"{name}.tar.gz"
    if archive.exists():
        parser.error(f"archive already exists: {archive}")
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / name
        shutil.copytree(output, root, symlinks=False)
        for path in [root, *root.rglob("*")]:
            path.chmod(path.stat().st_mode | 0o200)
        vendor = Path(env["cargoDeps"])
        for crate in vendor.iterdir():
            if crate.is_dir():
                copy_licenses(crate.resolve(), root / "share/licenses/dependencies" / crate.name)
        rune = Path(shlex.split(env["postPatch"])[2])
        copy_licenses(rune, root / "share/licenses/rune")
        binary = root / "bin" / ("folio-rune" if args.app == "folio" else args.app)
        if args.app == "folio":
            target = root / "libexec/folio"
            target.parent.mkdir()
            binary.rename(target)
            binary = target
            launcher = root / "bin/folio"
            launcher.write_text((Path(__file__).parent / "assets/folio-launch").read_text())
            launcher.chmod(0o755)
            desktop = root / "share/applications/local.folio.Reader.desktop"
            desktop.parent.mkdir(parents=True, exist_ok=True)
            desktop.write_text("[Desktop Entry]\nType=Application\nName=Folio\nComment=Read Markdown documents\nExec=folio -- %F\nIcon=local.folio.Reader\nTerminal=false\nCategories=Office;Viewer;\nMimeType=text/markdown;text/x-markdown;\nKeywords=Markdown;Reader;Mermaid;\n")
            icon = root / "share/icons/hicolor/scalable/apps/local.folio.Reader.svg"
            icon.parent.mkdir(parents=True)
            shutil.copyfile(Path(__file__).parent / "assets/folio.svg", icon)
        if args.app == "vitals":
            desktop = root / "share/applications/vitals.desktop"
            desktop.parent.mkdir(parents=True, exist_ok=True)
            desktop.write_text("[Desktop Entry]\nType=Application\nName=Vitals\nGenericName=System Monitor\nComment=Native Linux system monitor\nExec=vitals\nIcon=org.gnome.SystemMonitor\nTerminal=false\nCategories=System;Monitor;\n")
        binary.chmod(0o755)
        subprocess.run(["patchelf", "--remove-rpath", str(binary)], check=True)
        interpreter = "/lib/ld-linux-aarch64.so.1" if system == "aarch64-linux" else "/lib64/ld-linux-x86-64.so.2"
        subprocess.run(["patchelf", "--set-interpreter", interpreter, str(binary)], check=True)
        manifest = {"application": args.app, "version": args.version, "system": system,
                    "sourceRevision": args.revision, "runeRevision": "7ead7d63fcf6f9dd9669385a8b90e2ae80015d7b",
                    "buildOutput": str(output), "binarySha256": hashlib.sha256(binary.read_bytes()).hexdigest()}
        (root / "share/release.json").write_text(json.dumps(manifest, indent=2) + "\n")
        with archive.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as tar:
                for path in [root, *sorted(root.rglob("*"))]:
                    info = tar.gettarinfo(str(path), arcname=str(path.relative_to(root.parent)))
                    info.uid = info.gid = info.mtime = 0
                    info.uname = info.gname = "root"
                    info.mode = 0o755 if path.is_dir() or path.stat().st_mode & 0o111 else 0o644
                    if path.is_file():
                        with path.open("rb") as file:
                            tar.addfile(info, file)
                    else:
                        tar.addfile(info)
    print(json.dumps({"archive": str(archive), "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), **manifest}))


if __name__ == "__main__":
    main()
