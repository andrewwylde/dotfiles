# agent-sync

`agent-sync` fans out the agent-neutral `library/` into Claude Code, Cursor,
OpenCode, and Pi. Cursor receives copies; other Targets receive symlinks unless
their destination parent is itself a symlink.

```sh
cargo build --release
./target/release/agent-sync sync
./target/release/agent-sync sync --dry-run
./target/release/agent-sync verify
./target/release/agent-sync list
```

Set `DOTFILES_DIR` when the repo is not at `~/dotfiles` or
`~/dotfiles-local`. Use `sync --root <sandbox>` to redirect Target paths during
testing.

Migration is explicit and backed up under `.agent-sync-backups/`:

```sh
agent-sync migrate --dry-run
agent-sync migrate --write
agent-sync migrate --write --backup-targets
agent-sync migrate --rollback <backup-id>
```

`--write` refuses dirty legacy Target trees unless `--allow-dirty` is supplied.
Unsupported Target/kind combinations are reported and skipped. Do not run
`npx skills remove --all -y` unattended: it scans Target directories and can
delete `andrew-*` fan-outs; recover them with `agent-sync sync`.
# agent-sync

Fan out an agent-neutral Library (`library/{skills,commands,agents,hooks}`) to Claude Code, Cursor, OpenCode, and Pi.

## Build

```bash
cd agent-sync
cargo build --release
cp target/release/agent-sync ~/dotfiles/bin/agent-sync   # or use setup helpers
```

## Usage

```bash
export DOTFILES_DIR=~/dotfiles   # optional
agent-sync list
agent-sync sync --dry-run
agent-sync sync
agent-sync verify
agent-sync migrate --dry-run
agent-sync migrate --write
agent-sync migrate --rollback 20260818T000000Z
```

Sandbox / tests:

```bash
agent-sync sync --root /tmp/agent-sync-sandbox
```

## Library layout

See repo `CONTEXT.md` and `.taskmaster/docs/locked-manifest-schema.md`.
