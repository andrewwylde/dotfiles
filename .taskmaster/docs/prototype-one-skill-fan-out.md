# Prototype: one skill Fan-out to two Targets

Throwaway. Answers: does **Manifest + Wrapper + hybrid install** feel right when one Library skill lands in two Target dirs?

Not production migrate. Does not write to real `~/.claude` or `~/.cursor`.

## Run

From the repo root:

```bash
.taskmaster/prototype-fanout/run.sh
```

Idempotent: wipes `wrappers/` + `sandbox/` and regenerates. Prints a report (also `.taskmaster/prototype-fanout/LAST_RUN.txt`).

## What to look at

1. **Library** (unprefixed, shared body + opt-in Manifest):
   `library/skills/demo-echo/SKILL.md` + `manifest.toml`
2. **Wrappers** (generated per Target, Fan-out basename `andrew-demo-echo`):
   `.taskmaster/prototype-fanout/wrappers/{claude,cursor}/andrew-demo-echo/SKILL.md`
3. **Hybrid install** in the sandbox (mimics `~/.claude/skills/` and `~/.cursor/skills/`):
   - Claude: **symlink** → wrapper dir
   - Cursor: **copy** of wrapper dir (never symlink)
4. **Overlay visible on Cursor only**: `disable-model-invocation: true` plus a `body_append` HTML comment. Claude wrapper matches the Library body.
5. **Name split**: Library dir / frontmatter `name` stay `demo-echo`; install dir is `andrew-demo-echo`.

Diff that shows the shape:

```bash
diff -u library/skills/demo-echo/SKILL.md \
  .taskmaster/prototype-fanout/wrappers/cursor/andrew-demo-echo/SKILL.md
ls -la .taskmaster/prototype-fanout/sandbox/.claude/skills/
ls -la .taskmaster/prototype-fanout/sandbox/.cursor/skills/
```

## Locked decisions this demo honors

| Lock | Here |
|------|------|
| Manifest `manifest.toml` at item root | `library/skills/demo-echo/manifest.toml` |
| Overlay = deep-merge frontmatter + optional `body_append` | Cursor overlay only |
| Fan-out basename `andrew-<name>` | `andrew-demo-echo` |
| Cursor always copy | sandbox `.cursor/skills/` |
| Claude symlink OK | sandbox `.claude/skills/` |
| Coerce copy if skills parent is a symlink | coded in `run.sh` (sandbox parent is a real dir) |
| Output = Target-shaped trees, not committed production homes | `.taskmaster/prototype-fanout/sandbox/` |

See [locked-manifest-schema.md](./locked-manifest-schema.md), [locked-grills-batch.md](./locked-grills-batch.md), [research-target-install-path-matrix.md](./research-target-install-path-matrix.md), repo-root `CONTEXT.md`.

## Out of scope

Real `~/.claude` / `~/.cursor`, OpenCode/Pi, hooks, migrate, `npx skills`, production `agent-sync` CLI.
