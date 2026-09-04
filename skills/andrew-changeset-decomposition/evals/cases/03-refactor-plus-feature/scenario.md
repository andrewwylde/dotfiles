# Scenario 03 — refactor plus feature (same area)

**User message:**

---

This branch mixes a refactor and a new feature in the same feature folder. How should I split PRs?

Files:

```
M  apps/web-app/src/lib/domains/notifications/NotificationBell.svelte
M  apps/web-app/src/lib/domains/notifications/notificationStore.ts
A  apps/web-app/src/lib/domains/notifications/MuteThreadButton.svelte
A  apps/web-app/src/lib/domains/notifications/mute-thread.test.ts
M  apps/web-app/src/lib/domains/notifications/notificationBell.test.ts
```

Assume from code review notes (trust this):

- `notificationStore.ts` was refactored to extract pure selectors (no user-visible behavior change intended).
- `MuteThreadButton.svelte` and `mute-thread.test.ts` add a new mute action that calls the **new** selector API introduced in the refactor.
- `NotificationBell.svelte` has both: import path updates for refactor **and** wiring for the new mute button.

---
