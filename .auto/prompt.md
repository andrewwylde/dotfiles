# Autoresearch: Optimize dotfiles management performance

## Objective
Optimize the performance of the agent-sync dotfiles management tool, focusing on reducing the time required for library scanning and item installation operations.

## Metrics
- **Primary**: `sync_µs` — total sync operation time in microseconds (lower is better)
- **Secondary**: 
  - `library_scan_µs` — library scan phase time
  - `install_µs` — installation phase time
  - `items_processed` — number of items processed during sync

## How to Run
`./.auto/measure.sh` — outputs `METRIC name=value` lines.

## Files in Scope
- `agent-sync/` — the Rust project being optimized
- `library/` — dotfiles library items (139 skills, 22 commands, 99 agents, 1 hook)
- `Cargo.toml` and `src/` — source code files that may be modified for optimization

## Off Limits
- Do not remove or rename existing library items
- Do not change the fundamental sync algorithm or CLI interface
- Do not add new dependencies without strong justification
- Do not modify test files

## What's Been Tried
[This will be updated as experiments accumulate. Note key wins, dead ends, and architectural insights so the agent doesn't repeat failed approaches.]