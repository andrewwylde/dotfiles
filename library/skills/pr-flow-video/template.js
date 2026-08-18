/**
 * Template: capture per-flow videos of a PR's user-facing changes.
 *
 * Copy to /tmp/pr-flow-video-<NUMBER>.js, fill in the flow functions, then run via:
 *
 *   PORT=<webapp-port> PR_NUMBER=<n> \
 *     cd ~/.claude/skills/playwright-skill && node run.js /tmp/pr-flow-video-<n>.js
 *
 * Each flow gets its own browser context so its .webm video is independent.
 * Videos land under ~/.agent/videos/pr-<n>/<flow-name>/<flow-name>.webm.
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const os = require('os');

// ---------------------------------------------------------------------------
// Config (override via env when running the script)
// ---------------------------------------------------------------------------

const PORT = process.env.PORT || '25223';
const PR_NUMBER = process.env.PR_NUMBER || 'tbd';
const TENANT_BASE =
  process.env.TENANT_BASE || `https://acme-corp.local.parable.work:${PORT}`;
// Landing URL the flows open by default. Override per flow if needed.
const DEFAULT_URL =
  process.env.TARGET_URL || `${TENANT_BASE}/early-access/previews/time-spend`;
const DEV_USER = process.env.DEV_USER || 'Sarah Administrator';
const OUT_DIR = path.join(os.homedir(), '.agent/videos', `pr-${PR_NUMBER}`);

// ---------------------------------------------------------------------------
// Parable dev-login (comment out for non-Parable projects)
// ---------------------------------------------------------------------------

const { devLogin, dismissDevPanel } = require(path.join(
  os.homedir(),
  '.agent/scripts/parable/dev-login.js'
));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Open a new browser context that records video to its own subdir. */
async function newRecordingContext(browser, flowName) {
  const videoDir = path.join(OUT_DIR, flowName);
  fs.mkdirSync(videoDir, { recursive: true });
  const ctx = await browser.newContext({
    ignoreHTTPSErrors: true,
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: videoDir, size: { width: 1440, height: 900 } },
  });
  return { ctx, videoDir };
}

/** Close the context and rename its video to the flow name. */
async function renameVideoIfAny(page, ctx, videoDir, flowName) {
  const video = page.video();
  await ctx.close();
  if (!video) return null;
  const src = await video.path().catch(() => null);
  if (!src || !fs.existsSync(src)) return null;
  const dst = path.join(videoDir, `${flowName}.webm`);
  try {
    fs.renameSync(src, dst);
  } catch {}
  return dst;
}

/**
 * Wait up to 60s for at least one rendered donut segment to appear.
 * Returns the count. Writes a debug screenshot on timeout.
 */
async function waitForSegments(page, videoDir, flowName) {
  await page
    .locator('svg.donut-chart-svg')
    .first()
    .waitFor({ state: 'visible', timeout: 30000 })
    .catch(() => {});
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    const n = await page.locator('path.segment').count();
    if (n > 0) return n;
    await page.waitForTimeout(500);
  }
  await page.screenshot({
    path: path.join(videoDir, `${flowName}-no-segments.png`),
    fullPage: true,
  });
  return 0;
}

/** Log in + navigate to the default URL + wait for donut. */
async function loginAndLoad(page, videoDir, flowName, url = DEFAULT_URL) {
  await devLogin(page, url, DEV_USER);
  if (!page.url().includes(new URL(url).pathname)) {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 20000 });
  }
  await dismissDevPanel(page);
  await page.screenshot({
    path: path.join(videoDir, `${flowName}-landing.png`),
  });
  return waitForSegments(page, videoDir, flowName);
}

/**
 * Double-click that works for d3-rendered SVG segments.
 * `locator.dblclick()` fails with "parent SVG intercepts pointer events"
 * on d3 charts because d3 registers handlers via .on() on elements that
 * pass Playwright's actionability hit-test to their parent.
 */
async function dispatchDblClick(locator) {
  return locator.dispatchEvent('dblclick');
}

/**
 * Warmup: open a throwaway context, load the URL, close. This pre-resolves
 * Vite module graph so the first *real* recording doesn't capture a
 * loading/fallback state.
 */
async function warmup(browser, url = DEFAULT_URL) {
  const ctx = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await ctx.newPage();
  await devLogin(page, url, DEV_USER);
  await page.waitForTimeout(5000);
  await ctx.close();
}

// ---------------------------------------------------------------------------
// Flow definitions -- fill these in per PR
// ---------------------------------------------------------------------------

async function flow1_example(browser) {
  const flowName = '01-example';
  console.log(`\n[${flowName}] start`);
  const { ctx, videoDir } = await newRecordingContext(browser, flowName);
  const page = await ctx.newPage();

  const n = await loginAndLoad(page, videoDir, flowName);
  if (n === 0) return renameVideoIfAny(page, ctx, videoDir, flowName);

  // --- your flow steps here ---
  // e.g. drill into L2, then collapse:
  // const segments = page.locator('path.segment');
  // await dispatchDblClick(segments.first());
  // await page.waitForTimeout(2000);
  // await dispatchDblClick(segments.first());
  // await page.waitForTimeout(2500);

  return renameVideoIfAny(page, ctx, videoDir, flowName);
}

// Example: verify a Download button doesn't open the OS file picker.
// Shows the pattern for downloading + asserting-no-picker.
async function flow_download_example(browser) {
  const flowName = '02-download-no-picker';
  console.log(`\n[${flowName}] start`);
  const { ctx, videoDir } = await newRecordingContext(browser, flowName);
  const page = await ctx.newPage();

  await loginAndLoad(page, videoDir, flowName);

  const downloadPromise = page
    .waitForEvent('download', { timeout: 15000 })
    .catch(() => null);
  let pickerFired = false;
  page.on('filechooser', () => {
    pickerFired = true;
    console.log('  !! filechooser event fired — regression detected');
  });

  // Click the target button. Adjust selector per flow.
  const btn = page.getByRole('button', { name: /download template/i });
  await btn.waitFor({ state: 'visible', timeout: 10000 });
  await btn.click();

  const download = await downloadPromise;
  if (download) {
    const savedTo = path.join(videoDir, 'downloaded-file');
    await download.saveAs(savedTo).catch(() => {});
    console.log(`  download saved -> ${savedTo}`);
  }
  await page.waitForTimeout(1500);
  console.log(pickerFired ? '  FAIL: picker fired' : '  PASS: no picker');

  return renameVideoIfAny(page, ctx, videoDir, flowName);
}

// ---------------------------------------------------------------------------
// Entrypoint
// ---------------------------------------------------------------------------

(async () => {
  console.log(`Output dir: ${OUT_DIR}`);
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: false, slowMo: 80 });
  const results = [];
  try {
    await warmup(browser);

    // Add your flows here in order:
    results.push(await flow1_example(browser));
    results.push(await flow_download_example(browser));
  } catch (err) {
    console.error('ERROR:', err.message);
  } finally {
    await browser.close();
  }

  console.log('\n=== Video artifacts ===');
  for (const v of results) {
    console.log('  -', v || '(no video)');
  }
  console.log(`\nAll videos under: ${OUT_DIR}`);
})();
