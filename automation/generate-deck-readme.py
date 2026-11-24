#!/usr/bin/env python3
"""Write the Steam Deck release README (release notes and README.md asset)."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

KERNEL_RELEASE_RE = re.compile(r"\d+\.\d+\.\d+-[0-9A-Za-z.]+-\d+-csrutil-[0-9a-f]{7,40}")


def version(lock: dict, name: str) -> str:
    value = lock.get("components", {}).get(name, {}).get("project_version")
    return f"`{value}`" if value else "—"


def size(path: Path) -> str:
    return f"{path.stat().st_size / 1_048_576:.0f} MB" if path.is_file() else "—"


def render(args: argparse.Namespace, lock: dict, source: dict) -> str:
    if not KERNEL_RELEASE_RE.fullmatch(args.kernel_release):
        raise ValueError(f"unexpected kernel release: {args.kernel_release}")
    kernel_pkg = f"{args.pkgbase}-{args.pkgver}-{args.pkgrel}-x86_64.pkg.tar.zst"
    headers_pkg = f"{args.pkgbase}-headers-{args.pkgver}-{args.pkgrel}-x86_64.pkg.tar.zst"
    assets = Path(args.assets_dir)
    stock = source["stock_pkgbase"]
    stock_pkg = f"{stock}-{source['package']['pkgver']}-{source['package']['pkgrel']}-x86_64.pkg.tar.zst"
    repo_url = f"https://github.com/{args.repository}"
    tag = args.kernel_release
    if args.pull_request:
        origin = f"merge commit of {repo_url}/pull/{args.pull_request} (not merged into `master` yet)"
        channel = "Pre-release, built from a pull request"
    else:
        origin = "branch `master`"
        channel = "Latest, built from `master`"
    image = source["image"]
    return f"""# {tag} — Steam Deck kernel

> [!WARNING]
> **Use at your own risk.** This is an unofficial kernel. Valve does not make or support it.
> It can damage your Steam Deck, stop it from booting, or cause data loss. It raises the CPU frequency limit above stock (4000 MHz).
> It is provided "as is", without warranty of any kind. The author accepts no responsibility for any damage or loss.
> Do not install it if you do not accept this risk.

Charcoal SteamOS kernel, trimmed for the Steam Deck.

| | |
|---|---|
| Kernel name (`uname -r`) | `{tag}` |
| Package | `{args.pkgbase}` `{args.pkgver}-{args.pkgrel}` |
| Base | Valve `{source['tag']}` (SteamOS {image['version']} {source['channel']}) |
| Source commit | [`{args.commit[:7]}`]({repo_url}/commit/{args.commit}), {origin} |
| Build | {repo_url}/actions/runs/{args.run_id} |
| Release type | {channel} |
| Status | Build checks passed. Not boot-tested on a Steam Deck by this workflow. |

## Files

| File | Size | What it is |
|---|---|---|
| `{kernel_pkg}` | {size(assets / kernel_pkg)} | The kernel package. **This is the only file you need.** |
| `{headers_pkg}` | {size(assets / headers_pkg)} | Headers, only needed to build extra modules. Pulls in the LLVM toolchain. |
| `{args.release_zip}` | {size(assets / args.release_zip)} | Both packages in one bundle |
| `SHA256SUMS` | — | Checksums for the two packages |
| `RELEASE-ZIP-SHA256SUM` | — | Checksum for the zip |
| `patch-lock.json` | — | Exact versions and SHA-256 of every applied patch |
| `steamos-stable-source.json` | — | The SteamOS image and Valve source this build used |
| `logs.tar.gz` | — | All build logs, including the generated patch report (`release-notes.md`) |
| `README.md` | — | This file |

On a Mac, download everything into `~/Downloads/{tag}/` with `automation/download-release.sh {tag}`.

## Install

Run in Konsole on the Deck (Desktop Mode). Each `sudo` asks for your password.

```bash
# 0. Download into its own folder and check it
mkdir -p /home/deck/Downloads/{tag}
cd /home/deck/Downloads/{tag}
base={repo_url}/releases/download/{tag}
curl -LO "$base/{kernel_pkg}"
curl -LO "$base/SHA256SUMS"
sha256sum -c --ignore-missing SHA256SUMS

# 1. Make the system writable
sudo steamos-readonly disable
sudo steamos-devmode enable --no-prompt

# 2. Save a copy of the stock kernel (your rollback)
sudo pacman -Sy
sudo pacman -Sw --noconfirm {stock}
ls /var/cache/pacman/pkg/ | grep {stock}

# 3. Install (answer y to "Remove {stock}?", then y to proceed)
sudo pacman -U {kernel_pkg}

# 4. Update the boot menu, lock the system again, reboot
sudo grub-mkconfig -o /boot/grub/grub.cfg
sudo steamos-readonly enable
sudo reboot
```

- After step 0, `sha256sum` must print `OK`. After step 2, `ls` must show a `{stock}-…` file. If not, stop.
- During step 3, these messages are expected and harmless:
  - `gaming-swap: migration failed: Not enough free space in /home …; old swap is preserved` — see "Swap" below.
  - `ERROR: module not found:` for `virtio_*`, `qemu_fw_cfg`, `ata_*`, `pata_acpi`, `vmd`, `spi_intel*`, `blake2b_generic` — virtual-machine, Intel and legacy drivers the Deck does not have. `blake2b` is built into the kernel.
  - `WARNING: Possibly missing '/bin/bash'` and `xhci_pci_renesas` firmware warnings.
- Any other error: stop and do **not** reboot.

After the reboot, `uname -r` must print `{tag}`.

A SteamOS update replaces the system image, including this kernel. Install it again after each OS update.

## Roll back to the stock kernel

Use the file name that step 2 printed. For SteamOS {image['version']} it is `{stock_pkg}`.

```bash
sudo steamos-readonly disable
sudo pacman -U /var/cache/pacman/pkg/{stock_pkg}   # answer y to remove {args.pkgbase}
sudo grub-mkconfig -o /boot/grub/grub.cfg
sudo steamos-readonly enable
sudo reboot
```

If the Deck does not boot: try holding the **`…`** button while pressing **power** to open the SteamOS boot menu and start the previous image (not tested with this kernel). If that does not work, use a SteamOS recovery USB.

## What is in this kernel

**Removed** (compared with upstream Charcoal)

| Item | Note |
|---|---|
| 50 W power limit | Back to stock: 29 W sustained / 30 W fast |
| IOMMU PerfOpt | SteamOS boots with `amd_iommu=off` anyway |
| ZRAM-IR | With its udev rule, helper and zram drop-ins |
| ADIOS | Disk I/O scheduler is stock `mq-deadline` |
| NAP | Idle governor is stock `menu` |
| Clang Polly | |
| minstrel_ht ×3, ath11k remapped-CE | No effect on Deck Wi-Fi (firmware rate control; PCI, not AHB) |
| xone, xpadneo, xpad-noone | Stock `xpad` and `xbox-gip` are used |

**Changed**

| Item | Change |
|---|---|
| CPU soft maximum | 4000 MHz (SMU range `CCLK 1400–4000 MHz`); the CPU still reports 3.5 GHz as its real maximum |
| Kernel name | `<Valve version>-<pkgrel>-csrutil-<commit>`, no `-g<commit>`, `-dirty` or `+` |

**Kept**

| Item | Version in this build |
|---|---|
| BORE + sched_ext coexistence fix | {version(lock, 'bore')} |
| POC Selector | {version(lock, 'poc_selector')} |
| LRU CAST | {version(lock, 'lru_cast')} |
| AMD P-State EPP boost | `amd_pstate.epp_boost=1` |
| zstd level 1, Zen 01/02, Clear, O3 + Zen 2 CPU optimizations | |
| dkms-clang, libbpf, firmware-name, ryzen_smu | |
| Sysctl, memory and Mesa tuning; gaming zswap swap setup | |

Exact sources and SHA-256 for every patch are in `patch-lock.json`.

## Swap

The gaming swap setup (zswap 35 % RAM, ZRAM off, `/home` swapfile = 100 % of RAM) needs free space in `/home` equal to RAM + 1 GiB (about 15.5 GB on a 16 GB Deck). If there is not enough, it keeps the stock swap (zram + swapfile) and SteamOS keeps zswap off. After freeing space, run:

```bash
sudo /usr/lib/gaming-swap/configure
```

## Known messages that are not caused by this kernel

| Message | Note |
|---|---|
| `systemd-repart.service` failed | Same on the stock kernel: no free disk space to grow into |
| `opt3001 … error -121`, `i2c_designware … lost arbitration` | Same on the stock kernel |
| `ccp_crypto: no available CCPs` | No AMD crypto coprocessor to use; nothing depends on it |
| `Kernel compiled without mitigations` | Charcoal build choice; SteamOS already boots with `mitigations=off` |

## Check the files on a computer

```bash
shasum -a 256 -c RELEASE-ZIP-SHA256SUM            # sha256sum -c on Linux
shasum -a 256 -c SHA256SUMS
```
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("kernel-release", "pkgbase", "pkgver", "pkgrel", "release-zip", "lock", "source",
                 "repository", "commit", "run-id", "assets-dir", "output"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--pull-request", default="")
    args = parser.parse_args()
    lock = json.loads(Path(args.lock).read_text(encoding="utf-8"))
    source = json.loads(Path(args.source).read_text(encoding="utf-8"))
    Path(args.output).write_text(render(args, lock, source), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
