#!/usr/bin/env python3
"""Render auditable Charcoal release notes from the resolved build lock."""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
PATCH_LABELS = {
    "bore": "BORE", "bore_sched_ext_coexistence": "BORE sched_ext coexistence",
    "lru_cast": "LRU CAST", "poc_selector": "POC Selector",
    "cpu_optimizations": "CPU optimizations",
    "zen_interactive": "Zen Interactive", "reflex": "REFLEX",
}


def safe(value: object) -> str:
    """Keep untrusted lock metadata from producing markdown structure."""
    return str(value).replace("\r", " ").replace("\n", " ").replace("|", "\\|").replace("`", "'").strip()


def get_lock(path: Path) -> dict:
    lock = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(lock, dict) or not isinstance(lock.get("kernel"), dict):
        raise ValueError("patch lock has no kernel metadata")
    if not isinstance(lock.get("components"), dict) or not lock["components"]:
        raise ValueError("patch lock has no applied components")
    return lock


def format_components(components: dict) -> list[str]:
    lines = ["| Component | Patch version | Upstream series | Selection / origin |", "|---|---|---|---|"]
    details: list[str] = []
    for name, info in sorted(components.items()):
        if not isinstance(info, dict) or not SHA256_RE.fullmatch(str(info.get("sha256", ""))):
            raise ValueError(f"invalid patch SHA256 metadata: {name}")
        label = PATCH_LABELS.get(name, name.replace("_", " "))
        version = info.get("project_version") or "not recorded (see the patch file)"
        kernel_variant = info.get("kernel_version") or info.get("kernel_target") or "generic / not declared"
        selection = info.get("selection") or info.get("origin") or "not declared"
        lines.append(f"| **{safe(label)}** | `{safe(version)}` | `{safe(kernel_variant)}` | {safe(selection)} |")
        path = info.get("selected_path") or info.get("path") or info.get("url") or "no path"
        details.extend([
            f"**{safe(label)}** — source `{safe(path)}`",
            f"- Selected SHA256: `{info['sha256']}`",
        ])
        for key, heading in (("commit", "Upstream commit"), ("latest_upstream_project_version", "Newest upstream revision")):
            if info.get(key):
                details.append(f"- {heading}: `{safe(info[key])}`")
        if isinstance(info.get("compatibility_reference"), dict):
            ref = info["compatibility_reference"]
            details.append(f"- Port reference: `{safe(ref.get('kernel_version', '?'))}` / `{safe(ref.get('project_version', '?'))}`")
        if isinstance(info.get("upstream"), dict):
            ref = info["upstream"]
            details.append(f"- Local port reference: `{safe(ref.get('repository', '?'))}/{safe(ref.get('path', '?'))}` @ `{safe(ref.get('commit', '?'))}`")
        if info.get("upstream_sha256"):
            details.append(f"- Original SHA256 before the port: `{safe(info['upstream_sha256'])}`")
        details.append("")
    return lines + ["", "<details>", "<summary>Full source and SHA256 of every patch</summary>", ""] + details + ["</details>"]


def render(mode: str, lock: dict, package_version: str, kernel_tag: str, zip_name: str, release_tag: str, sha: str, run_id: str) -> str:
    if mode not in {"stable", "preview"}:
        raise ValueError("unsupported release mode")
    kernel = lock["kernel"]
    series = '.'.join(str(kernel.get('version', '')).split('.')[:2])
    if not re.fullmatch(r'\d+\.\d+', series) or tuple(map(int, series.split('.'))) < (7, 2):
        raise ValueError(f"unsupported stable kernel series: {series}")
    if not str(kernel.get("version", "")).startswith(series + "."):
        raise ValueError(f"wrong kernel series for {mode} release: {kernel}")
    if kernel.get("tag") != kernel_tag:
        raise ValueError("kernel tag disagrees with the validated patch lock")
    if mode == "preview" and not release_tag.startswith("charcoal-7.2-preview-"):
        raise ValueError("preview tag has invalid prefix")
    if mode == "stable" and not release_tag.startswith(f"charcoal-{kernel['version']}."):
        raise ValueError("stable tag has invalid prefix")
    lines = [
        f"# Charcoal — SteamOS {'Preview' if mode == 'preview' else 'Stable'} / Linux {series} — {safe(package_version)}",
        "",
        "## Kernel and build",
        f"- **Valve kernel (source):** `{safe(kernel_tag)}` — Linux `{safe(kernel['version'])}`.",
        f"- **Package version:** `{safe(package_version)}`; **bundle tag:** `{safe(release_tag)}`.",
        f"- **Build commit:** `{safe(sha)}`; **workflow run:** `{safe(run_id)}`.",
        "",
        "## Applied patches and selected versions",
        "The versions and origins below come from the `patch-lock.json` validated **in this run**, not from fixed values in the workflow.",
        "",
        *format_components(lock["components"]),
    ]
    for group, heading in (("auxiliary_components", "Auxiliary components"),):
        if lock.get(group):
            lines.extend(["", f"## {heading}", "", *format_components(lock[group])])
    lines.extend([
        "", "## Artifacts and audit", f"- ZIP: `{safe(zip_name)}`.",
        "- Use this run's `patch-lock.json` and the artifact SHA256 files to check the exact bytes that were used.",
        "- Extra drivers and modules are checked in the build logs; a driver that is not in the patch lock gets no version here.",
    ])
    if mode == "preview":
        lines.append("- Preview is a separate pre-release that the installer only finds by `charcoal-7.2-preview-*`; it does not change the Latest stable release.")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("mode", "lock", "pkgver", "kernel-tag", "release-tag", "release-zip", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    lock = get_lock(Path(args.lock))
    text = render(args.mode, lock, args.pkgver, args.kernel_tag, args.release_zip,
                  args.release_tag, os.getenv("GITHUB_SHA", "local"), os.getenv("GITHUB_RUN_ID", "local"))
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(text, encoding="utf-8")
    print(f"Generated {args.output}: {len(lock['components'])} patches from validated lock")


if __name__ == "__main__":
    main()
