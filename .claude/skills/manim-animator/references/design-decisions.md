# Design Decisions

Notes on decisions made while building this skill, kept for future maintainers (including future-me).

## Why one skill, not three

The brief asked for three sub-skills as peers:

- `pedagogical-animation` — narrated MP4 with transform reveals
- `static-illustration` — single-frame PNG from Manim
- `interactive-explainer` — scroll-driven HTML with embedded clips

I considered this and rejected the split. The skill-creator prompt explicitly allowed this: *"If during discovery you find the sub-skill split is not justified (e.g. 80% shared workflow), fold them into a single parameterized skill and explain the decision."*

### Shared workflow (~85%)

All three use cases flow through the same four steps:

1. Identify the concept and domain.
2. Storyboard the beats.
3. Apply 3b1b motion grammar.
4. Emit Manim scene code.

The only divergence is at step 4: which render command is printed, and whether an HTML scaffold is also emitted. That's a parameter, not a different skill.

### Trigger collision risks of splitting

Splitting into three peer skills would have created two kinds of collision:

**Intra-family collision.** "Make me a short explainer about X" could fire any of the three — they all produce explanatory content. The model would have to pick one based on fine trigger-phrase distinctions, and the user's intent is usually not that precise.

**Inter-family collision.** `static-illustration` as a peer skill would compete with `mermaid-studio`, `excalidraw-studio`, and `visual-explainer` on every "make a diagram" request. Manim is the *wrong* tool for most diagrams — it's overkill for block-and-arrow work, and a worse visual result than Mermaid or Excalidraw for 80% of static-diagram asks. A top-level `static-illustration` skill would over-trigger on exactly the asks that shouldn't use it.

By keeping static-frame as an output *mode* inside `manim-animator`, it only fires when the user has already signaled motion/pedagogy/Manim as part of the ask. The description is tight enough that "make a flowchart" does not trigger this skill.

### Why interactive-scroll stays in-family

Interactive-scroll is genuinely different from `visual-explainer`: visual-explainer produces a self-contained HTML page with static content (diagrams rendered inline, tables, typography). Interactive-scroll produces an HTML page whose *content is Manim MP4 clips* embedded with scroll triggers. The embedded clips are the distinctive value — you can't get them out of visual-explainer. But the *scene authoring* is identical to pedagogical-animation. So it's a mode, not a separate skill.

### What would justify splitting later

If we found that:

- A large user base was asking for static figures *without* the motion-grammar framing (e.g., "just generate the PNG, don't think about pacing"), such that the motion-grammar guidance was net noise.
- Interactive-scroll grew its own deep toolbox (e.g., a full scrollytelling framework with per-section audio narration, not just a scaffold).

…then splitting would make sense. Today, the shared workflow is dominant and a single skill is simpler.

## Why target ManimCE, not ManimGL

See `setup.md` — the short version is: installability, API stability, community support, and Grant Sanderson's own recommendation for people new to Manim. The motion grammar is the same either way.

## Why surface aesthetics are not prescribed

The 3b1b style is *motion and pacing*, not the specific dark background and electric-blue palette. A skill that always shipped 3b1b's surface look would:

1. Be instantly recognizable as "AI mimicking 3b1b" — the opposite of good pedagogy.
2. Conflict with users who have their own brand colors, want a light background for a paper figure, or want to embed the scene in a non-3b1b aesthetic context.
3. Violate the "surface is decoration, motion is pedagogy" principle that makes the motion grammar reusable across so many domains.

So: the skill never sets `config.background_color`, never hard-codes a palette, and defers to ManimCE's defaults (or whatever the user specifies). The validator enforces this by failing scenes that set `config.background_color`.

## Why the skill does not render video itself

Rendering with Manim:

- Takes anywhere from 10 seconds (`-ql`, low quality) to 10+ minutes (`-qk`, 4K) depending on quality and scene length.
- Requires ffmpeg and (for math) a working TeX distribution.
- Produces large files (tens of MB to hundreds of MB).

None of these are appropriate for a skill that might be invoked dozens of times in a session. The skill's contract is: "produce the `.py` and the render command; the user renders when they want to." This also keeps the skill fast, deterministic, and testable via static analysis.

If a user explicitly asks for the rendered video AND their environment has Manim installed, the skill can run `manim` for them. But that's not the default.

## Why the validator enforces the five pass criteria

The criteria (valid Python, Scene subclass, transform reveal, `self.wait` pause, no hard-coded background) map directly to the reliability properties we care about:

- **Valid Python** → the file can actually run.
- **Scene subclass** → the file is structured as a renderable Manim scene, not just a snippet.
- **Transform reveal** → the scene has *motion*, which is the whole point of choosing this skill over Mermaid.
- **`self.wait` pause** → the scene has *pacing*, which is the 3b1b teaching discipline.
- **No hard-coded background** → the scene is portable and does not assume the 3b1b dark aesthetic.

The validator is run before declaring a task done. It exists because "generated Manim code that doesn't parse" is a silent failure mode that breaks trust.
