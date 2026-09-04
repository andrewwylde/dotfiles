# Career growth toolkits

Skills, agents, and workflows for self-review and manager review of direct reports at Parable.

**Entry points:** [SKILL.md](SKILL.md) (index) | [career-growth-orchestrator](career-growth-orchestrator/SKILL.md) (full cycle)

## Organizational resources

Configure with your team's canonical matrices and review guidelines (via Notion URL, local path, or export):
- `Engineering Competency Matrix` (e.g., Notion page or company matrix URL)
- `Values Competency Matrix` (e.g., Notion page or company values framework URL)
- `EOY + mid-year reviews` (e.g., review cycle guidelines URL)

### Suggested artifacts

**Self-review:** promotion leveling worksheet, accomplishments doc

**Manager review:** promotion leveling worksheet

## External resources

- [Week 14: Using AI to draft performance reviews](https://claudecodefornoncoders.substack.com/p/week-14-using-claude-to-draft-performance)
- Meridian example prompt (reference only): [references/meridian-system-prompt.md](references/meridian-system-prompt.md)

---

## Skill map

| Skill | Purpose | Mode(s) | Key inputs | Key outputs | Depends on | Order |
|-------|---------|---------|------------|-------------|------------|-------|
| [career-growth-org-process](career-growth-org-process/SKILL.md) | Review calendar, sections, deadlines | Both | cycle, Notion | `org_process_brief` | -- | 1 |
| [career-growth-evidence](career-growth-evidence/SKILL.md) | GitHub, Linear, Slack evidence | Both | period, user IDs | `evidence_ledger` | -- | 2 |
| [career-growth-accomplishments](career-growth-accomplishments/SKILL.md) | Brag doc / journal | Self (primary) | ledger, notes | accomplishments markdown | evidence | 3 (opt) |
| [career-growth-competency](career-growth-competency/SKILL.md) | Matrix mapping, gaps | Both | matrices, ledger | `competency_mapping` | evidence | 4 |
| [career-growth-self-review](career-growth-self-review/SKILL.md) | Self-assessment draft | Self | input package | self-review draft | org, competency, evidence | 5a |
| [career-growth-manager-review](career-growth-manager-review/SKILL.md) | Direct-report review draft | Manager | 360 package | review draft | org, competency, evidence | 5b |
| [career-growth-development-plan](career-growth-development-plan/SKILL.md) | CDP / growth plan | Both | gaps, goals | CDP markdown | competency or review | 6 |
| [career-growth-promotion-packet](career-growth-promotion-packet/SKILL.md) | Promotion case evidence | Both | target level, ledger | promotion packet | competency, evidence | 7 (opt) |
| [career-growth-orchestrator](career-growth-orchestrator/SKILL.md) | Chain skills for EOY/mid-year | Both | mode selection | guided run | all above | entry |

Shared schemas: [references/evidence-ledger-schema.md](references/evidence-ledger-schema.md), [references/input-package-schema.md](references/input-package-schema.md).

---

## Workflows

### Self-review chain

```text
org-process -> evidence -> accomplishments (optional) -> competency -> self-review -> development-plan (optional) -> promotion-packet (optional)
```

1. **org-process** -- deadlines and required sections
2. **evidence** -- ledger from GitHub, Linear, Slack
3. **accomplishments** (optional) -- brag doc
4. **competency** -- map to Engineering + Values matrices
5. **self-review** -- draft first-person assessment
6. **development-plan** (optional) -- next-cycle CDP
7. **promotion-packet** (optional) -- if leveling up

Human gates: confirm ledger accuracy, edit draft before submit, no AI ratings.

### Manager review chain

```text
org-process -> evidence -> competency -> manager-review -> development-plan (optional) -> promotion-packet (optional)
```

1. **org-process** -- manager requirements and calibration notes from Notion
2. **evidence** -- direct report activity (with their identifiers)
3. **competency** -- gap analysis for calibration prep
4. **manager-review** -- synthesize 360 + observations
5. **development-plan** (optional)
6. **promotion-packet** (optional)

Human gates: manager observations required, [manager checklist](references/manager-checklist.md), calibration owns ratings.

---

## Skill directories

```text
skills/career-growth/
├── SKILL.md                          # index
├── README.md                         # this file
├── references/                       # shared schemas and Meridian example
├── career-growth-orchestrator/
├── career-growth-org-process/
├── career-growth-evidence/
├── career-growth-competency/
├── career-growth-accomplishments/
├── career-growth-self-review/
├── career-growth-manager-review/
├── career-growth-development-plan/
└── career-growth-promotion-packet/
```

---

## Meridian vs Parable

The original monolithic v1.0 prompt described **Meridian Consulting** (Professional, Problem Solver, Leader, Coach). Parable uses **Engineering** and **Values** matrices from Notion. Meridian content lives under `references/` as a structural example only.
