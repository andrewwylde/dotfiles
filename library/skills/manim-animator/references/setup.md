# Manim Setup and Flavor Choice

## Which Manim: choose ManimCE

This skill targets **ManimCE (Community Edition)** — the `manim` package on PyPI maintained by the Manim Community.

**Not** ManimGL (Grant Sanderson's own fork, the `manimgl` package).

### Rationale

- **Installability.** `pip install manim` works on macOS, Linux, and Windows with modest extra dependencies (ffmpeg, a TeX distribution for math). ManimGL depends on a specific OpenGL stack and is significantly harder to get running in the typical user environment.
- **API stability.** ManimCE follows a documented versioning policy and the docs at docs.manim.community match the latest release. ManimGL breaks its own API without notice; 3b1b's own video repo pins to specific commits.
- **Community.** ManimCE has far more tutorials, examples, and Stack Overflow answers. A user who hits a problem will find answers faster.
- **Grant's own position.** Grant himself has publicly recommended ManimCE for people new to Manim. He uses ManimGL for his own videos because of specific feature needs, not because it's better for general teaching.

The motion grammar, class names (`Scene`, `Transform`, `Write`, etc.), and core concepts are essentially identical between the two flavors. A user who learns ManimCE can read ManimGL code and vice versa. This skill's motion grammar reference works for both, but all code output targets ManimCE.

## Version pin

Pin `manim>=0.18,<0.20` in `requirements.txt`. This range covers the stable API surface we rely on (Scene, play, wait, Transform family, MovingCameraScene, Write, Create, FadeIn, FadeOut, GrowFromCenter, Indicate, VGroup, Text, MathTex, Line, Arrow, Rectangle, Circle, Dot, NumberPlane, Axes). Any release in that range will run the scenes in `domain-examples.md`.

If a newer major release is out (0.20+) by the time a user tries this, the scenes are likely to still work — ManimCE's major version bumps have been additive so far — but the pin protects against surprise breaking changes.

## Install command

On macOS:

```bash
pip install "manim>=0.18,<0.20"
# If math rendering (MathTex) is needed, install a TeX distribution:
brew install --cask mactex-no-gui
# And ffmpeg for video output:
brew install ffmpeg
```

On Linux (Debian/Ubuntu):

```bash
sudo apt-get install -y libcairo2-dev libpango1.0-dev ffmpeg texlive-latex-extra
pip install "manim>=0.18,<0.20"
```

On Windows: refer users to the official ManimCE install guide (docs.manim.community/en/stable/installation.html) — it's easier to link there than to maintain a Windows install section here.

## Render commands by mode

### Animation mode

```bash
# Medium quality for development (720p @ 30fps, quick):
manim -qm scene.py ClassName
# High quality for final output (1080p @ 60fps):
manim -qh scene.py ClassName
# 4K for final-final:
manim -qk scene.py ClassName
```

Output lands in `./media/videos/scene/<quality>/ClassName.mp4` relative to wherever the user runs the command. That's ManimCE's default; do not try to override it unless the user asks.

### Static-frame mode

```bash
manim -s -qh scene.py ClassName
```

The `-s` flag skips video and saves only the last frame as PNG to `./media/images/scene/ClassName.png`.

### Interactive-scroll mode

Render each scene class separately at a short duration, then serve the `index.html`:

```bash
manim -qm scene.py Beat1 Beat2 Beat3 Beat4
# Then open the scaffold:
python -m http.server 8000
# Visit http://localhost:8000/index.html
```

The generated `index.html` expects the videos at `./media/videos/scene/720p30/<ClassName>.mp4` (ManimCE's default output layout for `-qm`).

## If Manim is not installed

The skill deliverable is the scene script, not the rendered video. If `manim --version` fails on the user's machine:

1. Still write `scene.py`, `requirements.txt`, `README.md` under `~/.agent/manim/<slug>/`.
2. Tell the user: "Manim isn't installed yet. Install it with `pip install -r requirements.txt` and any system-level deps (ffmpeg, optionally TeX). Then render with `<the render command for the mode>`."
3. Do not pretend you rendered the video. Do not silently fall back to another diagramming tool — the user asked for motion, handing them a Mermaid diagram would be the wrong answer.

## Quick install-check snippet

If you want to verify the environment before writing files:

```bash
python -c "import manim; print(manim.__version__)" 2>/dev/null || echo "manim not installed"
```

You can run this, but don't gate on the result — the skill still produces useful output (the `.py` file) even when Manim is absent.
