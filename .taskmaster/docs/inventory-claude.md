# Inventory: `.claude` trees (agent-sync task 1.1)

> Generated: 2026-08-17  
> Scope: every top-level item under `.claude/skills/`, `.claude/commands/`, `.claude/agents/`.  
> Dispositions: `library` | `gitignore-private` | `abandon`.  
> No files were moved or copied.

## Summary counts

| Kind | Total | library | gitignore-private | abandon |
|------|------:|--------:|------------------:|--------:|
| skill | 133 | 79 | 9 | 45 |
| command | 21 | 19 | 2 | 0 |
| agent | 97 | 90 | 7 | 0 |
| **all** | **251** | **188** | **18** | **45** |

### Notable findings

- **Broken `.agents` symlinks**: 35 skills are broken relative links to `../../.agents/skills/<name>` (resolve under repo `.agents/`, which does not exist). Canonical copies often live under `~/.agents/skills/`. Disposition: **abandon** for the in-repo stub; do not migrate the broken link.
- **`nx-workspace`**: real Nx monorepo skill, but currently caught by `.gitignore` pattern `**/*-workspace/`. Disposition **library** (fix the pattern later).
- **Cursor overlaps**: skills `_shared`, `gh-stack`, `swarm-test-review`; many commands share names with `.cursor/commands/` (see notes).
- **Parable gitignore stubs absent on disk**: skills `create-migration`, `flesh-out-ticket`, `parable-pr-swarm`, `parable-product-review`, `parable-worktree-repo-hooks`, `seed-tts-data`, `switch-db`, `ticket-router`, `tts-state-restore`; agents `parable-security-reviewer.md`.
- **`skills-cursor`**: not under `.claude`; Cursor product skills are out of scope for this file (task 1.2 / abandon per map).

## `.gitignore` Parable / private patterns (cross-check)

From repo-root `.gitignore`:

```
# Skill eval artifacts and bulky deps
**/*-workspace/
**/*.zip
**/node_modules/
**/.temp-execution-*

# Parable-specific skills (.claude)
.claude/skills/arch-review/  # EXISTS
.claude/skills/classification-local-e2e/  # EXISTS
.claude/skills/create-migration/  # ABSENT
.claude/skills/deploy-release-notes/  # EXISTS
.claude/skills/flesh-out-ticket/  # ABSENT
.claude/skills/gap-analysis/  # EXISTS
.claude/skills/parable-pr-swarm/  # ABSENT
.claude/skills/parable-product-review/  # ABSENT
.claude/skills/parable-worktree-repo-hooks/  # ABSENT
.claude/skills/pr-flow-video/  # EXISTS
.claude/skills/psgen-workflow/  # EXISTS
.claude/skills/seed-tts-data/  # ABSENT
.claude/skills/swarm-review/  # EXISTS
.claude/skills/swarm-test-review/  # EXISTS
.claude/skills/switch-db/  # ABSENT
.claude/skills/ticket-router/  # ABSENT
.claude/skills/tts-state-restore/  # ABSENT
.claude/skills/worktree-snapshot/  # EXISTS

# Parable-specific agents (.claude)
.claude/agents/connector-specialist.md  # EXISTS
.claude/agents/e2e-debugger.md  # EXISTS
.claude/agents/migration-reviewer.md  # EXISTS
.claude/agents/parable-security-reviewer.md  # ABSENT
.claude/agents/psgen-reviewer.md  # EXISTS
.claude/agents/release-coordinator.md  # EXISTS
.claude/agents/spectacles-validator.md  # EXISTS
.claude/agents/tts-debugger.md  # EXISTS

# Parable-specific commands (.claude)
.claude/commands/add-experiment-note.md  # EXISTS
.claude/commands/implement-and-review-loop.md  # EXISTS
```

Also related (not under `.claude`): `config/parable/`, `zsh/configs/parable-platform.zsh`, `zsh/functions/parable-auth.zsh`, `.cursor/commands/implement-and-review-loop.md`.

## Skills (`.claude/skills/`)

| path | kind | disposition | notes |
|------|------|-------------|-------|
| `.claude/skills/_shared` | skill | library | shared prose helper (prose-clarity.md); not a SKILL.md skill; also under .cursor/skills/ |
| `.claude/skills/arch-review` | skill | gitignore-private | listed in .gitignore Parable-specific skills; no SKILL.md; top: evals |
| `.claude/skills/ask-matt` | skill | abandon | BROKEN symlink → ../../.agents/skills/ask-matt (relative .agents; content may live under ~/.agents/skills/ask-matt) |
| `.claude/skills/autoimprove` | skill | library | SKILL.md only |
| `.claude/skills/autoresearch` | skill | library | — |
| `.claude/skills/aws-advisor` | skill | library | — |
| `.claude/skills/changeset-decomposition` | skill | library | — |
| `.claude/skills/classification-local-e2e` | skill | gitignore-private | listed in .gitignore Parable-specific skills; no SKILL.md; top: .DS_Store, evals, scripts |
| `.claude/skills/classification-local-e2e.zip` | skill | abandon | matches **/*.zip bulky artifact; loose file |
| `.claude/skills/claude-handoff` | skill | abandon | BROKEN symlink → ../../.agents/skills/claude-handoff (relative .agents; content may live under ~/.agents/skills/claude-handoff) |
| `.claude/skills/code-review` | skill | abandon | BROKEN symlink → ../../.agents/skills/code-review (relative .agents; content may live under ~/.agents/skills/code-review) |
| `.claude/skills/codebase-design` | skill | abandon | BROKEN symlink → ../../.agents/skills/codebase-design (relative .agents; content may live under ~/.agents/skills/codebase-design) |
| `.claude/skills/codenavi` | skill | library | — |
| `.claude/skills/coding-guidelines` | skill | library | SKILL.md only |
| `.claude/skills/commit-subset` | skill | library | SKILL.md only |
| `.claude/skills/component-common-domain-detection` | skill | library | — |
| `.claude/skills/component-flattening-analysis` | skill | library | — |
| `.claude/skills/component-identification-sizing` | skill | library | — |
| `.claude/skills/content-to-pipeline` | skill | library | — |
| `.claude/skills/core-web-vitals` | skill | library | — |
| `.claude/skills/coupling-analysis` | skill | library | SKILL.md only |
| `.claude/skills/create-rfc` | skill | library | — |
| `.claude/skills/create-technical-design-doc` | skill | library | — |
| `.claude/skills/cursor-subagent-creator` | skill | library | SKILL.md only |
| `.claude/skills/decomposition-planning-roadmap` | skill | library | — |
| `.claude/skills/decomposition-planning-roadmap-workspace` | skill | abandon | matches **/*-workspace/ eval/artifact pattern; no SKILL.md; top: iteration-1, skill-new, skill-old |
| `.claude/skills/demo-script-writer` | skill | library | — |
| `.claude/skills/demo-script-writer-workspace` | skill | abandon | matches **/*-workspace/ eval/artifact pattern; no SKILL.md; top: iteration-1 |
| `.claude/skills/deploy-release-notes` | skill | gitignore-private | listed in .gitignore Parable-specific skills |
| `.claude/skills/deploy-release-notes-workspace` | skill | abandon | matches **/*-workspace/ eval/artifact pattern; no SKILL.md; top: .DS_Store, iteration-1 |
| `.claude/skills/diagnosing-bugs` | skill | abandon | BROKEN symlink → ../../.agents/skills/diagnosing-bugs (relative .agents; content may live under ~/.agents/skills/diagnosing-bugs) |
| `.claude/skills/disk-space-recovery` | skill | library | SKILL.md only |
| `.claude/skills/docs-writer` | skill | library | — |
| `.claude/skills/domain-analysis` | skill | library | — |
| `.claude/skills/domain-identification-grouping` | skill | library | — |
| `.claude/skills/domain-modeling` | skill | abandon | BROKEN symlink → ../../.agents/skills/domain-modeling (relative .agents; content may live under ~/.agents/skills/domain-modeling) |
| `.claude/skills/effectiveness-map` | skill | library | SKILL.md only |
| `.claude/skills/excalidraw-studio` | skill | library | — |
| `.claude/skills/expansion-retention` | skill | library | SKILL.md only |
| `.claude/skills/figma` | skill | library | — |
| `.claude/skills/figma-implement-design` | skill | library | SKILL.md only |
| `.claude/skills/find-skills` | skill | library | SKILL.md only |
| `.claude/skills/frontend-blueprint` | skill | library | — |
| `.claude/skills/frontend-design` | skill | library | — |
| `.claude/skills/full-export` | skill | library | — |
| `.claude/skills/gap-analysis` | skill | gitignore-private | listed in .gitignore Parable-specific skills |
| `.claude/skills/gap-analysis-workspace` | skill | abandon | matches **/*-workspace/ eval/artifact pattern; EMPTY directory (no files) |
| `.claude/skills/gh-address-comments` | skill | library | — |
| `.claude/skills/gh-fix-ci` | skill | library | — |
| `.claude/skills/gh-stack` | skill | library | SKILL.md only; also under .cursor/skills/ |
| `.claude/skills/git-guardrails-claude-code` | skill | abandon | BROKEN symlink → ../../.agents/skills/git-guardrails-claude-code (relative .agents; content may live under ~/.agents/skills/git-guardrails-claude-code) |
| `.claude/skills/grill-me` | skill | abandon | BROKEN symlink → ../../.agents/skills/grill-me (relative .agents; content may live under ~/.agents/skills/grill-me) |
| `.claude/skills/grill-with-docs` | skill | abandon | BROKEN symlink → ../../.agents/skills/grill-with-docs (relative .agents; content may live under ~/.agents/skills/grill-with-docs) |
| `.claude/skills/grilling` | skill | abandon | BROKEN symlink → ../../.agents/skills/grilling (relative .agents; content may live under ~/.agents/skills/grilling) |
| `.claude/skills/gtm-engineering` | skill | library | — |
| `.claude/skills/gtm-metrics` | skill | library | SKILL.md only |
| `.claude/skills/handoff` | skill | abandon | BROKEN symlink → ../../.agents/skills/handoff (relative .agents; content may live under ~/.agents/skills/handoff) |
| `.claude/skills/implement` | skill | abandon | BROKEN symlink → ../../.agents/skills/implement (relative .agents; content may live under ~/.agents/skills/implement) |
| `.claude/skills/improve-codebase-architecture` | skill | abandon | BROKEN symlink → ../../.agents/skills/improve-codebase-architecture (relative .agents; content may live under ~/.agents/skills/improve-codebase-architecture) |
| `.claude/skills/learning-opportunities` | skill | library | — |
| `.claude/skills/legacy-migration-planner` | skill | library | — |
| `.claude/skills/local-demo-stack` | skill | library | SKILL.md only |
| `.claude/skills/loop-me` | skill | abandon | BROKEN symlink → ../../.agents/skills/loop-me (relative .agents; content may live under ~/.agents/skills/loop-me) |
| `.claude/skills/manim-animator` | skill | library | — |
| `.claude/skills/manim-animator-workspace` | skill | abandon | matches **/*-workspace/ eval/artifact pattern; no SKILL.md; top: FINAL_REPORT.md, iteration-1 |
| `.claude/skills/mermaid-studio` | skill | library | — |
| `.claude/skills/migrate-to-shoehorn` | skill | abandon | BROKEN symlink → ../../.agents/skills/migrate-to-shoehorn (relative .agents; content may live under ~/.agents/skills/migrate-to-shoehorn) |
| `.claude/skills/modular-decomposition` | skill | library | — |
| `.claude/skills/modular-design-principles` | skill | library | — |
| `.claude/skills/multi-platform-launch` | skill | library | — |
| `.claude/skills/nx-ci-monitor` | skill | library | SKILL.md only |
| `.claude/skills/nx-generate` | skill | library | SKILL.md only |
| `.claude/skills/nx-run-tasks` | skill | library | SKILL.md only |
| `.claude/skills/nx-workspace` | skill | library | FALSE POSITIVE: currently gitignored by **/*-workspace/ but is a real Nx skill — migrate as library |
| `.claude/skills/partner-affiliate` | skill | library | — |
| `.claude/skills/perf-astro` | skill | library | SKILL.md only |
| `.claude/skills/perf-lighthouse` | skill | library | SKILL.md only |
| `.claude/skills/perf-web-optimization` | skill | library | — |
| `.claude/skills/plan-adversary-review` | skill | library | SKILL.md only |
| `.claude/skills/playwright-skill` | skill | library | contains node_modules (gitignored via **/node_modules/) |
| `.claude/skills/postmortem-to-improvement` | skill | library | SKILL.md only |
| `.claude/skills/pr-flow-video` | skill | gitignore-private | listed in .gitignore Parable-specific skills |
| `.claude/skills/prod-health-frontend-weekly` | skill | library | — |
| `.claude/skills/prompt-engineering-partner` | skill | library | — |
| `.claude/skills/prompt-engineering-partner-workspace` | skill | abandon | matches **/*-workspace/ eval/artifact pattern; no SKILL.md; top: iteration-1 |
| `.claude/skills/prototype` | skill | abandon | BROKEN symlink → ../../.agents/skills/prototype (relative .agents; content may live under ~/.agents/skills/prototype) |
| `.claude/skills/psgen-workflow` | skill | gitignore-private | listed in .gitignore Parable-specific skills; SKILL.md only |
| `.claude/skills/react-composition-patterns` | skill | library | — |
| `.claude/skills/read-memories` | skill | library | — |
| `.claude/skills/render-deploy` | skill | library | — |
| `.claude/skills/research` | skill | abandon | BROKEN symlink → ../../.agents/skills/research (relative .agents; content may live under ~/.agents/skills/research) |
| `.claude/skills/resolving-merge-conflicts` | skill | abandon | BROKEN symlink → ../../.agents/skills/resolving-merge-conflicts (relative .agents; content may live under ~/.agents/skills/resolving-merge-conflicts) |
| `.claude/skills/scaffold-exercises` | skill | abandon | BROKEN symlink → ../../.agents/skills/scaffold-exercises (relative .agents; content may live under ~/.agents/skills/scaffold-exercises) |
| `.claude/skills/security-best-practices` | skill | library | — |
| `.claude/skills/security-ownership-map` | skill | library | — |
| `.claude/skills/security-threat-model` | skill | library | — |
| `.claude/skills/session-postmortem` | skill | library | SKILL.md only |
| `.claude/skills/setup-matt-pocock-skills` | skill | abandon | BROKEN symlink → ../../.agents/skills/setup-matt-pocock-skills (relative .agents; content may live under ~/.agents/skills/setup-matt-pocock-skills) |
| `.claude/skills/setup-pre-commit` | skill | abandon | BROKEN symlink → ../../.agents/skills/setup-pre-commit (relative .agents; content may live under ~/.agents/skills/setup-pre-commit) |
| `.claude/skills/setup-ts-deep-modules` | skill | abandon | BROKEN symlink → ../../.agents/skills/setup-ts-deep-modules (relative .agents; content may live under ~/.agents/skills/setup-ts-deep-modules) |
| `.claude/skills/skill-architect` | skill | library | — |
| `.claude/skills/subagent-creator` | skill | library | SKILL.md only |
| `.claude/skills/swarm-review` | skill | gitignore-private | listed in .gitignore Parable-specific skills |
| `.claude/skills/swarm-review-workspace` | skill | abandon | matches **/*-workspace/ eval/artifact pattern; no SKILL.md; top: iteration-1 |
| `.claude/skills/swarm-test-review` | skill | gitignore-private | listed in .gitignore Parable-specific skills; also under .cursor/skills/ |
| `.claude/skills/targeted-file-read-workspace` | skill | abandon | matches **/*-workspace/ eval/artifact pattern; no SKILL.md; top: iteration-1 |
| `.claude/skills/tdd` | skill | abandon | BROKEN symlink → ../../.agents/skills/tdd (relative .agents; content may live under ~/.agents/skills/tdd) |
| `.claude/skills/teach` | skill | abandon | BROKEN symlink → ../../.agents/skills/teach (relative .agents; content may live under ~/.agents/skills/teach) |
| `.claude/skills/the-fool` | skill | library | — |
| `.claude/skills/tlc-spec-driven` | skill | library | — |
| `.claude/skills/to-questionnaire` | skill | abandon | BROKEN symlink → ../../.agents/skills/to-questionnaire (relative .agents; content may live under ~/.agents/skills/to-questionnaire) |
| `.claude/skills/to-spec` | skill | abandon | BROKEN symlink → ../../.agents/skills/to-spec (relative .agents; content may live under ~/.agents/skills/to-spec) |
| `.claude/skills/to-tickets` | skill | abandon | BROKEN symlink → ../../.agents/skills/to-tickets (relative .agents; content may live under ~/.agents/skills/to-tickets) |
| `.claude/skills/transcript-reviewer` | skill | library | SKILL.md only |
| `.claude/skills/triage` | skill | abandon | BROKEN symlink → ../../.agents/skills/triage (relative .agents; content may live under ~/.agents/skills/triage) |
| `.claude/skills/ubiquitous-language` | skill | library | SKILL.md only |
| `.claude/skills/ux-audit` | skill | library | — |
| `.claude/skills/ux-audit-workspace` | skill | abandon | matches **/*-workspace/ eval/artifact pattern; no SKILL.md; top: iteration-1, iteration-2 |
| `.claude/skills/vercel-deploy` | skill | library | — |
| `.claude/skills/verify-git-commit` | skill | library | SKILL.md only |
| `.claude/skills/wait-what` | skill | abandon | BROKEN symlink → ../../.agents/skills/wait-what (relative .agents; content may live under ~/.agents/skills/wait-what) |
| `.claude/skills/wayfinder` | skill | abandon | BROKEN symlink → ../../.agents/skills/wayfinder (relative .agents; content may live under ~/.agents/skills/wayfinder) |
| `.claude/skills/web-accessibility` | skill | library | — |
| `.claude/skills/web-best-practices` | skill | library | SKILL.md only |
| `.claude/skills/web-design-guidelines` | skill | library | — |
| `.claude/skills/web-quality-audit` | skill | library | — |
| `.claude/skills/wizard` | skill | abandon | BROKEN symlink → ../../.agents/skills/wizard (relative .agents; content may live under ~/.agents/skills/wizard) |
| `.claude/skills/worktree-awareness` | skill | library | SKILL.md only |
| `.claude/skills/worktree-snapshot` | skill | gitignore-private | listed in .gitignore Parable-specific skills; EMPTY directory (no files) |
| `.claude/skills/writing-beats` | skill | abandon | BROKEN symlink → ../../.agents/skills/writing-beats (relative .agents; content may live under ~/.agents/skills/writing-beats) |
| `.claude/skills/writing-for-agents` | skill | abandon | BROKEN symlink → ../../.agents/skills/writing-for-agents (relative .agents; content may live under ~/.agents/skills/writing-for-agents) |
| `.claude/skills/writing-fragments` | skill | abandon | BROKEN symlink → ../../.agents/skills/writing-fragments (relative .agents; content may live under ~/.agents/skills/writing-fragments) |
| `.claude/skills/writing-shape` | skill | abandon | BROKEN symlink → ../../.agents/skills/writing-shape (relative .agents; content may live under ~/.agents/skills/writing-shape) |

## Commands (`.claude/commands/`)

| path | kind | disposition | notes |
|------|------|-------------|-------|
| `.claude/commands/add-experiment-note.md` | command | gitignore-private | listed in .gitignore Parable-specific commands |
| `.claude/commands/autoresearch.md` | command | library | — |
| `.claude/commands/daily-plan.md` | command | library | — |
| `.claude/commands/deep-plan.md` | command | library | — |
| `.claude/commands/deslop.md` | command | library | duplicate of .cursor/commands/ |
| `.claude/commands/do.md` | command | library | — |
| `.claude/commands/flesh-out-ticket.md` | command | library | duplicate of .cursor/commands/ |
| `.claude/commands/generate-review-doc.md` | command | library | duplicate of .cursor/commands/ |
| `.claude/commands/grill-me.md` | command | library | duplicate of .cursor/commands/ |
| `.claude/commands/implement-and-review-loop.md` | command | gitignore-private | listed in .gitignore Parable-specific commands; duplicate of .cursor/commands/ |
| `.claude/commands/improve-skill.md` | command | library | — |
| `.claude/commands/incorporate-feedback.md` | command | library | duplicate of .cursor/commands/ |
| `.claude/commands/personal-voice-mcp-daily.md` | command | library | duplicate of .cursor/commands/ |
| `.claude/commands/pr-review.md` | command | library | duplicate of .cursor/commands/ |
| `.claude/commands/prepare-pr.md` | command | library | duplicate of .cursor/commands/ |
| `.claude/commands/restore.md` | command | library | duplicate of .cursor/commands/ |
| `.claude/commands/review-fix-loop.md` | command | library | — |
| `.claude/commands/scripts` | command | library | directory (1 files); helper scripts for commands |
| `.claude/commands/ship.md` | command | library | — |
| `.claude/commands/snapshot.md` | command | library | duplicate of .cursor/commands/ |
| `.claude/commands/update-ticket.md` | command | library | duplicate of .cursor/commands/ |

## Agents (`.claude/agents/`)

| path | kind | disposition | notes |
|------|------|-------------|-------|
| `.claude/agents/accessibility-tester.md` | agent | library | — |
| `.claude/agents/ad-security-reviewer.md` | agent | library | — |
| `.claude/agents/agent-installer.md` | agent | library | — |
| `.claude/agents/agent-organizer.md` | agent | library | — |
| `.claude/agents/ai-engineer.md` | agent | library | — |
| `.claude/agents/api-designer.md` | agent | library | — |
| `.claude/agents/api-documenter.md` | agent | library | — |
| `.claude/agents/architect-reviewer.md` | agent | library | — |
| `.claude/agents/backend-developer.md` | agent | library | — |
| `.claude/agents/build-engineer.md` | agent | library | — |
| `.claude/agents/business-analyst.md` | agent | library | — |
| `.claude/agents/chaos-engineer.md` | agent | library | — |
| `.claude/agents/cli-developer.md` | agent | library | — |
| `.claude/agents/cloud-architect.md` | agent | library | — |
| `.claude/agents/code-reviewer.md` | agent | library | — |
| `.claude/agents/codebase-to-course-references` | agent | library | reference bundle dir (10 files); companion to codebase-to-course.md |
| `.claude/agents/codebase-to-course.md` | agent | library | — |
| `.claude/agents/compliance-auditor.md` | agent | library | — |
| `.claude/agents/connector-specialist.md` | agent | gitignore-private | listed in .gitignore Parable-specific agents |
| `.claude/agents/context-manager.md` | agent | library | — |
| `.claude/agents/customer-success-manager.md` | agent | library | — |
| `.claude/agents/data-analyst.md` | agent | library | — |
| `.claude/agents/data-engineer.md` | agent | library | — |
| `.claude/agents/data-researcher.md` | agent | library | — |
| `.claude/agents/data-scientist.md` | agent | library | — |
| `.claude/agents/database-administrator.md` | agent | library | — |
| `.claude/agents/database-optimizer.md` | agent | library | — |
| `.claude/agents/debugger.md` | agent | library | — |
| `.claude/agents/dependency-manager.md` | agent | library | — |
| `.claude/agents/deployment-engineer.md` | agent | library | — |
| `.claude/agents/devops-engineer.md` | agent | library | — |
| `.claude/agents/devops-incident-responder.md` | agent | library | — |
| `.claude/agents/docker-expert.md` | agent | library | — |
| `.claude/agents/documentation-engineer.md` | agent | library | — |
| `.claude/agents/dx-optimizer.md` | agent | library | — |
| `.claude/agents/e2e-debugger.md` | agent | gitignore-private | listed in .gitignore Parable-specific agents |
| `.claude/agents/error-coordinator.md` | agent | library | — |
| `.claude/agents/error-detective.md` | agent | library | — |
| `.claude/agents/frontend-developer.md` | agent | library | — |
| `.claude/agents/fullstack-developer.md` | agent | library | — |
| `.claude/agents/game-developer.md` | agent | library | — |
| `.claude/agents/git-workflow-manager.md` | agent | library | — |
| `.claude/agents/golang-pro.md` | agent | library | — |
| `.claude/agents/graphql-architect.md` | agent | library | — |
| `.claude/agents/incident-responder.md` | agent | library | — |
| `.claude/agents/it-ops-orchestrator.md` | agent | library | — |
| `.claude/agents/javascript-pro.md` | agent | library | — |
| `.claude/agents/knowledge-synthesizer.md` | agent | library | — |
| `.claude/agents/kubernetes-specialist.md` | agent | library | — |
| `.claude/agents/llm-architect.md` | agent | library | — |
| `.claude/agents/machine-learning-engineer.md` | agent | library | — |
| `.claude/agents/mcp-developer.md` | agent | library | — |
| `.claude/agents/memory-archeologist.md` | agent | library | — |
| `.claude/agents/microservices-architect.md` | agent | library | — |
| `.claude/agents/migration-reviewer.md` | agent | gitignore-private | listed in .gitignore Parable-specific agents |
| `.claude/agents/ml-engineer.md` | agent | library | — |
| `.claude/agents/mlops-engineer.md` | agent | library | — |
| `.claude/agents/multi-agent-coordinator.md` | agent | library | — |
| `.claude/agents/network-engineer.md` | agent | library | — |
| `.claude/agents/nextjs-developer.md` | agent | library | — |
| `.claude/agents/payment-integration.md` | agent | library | — |
| `.claude/agents/penetration-tester.md` | agent | library | — |
| `.claude/agents/performance-engineer.md` | agent | library | — |
| `.claude/agents/performance-monitor.md` | agent | library | — |
| `.claude/agents/platform-engineer.md` | agent | library | — |
| `.claude/agents/postgres-pro.md` | agent | library | — |
| `.claude/agents/pr-review-orchestrator.md` | agent | library | — |
| `.claude/agents/product-manager.md` | agent | library | — |
| `.claude/agents/project-manager.md` | agent | library | — |
| `.claude/agents/prompt-engineer.md` | agent | library | — |
| `.claude/agents/psgen-reviewer.md` | agent | gitignore-private | listed in .gitignore Parable-specific agents |
| `.claude/agents/python-pro.md` | agent | library | — |
| `.claude/agents/qa-expert.md` | agent | library | — |
| `.claude/agents/refactoring-specialist.md` | agent | library | — |
| `.claude/agents/release-coordinator.md` | agent | gitignore-private | listed in .gitignore Parable-specific agents |
| `.claude/agents/research-analyst.md` | agent | library | — |
| `.claude/agents/risk-manager.md` | agent | library | — |
| `.claude/agents/rust-engineer.md` | agent | library | — |
| `.claude/agents/scrum-master.md` | agent | library | — |
| `.claude/agents/search-specialist.md` | agent | library | — |
| `.claude/agents/security-auditor.md` | agent | library | — |
| `.claude/agents/security-engineer.md` | agent | library | — |
| `.claude/agents/seo-specialist.md` | agent | library | — |
| `.claude/agents/slack-expert.md` | agent | library | — |
| `.claude/agents/spectacles-validator.md` | agent | gitignore-private | listed in .gitignore Parable-specific agents |
| `.claude/agents/sql-pro.md` | agent | library | — |
| `.claude/agents/sre-engineer.md` | agent | library | — |
| `.claude/agents/task-distributor.md` | agent | library | — |
| `.claude/agents/technical-writer.md` | agent | library | — |
| `.claude/agents/test-automator.md` | agent | library | — |
| `.claude/agents/tooling-engineer.md` | agent | library | — |
| `.claude/agents/trend-analyst.md` | agent | library | — |
| `.claude/agents/tts-debugger.md` | agent | gitignore-private | listed in .gitignore Parable-specific agents |
| `.claude/agents/typescript-pro.md` | agent | library | — |
| `.claude/agents/ui-designer.md` | agent | library | — |
| `.claude/agents/ux-researcher.md` | agent | library | — |
| `.claude/agents/workflow-orchestrator.md` | agent | library | — |

## Disposition legend

| Disposition | Meaning for migrate |
|-------------|---------------------|
| `library` | Candidate to move into repo-root `library/{skills,commands,agents}/` |
| `gitignore-private` | Parable/private; keep gitignored; fan-out via local/`~/dotfiles-local/library/` if needed |
| `abandon` | Do not migrate (eval workspaces, zips, empty dirs, broken symlinks, accidental stubs) |

## Counts by disposition (skills only, excluding abandon broken-symlink note)

- Skills library (incl. `_shared`, `nx-workspace`): 79
- Skills gitignore-private: 9
- Skills abandon: 45 (of which broken symlinks: 35)

