# Examples

## Epic execution map

User: "Check gap analysis current state, dependencies, and re-render the execution map."

1. Reuse `~/.agent/reviews/PARABLE-2685/gap-analysis.md` if same-day; re-verify Linear, GitHub, and `origin/main`.
2. Classify: 2686/2938/2699-C2 `done`; 2699-C1 and 2939 `review`; 2701/2708 `blocked` on C1; 2700 `coordinate`; 2696/2697/337 `external`.
3. Soft-edge 2985 → 2699 (Linear only). Hard-edge 2985 → 2708 only if the generator recomputes the predicate.
4. Overwrite `canvases/parable-2685-execution-map.canvas.tsx`. Default-select `2699`.
5. Chat: next merge is #5841; after it lands, dispatch 2701 and fixture-only 2708.

## Stacked PRs as one node

User: "Show the TSX stack."

One node `PARABLE-2939` with `statusLabel: "3 PRs open"` and links to #5815, #5816, #5817. Explode into three nodes only if the user asks to sequence the stack layers.

## Unblocked-next question

User: "Which features are unblocked?"

Do not redraw unless asked. Answer from the last verified canvas: in-flight `review` first, then `start` nodes whose hard edges are `done`.
