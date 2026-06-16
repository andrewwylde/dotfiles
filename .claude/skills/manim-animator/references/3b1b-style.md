# 3b1b Motion Grammar and Narrative Pacing

This reference codifies **motion grammar and pacing rules** drawn from 3Blue1Brown's teaching style. It is deliberately prescriptive on *how things move* and *how long the viewer has to absorb each beat* — and deliberately silent on colors, fonts, and backgrounds. Those are the user's choice or ManimCE defaults.

Why separate motion from surface: motion is the pedagogy. A dark background with electric-blue accents does not teach anything — the reveal-then-label discipline does. Ship the motion grammar, leave the surface configurable.

## The core loop: reveal, label, transform, pause

Every pedagogical beat in a 3b1b scene follows the same rhythm:

1. **Reveal** — an object appears. Use the verb that matches what the object *is*:
   - `Write(...)` for text and equations — the pen-stroke motion draws the eye along the content
   - `Create(...)` for geometric shapes, lines, axes — traces the outline
   - `FadeIn(...)` for objects that "just need to be there" without drama (a legend, a background element)
   - `GrowFromCenter(...)` / `GrowFromEdge(...)` for emphasis on a discrete new entity (a node appearing, a highlight box)
   - `DrawBorderThenFill(...)` for filled shapes where the outline carries semantic weight (a container being defined before it is populated)

2. **Label** — *after* the object exists. Never reveal a labeled object all at once; the viewer's eye cannot read the label and track the object simultaneously. The pattern is:

   ```python
   self.play(Create(node))
   self.wait(0.5)
   self.play(Write(node_label.next_to(node, UP)))
   ```

   Half a second of naked object before the label lands gives the eye a target.

3. **Transform** — the state changes. This is the work of the beat. The verb choice matters:
   - `Transform(old, new)` morphs `old` into `new` *by mutating `old`*. Use when `new` is a variation of `old` (an equation simplifies, a box resizes).
   - `ReplacementTransform(old, new)` turns `old` into `new` as separate objects. Use when they are conceptually different things occupying the same slot (a request `Dot` becomes a response `Dot` with a different color; a value in a node becomes a different value).
   - `FadeOut(old); FadeIn(new)` when the transition is *not* continuous — when you *want* the viewer to see that this is a cut, not a morph.
   - `MoveAlongPath(obj, path)` or `obj.animate.move_to(...)` for translation — a request flowing from service A to service B.
   - `Indicate(obj)` for a quick "look here" pulse without changing the object — useful when you're about to talk about it.

4. **Pause** — `self.wait(t)` where `t` is at least 0.5 seconds, usually 1.0–2.0. Pauses are where understanding happens. A scene without pauses is a demo reel, not a lesson.

   A useful heuristic: **the pause after a beat should be at least as long as the sentence a narrator would say about that beat.** For a simple reveal, 0.75s. For an insight ("and *this* is the key part"), 1.5–2.0s. For the final payoff frame, hold for 2–3s so the viewer can take a screenshot or screenshot the mental image.

## Build-up to payoff

A pedagogical scene is a small story: setup → complication → resolution. Map it onto Manim beats:

- **Setup (beats 1–2)**: establish the objects and the starting state. Everything is labeled and still. No motion yet besides the reveals. Pause generously so the viewer has time to read all the labels.
- **Complication (beats 3–5)**: introduce the change. One new idea per beat. Transforms happen here. Pause after each so the viewer can track what changed.
- **Payoff (final beat)**: the result is visible and the viewer can see it was inevitable from the setup. Hold this frame — 2+ seconds.

If you can't articulate a setup/complication/payoff for your scene, the scene is not teaching anything and you should go back to Step 1 of the workflow and restate the concept.

## One idea per beat

If you find yourself chaining two `self.play(...)` calls with no `self.wait` between them, you are animating two new ideas at once. Viewers cannot track two new ideas at once. Add a pause between them, or combine them into a single `self.play(a, b)` call only if `a` and `b` are *the same idea* expressed on two objects (e.g., two nodes lighting up together because they are part of the same set).

The `lag_ratio` parameter on `AnimationGroup` is useful for staggered reveals of similar objects — list items appearing one after another as a group, without three separate beats. But the group as a whole is still one idea.

## Static before dynamic

The first beat of a scene should be *still*. Reveal the objects, label them, then let them sit for a second or two. This gives the viewer's eye time to anchor before anything moves. It is the equivalent of a narrator saying "okay, here's what we're looking at" before starting the explanation.

Violation smell: the scene opens with a `self.play(Transform(...))` call. The viewer doesn't know what is transforming into what because they never saw either state as a stable picture.

## Camera moves have meaning

`self.play(self.camera.frame.animate.move_to(x).set(width=w))` (on `MovingCameraScene`) should only be used to **direct attention**. Never pan for aesthetic reasons. Two legitimate uses:

- **Zoom in** when one part of the frame becomes the focus of the next several beats (zoom in on a single node to show what's happening *inside* it).
- **Zoom out** at the end of a build-up to show the big picture after the detail work.

A scene that pans constantly is harder to follow than a static frame. When in doubt, don't move the camera.

## The "aha" beat

Every good pedagogical scene has one moment where the viewer goes "oh, I see." Design the beats so that this moment has the most space around it. Specifically:

- The beat *before* the aha should be a pause of 1.5s+ — the viewer is being given time to feel the question.
- The aha itself should use `Indicate(...)` or a color flash or a bold transform — something that says *"this is the point."*
- The beat *after* should hold for 2s+ so the viewer can lock it in.

In 3b1b's own videos this is often a highlighted equation, a moment of geometric alignment, or a graph suddenly touching a target point. Whatever it is in your scene, treat it as the structural centerpiece and give it room.

## Anti-patterns to avoid

- **Labeling while moving.** The label should land *before* the object moves, not during.
- **Skipping `self.wait`.** If every beat flows into the next with no pause, the scene feels like a fast-forward demo and teaches nothing.
- **Too many objects on screen.** If you can't fit every object on a 1080p frame at a legible size, you have too many. Split into multiple scenes or zoom in.
- **Decorative motion.** Bouncing, spinning, orbiting for no reason. Every animation should change the viewer's mental model.
- **`Transform` when you meant `ReplacementTransform`.** If the "after" is conceptually a different thing, `ReplacementTransform` makes the boundary clear. `Transform` is for "same thing, new form."

## What this reference deliberately does NOT prescribe

- Colors. Use ManimCE defaults or whatever palette the user asks for. Do not set `config.background_color`.
- Fonts. Use Manim's `Text` and `MathTex` defaults. Do not import or configure specific font families unless the user asks.
- Scene dimensions / resolution. Default to Manim's defaults (`-qm` for development, the user can re-render `-qh` or `-qk` later).
- Narrator audio. This skill does not generate audio tracks. Pacing is designed so a user can narrate over the rendered MP4 in post, with each pause long enough for one sentence.

The motion grammar is the skill's value. The surface look is the user's call.
