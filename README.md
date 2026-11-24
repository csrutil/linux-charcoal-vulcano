# Charcoal SteamOS Kernel — stable channel

`master` builds the Charcoal kernel for the current **SteamOS stable** channel. SteamOS 3.9 stable currently ships Linux 7.2; these are different version numbers. The complete maintained `kernel-7.2` stack has replaced the former 6.18 pipeline on `master`.

## Install Latest

Update SteamOS stable, then run in Desktop Mode.

```bash
curl -fsSL https://raw.githubusercontent.com/zarpon/linux-charcoal-vulcano/master/install-charcoal.sh -o install-charcoal.sh && bash install-charcoal.sh
```

The installer reads GitHub's [releases/latest](https://github.com/zarpon/linux-charcoal-vulcano/releases/latest), rejecting drafts, prereleases and Preview tags. It accepts a versioned stable `charcoal-<kernel package version>-r<run>` tag, one `linux-charcoal-<series>-*.zip` bundle and `RELEASE-ZIP-SHA256SUM`. Package names follow the resolved kernel series: currently `linux-charcoal-72` and `linux-charcoal-72-headers`, with a corresponding suffix for future kernels.

Before package changes, the installer verifies the ZIP SHA-256, safely extracts exactly the matching kernel/headers pair, verifies both package hashes and queries package metadata with pacman. `pacman -Qp` checks metadata; it does not simulate the complete transaction or available space.

It identifies previous `linux-charcoal*` packages and the conflicting stock kernel/headers for the selected series. Stock removal requires explicit confirmation; unrelated packages are excluded. After transaction confirmation, it enables filesystem writes and developer mode, removes approved packages with narrowly scoped `pacman -Rdd`, installs the verified pair, reapplies the persistent swap configuration and updates GRUB. Read-only mode is restored on exit. It never reboots automatically.

Exact cached copies in `/var/cache/pacman/pkg` are staged for rollback. If the new installation fails and every removed package was cached, restoration is attempted. Without complete cache copies, automatic rollback cannot be guaranteed: repair a failed kernel installation before rebooting. Keep a SteamOS recovery method available.

Existing unattended options are preserved: `CHARCOAL_72_REMOVE_STOCK=1` explicitly authorizes stock removal and `CHARCOAL_72_ASSUME_YES=1` accepts both prompts. Their legacy names remain compatible across kernel series.

After success, reboot manually and check `uname -r` and `pacman -Q | grep '^linux-charcoal'`. The running kernel is named `<Valve version>-<pkgrel>-csrutil-<commit>`, for example `7.2.7-valve2-1-csrutil-49c07cb`, where `<commit>` is this repository's short commit. Use this installer with the current SteamOS stable release, not an older unsupported OS image.

## Automatic stable tracking

The source of truth is Valve's [stable update metadata](https://steamdeck-atomupd.steamos.cloud/meta/holo/steamos/amd64/steamdeck/stable.json), not the largest kernel number in a source index. `automation/prepare-steamos-stable.py`:

1. Selects an image explicitly marked `stable`, with its SteamOS version and build ID.
2. Downloads that exact image's `.manifest.pacman` from Valve's image server.
3. Identifies the exact installed `linux-neptune-<series>` package/version.
4. Derives the matching source repository from the SteamOS major/minor version: 3.9 uses `jupiter-3.9`; 3.10 automatically uses `jupiter-3.10`.
5. Requires that exact source archive, resolves its Valve tag, fetches its Arch/Valve config and updates package names and the patch compatibility target.

Thus, a stable transition to Linux 7.3 or newer is discovered automatically, even when the SteamOS repository changes. Preview/main images and RC/beta kernel packages are rejected. Missing or ambiguous stable metadata fails the build; there is no silent fallback to main or an older source. Exact image, package-manifest URL, source URL, tag and series are recorded in `steamos-stable-source.json`.

Kernel discovery does not bypass patch compatibility. Every patch family remains required. The newest upstream project version is selected first, preferring a native variant for the resolved series; tracked ports/adapters preserve their upstream hashes and lineage. Existing ports are checked against the new source before compilation. If upstream bytes or kernel APIs change incompatibly, the build fails for correction instead of removing a patch, downgrading its project version or publishing an incomplete kernel. See [PATCH-SOURCES.md](PATCH-SOURCES.md).

The maintained stack includes BORE/sched_ext coexistence, POC Selector, LRU CAST, AMD P-State EPP boost, CPU/O3 optimizations, Clear/Zen changes, DKMS/Clang compatibility, firmware file-name logging, Ryzen SMU and a local Van Gogh CPU-frequency patch (soft maximum 4.0 GHz). The Van Gogh power limit stays at Valve's stock 29 W sustained / 30 W fast. Application order is preserved. `6.16.12-bore-6.8.0-final.patch` is retained as a compatibility reference; the current BORE source is selected dynamically. Superseded 6.18 payloads are replaced by their maintained 7.2 implementations.

Functionality already present in Valve's source remains accounted for by the resolver instead of being applied twice. Retired fsync opcode-31, C23/libbpf, Bluetooth SSP and upstream Qualcomm ath11k patches already absent from `kernel-7.2` are not reintroduced. The OpenWrt minstrel_ht and ath11k remapped-CE patches were removed: both Steam Deck Wi-Fi drivers (rtw88, ath11k PCI) use firmware rate control, and the remapped-CE change only affects ath11k AHB devices. ZRAM-IR, ADIOS, NAP, Clang Polly, IOMMU PerfOpt, the 50 W Van Gogh power limit and the out-of-tree xone/xpadneo/xpad-noone drivers were also removed. Valve's stock CPU idle governors and in-tree `xpad`/`xbox_gip` Xbox drivers are used instead. The validated `patch-lock.json` records actual patch versions, origins, hashes and upstream-provided functionality.

## Build and release policy

[push.yml](.github/workflows/push.yml) builds every `master` push and pull request, and publishes a GitHub release for each: `master` builds as **Latest**, pull request builds as **pre-release**. `validation/**` builds do not publish. A manual dispatch supports `publish_release=false` for artifacts only. The daily build runs at **03:05 UTC / 00:05 Brasília**, dispatching only `master`.

The release tag and title are the kernel name (`uname -r`, for example `7.2.7-valve2-1-csrutil-2244341`), read from the built package. Source/lock validation, checksum verification, patch preparation, config checks, compilation and packaging must succeed first. The workflow then rereads the release (and, for `master`, `/releases/latest`); publication or readback failure fails the run. Historical releases are retained.

Assets include kernel and headers, the ZIP, checksums, patch lock, stable-source metadata, `logs.tar.gz` and `README.md`. The release notes are that `README.md`: full install, rollback and verification instructions, generated by `automation/generate-deck-readme.py` from the build's validated lock. The ZIP also carries the patch lock, source metadata and checksum audit.

### Build artifacts

To download a release on a Mac, into its own folder `~/Downloads/<tag>/`, with checksums checked:

```bash
automation/download-release.sh            # newest release, including pre-releases
automation/download-release.sh <tag>      # a specific release
```

Every build also uploads one artifact named `linux-charcoal-7.2-<run number>`, kept for 14 days:

```bash
gh run download <run id> --repo csrutil/linux-charcoal-vulcano \
  -n linux-charcoal-7.2-<run number> -D ~/Downloads/linux-charcoal-7.2-<run number>
```

| File | Size (run 3) | What it is |
|---|---|---|
| `linux-charcoal-72-<pkgver>-<pkgrel>-x86_64.pkg.tar.zst` | 105 MB | The kernel package |
| `linux-charcoal-72-headers-<pkgver>-<pkgrel>-x86_64.pkg.tar.zst` | 40 MB | Headers, only needed to build extra modules |
| `linux-charcoal-72-<pkgver>-r<run number>.zip` | 145 MB | Both packages in one bundle |
| `RELEASE-ZIP-SHA256SUM` | — | Checksum for the zip |
| `logs/` | — | Build logs, patch lock and package checksums (`logs/SHA256SUMS`) |

For run 3, `<pkgver>-<pkgrel>` is `7.2.7.valve2.cc2-1`. The Deck needs the two `.pkg.tar.zst` files; the zip holds the same packages. Check the files before you install them (use `sha256sum -c` on Linux):

```bash
shasum -a 256 -c RELEASE-ZIP-SHA256SUM
grep 'pkg\.tar\.zst' logs/SHA256SUMS | shasum -a 256 -c -
```

`kernel-7.2` is retained for manual development builds only. [build-kernel-7.2.yml](.github/workflows/build-kernel-7.2.yml) has no push/schedule trigger or release publication steps; it uploads artifacts. It is no longer dispatched by the daily workflow.

For local preparation with Python 3, Bash and Git:

```bash
python3 automation/prepare-pkgbuild-7.2.py --write PKGBUILD
python3 automation/prepare-steamos-stable.py --fetch-config
python3 automation/resolve-latest-patches-7.2-policy.py --overrides logs/patch-source-overrides-stable.json --write
python3 automation/validate-patch-lock.py --manifest logs/patch-sources-7.2.json --overrides logs/patch-source-overrides-stable.json
```

Some helper filenames retain `7.2` for compatibility; the stable entry point supplies the dynamically detected series. The Dockerfile provides Arch Linux/LLVM. The workflow finalizes checksums from resolved bytes, verifies sources, prepares patches and compiles with makepkg. Static tests do not replace target-hardware boot testing.

## Preserved runtime features

The software Crypto API ZSTD default is **level 1** (ZSTD_DEF_LEVEL=1), used by generic ZSTD zswap. The existing code derives compression parameters and workspace sizes automatically; its window limit and decompressor are unchanged. The build checks the prepared source and publishes zstd-crypto-level.txt and zstd-crypto-source.sha256. This default also applies to other users of the generic Crypto API codec. ZRAM-IR's separate fast setting and hardware-specific Intel QAT backends retain their existing behavior.


O3 and Charcoal gaming/memory configuration remain enabled. Installation persistently disables ZRAM/services, enables ZSTD zswap with a **35% RAM pool**, shrinker enabled, and a `/home` swapfile sized to **100% of RAM**. See [SWAP.md](SWAP.md).

Runtime values remain `vm.vfs_cache_pressure=100`, `vm.dirty_background_ratio=2` and `vm.dirty_ratio=5`, preserving LRU CAST defaults. `CONFIG_ZEN_INTERACTIVE` controls the existing evdev asynchronous RCU and P-State schedutil-selection changes, without importing additional Zen memory/scheduler defaults.
