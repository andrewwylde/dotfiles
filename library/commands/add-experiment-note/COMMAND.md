# add-experiment-note

Add a self-contained HTML page to the andrew-experiments notes site and deploy it.

## Usage

```
/add-experiment-note <topic or description>
```

The argument is a free-form description of what the note should contain. Examples:
- `/add-experiment-note analysis of connector latency patterns`
- `/add-experiment-note summary of this week's auth refactor decisions`
- `/add-experiment-note thoughts on moving to event-driven ingestion`

## AI Execution Steps

When this command is invoked, perform these steps in order:

### 1. Determine Content

Read the argument to understand what the note is about. If the conversation has relevant context (e.g., a recent analysis, investigation, or discussion), use it as source material. If the argument is vague, ask one clarifying question before proceeding.

Content types this skill handles:
- **Analysis** — data-driven investigation with findings
- **Summary** — concise recap of a project, decision, or event
- **Thought** — exploratory thinking, proposals, or design notes

### 2. Generate the HTML Page

Create a self-contained HTML file following these rules:

**Typography:** Use `Fraunces` (body) + `Source Code Pro` (mono) to match the existing site. Load via Google Fonts CDN.

**Palette:** Warm paper/ink aesthetic matching the site — cream background `#faf8f4`, muted greens and blues for accents. Support both light and dark mode via `prefers-color-scheme`.

**CSS variables (copy exactly):**
```css
:root {
  --font-body: 'Fraunces', Georgia, serif;
  --font-mono: 'Source Code Pro', monospace;
  --bg: #faf8f4;
  --surface: #ffffff;
  --surface2: #f3f0ea;
  --border: rgba(0,0,0,0.07);
  --text: #2c2a25;
  --text-dim: #7c7568;
  --accent: #1a6b5a;
  --accent-dim: rgba(26,107,90,0.07);
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1c1a17;
    --surface: #262320;
    --surface2: #302d29;
    --border: rgba(255,255,255,0.06);
    --text: #ede8df;
    --text-dim: #a69e90;
    --accent: #6ee7b7;
    --accent-dim: rgba(110,231,183,0.1);
  }
}
```

**Structure requirements:**
- Single self-contained `.html` file — no external assets except Google Fonts CDN
- Include a header with the note title, date (`YYYY-MM-DD`), and author
- Include a "back to index" link: `<a href="/">← Back to index</a>`
- Use visual elements (cards, tables, diagrams, callouts) over walls of text
- If Mermaid diagrams are appropriate, include them with the full zoom/pan controls from the visual-explainer skill
- Staggered fade-in animations with `prefers-reduced-motion` respect
- Responsive — must work on mobile

**Filename:** Derive from the topic. Use lowercase kebab-case. Prefix with the date: `2026-04-04-connector-latency-analysis.html`

### 3. Write to Site Directory

Write the HTML file to `~/parable-notes/site/`.

### 4. Update the Index Page

Read `~/parable-notes/site/index.html` and add the new page to the appropriate section. If no section fits, add a new one. Each entry follows this format:

```html
<li>
  <a href="filename.html">Page Title</a>
  <div class="meta">One-line description</div>
</li>
```

### 5. Build and Deploy

Run these commands in sequence:

```bash
cd ~/parable-notes && \
docker build --platform linux/amd64 \
  -t us-east1-docker.pkg.dev/parable-development/parable-notes/site:latest . && \
docker push us-east1-docker.pkg.dev/parable-development/parable-notes/site:latest && \
gcloud run deploy andrew-experiments \
  --project=parable-development \
  --region=us-east1 \
  --image=us-east1-docker.pkg.dev/parable-development/parable-notes/site:latest \
  --quiet
```

### 6. Confirm

After deployment, report:
- The page filename and title
- The live URL: `https://andrew-experiments-1075379232366.us-east1.run.app/<filename>`
- Remind the user that IAP auth means they need to be signed in with their `@askparable.com` account

## Notes

- The site is hosted on Cloud Run in `parable-development` with IAP enabled
- All Parable project owners have access automatically
- The Artifact Registry repo is `parable-notes` in `us-east1`
- Local project files live at `~/parable-notes/`
- If Docker is not running, tell the user to start Docker Desktop and retry
- If the visual-explainer skill is available, you may use its templates and CSS patterns for richer pages — but the page MUST use the Fraunces + Source Code Pro font pairing and the warm palette defined above for visual consistency with the rest of the site
