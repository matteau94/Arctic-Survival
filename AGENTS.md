# Disk usage and Git LFS

- ACTIVE STORAGE GUARD: repository-local `filter.lfs.process` is empty, `filter.lfs.clean=false`, and `filter.lfs.required=true`. This intentionally fails LFS clean operations. Do not restore the filter or run `git lfs install` automatically: the desktop app's background `git hash-object --stdin-paths` repeatedly accumulated another ~10 GiB after cleanup, even when agents ran no Git commands. New LFS asset staging remains blocked until that background behavior is resolved. Never set `required=false` or commit raw binary files as a workaround. Explain this limitation when asked to commit assets.

- This repository contains large Blender assets tracked with Git LFS. On 2026-09-27, abandoned files in `.git/lfs/tmp` consumed 45.38 GiB and filled the drive.
- Git operations that inspect changed LFS assets can invoke the clean filter and write temporary copies, even for status or diff. Use the approved elevated execution path when sandbox restrictions block access to `.git`; do not repeatedly retry failing sandboxed Git commands.
- After an LFS permission or disk-space error, stop retries and inspect `.git/lfs/tmp`. Only remove abandoned temporary files after confirming no Git LFS process is active. Preserve `.git/lfs/objects`, repository history, and project assets.
- Prefer scoped source-file diffs when inspecting code. Avoid repeatedly hashing or staging large assets that have not changed.
- Do not create additional full-scene backups or repeated render/export batches unless needed for the user's request. Check available space before large outputs and reuse disposable build outputs.
