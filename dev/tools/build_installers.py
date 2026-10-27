"""Bundle a built wheel into three standalone online setup files."""

import argparse
import base64
import hashlib
import json
import textwrap
from pathlib import Path
from zipfile import ZipFile

UV_VERSION = "0.13.6"
# Official SHA-256 digests from https://github.com/astral-sh/uv/releases/tag/0.13.6.
# Pin the tool as well as its checksums; a changing 'latest' endpoint is never executed.
UV_HASHES = {
    "x86_64-pc-windows-msvc": "a2a8820d5eea32f08ef467ef3b7f66883a9b076d5737a2fc2fbb5f458d1bb50f",
    "aarch64-pc-windows-msvc": "c2426c0c8e28b53d8c440e47a18d96ad4db51e159866c0e81435b196d7f0081c",
    "x86_64-apple-darwin": "63ba17fdda55ad1a230d4b37fc6017ffa10c23688c83818bd3bfdf914c652a02",
    "aarch64-apple-darwin": "60fbd5c8a1ed681845eea28d9d622fcde03c51e91a43465b64a1e17db1ed3472",
    "x86_64-unknown-linux-musl": "5d61f26b6c7213779eda90edc6971ea6b0b796bfb8d49a574c8ad69b59838548",
    "aarch64-unknown-linux-musl": "819692e404d23e5aae6bc44c0e260f1f5492fd1910ab4693b2c650f926dbe800",
}
ROOT = Path(__file__).resolve().parents[2]


def build(wheel: Path, output: Path) -> list[Path]:
    output = output.resolve()
    data = wheel.read_bytes()
    with ZipFile(wheel) as archive:
        metadata = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
        version = next(
            line[9:] for line in archive.read(metadata).decode().splitlines() if line.startswith("Version: ")
        )
        if "git_companion/install_support.py" not in archive.namelist():
            raise ValueError("Build a fresh wheel containing the setup helper first.")
    replacements = {
        "APP_VERSION": version,
        "UV_VERSION": UV_VERSION,
        "WHEEL_NAME": wheel.name,
        "WHEEL_SHA256": hashlib.sha256(data).hexdigest(),
        "WHEEL_BASE64_COMMENTS": "\n".join(
            "# " + line for line in textwrap.wrap(base64.b64encode(data).decode(), 76)
        ),
        "UV_WINDOWS_X64_SHA256": UV_HASHES["x86_64-pc-windows-msvc"],
        "UV_WINDOWS_ARM64_SHA256": UV_HASHES["aarch64-pc-windows-msvc"],
        "UV_POSIX_HASHES": "\n".join(
            f"    {target}) uv_sha256='{digest}' ;;"
            for target, digest in UV_HASHES.items()
            if not target.endswith("msvc")
        ),
    }
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    for filename, template, system in (
        ("setup-windows.cmd", "setup-windows.cmd.in", "Windows"),
        ("setup-macos.command", "setup-posix.sh.in", "Darwin"),
        ("setup-linux.sh", "setup-posix.sh.in", "Linux"),
    ):
        content = (ROOT / "dev" / "packaging" / template).read_text(encoding="utf-8")
        for key, value in {**replacements, "TARGET_OS": system}.items():
            content = content.replace(f"@{key}@", value)
        path = output / filename
        path.write_text(content, encoding="utf-8", newline="\r\n" if system == "Windows" else "\n")
        path.chmod(0o755)
        paths.append(path)
    manifest = {
        "version": version,
        "uv_version": UV_VERSION,
        "wheel_sha256": replacements["WHEEL_SHA256"],
        "setups": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
    }
    manifest_path = (
        ROOT / "dev" / "artifacts" / "setup-manifest.json" if output == ROOT else output / "manifest.json"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT)
    args = parser.parse_args()
    for path in build(args.wheel, args.output):
        print(path)


if __name__ == "__main__":
    main()
