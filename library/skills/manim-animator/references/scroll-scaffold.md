# Interactive-Scroll HTML Scaffold

Template for the `index.html` emitted in `interactive-scroll` mode. The idea: each beat in the explanation becomes a scene that renders to a short MP4 clip; the page stacks them vertically; scrolling a clip into view auto-plays it; scrolling away pauses it.

This is the Bartosz Ciechanowski / Distill.pub pattern. The scaffold is minimal on purpose — the user can restyle the page afterward. The distinctive value is the clip-playback discipline, not the page chrome.

## Scene authoring for scroll mode

Each beat is its own `Scene` subclass. Keep each one short (5–15 seconds rendered) so a file isn't too heavy and the auto-play feels responsive. You still apply all 3b1b pacing rules inside each scene — reveal, label, transform, pause — but the scene as a whole is one or two beats rather than a full story arc. The *page* is the story arc; each *scene* is a chapter.

Typical split for a 4-chapter explainer:

```python
from manim import *

class Beat1Setup(Scene):
    def construct(self):
        # ... introduce the objects
        self.wait(2)

class Beat2Complication(Scene):
    def construct(self):
        # ... show the interesting transform
        self.wait(2)

class Beat3Insight(Scene):
    def construct(self):
        # ... the "aha" moment
        self.wait(2)

class Beat4Resolution(Scene):
    def construct(self):
        # ... the payoff frame
        self.wait(3)
```

Render all scenes in one command:

```bash
manim -qm scene.py Beat1Setup Beat2Complication Beat3Insight Beat4Resolution
```

## `index.html` scaffold

Generate with ManimCE's default output path (`./media/videos/scene/720p30/<ClassName>.mp4` for `-qm` quality):

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{{EXPLAINER_TITLE}}</title>
  <style>
    :root { color-scheme: light dark; }
    body {
      max-width: 42rem;
      margin: 0 auto;
      padding: 3rem 1.25rem 8rem;
      font: 1rem/1.6 system-ui, -apple-system, sans-serif;
    }
    h1 { font-size: 2rem; margin-bottom: 0.25rem; }
    .lede { font-size: 1.15rem; opacity: 0.75; margin-bottom: 3rem; }
    section {
      margin: 4rem 0;
      display: grid;
      gap: 1rem;
    }
    section h2 { font-size: 1.25rem; margin: 0; }
    section p { margin: 0; }
    section video {
      width: 100%;
      height: auto;
      border-radius: 8px;
      background: #000;
    }
  </style>
</head>
<body>
  <h1>{{EXPLAINER_TITLE}}</h1>
  <p class="lede">{{ONE_LINE_SUMMARY}}</p>

  <section data-beat="1">
    <h2>1. {{BEAT_1_HEADING}}</h2>
    <p>{{BEAT_1_NARRATION}}</p>
    <video muted playsinline loop preload="metadata"
           src="./media/videos/scene/720p30/Beat1Setup.mp4"></video>
  </section>

  <section data-beat="2">
    <h2>2. {{BEAT_2_HEADING}}</h2>
    <p>{{BEAT_2_NARRATION}}</p>
    <video muted playsinline loop preload="metadata"
           src="./media/videos/scene/720p30/Beat2Complication.mp4"></video>
  </section>

  <section data-beat="3">
    <h2>3. {{BEAT_3_HEADING}}</h2>
    <p>{{BEAT_3_NARRATION}}</p>
    <video muted playsinline loop preload="metadata"
           src="./media/videos/scene/720p30/Beat3Insight.mp4"></video>
  </section>

  <section data-beat="4">
    <h2>4. {{BEAT_4_HEADING}}</h2>
    <p>{{BEAT_4_NARRATION}}</p>
    <video muted playsinline loop preload="metadata"
           src="./media/videos/scene/720p30/Beat4Resolution.mp4"></video>
  </section>

  <script>
    const videos = document.querySelectorAll("video");
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        const v = e.target;
        if (e.isIntersecting && e.intersectionRatio > 0.5) {
          v.play().catch(() => {});
        } else {
          v.pause();
        }
      }
    }, { threshold: [0, 0.5, 1] });
    videos.forEach(v => io.observe(v));
  </script>
</body>
</html>
```

## Guidance for filling the template

- **`{{EXPLAINER_TITLE}}`**: the concept in 2–6 words.
- **`{{ONE_LINE_SUMMARY}}`**: the one-sentence distillation from Step 1 of the core workflow.
- **`{{BEAT_N_HEADING}}`**: the beat's role in the narrative — not the Manim class name. "Setup", "The problem appears", "Key insight", "Payoff" or the domain-specific equivalents.
- **`{{BEAT_N_NARRATION}}`**: 2–3 sentences. This is the text the reader sees while the clip plays. Keep it shorter than the clip's duration so the reader finishes reading and watches the motion land.

## Styling

The scaffold uses `color-scheme: light dark` so it respects the user's OS preference and does not lock to a 3b1b-ish dark theme. If the user wants a specific look, they restyle — this scaffold is the minimum viable structure.

## Not included and why

- **Audio narration tracks.** Out of scope. Users who want narration record it separately and overlay in a video editor, or use the page's text as a reading script.
- **Per-section deep-link URLs.** Easy to add (`<section id="beat-1">`) but not default — keeps the scaffold under 100 lines.
- **Frontmatter / MDX / framework integration.** The skill emits raw HTML. Users on Astro/Next/MDX can adapt by copying the sections and swapping the `<video>` elements into their component system.
