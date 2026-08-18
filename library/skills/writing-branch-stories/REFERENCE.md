# Branch Story Workflow Reference

Read this file when executing `writing-branch-stories`.

## Resolve the range

1. Detect repository and worktree rules.
2. Natural-language `main` means `origin/main`. Only an explicit SHA, full ref,
   or request for local `main` overrides this default. Refresh it with:

   ```bash
   git fetch origin main:refs/remotes/origin/main
   ```

3. Verify the fetched SHA with `git rev-parse origin/main`. If fetching fails
   but the ref exists, disclose its commit date and continue with that
   limitation. If it does not exist, ask for an exact base and stop.
4. Pin base, merge-base, and HEAD SHAs before dispatching agents.
5. If staged, unstaged, or untracked changes exist, ask whether to include
   them. "Session changes" means only Git working-tree state. If excluded,
   agents inspect pinned Git objects and patches rather than potentially dirty
   working files.

Never run tests or builds. Source, test, schema, and configuration files are
evidence only; report them as not runtime-verified.

## Inventory

Create a temporary directory and run:

```bash
python3 scripts/inventory_branch.py \
  --repo <repository> \
  --base <base-ref> \
  --head HEAD \
  --output <temporary-directory>/inventory.json
```

When the user includes working-tree changes, add `--include-working-tree`.
Before final validation, rerun the same inventory command and require the
`snapshot_sha256` values to match. A changed snapshot invalidates the draft.

The inventory contains immutable SHAs, all reachable branch commits, each
commit's parent-relative changes, final file changes, text hunks, modes,
binary/LFS/submodule flags, and working-tree entries.

Use file IDs as coverage units by default. Set `split_into_hunks` only when one
file contains changes belonging to different stories or scope dispositions.
Generated files map to their source definition. Identify them from
`.gitattributes`, generated-file markers, generator configuration, and source
relationships. Missing sources or unverified regeneration consistency become
readiness findings; uncertainty is never silently classified as generated.

## Scope

### Scope sanity gate

Before inventory or swarm, compare **committed branch**, **session delta**
(working tree), and **named-feature/theme** scopes. If any two materially
differ (file count, mixed themes, large unrelated cleanup), present all three
and require an explicit user choice. Do not invent business stories for
ambiguous unrelated survivors — propose them as exclusions until confirmed.

- Without a user-supplied theme, and after the sanity gate, include all
  committed branch work.
- For a scoped request, decide from behavior and evidence, never paths or
  commit subjects alone.
- Retrieve referenced Linear issues, GitHub PRs, and design documents when
  available. They support intent but do not replace branch evidence.
- Only base, inclusion scope, or story-boundary ambiguity blocks drafting.
  Other uncertainty becomes `Needs decision`.
- Excluded work appears in the final report, not in separate stories.
- If a scoped theme has no surviving changes but has reverted or superseded
  commit evidence, create one clearly labeled context story. If no historical
  evidence exists, create no file.
- If the entire branch has no storyable changes, create no files.

## Swarm

Use at least two analysis agents and one independent auditor.

- Tiny branch: combine history/change analysis in one agent and
  product/readiness/plain-language review in another.
- Medium branch: separate historian, change scouts, product analyst,
  readiness skeptic, and technical writer.
- Large branch: partition commits and final files further while preserving
  collectively exhaustive coverage.

Initial analysis runs in parallel. The auditor runs after drafting and rebuilds
the inventory independently. On agent failure, retry once, then reassign the
partition. If coverage still cannot be proven, write no final files.

Each agent returns JSON:

```json
{
  "schema_version": 1,
  "role": "change-scout",
  "partition": {
    "commit_ids": ["commit:<sha>"],
    "file_ids": ["file:<id>"]
  },
  "findings": [
    {
      "change_ids": ["file:<id>", "hunk:<id>"],
      "commit_ids": ["commit:<sha>"],
      "paths": ["path/to/file"],
      "observed_behavior": "Plain factual description",
      "scope_disposition": "included",
      "candidate_story": "candidate-name",
      "evidence": ["Source and test express the same behavior"],
      "readiness_gaps": [
        {
          "severity": "Required follow-up",
          "detail": "Add missing failure handling"
        }
      ],
      "confidence": "high"
    }
  ]
}
```

Allowed scope dispositions are `included`, `excluded`, `reverted`,
`superseded`, and `ambiguous`. Confidence is `low`, `medium`, or `high`.

## Group stories

Start with one candidate. Split only for different user/business problems,
acceptance boundaries, or rollout decisions. Never split merely by commit,
directory, language, or subsystem. Challenge the result pairwise and with an
independent alternative grouping.

Requirements use:

- `Confirmed:` only for explicit user direction or an authoritative linked
  requirement.
- `Inferred:` for behavior suggested by code, tests, or commit history.
- `Needs decision:` for unresolved product choices.

Use `assets/story-template.md`. Keep Problem and Requirements free of
repository jargon and unexplained acronyms. A technical writer reviews
medium/large branches; the product analyst performs this review for tiny ones.

Recommended implementation may include only work needed to make the captured
outcome safe, correct, operable, and supportable. Do not expand into unrelated
enhancements or an idealized redesign.

Readiness findings use `Release blocker`, `Required follow-up`,
`Present in branch, not runtime-verified`, or `Not applicable`.

## Coverage manifest

Create this temporary JSON after grouping:

```json
{
  "schema_version": 1,
  "base_sha": "<sha>",
  "head_sha": "<sha>",
  "inventory_snapshot_sha256": "<inventory snapshot_sha256>",
  "allow_extra_sections": false,
  "stories": [
    {
      "id": "story-1",
      "file": "01-story-title.md",
      "kind": "implementation"
    }
  ],
  "commits": {
    "commit:<sha>": {
      "disposition": "included",
      "story_ids": ["story-1"]
    }
  },
  "files": {
    "file:<id>": {
      "disposition": "included",
      "story_id": "story-1",
      "split_into_hunks": false
    }
  },
  "hunks": {}
}
```

Excluded, reverted, and superseded entries require a concise `reason`.
Split files omit `story_id`; every hunk in that file gets its own disposition
and included hunks get one primary `story_id`.

Context stories use `kind: "context"` and a non-empty
`evidence_commit_ids` array containing only reverted or superseded commits.
Their Current branch implementation bullet must state that no surviving
implementation remains.

Validate before writing the final directory:

```bash
python3 scripts/validate_coverage.py \
  --inventory <temporary-directory>/inventory.json \
  --coverage <temporary-directory>/coverage.json \
  --stories-dir <temporary-draft-directory> \
  --handoff <temporary-directory>/agent-result.json
```

Pass every handoff with another `--handoff`. Validation must return zero.

## Output and reruns

Write validated stories to:

```text
~/.agent/stories/<repo>/<branch-slug>/<short-head>/NN-<story-slug>.md
```

Use a 12-character HEAD SHA. Sanitize repository, branch, and story slugs by
lowercasing ASCII, replacing each run of non-alphanumeric characters with one
hyphen, trimming hyphens, and limiting each segment to 80 characters. Use
`detached` when no branch name exists. Draft outside the final directory. If
the same HEAD directory exists, compare the new validated story set
byte-for-byte. Reuse equivalent output; otherwise write a sibling suffixed
with UTC `YYYYMMDDHHMMSS`. Never overwrite or delete an earlier run.

Delete temporary manifests after completion unless the user requested audit
artifacts.

The final response reports:

- Output path
- Base, merge-base, and HEAD SHAs
- Commit, change-unit, and story counts
- Excluded change and commit counts with concise reasons
- Reverted and superseded counts
- Unresolved items
- Fetch or other evidence limitations
