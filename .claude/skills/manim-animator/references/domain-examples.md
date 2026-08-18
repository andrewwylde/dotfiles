# Domain Examples

Four complete, runnable Manim scenes — one per target domain — demonstrating how the motion grammar applies across very different subject matter. Use these as starting points when the user's ask lines up with one of the domains.

All four scenes:

- Parse as valid Python (ManimCE 0.18+).
- Define a `Scene` subclass.
- Apply at least one transform-family reveal (`Write`, `Create`, `FadeIn`, `ReplacementTransform`, etc.).
- Include explicit `self.wait(...)` pacing beats.
- Do **not** set `config.background_color`, do **not** hard-code a 3b1b-specific palette — they use ManimCE defaults and named color constants only, so the user's environment (or a user override) decides the surface look.

## Table of contents

1. [Math — derivative as a tangent line](#math--derivative-as-a-tangent-line)
2. [Systems — request flowing through three services](#systems--request-flowing-through-three-services)
3. [Data pipeline — rows moving through transforms](#data-pipeline--rows-moving-through-transforms)
4. [Algorithm — breadth-first search on a graph](#algorithm--breadth-first-search-on-a-graph)

---

## Math — derivative as a tangent line

**One-sentence distillation.** The derivative of `f` at a point is the slope of the tangent line that matches the curve's direction there.

**Beats.**

1. Reveal axes + curve. Pause.
2. Reveal a moving dot on the curve. Pause.
3. Reveal the tangent line attached to the dot. Pause.
4. Slide the dot along the curve; the tangent tracks it. Pause at the turning point — that's the "aha" (slope = 0 at the minimum).
5. Hold the final frame.

```python
from manim import *


class DerivativeAsTangent(Scene):
    def construct(self):
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-1, 5, 1],
            x_length=8,
            y_length=4.5,
            tips=False,
        )
        axes_labels = axes.get_axis_labels(x_label="x", y_label="f(x)")

        def f(x):
            return 0.5 * x ** 2

        curve = axes.plot(f, x_range=[-2.8, 2.8], color=BLUE)
        curve_label = MathTex("f(x) = \\tfrac{1}{2}x^2").to_edge(UR).shift(DOWN * 0.5)

        # Beat 1: establish the space
        self.play(Create(axes), Write(axes_labels))
        self.wait(0.75)
        self.play(Create(curve), Write(curve_label))
        self.wait(1.25)

        # Beat 2: introduce the moving point
        x_tracker = ValueTracker(-2.0)

        dot = always_redraw(
            lambda: Dot(
                axes.c2p(x_tracker.get_value(), f(x_tracker.get_value())),
                color=YELLOW,
            )
        )
        self.play(FadeIn(dot, scale=0.5))
        self.wait(0.75)

        # Beat 3: attach the tangent line
        def tangent_line():
            x0 = x_tracker.get_value()
            slope = x0  # derivative of 0.5 x^2
            y0 = f(x0)
            dx = 1.25
            p1 = axes.c2p(x0 - dx, y0 - slope * dx)
            p2 = axes.c2p(x0 + dx, y0 + slope * dx)
            return Line(p1, p2, color=GREEN)

        tangent = always_redraw(tangent_line)
        self.play(Create(tangent))
        self.wait(1.25)

        # Beat 4: slide the dot, pause at the turning point
        self.play(x_tracker.animate.set_value(0.0), run_time=2.5, rate_func=smooth)
        self.wait(1.75)  # the "aha" — slope is zero at the minimum

        self.play(x_tracker.animate.set_value(2.0), run_time=2.5, rate_func=smooth)
        self.wait(0.75)

        # Beat 5: hold
        payoff = Tex("slope of tangent = $f'(x)$").to_edge(DOWN)
        self.play(Write(payoff))
        self.wait(2.5)
```

Render: `manim -qm scene.py DerivativeAsTangent`

---

## Systems — request flowing through three services

**One-sentence distillation.** A client request is handled by the API gateway, which delegates to an auth service and a data service, then the response bubbles back.

**Beats.**

1. Reveal the three service boxes, labeled, static. Pause.
2. Reveal the client. Pause.
3. Request `Dot` travels client → gateway → auth → data (with arrows appearing alongside). Pause at each arrival.
4. Response transforms color and returns along the reverse path.
5. Final frame: the full request/response path stays highlighted.

```python
from manim import *


class RequestFlow(Scene):
    def construct(self):
        # Beat 1: lay out the services
        client = RoundedRectangle(width=1.6, height=0.9, corner_radius=0.15).shift(
            LEFT * 5
        )
        gateway = RoundedRectangle(width=1.8, height=0.9, corner_radius=0.15).shift(
            LEFT * 2
        )
        auth = RoundedRectangle(width=1.6, height=0.9, corner_radius=0.15).shift(
            RIGHT * 1 + UP * 1.25
        )
        data = RoundedRectangle(width=1.6, height=0.9, corner_radius=0.15).shift(
            RIGHT * 1 + DOWN * 1.25
        )

        client_lbl = Text("client", font_size=24).move_to(client)
        gateway_lbl = Text("gateway", font_size=24).move_to(gateway)
        auth_lbl = Text("auth-svc", font_size=22).move_to(auth)
        data_lbl = Text("data-svc", font_size=22).move_to(data)

        services = VGroup(gateway, auth, data)
        service_labels = VGroup(gateway_lbl, auth_lbl, data_lbl)

        self.play(
            LaggedStart(
                *[Create(s) for s in services], lag_ratio=0.25, run_time=1.5
            )
        )
        self.play(
            LaggedStart(
                *[Write(l) for l in service_labels], lag_ratio=0.15, run_time=1.0
            )
        )
        self.wait(1.25)

        # Beat 2: introduce the client
        self.play(Create(client), Write(client_lbl))
        self.wait(0.75)

        # Beat 3: request travels
        request = Dot(client.get_right(), color=BLUE, radius=0.12)
        self.play(FadeIn(request))
        self.wait(0.4)

        arrow_c_g = Arrow(
            client.get_right(), gateway.get_left(), buff=0.05, color=BLUE
        )
        self.play(
            request.animate.move_to(gateway.get_center()),
            GrowArrow(arrow_c_g),
            run_time=0.9,
        )
        self.play(Indicate(gateway, color=BLUE))
        self.wait(0.5)

        arrow_g_a = Arrow(
            gateway.get_right(), auth.get_left(), buff=0.05, color=BLUE
        )
        self.play(
            request.animate.move_to(auth.get_center()),
            GrowArrow(arrow_g_a),
            run_time=0.9,
        )
        self.play(Indicate(auth, color=BLUE))
        self.wait(0.5)

        # Back to gateway, then down to data
        self.play(request.animate.move_to(gateway.get_center()), run_time=0.7)
        arrow_g_d = Arrow(
            gateway.get_right(), data.get_left(), buff=0.05, color=BLUE
        )
        self.play(
            request.animate.move_to(data.get_center()),
            GrowArrow(arrow_g_d),
            run_time=0.9,
        )
        self.play(Indicate(data, color=BLUE))
        self.wait(0.75)

        # Beat 4: response bubbles back (color flip)
        response = Dot(data.get_center(), color=GREEN, radius=0.12)
        self.play(ReplacementTransform(request, response))
        self.wait(0.4)
        self.play(response.animate.move_to(gateway.get_center()), run_time=0.9)
        self.play(response.animate.move_to(client.get_right()), run_time=0.9)
        self.wait(0.75)

        # Beat 5: payoff — full path highlighted
        path_arrows = VGroup(arrow_c_g, arrow_g_a, arrow_g_d)
        self.play(path_arrows.animate.set_color(GREEN))
        caption = Text(
            "request in blue, response in green", font_size=22
        ).to_edge(DOWN)
        self.play(Write(caption))
        self.wait(2.5)
```

Render: `manim -qm scene.py RequestFlow`

---

## Data pipeline — rows moving through transforms

**One-sentence distillation.** A raw row enters the pipeline, gets filtered, enriched, and aggregated into a final output.

**Beats.**

1. Reveal the four pipeline stage boxes labeled with transform names. Pause.
2. Reveal a raw row at the left. Pause.
3. Row moves into "filter" — transforms to show one column dimming. Pause.
4. Moves into "enrich" — a new column appears via `Write`. Pause.
5. Moves into "aggregate" — multiple rows merge into one via `ReplacementTransform`. Pause.
6. Output row holds at the right. Hold.

```python
from manim import *


class PipelineFlow(Scene):
    def make_row(self, values):
        cells = VGroup()
        for i, v in enumerate(values):
            cell = Rectangle(width=0.8, height=0.5, stroke_width=1.5)
            text = Text(str(v), font_size=20).move_to(cell)
            cells.add(VGroup(cell, text))
        cells.arrange(RIGHT, buff=0)
        return cells

    def construct(self):
        # Beat 1: the stages
        stages = VGroup()
        for label in ["source", "filter", "enrich", "aggregate"]:
            box = RoundedRectangle(
                width=2.0, height=1.4, corner_radius=0.1, stroke_width=2
            )
            text = Text(label, font_size=22).next_to(box, DOWN, buff=0.2)
            stages.add(VGroup(box, text))
        stages.arrange(RIGHT, buff=0.6).shift(UP * 0.3)

        self.play(
            LaggedStart(
                *[Create(s[0]) for s in stages], lag_ratio=0.2, run_time=1.5
            )
        )
        self.play(
            LaggedStart(
                *[Write(s[1]) for s in stages], lag_ratio=0.15, run_time=1.0
            )
        )
        self.wait(1.25)

        # Beat 2: a raw row
        row = self.make_row([101, 42, "A"]).move_to(stages[0][0])
        self.play(FadeIn(row))
        self.wait(0.75)

        # Beat 3: filter — dim the dropped column
        self.play(row.animate.move_to(stages[1][0]))
        self.wait(0.3)
        dropped = row[1]  # the "42" column gets dropped
        self.play(dropped.animate.set_opacity(0.25))
        self.wait(1.0)

        # Beat 4: enrich — add a new column
        self.play(row.animate.move_to(stages[2][0]))
        self.wait(0.3)
        new_cell = Rectangle(width=0.8, height=0.5, stroke_width=1.5)
        new_text = Text("EU", font_size=20).move_to(new_cell)
        new_col = VGroup(new_cell, new_text)
        # Place to the right of the existing row cells
        new_col.next_to(row[-1], RIGHT, buff=0)
        self.play(Write(new_col))
        row.add(new_col)
        self.wait(1.0)

        # Beat 5: aggregate — more rows arrive and merge into one
        peers = VGroup(
            self.make_row([102, 7, "A", "EU"]),
            self.make_row([103, 19, "A", "EU"]),
        )
        for i, peer in enumerate(peers):
            peer.move_to(stages[2][0]).shift(DOWN * (0.7 + 0.6 * i))
            peer[1].set_opacity(0.25)
        self.play(
            LaggedStart(
                *[FadeIn(p, shift=LEFT * 0.5) for p in peers],
                lag_ratio=0.2,
                run_time=1.0,
            )
        )
        self.wait(0.5)

        group_to_agg = VGroup(row, *peers)
        agg_row = self.make_row(["A", "EU", "count=3"]).move_to(stages[3][0])
        self.play(ReplacementTransform(group_to_agg, agg_row))
        self.wait(1.5)

        # Beat 6: payoff
        caption = Text(
            "filter → enrich → aggregate", font_size=24
        ).to_edge(DOWN)
        self.play(Write(caption))
        self.wait(2.5)
```

Render: `manim -qm scene.py PipelineFlow`

---

## Algorithm — breadth-first search on a graph

**One-sentence distillation.** BFS explores a graph layer by layer: visit all neighbors of the start, then all of theirs, and so on.

**Beats.**

1. Reveal the graph nodes and edges. Pause.
2. Highlight the start node. Pause.
3. Expand to its neighbors (layer 1) — they flash in sequence. Pause.
4. Expand to layer 2. Pause.
5. Expand to layer 3 until the graph is exhausted. Pause.
6. Show the layer count on the side. Hold.

```python
from manim import *


class BFSTraversal(Scene):
    def construct(self):
        # Define the graph: node id -> (x, y)
        positions = {
            "A": (-4, 0, 0),
            "B": (-2, 1.5, 0),
            "C": (-2, -1.5, 0),
            "D": (0, 2.5, 0),
            "E": (0, 0.5, 0),
            "F": (0, -1.0, 0),
            "G": (0, -2.5, 0),
            "H": (2, 1.5, 0),
            "I": (2, -1.5, 0),
            "J": (4, 0, 0),
        }
        edges = [
            ("A", "B"), ("A", "C"),
            ("B", "D"), ("B", "E"),
            ("C", "F"), ("C", "G"),
            ("D", "H"), ("E", "H"), ("F", "I"), ("G", "I"),
            ("H", "J"), ("I", "J"),
        ]
        # BFS layers starting from A
        layers = [["A"], ["B", "C"], ["D", "E", "F", "G"], ["H", "I"], ["J"]]

        # Beat 1: draw the graph
        dots = {name: Dot(point=pos, radius=0.18) for name, pos in positions.items()}
        labels = {
            name: Text(name, font_size=22).move_to(dots[name]).shift(UP * 0.35)
            for name in dots
        }
        edge_lines = VGroup(
            *[
                Line(dots[a].get_center(), dots[b].get_center(), stroke_width=2)
                for a, b in edges
            ]
        )
        self.play(Create(edge_lines), run_time=1.2)
        self.play(
            LaggedStart(
                *[FadeIn(d, scale=0.5) for d in dots.values()],
                lag_ratio=0.05,
                run_time=1.0,
            )
        )
        self.play(
            LaggedStart(
                *[Write(l) for l in labels.values()],
                lag_ratio=0.05,
                run_time=1.0,
            )
        )
        self.wait(1.25)

        # Beat 2: highlight start
        self.play(dots["A"].animate.set_color(YELLOW).scale(1.3))
        start_tag = Text("start", font_size=22).next_to(dots["A"], LEFT, buff=0.3)
        self.play(Write(start_tag))
        self.wait(1.0)

        # Beats 3–5: expand layer by layer
        layer_counter = Text("layer 0", font_size=26).to_edge(UR)
        self.play(Write(layer_counter))
        self.wait(0.4)

        layer_colors = [YELLOW, BLUE, GREEN, PURPLE, RED]
        for i, layer in enumerate(layers[1:], start=1):
            new_counter = Text(f"layer {i}", font_size=26).to_edge(UR)
            self.play(ReplacementTransform(layer_counter, new_counter))
            layer_counter = new_counter
            color = layer_colors[i % len(layer_colors)]
            self.play(
                LaggedStart(
                    *[
                        dots[name].animate.set_color(color).scale(1.2)
                        for name in layer
                    ],
                    lag_ratio=0.2,
                    run_time=max(0.6, 0.3 * len(layer)),
                )
            )
            self.wait(1.0)

        # Beat 6: payoff
        done = Text("graph explored in 4 layers", font_size=24).to_edge(DOWN)
        self.play(Write(done))
        self.wait(2.5)
```

Render: `manim -qm scene.py BFSTraversal`

---

## Using these examples

When the user's ask matches a domain, copy the closest scene as a starting point and adapt:

- Change the symbols, names, and specific motion (e.g., a sorting algorithm reuses the `BFSTraversal` "highlight layer by layer" vocabulary with different rules).
- Keep the pacing — the `self.wait(...)` durations are tuned for narratable beats.
- Do not introduce `config.background_color` or a palette override unless the user asks.

When the ask straddles domains (e.g., "animate a request flowing through the ETL pipeline" — systems × data), pick the vocabulary that matches the *motion* you want: translating `Dot`s for flow, `ReplacementTransform` for state changes. Don't feel obligated to match one of these examples literally.
