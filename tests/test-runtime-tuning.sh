#!/usr/bin/env bash
set -Eeuo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sandbox="$(mktemp -d)"
trap 'rm -rf "$sandbox"' EXIT

fail() {
  echo "runtime tuning validation failed: $*" >&2
  exit 1
}

require_line() {
  local file="$1"
  local line="$2"
  grep -Fxq -- "$line" "$file" || fail "missing '$line' in ${file#$root/}"
}

require_value() {
  local file="$1"
  local value="$2"
  [[ "$(<"$file")" == "$value" ]] || fail "expected '$value' in $file"
}

bash -n "$root/PKGBUILD"

require_line "$root/99-charcoal-sysctl.conf" "vm.min_free_kbytes=131072"
require_line "$root/99-charcoal-sysctl.conf" "vm.compaction_proactiveness=15"
require_line "$root/99-charcoal-sysctl.conf" "vm.compact_unevictable_allowed=0"
require_line "$root/99-charcoal-sysctl.conf" "vm.dirty_expire_centisecs=1500"
require_line "$root/99-charcoal-sysctl.conf" "vm.dirty_writeback_centisecs=500"
require_line "$root/99-charcoal-sysctl.conf" "vm.watermark_boost_factor=0"
require_line "$root/99-charcoal-sysctl.conf" "vm.watermark_scale_factor=125"
require_line "$root/99-charcoal-sysctl.conf" "kernel.split_lock_mitigate=0"
require_line "$root/99-charcoal-sysctl.conf" "vm.dirty_background_ratio=2"
require_line "$root/99-charcoal-sysctl.conf" "vm.dirty_ratio=5"
require_line "$root/99-charcoal-sysctl.conf" "vm.vfs_cache_pressure=100"

require_line "$root/99-charcoal-gaming.conf" "MESA_SHADER_CACHE_MAX_SIZE=10G"
require_line "$root/99-charcoal-gaming.conf" "MESA_DISK_CACHE_DATABASE=1"
require_line "$root/99-charcoal.sh" "export MESA_SHADER_CACHE_MAX_SIZE=10G"
require_line "$root/99-charcoal.sh" "export MESA_DISK_CACHE_DATABASE=1"

require_line "$root/99-charcoal-memory.conf" "w! /sys/kernel/mm/transparent_hugepage/enabled - - - - madvise"
require_line "$root/99-charcoal-memory.conf" "w! /sys/kernel/mm/transparent_hugepage/defrag - - - - defer"
require_line "$root/99-charcoal-memory.conf" "w! /sys/kernel/mm/transparent_hugepage/shmem_enabled - - - - advise"
require_line "$root/99-charcoal-memory.conf" "w! /sys/kernel/mm/transparent_hugepage/khugepaged/defrag - - - - 0"
require_line "$root/99-charcoal-memory.conf" "w! /sys/kernel/mm/transparent_hugepage/khugepaged/max_ptes_none - - - - 128"
require_line "$root/99-charcoal-memory.conf" "w! /sys/kernel/mm/transparent_hugepage/khugepaged/max_ptes_swap - - - - 8"
require_line "$root/99-charcoal-memory.conf" "w! /sys/kernel/mm/ksm/run - - - - 0"
require_line "$root/99-charcoal-memory.conf" "w! /sys/kernel/mm/lru_gen/enabled - - - - 7"
require_line "$root/99-charcoal-memory.conf" "w! /sys/kernel/mm/lru_gen/min_ttl_ms - - - - 0"

require_line "$root/config-charcoal" "CONFIG_CMDLINE_BOOL=y"
require_line "$root/config-charcoal" 'CONFIG_CMDLINE="amd_pstate.epp_boost=1"'
require_line "$root/config-charcoal" "# CONFIG_CMDLINE_OVERRIDE is not set"
grep -Fq 'latest-amd-pstate-epp-boost-03-core.patch' "$root/PKGBUILD" || fail "AMD P-State EPP boost patch is missing from the dynamic patch stack"

for package_path in \
  'usr/lib/gaming-swap/configure' \
  'usr/lib/systemd/system/gaming-zswap.service' \
  'usr/lib/sysctl.d/99-charcoal.conf' \
  'usr/lib/tmpfiles.d/99-charcoal-memory.conf' \
  'usr/lib/environment.d/99-charcoal-gaming.conf'; do
  grep -Fq "\$pkgdir/$package_path" "$root/PKGBUILD" || fail "package install missing: $package_path"
done

# Local sources are pinned by the checked-out Git commit. Keep a real SHA-256
# entry for every local source (never SKIP), but defer byte-for-byte comparison
# until the build stage regenerates checksums from the final source set and
# executes makepkg --verifysource. This avoids stale local SHA failures after
# legitimate branch changes such as config-neptune updates.
source "$root/PKGBUILD"
for index in "${!source[@]}"; do
  candidate="${source[$index]%%::*}"
  [[ -f "$root/$candidate" ]] || continue
  checksum="${sha256sums[$index]}"
  [[ "$checksum" != "SKIP" ]] || fail "local source has SKIP checksum: $candidate"
  [[ "$checksum" =~ ^[0-9a-f]{64}$ ]] || fail "invalid SHA-256 entry: $candidate"
done

# Have systemd parse and apply the shipped tmpfiles payload in an isolated root.
if command -v systemd-tmpfiles >/dev/null 2>&1; then
  rootfs="$sandbox/rootfs"
  install -D -m 0644 "$root/99-charcoal-memory.conf" \
    "$rootfs/usr/lib/tmpfiles.d/99-charcoal-memory.conf"
  while read -r path; do
    install -D -m 0644 /dev/null "$rootfs$path"
  done <<'EOF'
/sys/kernel/mm/transparent_hugepage/enabled
/sys/kernel/mm/transparent_hugepage/defrag
/sys/kernel/mm/transparent_hugepage/shmem_enabled
/sys/kernel/mm/transparent_hugepage/khugepaged/defrag
/sys/kernel/mm/transparent_hugepage/khugepaged/max_ptes_none
/sys/kernel/mm/transparent_hugepage/khugepaged/max_ptes_swap
/sys/kernel/mm/ksm/run
/sys/kernel/mm/lru_gen/enabled
/sys/kernel/mm/lru_gen/min_ttl_ms
EOF
  systemd-tmpfiles --create --boot --root="$rootfs"
  require_value "$rootfs/sys/kernel/mm/transparent_hugepage/enabled" "madvise"
  require_value "$rootfs/sys/kernel/mm/transparent_hugepage/defrag" "defer"
  require_value "$rootfs/sys/kernel/mm/transparent_hugepage/shmem_enabled" "advise"
  require_value "$rootfs/sys/kernel/mm/transparent_hugepage/khugepaged/defrag" "0"
  require_value "$rootfs/sys/kernel/mm/transparent_hugepage/khugepaged/max_ptes_none" "128"
  require_value "$rootfs/sys/kernel/mm/transparent_hugepage/khugepaged/max_ptes_swap" "8"
  require_value "$rootfs/sys/kernel/mm/ksm/run" "0"
  require_value "$rootfs/sys/kernel/mm/lru_gen/enabled" "7"
  require_value "$rootfs/sys/kernel/mm/lru_gen/min_ttl_ms" "0"
fi

# Deterministic admission-control simulation for one 2 MiB x86 THP. This is
# not a hardware FPS benchmark: it proves that the shipped limits accept the
# configured 128-hole/8-swapped candidate while retaining explicit bounds
# against candidates that exceed the configured khugepaged limits.
python3 - "$root/99-charcoal-memory.conf" <<'PY'
from dataclasses import dataclass
from pathlib import Path
import sys

PTE_PER_THP = 512
PAGE_SIZE = 4096


def tmpfiles_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        fields = raw_line.split()
        if len(fields) == 7 and fields[0] == "w!":
            values[fields[1]] = fields[-1]
    return values


@dataclass(frozen=True)
class Policy:
    max_none: int
    max_swap: int


def eligible(policy: Policy, *, none: int, swap: int) -> bool:
    present = PTE_PER_THP - none - swap
    assert present >= 0
    return none <= policy.max_none and swap <= policy.max_swap


values = tmpfiles_values(Path(sys.argv[1]))
assert values["/sys/kernel/mm/transparent_hugepage/defrag"] == "defer"
proposed = Policy(
    max_none=int(values["/sys/kernel/mm/transparent_hugepage/khugepaged/max_ptes_none"]),
    max_swap=int(values["/sys/kernel/mm/transparent_hugepage/khugepaged/max_ptes_swap"]),
)
assert proposed == Policy(max_none=128, max_swap=8)

legacy = Policy(max_none=64, max_swap=0)
assert eligible(legacy, none=64, swap=0)
assert eligible(proposed, none=128, swap=8)
assert not eligible(legacy, none=128, swap=0)
assert eligible(proposed, none=128, swap=0)
assert not eligible(legacy, none=0, swap=16)
assert eligible(proposed, none=0, swap=8)
assert not eligible(proposed, none=129, swap=0)
assert not eligible(proposed, none=0, swap=9)

legacy_zero_fill = legacy.max_none * PAGE_SIZE
proposed_zero_fill = proposed.max_none * PAGE_SIZE
legacy_swap_bytes = legacy.max_swap * PAGE_SIZE
proposed_swap_bytes = proposed.max_swap * PAGE_SIZE
assert proposed_zero_fill - legacy_zero_fill == 262_144
assert proposed_swap_bytes - legacy_swap_bytes == 32_768

print(
    "THP admission simulation passed: zero-fill cap "
    f"{legacy_zero_fill / 1024**2:.2f} MiB -> "
    f"{proposed_zero_fill / 1024**2:.2f} MiB; "
    f"swap candidate cap {legacy_swap_bytes // 1024} KiB -> "
    f"{proposed_swap_bytes // 1024} KiB"
)
PY

python3 "$root/tests/test_gaming_swap.py"
python3 "$root/tests/test_kernel_config_validation.py"

echo "runtime tuning validation passed"
