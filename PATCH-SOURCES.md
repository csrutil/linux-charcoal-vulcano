# Source and compatibility policy

The entry point `automation/prepare-steamos-stable.py` reads Valve's official stable channel, finds the kernel in the image's package list, and derives the source index from the SteamOS version. SteamOS 3.9 uses `jupiter-3.9`; 3.10 automatically uses `jupiter-3.10`. A series is never selected only because it appears in main or in the source index.

`automation/patch-sources.json` declares every patch family. The generated policy in `logs/patch-source-overrides-stable.json` uses the detected series and keeps the families, ports and source hashes. Some helper names still contain `7.2` for historical reasons; stable discovery is not fixed to that version.

The resolver first finds the newest version of each upstream project. It prefers that version's native variant for the detected series. When a local port is needed, it requires the exact upstream version and hash; if those bytes change, the build stops for review. Adapters check the expected structure, and preparation checks that each patch applies to the real tree before compilation. A new series can require port fixes; patches are never removed to make a build pass.

This priority includes `rN` revisions: the native variant only wins when it belongs to the newest upstream version; if a later version exists only for another series, the revised port of that version is used. CAST comes from `firelzrd/lru_cast`, with `CONFIG_LRU_CAST=y` and the upstream default activation. The adapter tries the original bytes first and only adapts the revised include context; unknown changes require review, without falling back to an older release. No `vm.swappiness` tuning is installed: it stays at the kernel default, subject to external system settings.

Single-commit and mailing-list sources are recorded by their exact bytes. MBOX/MIME is decoded before hashing and applying. The AMD P-State EPP boost series keeps four separate components. Sources that Valve already includes are counted by the resolver and not applied twice.

`logs/patch-lock.json` records versions, commits, paths, URLs, origins, SHA-256 and size of the main and auxiliary components. `logs/steamos-stable-source.json` records the stable image and the exact source. The build checks both before it publishes a release.

The local Van Gogh CPU frequency patch stays in the repository. The old BORE 6.16 overlay is kept as a compatibility reference; it does not replace the current upstream BORE selection. The replaced 6.18 implementations were removed from the current tree and remain available in the Git history.
