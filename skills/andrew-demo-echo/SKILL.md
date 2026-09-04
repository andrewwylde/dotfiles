---
name: demo-echo
description: Throwaway prototype skill. Echo a fixed phrase so Manifest + Wrapper fan-out is visible. Do not use in production.
---

# Demo Echo

Throwaway Library skill for the agent-sync one-skill fan-out prototype.

When invoked, reply with exactly:

`demo-echo: shared-body`

This body is Target-neutral. Cursor-only additions come from `manifest.toml` overlays at Fan-out.
