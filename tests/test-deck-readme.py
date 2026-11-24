#!/usr/bin/env python3
"""The Steam Deck release README is complete and follows the build's own data."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "automation/generate-deck-readme.py"
LOCK = {"schema": 5, "kernel": {"tag": "7.2.7-valve2", "version": "7.2.7"},
        "components": {"bore": {"project_version": "7.0.1r2"},
                       "poc_selector": {"project_version": "3.0.1"},
                       "lru_cast": {"project_version": "0.2.11"}},
        "auxiliary_components": {}}
SOURCE = {"tag": "7.2.7-valve2", "channel": "stable", "stock_pkgbase": "linux-neptune-72",
          "image": {"version": "3.9.5"}, "package": {"pkgver": "7.2.7.valve2", "pkgrel": 2}}


def render(tmp: Path, kernel_release: str, pull_request: str = "") -> subprocess.CompletedProcess:
    (tmp / "lock.json").write_text(json.dumps(LOCK))
    (tmp / "source.json").write_text(json.dumps(SOURCE))
    (tmp / "linux-charcoal-72-7.2.7.valve2.cc2-1-x86_64.pkg.tar.zst").write_bytes(b"x" * 3_145_728)
    return subprocess.run([
        sys.executable, str(SCRIPT), "--kernel-release", kernel_release,
        "--pkgbase", "linux-charcoal-72", "--pkgver", "7.2.7.valve2.cc2", "--pkgrel", "1",
        "--release-zip", "linux-charcoal-72-7.2.7.valve2.cc2-r3.zip",
        "--lock", str(tmp / "lock.json"), "--source", str(tmp / "source.json"),
        "--repository", "csrutil/linux-charcoal-vulcano", "--commit", "2244341" + "0" * 33,
        "--run-id", "45188400505", "--pull-request", pull_request,
        "--assets-dir", str(tmp), "--output", str(tmp / "README.md"),
    ], capture_output=True, text=True)


class DeckReadmeTests(unittest.TestCase):
    def test_pull_request_readme_names_everything_from_the_build(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            result = render(tmp, "7.2.7-valve2-1-csrutil-2244341", "1")
            self.assertEqual(result.returncode, 0, result.stderr)
            text = (tmp / "README.md").read_text()
        for expected in (
            "# 7.2.7-valve2-1-csrutil-2244341 — Steam Deck kernel",
            "mkdir -p /home/deck/Downloads/7.2.7-valve2-1-csrutil-2244341",
            "releases/download/7.2.7-valve2-1-csrutil-2244341",
            "sudo pacman -U linux-charcoal-72-7.2.7.valve2.cc2-1-x86_64.pkg.tar.zst",
            "/var/cache/pacman/pkg/linux-neptune-72-7.2.7.valve2-2-x86_64.pkg.tar.zst",
            "Pre-release, built from a pull request",
            "https://github.com/csrutil/linux-charcoal-vulcano/pull/1",
            "| `linux-charcoal-72-7.2.7.valve2.cc2-1-x86_64.pkg.tar.zst` | 3 MB |",
            "| BORE + sched_ext coexistence fix | `7.0.1r2` |",
            "| POC Selector | `3.0.1` |",
            "| LRU CAST | `0.2.11` |",
            "Not boot-tested",
            "> [!WARNING]",
            "It can damage your Steam Deck",
            "The author accepts no responsibility for any damage or loss.",
        ):
            self.assertIn(expected, text)
        self.assertNotIn("{", text.replace("${", ""))

    def test_master_readme_is_the_latest_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            self.assertEqual(render(tmp, "7.2.7-valve2-1-csrutil-49c07cb").returncode, 0)
            text = (tmp / "README.md").read_text()
        self.assertIn("Latest, built from `master`", text)
        self.assertNotIn("/pull/", text)

    def test_rejects_a_kernel_name_that_is_not_the_csrutil_format(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for bad in ("7.2.7-valve2-1-charcoal-72", "../7.2.7-valve2-1-csrutil-2244341",
                        "7.2.7-valve2-1-csrutil-2244341-dirty"):
                with self.subTest(bad=bad):
                    self.assertNotEqual(render(Path(directory), bad).returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
