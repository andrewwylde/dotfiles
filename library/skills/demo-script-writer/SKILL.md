---
name: demo-script-writer
description: "Turns a feature (from a Linear ticket, PRD, or plain description) into a timestamped, performable demo script for a solo presenter, with optional export to textream teleprompter format. Use whenever the user asks to \"write a demo script\", \"prep for a demo\", \"practice a demo\", \"script my demo\", \"write a talk track\", \"rehearse a demo\", or mentions an upcoming sprint review, customer demo, exec review, all-hands, or conference walkthrough. Also use when the user asks to \"textream this demo\", \"convert my demo to textream\", \"give me the teleprompter version\", \"export to textream\", or needs a `.textream` file for on-camera / streaming delivery. Produces a script with running [MM:SS] timestamps, scene structure, talk track, action beats, and branching contingencies — tuned for a dual-audience room (engineers + C-suite). Also use when the user needs to hit specific timing marks, needs a 5-minute or 10-minute version of a demo, or wants a rehearsal-ready script they can practice against a stopwatch."
---

# Demo Script Writer

You turn a feature — described in a Linear ticket, a PRD, or free text — into a **performable, timestamped demo script** that a solo presenter can rehearse against a stopwatch.

The audience for these demos is mixed: **internal technical folks and C-suite in the same room**. The script has to work for both without reading as two different scripts stapled together.

## When to use

Use this skill whenever the user is preparing to demo a feature and wants a script they can practice against — not just bullet-point speaker notes. Signals:

- "write a demo script for…"
- "I'm demoing X at sprint review / to the execs / for the customer call on Friday"
- "help me prep a 5-min demo"
- "practice the timing on…"
- "turn this PRD / ticket into a talk track"

Do not use for:
- Slide decks or presentation content (not the same craft)
- Written product announcements / blog posts (use docs-writer)
- Feature spec or PRD writing (use create-technical-design-doc or similar)

## The core idea

Treat the demo like a short film, not a feature tour. A feature tour lists what the feature does. A demo script has a **hook, a turn, and a payoff** — and puts the viewer inside the problem before showing the fix. A C-suite exec and a staff engineer both respond to story; they just pay attention to different details.

The output is structured: scene headings with time windows, what the presenter does (action), what the presenter says (talk track), and branch points for contingencies. Delivery cues are fine — `[PAUSE]`, `[beat]`, `>> CLICK next slide`, "hold for two seconds", "let the room sit with it" — use them where they actually help the presenter hit a moment. Don't sprinkle them for decoration; a cue earns its place by marking a beat that matters.

## Workflow

### 1. Resolve the input

The user provides the feature in one of three ways:

- **Linear ticket** — an ID like `SYSTEM-1354` or a URL. Use the Linear MCP (`mcp__linear__*`) to fetch the ticket, its description, comments, and linked PRs. If Linear isn't authenticated, say so and ask the user to paste the content.
- **PRD or doc** — a file path, a Notion link, or a Google Doc link. Read it. For Notion, use `mcp__notion__notion-fetch`. For Drive docs, say you need the content pasted or exported if you can't reach it.
- **Free text** — just use what the user wrote. If it's thin (one sentence), ask one or two targeted questions before drafting, not a laundry list.

Extract: **what the feature is, who it's for, what problem it solves, what the "aha" moment looks like when shown live, and any numbers you can quote** (latency, cost, reduction, users affected). Numbers matter — they anchor the business framing for the C-suite half of the room.

If you can't find a crisp problem statement or an "aha" moment, pause and ask the user: *"What's the single most visceral thing that changes for a user after this ships?"* That's the demo's center of gravity.

### 2. Pick the length

Ask the user — or honor what they already specified:

- **5-minute standard** — default. Tight. One scene per beat. No deep-dives.
- **10-minute extended** — room for one technical deep-dive and light Q&A prep.

If the user didn't say, default to 5 minutes and note that you defaulted.

### 3. Shape the arc

A demo script has four structural beats. The time budgets below are defaults — adjust if the feature genuinely doesn't fit.

**5-minute arc (total 5:00):**

| Beat | Window | Purpose |
|---|---|---|
| 1. Hook / problem | `00:00–00:45` | Put the audience inside the cost of the status quo. Concrete, quantified where possible. |
| 2. Show the fix | `00:45–02:30` | Walk the feature in action. One path. No side quests. |
| 3. The turn / aha | `02:30–03:15` | The single moment where the room realizes *oh — that's different*. |
| 4. Impact + close | `03:15–05:00` | Business framing, callback to the hook, what ships next, CTA. |

**10-minute arc (total 10:00):**

| Beat | Window | Purpose |
|---|---|---|
| 1. Hook / problem | `00:00–01:00` | Same as 5-min, slightly more room for context. |
| 2. Approach / context | `01:00–02:30` | Why this approach, what was ruled out. Light. |
| 3. Show the fix | `02:30–06:00` | Walk the feature. Can include one happy-path + one edge case. |
| 4. The turn / aha | `06:00–06:45` | Same purpose. |
| 5. Technical deep-dive | `06:45–08:30` | The one detail the engineers in the room actually want. Clearly optional-looking so C-suite can tune out without feeling talked-down-to. |
| 6. Impact + close | `08:30–10:00` | Business framing, callback, CTA, Q&A handoff. |

### 4. Write the dual-audience talk track

This is the craft part. The main talk track should work for C-suite — **value-forward, quantified, jargon-light**. Where technical depth is useful, put it in a **branch** (see format below) so the presenter can flex based on who's asking.

Guidelines:

- **Lead every scene with the "why it matters" before the "how it works."** C-suite will tune out during a mechanics-first explanation; engineers won't punish you for leading with impact.
- **Quote numbers early and once.** "$47K in SLA credits last quarter" is better than "significant SLA impact." One number per scene, tops.
- **Name the user.** "A connector admin opens this view to…" beats "the user can…". Specific roles make it feel real.
- **One verb per action line.** "Open the dashboard." not "The presenter navigates to the dashboard and then proceeds to open it."
- **Delivery cues are welcome when they earn it.** `[PAUSE]`, `[beat]`, `[slower]`, `>> CLICK next slide`, "hold for two seconds" — use them to mark a specific moment you want the presenter to protect. The test is whether removing the cue would lose something real; if not, cut it.

### 5. Add branching contingencies

Demos go wrong. The script has to survive that without the presenter improvising in front of executives.

Two kinds of branches:

**Audience branches** — adapt depth on the fly based on who's engaging:
```
Branch — if technical questions dominate: After the fix lands, add 30s on retry policy: exponential backoff with jitter, capped at 5 attempts.
Branch — if C-suite dominates: Skip the retry detail, extend the impact scene with the $47K callback.
```

**Failure branches** — what to do when something breaks mid-demo:
```
Branch — if the live API call hangs >3s: Switch to the pre-recorded clip at ~/demos/backup/sync-success.mov. Narrate over it.
Branch — if the test tenant is empty: seed demo data before the call, or fall back to a pre-staged staging environment you control.
```

Put failure branches inline at the scene where they might fire, and also gather them in a **CONTINGENCIES** section at the end for pre-demo review.

### 6. Generate the surrounding scaffolding

Every script also includes:

- **Pre-demo checklist** — browser tabs, logged-in accounts, notifications silenced, test data seeded, backup clips accessible. This lives at the top so the presenter can run it T-5 minutes before showtime.
- **Anticipated Q&A** — 3–5 questions you'd expect from this room with one- or two-sentence answers prepared. Split into "technical Qs" and "exec Qs" so the presenter can scan fast.
- **Practice marks** — a short list of specific times at which the presenter should be at a specific place in the script. These are the marks to hit when rehearsing with a stopwatch. Example: `:45 — off the problem frame and into the demo`. Four or five marks is plenty for a 5-min demo, six or seven for a 10-min.

### 7. Save and tell the user

Per the user's global rules, artifacts go to `~/.agent/`, not the repo. Save as:

```
~/.agent/demo-scripts/<slugified-feature-name>-<YYYY-MM-DD>.md
```

Create the directory if it doesn't exist. Tell the user the path and read the file back to them inline so they can review without opening it. If the user's request mentioned textream, teleprompter, on-camera, or streaming — or if they asked for it explicitly — continue to step 8. Otherwise stop here.

### 8. Textream export (on request)

**When to run this step.** Only when the user asked for it — either in the initial request (mentions textream, teleprompter, on-camera, streaming, "I'll be reading this") or in a follow-up ("also textream", "give me the teleprompter version", "export to textream"). Don't generate a `.textream` file by default; most demos are live in-person and don't need one.

**What textream is.** Textream is a macOS teleprompter app that reads `.textream` files — a minimalist JSON array of strings with inline bracketed delivery cues like `[pause]`, `[beat]`. The app highlights your words in real time as you read aloud, and action cues in the brackets are shown to you but not read. The `.md` is for preparation (checklist, Q&A, rehearsal); `.textream` is for performance.

**Translation rules (summary).**

1. One JSON element per SCENE (talk-track paragraphs joined with `\n\n`).
2. Actions merge inline as uppercase bracketed cues at the moment they fire: `[CLICK sidebar]`, `[SWITCH tab]`, `[POINT AT credit meter]`.
3. Existing delivery cues pass through unchanged. Normalize to lowercase if needed: `[pause]`, `[beat]`, `[slower]` — matching textream's example vocabulary.
4. Drop entirely: pre-demo checklist, `**Branch — …**` sections, contingencies, Q&A, practice marks, presenter notes, scene timestamps, scene titles. If a scene has an audience-adaptation branch the presenter expected to hit live, warn the user in the chat message that the teleprompter version is the happy-path only — the branches stay in the `.md`.
5. Refuse to export if the `.md` has `[GAP: …]` placeholders. Tell the user which gaps remain and offer to export once they're filled. A teleprompter reading "gap colon insert the number" is worse than no teleprompter.
6. Output must be valid JSON (round-trips through `json.loads`), UTF-8, no BOM.

**File path.** Same slug as the `.md`, `.textream` extension, same directory:

```
~/.agent/demo-scripts/<slugified-feature-name>-<YYYY-MM-DD>.textream
```

**Detailed rules and a full worked example** (side-by-side `.md` → `.textream` for the UI-245 demo) are in `references/textream-export.md`. Read that file before generating a `.textream` if you're unsure how a specific scene should translate — especially for scenes that are mostly action with minimal talk track, or scripts with load-bearing branches.

**After saving,** tell the user both file paths, mention any warnings (dropped branches, etc.), and note that the `.md` remains the source of truth — if the script changes, regenerate both.

## Output format

Use this exact template. Adapt content; keep the structure.

```markdown
# Demo: <Feature Name>

**Runtime target:** <5:00 or 10:00>
**Audience:** Internal technical + C-suite (mixed room)
**Source:** <Linear ticket / PRD path / free text>
**Drafted:** <YYYY-MM-DD>

---

## Pre-demo checklist (T-5 minutes)

- [ ] <specific tab / URL loaded>
- [ ] <test tenant or account>
- [ ] Slack + calendar notifications silenced
- [ ] Backup clips accessible at <path>
- [ ] Screen resolution / zoom level checked
- [ ] <feature-specific prep>

---

## SCENE 1 — <Title> [00:00–00:45]

**Action**
<One or two sentences describing what the presenter is doing on screen.>

**Talk track**
<The actual words, written to be spoken. Paragraph form, 2–4 sentences per scene for 5-min, 4–6 for 10-min.>

**Branch — <condition>**
<What to do or say instead.>

---

## SCENE 2 — <Title> [00:45–02:30]

...

---

## Contingencies

- **If <thing breaks>:** <recovery action>
- **If <another thing>:** <recovery action>

---

## Anticipated Q&A

**Technical**
- *"<likely technical question>"* — <one to two sentence answer>
- *"<another>"* — <answer>

**Exec**
- *"<likely exec question, usually about cost/timeline/risk>"* — <answer>
- *"<another>"* — <answer>

---

## Practice marks

Rehearse with a stopwatch. Hit these marks within ±10 seconds:

- `:45` — <where you should be>
- `2:30` — <where you should be>
- `3:15` — <where you should be>
- `4:45` — <where you should be>

---

## Notes for the presenter

<1–3 sentences of craft-level guidance the skill picked up from the source — e.g., "this feature's main value is latency reduction, lean on the 12ms number"; "avoid going deep on the migration story unless asked, it distracts from the payoff". Delivery cues belong in the scenes themselves; this section is for higher-level shape notes.>
```

## Craft notes

A few things that distinguish good demo scripts from mediocre ones. Keep these in mind as you write:

- **Cut ruthlessly.** Every sentence in a 5-minute script has to pay rent. If a line could be removed without the audience missing anything, remove it. The script should feel slightly under-stuffed, because live delivery always expands.
- **Callbacks pay off.** If the hook is "$47K in SLA credits," the close should name that number again. Circular structure is satisfying and it helps the C-suite half of the room remember the point when they're repeating it to someone else later.
- **One turn, not many.** A demo has one "oh, that's different" moment. If the feature has several cool aspects, pick the most visceral one for the turn and demote the others to supporting detail or the deep-dive scene. Multiple turns dilute each other.
- **Action lines are commands, not narrations.** Write "Open the dashboard." The presenter is reading this in rehearsal and live; they don't need "the presenter then proceeds to open the dashboard."
- **Talk track is spoken, not written.** Contractions, short sentences, no sub-clauses stacked three deep. Read it out loud when drafting — if you stumble, rewrite.
- **Numbers beat adjectives.** "47% faster" beats "significantly faster." If you don't have a number, either find one in the source or don't make the claim.
- **The script is a floor, not a ceiling.** The presenter will improvise. Your job is to give them a shape solid enough that improvising feels safe — they can come back to the script if the room goes sideways.

## Interaction style

When the input is thin, ask at most **two** targeted questions before drafting. Don't interview the user. Common gaps worth asking about:

- The "aha" moment (what's the single visceral change?)
- The quantified business impact (a number, even rough)

If the user doesn't know either, draft your best guess and flag the gaps clearly at the top of the script so they know what to sharpen before presenting.

Default to 5 minutes if the user didn't specify a length. Default to Linear if they reference a ticket ID without context. Assume the audience is mixed technical + exec unless the user says otherwise.
