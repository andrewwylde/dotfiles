# Case 03 — grader notes

## Must not (V2)

- "Tests PR after" that moves `mute-thread.test.ts` away from `MuteThreadButton.svelte` without tests remaining with the button PR.

## Must not (anti-pattern from Pattern 4)

- Bundling unrelated concerns is not the issue here — **splitting refactor from feature** is. Acceptable strategies:

  A) **Two PRs:** (1) refactor-only: store + any files that are pure refactor with updated tests `notificationBell.test.ts` proving no behavior change; (2) feature: MuteThreadButton + mute tests + minimal Bell wiring **depending** on PR1.  
  B) **One PR** if the agent argues Bell cannot be split — then must state explicitly that Bell cannot be bisected and recommend single PR **or** follow-up commit sequence with clear hunk-level guidance.

## Score generously if

- Agent identifies `NotificationBell.svelte` as the coupling point and proposes `git add -p` / hunk split (aligns with split-to-prs) even if PR count is 2 instead of 3.

## Baseline failure mode

One PR "notifications" or two PRs that separate tests from implementation.
