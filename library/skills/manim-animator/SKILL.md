---
name: manim-animator
description: "Generate Manim (Python) scene scripts for narrated pedagogical animations that explain a concept through motion — the 3Blue1Brown style of \"reveal, label, transform, pause.\" Reliable across domains: math, systems/architecture flow, data pipelines, algorithms (graph traversals, sorting), and abstract CS. Use when the user asks to \"explain X with animation/motion\", \"visualize how X works over time\", \"3blue1brown style\", \"show the request moving through services\", \"animate the algorithm\", \"build a pedagogical video/clip\", or mentions Manim. Also applicable for a static figure when they want a single frame rendered from a Manim construction (mathematical notation, precise geometry), and for scroll-driven explainers that embed short Manim clips per section. Do NOT use for static block-style diagrams (use mermaid-studio), hand-drawn sketchy diagrams (use excalidraw-studio), self-contained styled HTML pages with static content (use visual-explainer), or production UI work (use frontend-design). The distinctive value is *motion grammar and narrative pacing*, not a surface aesthetic."
license: MIT
---

# Manim Animator

Generate Manim scene scripts that explain a concept through motion and narrative pacing, in the pedagogical tradition of 3Blue1Brown. The output is a Python file the user (or their environment) renders with `manim`. You do not block on rendering.

This skill's *style* is the motion grammar and narrative pacing — not a surface look. Colors, typography, and background stay at ManimCE defaults (or whatever the user specifies) unless they ask for a specific palette.

## When this skill applies

Use this skill when the ask involves **motion over time to build understanding**. The test: would a static diagram answer the question, or does the explanation need a sequence of reveals, transforms, and pauses?

Pattern match these:
- "animate how a request moves through our services"
- "explain the quicksort algorithm visually"
- "show how backpropagation updates weights"
- "visualize the data flowing through this ETL pipeline"
- "make a short clip explaining what a Kalman filter does"
- "3blue1brown style explanation of eigenvectors"
- "manim scene for a graph traversal"

Skip this skill and defer to a sibling when:
- The user wants a static block/flow diagram → `mermaid-studio`
- The user wants a hand-drawn feel → `excalidraw-studio`
- The user wants a self-contained HTML page with static content → `visual-explainer`
- The user wants a polished UI → `frontend-design`

## Output modes

Pick the mode from the user's ask. Default to **animation**.

| Mode | User signal | What you produce |
|------|-------------|------------------|
| **animation** (default) | "explain", "show how", "animate", "walk through", "build intuition" | One `Scene` subclass. Render with `manim -qm scene.py <ClassName>` → MP4. |
| **static-frame** | "make a figure", "illustration for my post", "single frame", "PNG" | Same Scene, but with a final `self.wait(0.1)` beat; render with `manim -s -qh scene.py <ClassName>` → PNG of the last frame. |
| **interactive-scroll** | "scroll-driven explainer", "Bartosz Ciechanowski style", "Distill-style article", "each section has a small clip" | Multiple small `Scene` subclasses (one per concept beat) **plus** a minimal HTML scaffold with `<video>` tags + IntersectionObserver. You don't render the clips; you produce the scaffolding and the `manim` command(s) to run. |

For a concrete scaffolding template for interactive-scroll, read `references/scroll-scaffold.md`.

## The core workflow

Every mode follows the same four steps. The mode only changes what you output at step 4.

### Step 1 — Identify the concept and the domain

Write a one-sentence distillation in your own words: *"The idea is that X happens because Y."* If you can't state it in one sentence, press the user for the core idea before coding. A Manim scene that visualizes a fuzzy concept will be a fuzzy scene.

Then name the domain: **math**, **systems/architecture**, **data pipeline**, **algorithm**, or **abstract CS**. The domain determines the motion vocabulary — a request flowing between services wants translating `Dot` objects; a derivative wants a tangent line tracking a moving point. Pick the vocabulary that matches, not the first one that comes to mind.

For worked examples per domain, read `references/domain-examples.md` — it has four complete, runnable scenes (math, systems, data, algorithm) to use as starting points.

### Step 2 — Storyboard the beats

Before writing code, list the beats. A beat is **one idea introduced, one pause to absorb it**. Aim for 4–8 beats for a ~30–60 second clip.

Example for "request flowing through three services":
1. Draw the three service boxes, labeled, static. Pause.
2. Introduce the client as a `Dot`. Pause.
3. Translate the `Dot` from client → service A, arrow appears as it moves. Pause at arrival.
4. Service A "lights up" (fill color flashes), spawns a sub-request to service B. Pause.
5. Response bubbles back through the chain with a `ReplacementTransform` of the dot color. Pause.
6. Final state: steady-state highlight of the full path. Hold.

The beats are the narrative. Don't skip this step — rushing straight to `self.play(...)` calls produces busy, hard-to-follow scenes.

### Step 3 — Apply 3b1b motion grammar

For the rules of *which* Manim method to use for *which* narrative move (Write vs FadeIn vs Create, when to `ReplacementTransform` vs `Transform`, how to use `self.wait()`, when to move the camera), read `references/3b1b-style.md`. It codifies motion grammar and pacing only — it explicitly does NOT prescribe colors, fonts, or background.

### Step 4 — Emit the artifacts

All generated files go under `~/.agent/manim/<slug>/` (per the user's global rule that agent artifacts do not go in the repo or `/tmp`). Create:

1. `scene.py` — the Manim code. One `Scene` subclass for animation/static-frame; multiple for interactive-scroll.
2. `requirements.txt` — pin Manim (see `references/setup.md` for the current-recommended version line).
3. `README.md` — a three-line file with: the install command, the render command for the mode chosen, and the output path. Nothing else; the user wants to *run* this, not read about it.
4. For interactive-scroll only: `index.html` — scaffold with `<video>` tags and a small IntersectionObserver snippet (template in `references/scroll-scaffold.md`).

Then tell the user what you produced and print the render command. Do not try to run `manim` yourself unless the user has explicitly asked for a rendered artifact AND you have confirmed Manim is installed. If Manim is missing, say so and hand over the install command — do not pretend to have rendered.

## Surface aesthetics are not this skill's job

The 3b1b inspiration here is the *motion grammar* — the discipline of reveal-then-label, transform chains, deliberate pauses, one-idea-per-beat. That is prescriptive.

The *surface look* — Grant's specific dark background, his particular blues and yellows, his fonts — is NOT prescriptive. Leave it at ManimCE defaults. If the user asks for a specific palette or dark theme, apply it then; otherwise do not set `config.background_color`, do not import `BLUE_E`/`YELLOW_E` as a fixed palette, and do not assume dark-on-light vs light-on-dark. Let the environment decide.

This matters because a skill that always ships dark + electric-blue would be instantly recognizable as "AI imitating 3b1b," which is the opposite of good pedagogy. The motion is the pedagogy; the look is decoration.

## When Manim is not installed

Do not block on this. The skill's deliverable is the scene script — a user who doesn't have Manim today can install it tomorrow and render the same file. In your final message:

1. Tell them the file path (`~/.agent/manim/<slug>/scene.py`).
2. Print the install command from `references/setup.md`.
3. Print the render command for the mode chosen.
4. If you want to be helpful, validate the scene parses as Python (`python -c "import ast; ast.parse(open('<path>').read())"`) so at least you know the file isn't broken.

Do not render the video and claim success when you didn't. Do not silently skip Manim and fall back to a Mermaid diagram — that's a different skill's output.

## Validation before declaring done

Run the bundled validator before reporting completion:

```bash
python ~/.claude/skills/manim-animator/scripts/validate_scene.py <path-to-scene.py>
```

It checks the five reliability criteria: valid Python, at least one `Scene` subclass, at least one transform-family call, at least one `self.wait(...)` beat, and no hard-coded `config.background_color` (so the scene stays portable). If the validator fails, fix the scene — do not hand the user a script that doesn't parse.

## References

- `references/3b1b-style.md` — motion grammar and pacing rules (prescriptive)
- `references/domain-examples.md` — four complete runnable scenes (math, systems, data, algorithm)
- `references/setup.md` — ManimCE install + version pin + rationale for choosing CE over GL
- `references/scroll-scaffold.md` — HTML + IntersectionObserver template for interactive-scroll mode
- `references/design-decisions.md` — why this is one skill and not three, and other design notes
