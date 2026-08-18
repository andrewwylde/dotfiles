---
name: local-demo-stack
description: >
  Start parable-platform local demo services (web-api, web-admin-api, web-app)
  in durable terminals with health checks. Use when preparing a demo, when
  managed background shells keep dying mid-session, or when the user asks to
  bring up the local stack for UI dogfood. Do not use for production deploys.
---

# Local Demo Stack

Keep demo services alive in durable terminals (user-owned or long-lived), not
ephemeral agent background shells that exit when the parent turn ends.

## Services

| Service | Typical command | Health |
|---------|-----------------|--------|
| Postgres | `make start-postgres` | `pg_isready` / docker health |
| web-api | `cd services/web-api && set -a && . ./.env && set +a && go run ./cmd/server` | `curl -sf localhost:8080/health` (or service health path) |
| web-admin-api | `cd services/web-admin-api && set -a && . ./.env && set +a && go run ./cmd/server` | admin health endpoint |
| web-app | `cd apps && bun run link-schemas && bun run dev:web-app` | Vite URL printed (port may not be 5173) |

Prefer `make dev` when Overmind/tmux is already the team convention for the
worktree. Otherwise start each process in a **durable** terminal:

- Tell the user which commands to leave running in iTerm/Terminal tabs, **or**
- Use the project's documented long-lived launcher (e.g. `ppwt` / overmind), **or**
- Start with `block_until_ms: 0` only after confirming a watcher/keepalive exists

## Bootstrap order

1. Worktree path awareness (`worktree-awareness`)
2. Stage 0 schemas + deps: `make build-schemas && make install-deps`
3. Postgres + migrations + seed if needed
4. Start APIs, then frontend
5. Record URLs (Vite may bump ports) and cookie host (localhost vs 127.0.0.1)

## Health gate before demo

Do not claim "ready" until:

```bash
curl -sf "$API_HEALTH" >/dev/null
curl -sf "$ADMIN_HEALTH" >/dev/null
curl -sf "$WEB_ORIGIN/" >/dev/null
```

If a managed shell exited, restart that service only and re-check health —
do not restart the whole stack blindly.

## Anti-patterns

- Relying on agent-managed shells that die when the conversation idles
- Symlinking main-repo `node_modules` into the worktree
- Skipping `link-schemas` before frontend demo
- Mixing `localhost` and `127.0.0.1` cookie origins during login demos
