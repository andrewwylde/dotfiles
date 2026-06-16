# Textream export — detailed rules

Read this file when generating a `.textream` sidecar and the scene has anything non-obvious: mostly-action scenes, load-bearing branches, multiple competing delivery cues, or `[GAP: …]` placeholders in the source `.md`.

## What textream is

[Textream](https://github.com/f/textream) is a macOS teleprompter that reads `.textream` files — a JSON array of strings. Each string is a "page" of text the presenter reads aloud while the app highlights words in real time using on-device speech recognition. Inline bracketed cues (`[pause]`, `[beat]`, `[smile]`) are visible to the presenter but not read. Designed for on-camera delivery: streams, recorded demos, podcast intros, any situation where the presenter needs to look at the camera while reading.

Format shape (minimalist — no formal schema published):

```json
["first block of spoken text. [pause] more text.", "second block..."]
```

That's the whole format. Valid JSON, UTF-8, array of strings.

## Translation rules in full

### One JSON element per SCENE

Each `SCENE N` block in the `.md` becomes one string in the array. Textream auto-advances between elements on voice match, giving the presenter a natural scene break. Do not merge scenes; do not split a scene across multiple elements.

### Talk track is the backbone

The spoken content is the scene's **Talk track**. If the talk track has multiple paragraphs, join them with `\n\n` (literal `\n` characters inside the JSON string — which `json.dumps` will encode correctly).

### Actions merge inline as uppercase bracketed cues

Convert the **Action** section's described movements into inline `[UPPERCASE]` bracket cues, placed at the moment the action should fire in the spoken flow. Examples of action verbs (lean into these — they read well in peripheral vision):

- `[CLICK …]`, `[CLICK on …]`
- `[SWITCH to …]`, `[FLIP to tenant tab]`
- `[OPEN …]`, `[RELOAD]`
- `[POINT AT …]`, `[HOVER over …]`
- `[SHOW …]`, `[HOLD on …]`
- `[TYPE "…"]`, `[SELECT …]`, `[SAVE]`
- `[LOG OUT]`, `[LOG IN]`

**Grouping.** When multiple actions happen in one continuous motion ("reload, then click the Lab item"), use commas inside one bracket group: `[RELOAD tenant tab, CLICK Lab in sidebar]`. When the presenter should mentally pause between actions, split into multiple bracket groups separated by text or a `[beat]`.

**Placement.** Put the cue where the hand-eye action should start — usually right before the sentence it enables. Don't sprinkle actions mid-clause; they fragment the read. A sentence that's all narration can have the action bracket prepended; a sentence with a natural pivot point (after a dash, at a paragraph boundary) is the right place for mid-sentence actions.

### Normalize delivery cues to lowercase

The existing `.md` might emit `[PAUSE]`, `[BEAT]`, `[SLOWER]` — normalize to textream's observed vocabulary: lowercase and minimal. Specifically:

| `.md` might contain | `.textream` should use |
|---|---|
| `[PAUSE]`, `[PAUSE for reaction]`, `[PAUSE after clicking rocket_launch]` | `[pause]` |
| `[beat]`, `[BEAT]` | `[beat]` |
| `[slower]`, `[SLOWER]`, `[slower here]` | `[slower]` |
| `[emphasize]`, `[louder]` | `[emphasize]` |

The rule of thumb: delivery cues are lowercase, short, and vocabulary-limited. Actions are uppercase and descriptive. That visual split helps the presenter parse them at a glance on the teleprompter.

### Drop entirely

These sections of the `.md` don't make it into `.textream` at all — they exist for rehearsal, not performance:

- Header block (`**Runtime target:**`, `**Audience:**`, `**Source:**`, `**Drafted:**`)
- `## Pre-demo checklist`
- Scene titles (`## SCENE 1 — The two-click problem [00:00–00:45]`) — the JSON array position conveys the sequence; the title is for humans navigating the `.md`
- Scene timestamps (the `[00:00–00:45]` bracket in scene titles)
- `**Action**` header and `**Talk track**` header labels — the talk-track content becomes the string, the action content gets merged in as cues
- `**Branch — …**` subsections in any scene
- `## Contingencies`
- `## Anticipated Q&A`
- `## Practice marks`
- `## Notes for the presenter`
- Any leading "Gaps flagged" section from a thin-input draft (handled separately — see GAP refusal below)

### Refuse if `[GAP: …]` placeholders are present

Scan the `.md` for `[GAP:` literally. If any remain, do not emit the `.textream` file. Respond to the user with:

> The `.md` still has these unfilled gaps, which would read aloud as actual words on a teleprompter. Fill them first, then I'll export:
>
> - `[GAP: …first gap…]`
> - `[GAP: …second gap…]`
>
> …once the script is gap-free, run the export again.

List every gap (not just the first one) so the user can fill them in one pass.

### Flag load-bearing branches

If a scene has an audience-adaptation branch that the presenter will likely hit live (`**Branch — if C-suite dominates**`, `**Branch — if technical questions dominate**`), the `.textream` version is necessarily the happy-path only. After saving, tell the user:

> Saved `.textream` to `<path>`. Note: Scenes N, M have branches (e.g. "if C-suite dominates, skip X") that aren't in the teleprompter version — the `.md` is still the source of truth for live branching. If you hit a branch during delivery, look away from the teleprompter for that beat.

Only include scenes that actually had branches; don't warn generically.

### Scenes that are mostly action

Some scenes are more visual than verbal — e.g., a silent reveal or a side-by-side comparison with minimal narration. Write the talk track anyway even if thin: the textream element can be short. If a scene is literally zero talk track (just an action beat), emit an element that's only the action cues with no prose, e.g. `"[SHOW sidebar with icon + pill]"` — the presenter knows to stay silent. Don't omit the scene.

### What about ampersands, quotes, special characters?

Valid JSON encoding handles these. Use `json.dumps(array, ensure_ascii=False, indent=2)` when writing the file — it produces readable output, preserves UTF-8 characters, and escapes quotes/backslashes correctly. The output is valid textream regardless of indentation; indentation just helps the user read the file.

## Worked example — UI-245

Source `.md`: `~/.agent/demo-scripts/ui-245-simplify-nav-2026-04-17.md`

Transformed `.textream`:

```json
[
  "[OPEN tenant tab, CLICK Early Access in sidebar] This is what our early-access customers do every session to reach the one thing they actually pay us for — they click \"Early Access,\" [CLICK the Early Access Lab card] then they click the same Lab again inside the page, and only then are they in the product. Two clicks, redundant naming, and a whole intermediate page they learn to ignore. [pause] One lab. Two clicks.",

  "[RELOAD tenant tab, CLICK Lab directly in sidebar] One click, straight in. [beat] [SWITCH to admin tab, OPEN /admin/features, EDIT the release, OPEN icon picker, TYPE \"rocket\"] And because the nav is reading from the same catalog admins already manage, the moment I pick an icon in the admin form — any Material icon, searchable — [CLICK rocket_launch, SAVE, SWITCH back to tenant tab, RELOAD] it shows up on the tenant's sidebar the next time they load the page. [pause] That's an optional field that took one column in the database and it's now the per-tenant branding for every Lab we ship.",

  "[SHOW both tabs side-by-side, CHANGE icon to insights in admin] The thing I want you to notice isn't the icon. [FLIP to tenant tab, RELOAD] It's that this whole panel — the icon, the \"Lab\" versus \"Preview\" pill, the order, whether it opens in-app or in a new tab — is one row in the releases table. [slower] When we ship a second Lab, that's one admin form. No code. [pause] And when we have too many to fit cleanly — we put the cap at four — the sidebar gracefully falls back to the Early Access page we used to have. Nothing gets lost; the old UX is the fallback.",

  "[SHOW sidebar alphabetized with icon + pill] Two clicks to one. An admin form that makes new labs self-service for the squad shipping them — no UI PR for each new lab. [LOG OUT, LOG BACK IN] And the landing page now takes an early-access user straight into their product, because every login that doesn't matter is a friction tax on the customer we charge the most. [pause]\n\nWe preserved the Early Access page — it's still there, still deep-linkable, and it's what the sidebar falls back to the moment we have more than four labs in-flight. We didn't burn the old UX; we demoted it behind a threshold. [beat] Next: Time Spend ships, the squad creates the release in admin, picks an icon, flips the flag — and it lights up in every enabled tenant's sidebar the next render. No deploy. That's the CTA: if your squad is about to ship an EA product, you now have one form to fill out."
]
```

Notes on this conversion:

- Scene titles and timestamps are gone — the array position (`[0]` through `[3]`) conveys the sequence.
- Header metadata, pre-demo checklist, contingencies, Q&A, practice marks, presenter notes are all dropped. Compare against the original `.md` to see what's missing on purpose.
- `[PAUSE]` from the source was normalized to `[pause]`. `[PAUSE after clicking rocket_launch]` became just `[pause]` — the action context ("after clicking") is already conveyed by the preceding action cue on the same line.
- Branches in scenes 1–4 were dropped. When saving this file, the user should be told: "Scenes 2, 3, and 4 have branches for technical/C-suite pivots — the `.md` is still the source of truth for live branching."
- Scene 2's dense admin-side actions are grouped into one bracket: `[SWITCH to admin tab, OPEN /admin/features, EDIT the release, OPEN icon picker, TYPE "rocket"]`. These are a continuous motion; the presenter doesn't pause between them. Separating them into four brackets would create four visual beats on the teleprompter — wrong.
- Scene 4's talk track has two paragraphs in the `.md`, joined with `\n\n` in the JSON string. Textream renders the newline; the presenter gets a natural paragraph pause mid-element.

## Templates for chat messages

**After successful export (no complications):**

> Saved `.textream` to `~/.agent/demo-scripts/<slug>-<date>.textream`. Four scenes, valid JSON, ready to open in the Textream app. The `.md` stays the source of truth — if you revise the script, regenerate both.

**After export with dropped branches:**

> Saved `.textream` to `~/.agent/demo-scripts/<slug>-<date>.textream`. Heads-up: Scenes 2 and 3 have audience branches (technical-dominant / exec-dominant pivots) that aren't in the teleprompter version — it's the happy-path only. If you hit a branch live, look away from the teleprompter for that beat; the `.md` has the full branch text if you want to rehearse against it.

**Refusing export due to GAPs:**

> The source `.md` has unfilled gaps that would read aloud as actual words on a teleprompter. Fill these first, then I'll export:
>
> - Scene 1: `[GAP: insert the number — e.g., "$X in ARR is currently gated on this single question"]`
> - Pre-demo checklist: `[GAP: path to pre-recorded SSO login clip]`
> - Scene 4: `[GAP: confirm this is the aha]`
> - …
>
> Drop in the missing values and run the export again.
