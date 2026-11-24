# Working rules for this repository

These are the owner's (csrutil) standing instructions. Follow them without being asked again.

## Files and folders
- Never put files directly in `~`. Always use a dedicated folder, so a mistake can only affect that folder.
  - Mac: `~/Downloads/<name>/` (for releases: `~/Downloads/<tag>/`).
  - Steam Deck: `/home/deck/Downloads/<name>/`.
- After a successful build, download the release into `~/Downloads/<tag>/` right away with `automation/download-release.sh` (it checks the checksums). Do not only post a link.

## Builds, releases and GitHub Actions
- Actions hours are limited. Use `[skip ci]` for docs-only commits. Cancel runs that a newer push makes useless.
- Every successful build publishes a GitHub release named after the kernel (`uname -r`): pull requests as pre-release, `master` as Latest. The release notes are the generated `README.md` with full install instructions and a risk warning at the top (may damage the device, no warranty, no responsibility). Keep that warning.
- Pull request builds save the compiler cache; later runs of the same PR are warm.
- Open pull requests on this fork (`csrutil/linux-charcoal-vulcano`), not on upstream (`zarpon/linux-charcoal-vulcano`).
- When waiting, sleep at most 180 seconds per command.

## Kernel
- Kernel name: `<Valve version>-<pkgrel>-csrutil-<commit>`, for example `7.2.7-valve2-1-csrutil-2244341`. Never `-g<commit>`, `-dirty` or `+`.
- Kept, removed and changed patches are listed in the release `README.md` (`automation/generate-deck-readme.py`). Do not add back a removed item without asking.

## Steam Deck
- Reach it with `ssh deck@steamdeck`. `sudo` needs the owner's password: give the owner the full command list, in order, in one block.
- Never install, remove, reboot or change settings on the Deck without the owner. Read-only checks are fine; restore anything you change for a test.
- After an install and reboot, check: `uname -r`, failed units, kernel errors compared with the previous boot, Wi-Fi, Bluetooth, idle governor, CPU/power limits, swap.

## Communication
- English only: docs, release notes, generated reports, code comments and commit messages.
- Do the whole job end to end; do not stop to offer the next obvious step.
- Short answers. Group long lists into small tables (for example Removed / Changed / Kept).
