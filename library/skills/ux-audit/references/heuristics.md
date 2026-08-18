# UX Audit Heuristics

Evaluation criteria organized by category. Use this as a checklist when analyzing audit results and screenshots.

## Interaction Patterns

These assess whether the interface communicates clearly and responds predictably.

### Affordance and discoverability

- **Buttons look clickable.** They have contrast, shape, or visual weight that distinguishes them from static text. Ghost buttons with low contrast are a common failure here.
- **Links are identifiable.** Underlined, colored, or otherwise visually distinct from body text. Link text is descriptive (not "click here").
- **Interactive elements have hover/active states.** Cursor changes on hover. There's visual feedback on click/tap. Elements that look interactive but aren't are a serious issue.
- **Navigation is predictable.** Users can tell where they are, where they can go, and how to get back. Breadcrumbs, active nav states, and clear hierarchy help.

### Forms and input

- **Labels are visible and associated.** Every input has a visible label (not just placeholder text, which disappears on focus). Labels are programmatically associated via `for`/`id`.
- **Error messages are specific and near the problem.** "Something went wrong" is useless. "Email must include @" next to the email field is useful.
- **Required fields are marked.** Before submission, not after.
- **Input types match the data.** Email fields use `type="email"`, phone uses `type="tel"`, etc. This affects mobile keyboard and autocomplete.

### Feedback and state

- **Actions produce visible feedback.** Button clicks, form submissions, and navigation all produce a response. No silent failures.
- **Loading states are communicated.** Spinners, skeleton screens, or progress indicators for anything that takes more than ~200ms.
- **Destructive actions require confirmation.** Delete, cancel, or irreversible operations have a confirmation step or undo mechanism.
- **Empty states are helpful.** When there's no data, the page explains why and suggests a next action — not just a blank area.

### Touch and mobile

- **Tap targets are at least 44x44px.** This is the minimum recommended by both Apple and Google. Check the audit data for undersized targets.
- **No horizontal scroll on mobile.** Content fits the viewport. Tables or wide elements have horizontal scroll containers, not page-level overflow.
- **Critical actions are thumb-reachable.** Primary CTAs aren't buried at the top of the screen on mobile.

---

## Performance Perception

These assess how fast the page *feels*, which is distinct from how fast it actually loads. A 3-second load that shows content progressively feels faster than a 2-second load that shows nothing until it's done.

### First impression speed

- **FCP under 1.8s is good, under 1s is excellent.** First Contentful Paint tells you when the user first sees something. Over 3s is a problem.
- **TTFB under 600ms.** Time to First Byte reflects server response time. Over 1s suggests server-side issues.
- **Above-the-fold content loads first.** Look at the desktop viewport screenshot — is meaningful content visible, or is it waiting for below-fold resources?

### Layout stability

- **CLS should be minimal.** Elements shouldn't jump around as the page loads. Common causes: images without dimensions, late-loading fonts, injected content above existing content.
- **Font loading doesn't cause flash.** Text should be readable immediately — either via `font-display: swap` with a good fallback, or preloaded fonts.

### Resource weight

- **Total transfer under 2MB is reasonable.** Over 5MB is heavy, especially on mobile.
- **Resource count under 80 is typical.** Over 150 suggests missing bundling or excessive third-party scripts.
- **Images are appropriately sized.** Serving a 4000px-wide image in a 400px container is waste.

### Perceived responsiveness

- **Interactions feel instant.** Clicks, hovers, and keypresses should produce feedback within 100ms.
- **Progressive loading over blank screens.** Skeleton screens, placeholder content, or gradual reveal are better than a blank page followed by everything at once.
- **No janky scrolling.** Scroll should be smooth. Heavy scroll handlers, fixed backgrounds with `background-attachment: fixed`, or unoptimized animations cause jank.

---

## Accessibility

These cover both programmatic issues (caught by axe-core) and perceptual issues (caught by looking at the screenshots and keyboard nav data).

### Keyboard navigation

- **All interactive elements are reachable by Tab.** If you can click it, you should be able to Tab to it.
- **Focus is visible.** Every focused element must have a clear visual indicator — outline, ring, color change. The audit captures focus screenshots; look at them. Invisible focus is a critical issue.
- **No tab traps.** Focus should never get stuck in a component with no way to Tab out. The audit tests for this automatically.
- **Focus order matches visual order.** Tab should move through the page in a logical sequence, not jump around randomly.
- **Skip link is present.** A "Skip to main content" link (visible on focus) lets keyboard users bypass repetitive navigation.

### Screen reader compatibility

- **Semantic HTML is used.** `<nav>`, `<main>`, `<header>`, `<footer>`, `<article>`, `<section>` — not everything in `<div>`.
- **Headings form a logical hierarchy.** `h1` → `h2` → `h3`, not skipping levels. Only one `h1` per page. The audit captures heading structure.
- **Images have alt text.** The audit reports images without `alt` attributes. Decorative images should have `alt=""`, meaningful images need descriptive alt.
- **ARIA is used correctly (or not at all).** Bad ARIA is worse than no ARIA. Check axe-core results for ARIA violations.

### Visual accessibility

- **Text contrast ratio meets WCAG AA.** 4.5:1 for normal text, 3:1 for large text. Axe-core catches many contrast issues, but check light-on-light or dark-on-dark patterns in screenshots.
- **Content is readable at default text size.** Body text should be at least 16px. Don't rely on users zooming.
- **Color is not the only indicator.** Error states, status indicators, and required fields need more than just a color change — add icons, text, or patterns.
- **`lang` attribute is set.** The `<html>` element should have a `lang` attribute. The audit captures this.

### Axe-core violations

Axe-core reports violations with impact levels. Map them to audit severity:

| Axe impact | Audit severity |
|-----------|---------------|
| critical | Critical |
| serious | Major |
| moderate | Minor |
| minor | Minor |

Group related violations together rather than listing each node separately. For violations affecting many nodes (e.g., 20 images missing alt text), describe the pattern and give the count — don't enumerate all 20.
