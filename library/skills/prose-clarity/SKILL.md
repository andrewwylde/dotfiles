# Prose clarity (technical writer)

Canonical prose rules for skills that produce user-facing or onboarding content.
`docs-writer` owns the full style guide; this file is the **portable subset** other
skills import by reference.

**Read this file** when your skill outputs paragraphs, card bodies, PR descriptions,
release notes, runbook steps, Mintlify pages, or HTML learning guides.

## Audience modes

Pick one mode per deliverable. Do not mix telegraphic EDR style with onboarding style.

| Mode | Use for | Sentence style |
|------|---------|----------------|
| **Onboarding** | Learning guides, visual explainers, recap pages, "catch me up" docs | Full sentences. Explain jargon on first use. 2-4 sentences per card section minimum. |
| **Operational** | Runbooks, triage reports, debug summaries | Imperative steps, but each step is a complete instruction. No orphan bullet fragments. |
| **Decision record** | EDRs, RFCs, ADRs | Can be denser, but defined terms still need one-line glosses on first use. |
| **Review artifact** | PR descriptions, release notes | Lead with why. Split product vs engineering voice when audiences differ. |

## Onboarding rules (learning guides, visual explainers)

These rules exist because compressing EDR language into card bodies produces copy
like *"Parable owns the canonical concretization. Plotter aligns when its tables land."*
That is accurate but unusable for someone catching up.

1. **Full sentences in card bodies and callouts.** Not bullet telegraphy.
2. **Explain jargon on first use** in the same section: `@source`, sparse overlay,
   read-through, byte-identical, rootKind, tombstone, schemaEpoch, etc.
3. **Inline explanation cards** for mechanisms readers will ask about (mirror-ban,
   propagation window, floating overlay). Do not defer to chat.
4. **`.prose` intros** before dense tables or layer stacks when the table alone
   would not teach the concept.
5. **Self-check before delivery:**
   - Read each card body aloud. Would a new engineer understand without the source doc open?
   - Search for fragments, undeclared acronyms, and "X aligns when Y lands" phrasing; expand hits.
   - If the user already asked to explain a term from the page, that explanation must be in the deliverable.

## Operational rules (runbooks, debug reports)

1. Start steps with imperative verbs; one action per step.
2. Put preconditions before actions ("If alert X fires..." then "Run...").
3. Name the environment explicitly (dev, staging, prod). Never assume context.
4. Link to related runbooks/EDRs with descriptive anchor text.

## Review artifact rules (PRs, release notes)

1. **Why before what** in the summary. Reviewers need motivation.
2. **Complete sentences** in PR bodies; no commit-message paste without context.
3. **Release notes:** product-facing bullets avoid internal codenames unless explained;
   engineering sections can use identifiers but still need one-line impact statements.
4. Avoid: "Various fixes", "Misc updates", "Refactor" without stating user-visible effect.

## Shared voice (from docs-writer style guide)

- Active voice, second person where appropriate ("you"), present tense for behavior.
- US English. No slang. Define technical terms; do not ban precise jargon after defining it.
- Short paragraphs beat walls of bullets, but bullets are fine when items are parallel and each is a full phrase.

## When to run a full docs-writer pass

Invoke `docs-writer` (or apply these rules manually) when:

- The deliverable is **8+ sections** or **>1500 words** of new prose.
- The user said **cryptic**, **unclear**, **too terse**, or **explain more**.
- The source is an **EDR/RFC** being turned into onboarding material.
- The output is **customer-facing** Mintlify (`docs/customer/`).

Quick edits (<3 paragraphs) can follow this file alone without loading the full style guide.

## Skill integration map

Skills that MUST read this file before writing prose:

| Skill | Mode | When |
|-------|------|------|
| `visual-explainer` | Onboarding | Learning guides, project-recap, plan-review narrative |
| `visual-explainer:plan-review` | Onboarding | Plan summary, rationale panels, risk cards |
| `docs-writer` | All | Always (canonical owner) |
| `mintlify` | Onboarding / Operational | New or heavily rewritten MDX pages |
| `runbook` | Operational | Create/update runbook content |
| `deploy-release-notes` | Review artifact | Release note bullets |
| `create-pr` | Review artifact | PR summary and test plan |
| `edr-finalize` | Decision record | Final EDR body (glosses, not telegraphy) |
| `blogpost` | Onboarding | Pre-publish HTML clarity + meta description |
| `pm` | Onboarding / Review artifact | Plan files and Linear comments |
