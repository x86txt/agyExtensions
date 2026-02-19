#!/usr/bin/env python3
"""
force_install_vsix.py

Download a VSIX from the VS Code Marketplace, patch engines.vscode to broaden
compatibility (e.g., '>=1.0.0'), and optionally install it using Antigravity's
CLI (agy).

Designed for both local use and GitHub Actions.

Examples:
  python3 force_install_vsix.py github.vscode-pull-request-github --engine ">=1.0.0" --out-dir dist --notes --meta-json dist/meta.json
  python3 force_install_vsix.py github.vscode-pull-request-github --engine ">=1.0.0" --install --agy agy

Notes:
- This bypasses extension compatibility gating. Runtime API mismatches may still break the extension.
- The VSIX is downloaded from marketplace.visualstudio.com public gallery API.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import textwrap
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


GALLERY_QUERY_URL = "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery"
GALLERY_ACCEPT = "application/json;api-version=3.0-preview.1"


@dataclass(frozen=True)
class VsixInfo:
    extension_id: str          # publisher.name
    display_name: str
    version: str
    vsix_url: str


def _http_post_json(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=data,
        method="POST",
        headers={
            "Accept": GALLERY_ACCEPT,
            "Content-Type": "application/json",
            "User-Agent": "force_install_vsix.py",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as e:
        snippet = raw[:500].decode("utf-8", errors="replace")
        raise RuntimeError(f"Failed to parse JSON response: {e}\nResponse snippet:\n{snippet}") from e


def lookup_vsix_info(extension_id: str) -> VsixInfo:
    payload = {
        "filters": [{
            "criteria": [{"filterType": 7, "value": extension_id}],
            "pageNumber": 1,
            "pageSize": 1,
        }],
        "flags": 103,  # includes versions + files
    }

    j = _http_post_json(GALLERY_QUERY_URL, payload)

    try:
        ext = j["results"][0]["extensions"][0]
        display_name = ext.get("displayName") or ext.get("extensionName") or extension_id
        v = ext["versions"][0]
        version = v["version"]
        files = v["files"]
        vsix_url = next(
            f["source"] for f in files
            if f.get("assetType") == "Microsoft.VisualStudio.Services.VSIXPackage"
        )
    except Exception as e:
        raise RuntimeError(f"Marketplace response did not contain expected fields for {extension_id}") from e

    return VsixInfo(
        extension_id=extension_id,
        display_name=display_name,
        version=version,
        vsix_url=vsix_url,
    )


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "force_install_vsix.py"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as f:
        f.write(resp.read())


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def patch_vsix_engines(
    src_vsix: Path,
    dst_vsix: Path,
    engine_range: str,
    package_json_path: str = "extension/package.json",
) -> None:
    if not src_vsix.exists():
        raise FileNotFoundError(src_vsix)

    with zipfile.ZipFile(src_vsix, "r") as zin:
        names = zin.namelist()
        if package_json_path not in names:
            candidates = [n for n in names if n.endswith("package.json")]
            msg = f"Could not find {package_json_path} inside VSIX.\nFound package.json candidates:\n"
            msg += "\n".join(candidates[:50]) if candidates else "(none)"
            raise RuntimeError(msg)

        with zipfile.ZipFile(dst_vsix, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for name in names:
                data = zin.read(name)
                if name == package_json_path:
                    pkg = json.loads(data.decode("utf-8"))
                    pkg.setdefault("engines", {})["vscode"] = engine_range
                    data = (json.dumps(pkg, indent=2) + "\n").encode("utf-8")
                zout.writestr(name, data)


def run_cmd(cmd: list[str]) -> int:
    try:
        proc = subprocess.run(cmd, check=False)
        return int(proc.returncode)
    except FileNotFoundError:
        return 127


def build_release_notes(
    info: VsixInfo,
    engine_range: str,
    original_vsix: Path,
    forced_vsix: Path,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    o_sha = sha256_file(original_vsix) if original_vsix.exists() else "unknown"
    f_sha = sha256_file(forced_vsix) if forced_vsix.exists() else "unknown"

    notes = f"""\
    # Forced VSIX build: {info.extension_id}

    **What this is:** A repack of the upstream VSIX with `extension/package.json -> engines.vscode`
    set to a broader semver range so stricter VS Code forks may load it.

    - Extension: **{info.display_name}** (`{info.extension_id}`)
    - Upstream version: **{info.version}**
    - Patched engines.vscode: **{engine_range}**
    - Build time (UTC): **{now}**

    ## Files
    - Original VSIX: `{original_vsix.name}`
      - SHA256: `{o_sha}`
    - Forced VSIX: `{forced_vsix.name}`
      - SHA256: `{f_sha}`

    ## Compatibility notes
    - This bypasses *version gating* only.
    - If the extension uses APIs not present in your editor build, it may still malfunction at runtime.
    """
    return textwrap.dedent(notes).strip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Download a VSIX, patch engines.vscode, and optionally install using agy.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    ap.add_argument("extension_id", help="Extension identifier: publisher.name (e.g., github.vscode-pull-request-github)")
    ap.add_argument("--engine", default=">=1.0.0", help='New engines.vscode semver range (default: ">=1.0.0")')
    ap.add_argument("--out-dir", default="dist", help="Output directory (default: dist)")
    ap.add_argument("--install", action="store_true", help="Attempt to install forced VSIX via `agy --install-extension`")
    ap.add_argument("--agy", default="agy", help="Path to agy binary (default: agy)")
    ap.add_argument("--notes", action="store_true", help="Also write release notes markdown into out-dir")
    ap.add_argument("--meta-json", default=None, help="Write build metadata JSON to this path (useful for CI)")
    args = ap.parse_args()

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"🔎 Looking up {args.extension_id} ...")
    info = lookup_vsix_info(args.extension_id)
    print(f"✅ Found: {info.display_name} version {info.version}")
    print(f"⬇️  VSIX URL: {info.vsix_url}")

    orig_vsix = out_dir / f"{info.extension_id}-{info.version}.vsix"
    forced_vsix = out_dir / f"{info.extension_id}-{info.version}.forced.vsix"
    notes_md = out_dir / f"{info.extension_id}-{info.version}.RELEASE_NOTES.md"

    if not orig_vsix.exists():
        print(f"⬇️  Downloading to {orig_vsix} ...")
        download_file(info.vsix_url, orig_vsix)
    else:
        print(f"↪️  Using existing file {orig_vsix}")

    print(f"🧪 Patching engines.vscode -> {args.engine}")
    patch_vsix_engines(orig_vsix, forced_vsix, args.engine)

    o_sha = sha256_file(orig_vsix)
    f_sha = sha256_file(forced_vsix)

    print("🔐 Checksums:")
    print(f"  original: {o_sha}")
    print(f"  forced:   {f_sha}")

    if args.notes:
        notes_md.write_text(build_release_notes(info, args.engine, orig_vsix, forced_vsix), encoding="utf-8")
        print(f"📝 Wrote release notes: {notes_md}")

    if args.meta_json:
        meta_path = Path(args.meta_json).expanduser().resolve()
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta = {
            "extension_id": info.extension_id,
            "display_name": info.display_name,
            "version": info.version,
            "engine_range": args.engine,
            "original_vsix": str(orig_vsix),
            "forced_vsix": str(forced_vsix),
            "original_sha256": o_sha,
            "forced_sha256": f_sha,
            "built_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"),
        }
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        print(f"🧾 Wrote metadata: {meta_path}")

    if args.install:
        print(f"🧩 Installing via {args.agy} ...")
        rc = run_cmd([args.agy, "--install-extension", str(forced_vsix)])
        if rc != 0:
            print(f"❌ Install command failed with exit code {rc}", file=sys.stderr)
            return rc
        print("✅ Install command completed. Fully restart Antigravity to ensure extension host reloads.")

    print(f"🎉 Done. Forced VSIX: {forced_vsix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
