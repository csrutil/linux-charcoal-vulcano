# Zswap and a swapfile on the home partition

The installation uses `zswap.enabled=1`, `zswap.max_pool_percent=35`,
`zswap.shrinker_enabled=1`, `zswap.compressor=zstd` and the `zsmalloc` allocator.
The `zswap.zpool=zsmalloc` argument is kept for older kernels; current kernels
use zsmalloc directly and do not offer that selector in sysfs.

The package creates `/home/.gaming-swap/swapfile` on the partition that holds
`/home`, sized to 100% of `MemTotal`, rounded to whole pages. The folder is
root-only (0700) and the file has mode 0600. On Btrfs it uses a separate
subvolume and `btrfs filesystem mkswapfile`, without CoW or holes, and checks
the mapping before `swapon`. ext4 and XFS are also supported.

The new file is turned on before the previous swapfiles are drained and removed.
They are found from active swaps, fstab, swap units and usual paths, including
old inactive swapfiles in usual folders and in user folders under `/home`. The
migration only finishes after it **physically deletes** the old files and checks
that they are gone. Files without a swap signature are not deleted. Swap
partitions are kept. Not enough space, an invalid Btrfs layout or a `swapoff`
failure stops the migration and keeps the old files.
Creating the file needs free space for the new file plus a 1 GiB reserve, in
addition to the old swap that still exists. Updates reuse a file of the correct
size; a RAM change creates another name in the same folder.

Persistence uses `/etc/fstab`, GRUB parameters, modprobe, a disabled
zram-generator and masks for the zram services found, including SteamOS's.
`gaming-zswap.service` applies the parameters again through sysfs at every boot.
The file `/etc/tmpfiles.d/zswap-disable.conf` points to `/dev/null`, which
cancels the SteamOS rule of the same name that turns zswap off after the
service. A previous local configuration is kept as
`zswap-disable.conf.gaming-swap.bak`.
LRU CAST's own settings are kept. The migration runs on the installed system,
never in the package build environment.

The settings stay across reboots and kernel reinstalls.
A SteamOS image update that replaces settings or packages requires installing
the kernel/tuning again. The script does not set up hibernation.

After a reboot, check:

```bash
swapon --show
cat /sys/module/zswap/parameters/{enabled,max_pool_percent,shrinker_enabled,compressor}
systemctl status gaming-zswap.service
```

`swapon --show` must list the file in `/home/.gaming-swap` and must not list
`/dev/zram*`. The parameters must show `Y`, `35`, `Y` and `zstd`.
If the installation fails, fix the reported error and run again:

```bash
sudo /usr/lib/gaming-swap/configure
```
