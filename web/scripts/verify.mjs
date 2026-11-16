#!/usr/bin/env node
/**
 * SIDE / CHIPS — local browser verification.
 *
 * Serves web/dist from an in-process Node static server, drives Playwright's
 * **WebKit** engine in headless mode (never Firefox/Chrome, never headed), and
 * checks the behaviour + accessibility of the prototype.
 *
 *   npm run build && npm run verify
 *
 * Playwright is pinned to 1.61.1 rather than 1.65.x on purpose: on macOS 14
 * ("mac14-arm64") Playwright >= 1.62 installs the WebKit "special" build 2251
 * but then sends the `Page.overrideSetting: PushAPIEnabled` protocol command,
 * which that build rejects — every `newPage()` fails with
 * "Protocol error (Page.overrideSetting): Unknown setting: PushAPIEnabled".
 * 1.61.x is the newest release that still uses the same mac14 build without
 * that command. Revisit when Playwright ships a mac14-compatible WebKit.
 *
 * Exit code: 0 when all behaviour checks pass. axe-core violations are
 * reported but do not fail the run (they are for triage).
 */
import http from 'node:http';
import { mkdir, readFile, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { webkit } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import axe from 'axe-core';
import { movementRuns } from '../src/lib/movement.mjs';
import { iso2For } from '../src/lib/iso.mjs';
import {
  FLAG_COUNT,
  TOP15_COUNT,
  methodFlagIso3s,
  topByScoreIso3s,
} from '../src/lib/flags.mjs';

const WEB_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DIST = path.join(WEB_ROOT, 'dist');
const OUT = path.join(WEB_ROOT, '.verify');

// The same generated payload the site built from (prebuild copies it to src/).
const CHIPS = JSON.parse(
  await readFile(path.join(WEB_ROOT, 'src', 'data', '2026', 'chips.json'), 'utf8'),
);
const OVERVIEW = JSON.parse(
  await readFile(path.join(WEB_ROOT, 'src', 'data', 'overview.json'), 'utf8'),
);

/**
 * Pane 5 encodes score and the payload carries one block per scaling method,
 * so every expectation below is read from the method being checked.
 */
const DEFAULT_METHOD = OVERVIEW.meta.defaultMethod;
const METHOD_IDS = OVERVIEW.meta.methods ?? Object.keys(OVERVIEW.methods);
const OTHER_METHOD = METHOD_IDS.find((id) => id !== DEFAULT_METHOD);
const block = (id) => OVERVIEW.methods[id];
const countryIn = (id, iso3) =>
  block(id).field.values.find((row) => row.iso3 === iso3);
const scoreText = (value) => (value * 100).toFixed(2);

/**
 * Panes 1, 7 and 8 draw the top 10 by score as flags; pane 2 draws all 15.
 * Every expectation is recomputed here from the payload rather than written
 * down, so a different method (or edition) is checked against its own scores.
 */
const topFlagIso3s = (methodId) =>
  topByScoreIso3s(block(methodId).field.values, FLAG_COUNT);

/** Every flag one method's panes can draw: the page sprite's per-method share. */
const methodFlags = (methodId) =>
  methodFlagIso3s(block(methodId).field.values, block(methodId).top15);

/** Pane 2's rows, in rank order, as the export lists them. */
const top15Iso3s = (methodId) =>
  [...block(methodId).top15].sort((a, b) => a.rank - b.rank).map((row) => row.iso3);

/** Score delta across the movement window, in points, from the payload. */
function scoreDelta(methodId, iso3, years) {
  const country = block(methodId).movement.countries.find((row) => row.iso3 === iso3);
  if (!country) return null;
  const present = years
    .map((year) => country.scores?.[String(year)])
    .filter((value) => Number.isFinite(value));
  if (present.length < 2) return null;
  return (present[present.length - 1] - present[0]) * 100;
}

/** The exporter's sub-pillar rank for one country, or null. */
function jsonSubPillar(method, iso3, key) {
  const row = CHIPS.methods[method]?.scores.find((item) => item.iso3 === iso3);
  return row?.subPillars[key] ?? null;
}

/** Denominator beside the exporter's rank: countries where it is present. */
function jsonSubPillarOf(method, key) {
  return CHIPS.methods[method].scores.filter(
    (row) =>
      row.subPillars[key]?.status === 'present' && row.subPillars[key]?.score !== null,
  ).length;
}

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.webp': 'image/webp',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ico': 'image/x-icon',
  '.txt': 'text/plain; charset=utf-8',
};

/* ------------------------------------------------------------------ server */

async function startServer(root) {
  const server = http.createServer(async (req, res) => {
    let pathname;
    try {
      pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    } catch {
      res.writeHead(400).end('Bad request');
      return;
    }

    const file = path.resolve(root, `.${pathname}`);
    // Never serve outside dist/.
    if (file !== root && !file.startsWith(root + path.sep)) {
      res.writeHead(403).end('Forbidden');
      return;
    }

    try {
      let target = file;
      const info = await stat(target).catch(() => null);
      if (!info) {
        target = path.join(file, 'index.html'); // /country/IND/ -> index.html
      } else if (info.isDirectory()) {
        target = path.join(file, 'index.html');
      }
      const body = await readFile(target);
      res.writeHead(200, {
        'content-type': MIME[path.extname(target).toLowerCase()] ?? 'application/octet-stream',
        'cache-control': 'no-store',
      });
      res.end(body);
    } catch {
      res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' }).end('Not found');
    }
  });

  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const { port } = server.address();
  return {
    base: `http://127.0.0.1:${port}`,
    close: () =>
      new Promise((resolve) => {
        server.closeAllConnections?.();
        server.close(() => resolve());
      }),
  };
}

/* ------------------------------------------------------------------ checks */

const checks = [];
function record(name, ok, detail = '') {
  checks.push({ name, ok, detail });
  return ok;
}
async function check(name, fn) {
  try {
    const detail = await fn();
    return record(name, true, detail ?? '');
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return record(name, false, message);
  }
}
function expect(cond, message) {
  if (!cond) throw new Error(message);
}
function expectEqual(actual, expected, label) {
  if (actual !== expected) throw new Error(`${label}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}
function expectMatch(actual, pattern, label) {
  if (!pattern.test(actual)) throw new Error(`${label}: ${JSON.stringify(actual)} does not match ${pattern}`);
}

const num = (text) => Number(String(text).trim().replace(/[^\d.+-]/g, ''));

/* -------------------------------------------------------------------- main */

if (!(await stat(DIST).catch(() => null))) {
  console.error('✗ web/dist is missing.');
  console.error('  Run `npm run build` in web/ first, then re-run `npm run verify`.');
  process.exit(1);
}

await mkdir(OUT, { recursive: true });

const server = await startServer(DIST);
const browser = await webkit.launch({ headless: true });
const engineVersion = browser.version();
const shots = [];
let mobilePage = null;
let narrowPage = null;
let axeReport = [];
let tabTrace = [];

const desktopViewport = { width: 1400, height: 1000 };
const mobileViewport = { width: 390, height: 844 };

async function newPage(viewport) {
  // axe-core/playwright needs a real BrowserContext; browser.newPage()'s
  // implicit context is rejected by AxeBuilder.analyze().
  const context = await browser.newContext({ viewport, deviceScaleFactor: 1 });
  const page = await context.newPage();
  page.setDefaultTimeout(15_000);
  return page;
}
const settle = (page) => page.evaluate(async () => {
  await document.fonts.ready;
  // Wait out the 180ms pane entry animation so screenshots are not captured
  // mid-fade. A fixed wait rather than animation promises: some transitions run
  // indefinitely and awaiting them never resolves.
  await new Promise((r) => setTimeout(r, 240));
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
});
async function shot(page, name, fullPage) {
  const file = path.join(OUT, name);
  await page.evaluate(() => {
    const html = document.documentElement;
    const previous = html.style.scrollBehavior;
    html.style.scrollBehavior = 'auto';
    window.scrollTo(0, 0);
    html.style.scrollBehavior = previous;
  });
  await settle(page);
  await page.screenshot({ path: file, fullPage });
  const bytes = (await stat(file)).size;
  shots.push({ name, bytes });
  return name;
}

const rowsOf = (page) => page.locator('table tbody tr');
const saudiRow = (page) => page.locator('table tbody tr', { hasText: 'Saudi Arabia' });
const liveRegion = (page) =>
  page.locator('section[aria-labelledby="rankings-heading"] [aria-live]');

try {
  /* -------------------------------------------------------- desktop: overview */
  const overview = await newPage(desktopViewport);
  await overview.goto(`${server.base}/`, { waitUntil: 'load' });
  await settle(overview);

  const pane = (n) => overview.locator(`[data-pane="${n}"]`);
  const livePane = () =>
    overview.locator('[data-pane]:not([hidden])').getAttribute('data-pane');
  const counterText = () =>
    overview.locator('.carousel__count').innerText().then((text) => text.trim());
  const announcement = () =>
    overview.locator('.carousel [aria-live]').innerText().then((text) => text.trim());
  const waitPane = (n) =>
    overview.waitForFunction(
      (number) =>
        document.querySelector(`[data-pane="${number}"]`)?.hasAttribute('hidden') === false,
      n,
    );

  await check('/ renders 8 carousel panes, exactly one visible', async () => {
    const total = await overview.locator('[data-pane]').count();
    expectEqual(total, 8, 'pane count');
    const visible = await overview.locator('[data-pane]:not([hidden])').count();
    expectEqual(visible, 1, 'visible panes');
    expectEqual(await livePane(), '1', 'visible pane');
    expectEqual(await counterText(), '1 / 8', 'counter');
    return '8 panes in the DOM, pane 1 visible';
  });

  await check('carousel is a labelled group with a roledescription', async () => {
    const group = overview.locator('[aria-roledescription="carousel"]');
    await group.waitFor();
    const label = await group.getAttribute('aria-label');
    expect(label && label.length > 8, `missing aria-label: ${label}`);
    return `role=group, "${label}"`;
  });

  await check('pane 1: 61 dots + 10 flags, India marked, median tick', async () => {
    const flagged = topFlagIso3s(DEFAULT_METHOD).length;
    const dots = await pane(1).locator('circle[data-dot]').count();
    const flags = await pane(1).locator('.flag-mark').count();
    expectEqual(dots, 71 - flagged, 'field dots');
    expectEqual(flags, flagged, 'field flags');
    expectEqual(await pane(1).locator('[data-field]').count(), 71, 'every country marked');
    expectEqual(await pane(1).locator('.field-chart__ring').count(), 1, 'India marks');
    expectEqual(await pane(1).locator('.field-chart__median').count(), 1, 'median tick');
    const label = await pane(1).locator('.field-chart').getAttribute('aria-label');
    expectMatch(label, /71 CHIPS scores/, 'chart label');
    expectMatch(label, /India is 3rd/, 'India in chart label');
    return `${dots} dots, ${flags} flags, 1 India mark, median tick; "${label.slice(0, 60)}…"`;
  });

  await check('pane 1 has a View as table fallback with 71 rows', async () => {
    const details = pane(1).locator('details[data-pane-table]');
    expectEqual(await details.count(), 1, 'details count');
    expectMatch((await details.locator('summary').innerText()).trim(), /View as table/, 'summary');
    const rows = await pane(1).locator('table tbody tr').count();
    expectEqual(rows, 71, 'table rows');
    await details.locator('summary').click();
    expectEqual(await details.getAttribute('open'), '', 'disclosure open');
    const first = (await pane(1).locator('table tbody tr').first().innerText()).replace(/\s+/g, ' ');
    const usa = countryIn(DEFAULT_METHOD, 'USA');
    expectMatch(first, new RegExp(`1 USA ${scoreText(usa.score).replace('.', '\\.')}`), 'first row');
    await details.locator('summary').click();
    expectEqual(await details.getAttribute('open'), null, 'disclosure closed again');
    return `71 table rows; opened and closed the disclosure; first row ${first}`;
  });

  await check('overview defaults to z-score: pane 1 USA at 80.91', async () => {
    expectEqual(DEFAULT_METHOD, 'z', 'payload default method');
    const checked = await overview
      .locator('input[name="overview-scale"]:checked')
      .inputValue();
    expectEqual(checked, DEFAULT_METHOD, 'checked scale');
    expect(
      !overview.url().includes('scale='),
      `URL should not carry scale= by default: ${overview.url()}`,
    );
    // USA is rank 1, so it is a flag now; the score hook is the same.
    const mark = Number(await pane(1).locator('[data-field="USA"]').getAttribute('data-score'));
    expectEqual(scoreText(mark), '80.91', 'pane 1 USA mark score');
    return `z active, no ?scale; USA mark ${scoreText(mark)}`;
  });

  await check('scale toggle: pane 1 USA 80.91 → 67.27 → 80.91', async () => {
    await overview.getByRole('radio', { name: 'Min–max' }).check();
    await settle(overview);
    expectMatch(overview.url(), /[?&]scale=minmax(&|$)/, 'URL after toggle');
    const minmax = Number(
      await pane(1).locator('[data-field="USA"]').getAttribute('data-score'),
    );
    expectEqual(scoreText(minmax), '67.27', 'pane 1 USA under min–max');

    await overview.getByRole('radio', { name: 'Z-score' }).check();
    await settle(overview);
    expect(!overview.url().includes('scale='), `scale=z should normalise away: ${overview.url()}`);
    const back = Number(
      await pane(1).locator('[data-field="USA"]').getAttribute('data-score'),
    );
    expectEqual(scoreText(back), '80.91', 'pane 1 USA back under z');
    return '80.91 → 67.27 → 80.91; ?scale=minmax appears then drops';
  });

  const spanText = (methodId) => {
    const top15 = [...block(methodId).top15].sort((a, b) => a.rank - b.rank);
    return `Places 4–13 span ${scoreText(top15[3].score)} → ${scoreText(top15[12].score)}`;
  };
  const indiaRankOf = (methodId, pillar) =>
    block(methodId).india.pillars.find((item) => item.id === pillar).rank;
  const rhoText = (methodId) =>
    `ρ Spearman ${block(methodId).correlation.spearman.toFixed(4)}`;
  const highlighted = async () =>
    (
      await overview
        .locator('[data-dumbbell][data-highlighted="true"]')
        .evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-dumbbell')))
    )
      .sort()
      .join(',');

  await check('scale toggle re-scores panes 2, 4, 5 and 7 together', async () => {
    await overview.goto(`${server.base}/`, { waitUntil: 'load' });
    await settle(overview);

    const read = async () => ({
      zSpan: (await pane(2).locator('.pane__caption').textContent()).replace(/\s+/g, ' '),
      zSust: await pane(4)
        .locator('[data-verdict="SUSTAINABILITY"] .verdict__rank-value')
        .getAttribute('data-rank'),
      zRho: (await pane(7).locator('.pane__caption').textContent()).replace(/\s+/g, ' '),
      zDots: await highlighted(),
    });

    const first = await read();
    expectMatch(first.zSpan, new RegExp(spanText(DEFAULT_METHOD)), 'pane 2 span (z)');
    expectEqual(Number(first.zSust), indiaRankOf(DEFAULT_METHOD, 'SUSTAINABILITY'), 'pane 4 SUSTAINABILITY (z)');
    expectMatch(first.zRho, new RegExp(rhoText(DEFAULT_METHOD).replace('.', '\\.')), 'pane 7 ρ (z)');
    expectEqual(Number(first.zSust), 42, 'z SUSTAINABILITY rank');

    await overview.getByRole('radio', { name: 'Min–max' }).check();
    await settle(overview);

    const second = await read();
    expectMatch(second.zSpan, new RegExp(spanText(OTHER_METHOD)), 'pane 2 span (min–max)');
    expectEqual(Number(second.zSust), indiaRankOf(OTHER_METHOD, 'SUSTAINABILITY'), 'pane 4 SUSTAINABILITY (min–max)');
    expectMatch(second.zRho, new RegExp(rhoText(OTHER_METHOD).replace('.', '\\.')), 'pane 7 ρ (min–max)');
    expectEqual(Number(second.zSust), 66, 'min–max SUSTAINABILITY rank');
    expect(second.zDots !== first.zDots, `pane 5 highlight set did not change: ${first.zDots}`);

    expect(first.zSpan !== second.zSpan, 'pane 2 span text unchanged');
    expect(first.zRho !== second.zRho, 'pane 7 caption unchanged');
    return `span "${spanText(DEFAULT_METHOD)}" → "${spanText(OTHER_METHOD)}"; SUST 42 → 66; ` +
      `ρ ${block(DEFAULT_METHOD).correlation.spearman} → ${block(OTHER_METHOD).correlation.spearman}; ` +
      `highlighted ${first.zDots} → ${second.zDots}`;
  });

  await check('pane 6 is exempt: its numbers do not change with the toggle', async () => {
    const before = {
      headline: (await pane(6).locator('.pane__callout').textContent()).replace(/\s+/g, ' '),
      first: await pane(6).locator('[data-diverge]').first().getAttribute('data-delta'),
      rows: await pane(6).locator('[data-diverge]').count(),
    };
    await overview.getByRole('radio', { name: 'Z-score' }).check();
    await settle(overview);
    const after = {
      headline: (await pane(6).locator('.pane__callout').textContent()).replace(/\s+/g, ' '),
      first: await pane(6).locator('[data-diverge]').first().getAttribute('data-delta'),
      rows: await pane(6).locator('[data-diverge]').count(),
    };
    expectEqual(after.headline, before.headline, 'pane 6 headline');
    expectEqual(after.first, before.first, 'pane 6 largest delta');
    expectEqual(after.rows, before.rows, 'pane 6 row count');
    const caption = (await pane(6).locator('.pane__caption').textContent()).replace(/\s+/g, ' ');
    expectMatch(caption, /always shows both methods/, 'pane 6 caption note');
    return `${before.rows} rows, headline "${before.headline.slice(0, 60)}…" stable; caption notes the exemption`;
  });

  await check('?pane=4&scale=minmax reloads pane 4 open with min–max active', async () => {
    await overview.goto(`${server.base}/?pane=4&scale=minmax`, { waitUntil: 'load' });
    await settle(overview);
    await waitPane(4);
    expectEqual(await livePane(), '4', 'visible pane');
    expectEqual(await counterText(), '4 / 8', 'counter');
    const checked = await overview
      .locator('input[name="overview-scale"]:checked')
      .inputValue();
    expectEqual(checked, OTHER_METHOD, 'checked scale after reload');
    const rank = await pane(4)
      .locator('[data-verdict="SUSTAINABILITY"] .verdict__rank-value')
      .getAttribute('data-rank');
    expectEqual(Number(rank), 66, 'SUSTAINABILITY rank under min–max');
    expectMatch(overview.url(), /pane=4/, 'pane param kept');
    expectMatch(overview.url(), /scale=minmax/, 'scale param kept');
    return 'pane 4 open, min–max active, SUSTAINABILITY 66';
  });

  await overview.goto(`${server.base}/`, { waitUntil: 'load' });
  await settle(overview);
  await shot(overview, 'desktop-overview-z.png', true);

  await overview.getByRole('radio', { name: 'Min–max' }).check();
  await settle(overview);
  await shot(overview, 'desktop-overview-minmax.png', true);

  await check('Next moves to pane 2, writes ?pane=2 and announces it', async () => {
    await overview.getByRole('button', { name: 'Next pane' }).click();
    await waitPane(2);
    expectEqual(await livePane(), '2', 'visible pane');
    expectMatch(overview.url(), /[?&]pane=2(&|$)/, 'URL');
    expectEqual(await counterText(), '2 / 8', 'counter');
    expectEqual(
      await announcement(),
      'Pane 2 of 8: The podium and the pack',
      'live region',
    );
    return `pane 2; ${new URL(overview.url()).search}; "${await announcement()}"`;
  });

  await check('pane 2: 15 lollipop rows, a line and a flag each', async () => {
    const rows = await pane(2).locator('[data-lollipop]').count();
    expectEqual(rows, 15, 'lollipop rows');
    expectEqual(await pane(2).locator('.lollipop__line').count(), 15, 'lines');
    expectEqual(await pane(2).locator('.lollipop__row .flag-mark').count(), 15, 'flags');
    expectEqual(await pane(2).locator('.lollipop__dot').count(), 0, 'tip dots replaced');
    const text = (await pane(2).innerText()).replace(/\s+/g, ' ');
    expectMatch(text, /Places 4–13 span/, 'span annotation');
    return '15 rows, 15 lines, 15 flags; 4–13 annotation present';
  });

  await check('pane 2 has a View as table fallback with 15 rows', async () => {
    const rows = await pane(2).locator('table tbody tr').count();
    expectEqual(rows, 15, 'table rows');
    return '15 table rows';
  });

  await shot(overview, 'desktop-overview-pane2.png', true);

  /* ---------------------------------------------------------- pane 3 */
  await overview.goto(`${server.base}/?pane=3`, { waitUntil: 'load' });
  await settle(overview);
  await waitPane(3);

  await check('pane 3: 10 stacked bars, 5 segments each, matching overview.json', async () => {
    const bars = pane(3).locator('[data-composition-country]');
    expectEqual(await bars.count(), 10, 'bar count');
    expectEqual(await pane(3).locator('rect[data-segment]').count(), 50, 'segment count');

    const top = [...block(DEFAULT_METHOD).composition].sort((a, b) => a.rank - b.rank)[0];
    const row = pane(3).locator(`[data-composition-country="${top.iso3}"]`);
    const contributions = await row
      .locator('rect[data-segment]')
      .evaluateAll((elements) =>
        elements.map((element) => Number(element.getAttribute('data-contribution'))),
      );
    expectEqual(contributions.length, top.pillars.length, 'top bar segments');
    const expected = top.pillars.map((pillar) => pillar.contribution);
    expected.forEach((value, index) => {
      expect(
        Math.abs(contributions[index] - value) <= 1e-6,
        `segment ${index} is ${contributions[index]}, payload has ${value}`,
      );
    });
    const expectedSum = expected.reduce((sum, value) => sum + value, 0);
    const drawnTotal = contributions.reduce((sum, value) => sum + value, 0);
    expect(
      Math.abs(drawnTotal - expectedSum) <= 1e-6,
      `segments sum to ${drawnTotal}, payload sums to ${expectedSum}`,
    );
    const total = Number(await row.getAttribute('data-total'));
    expect(
      Math.abs(total - expectedSum) <= 1e-6,
      `bar total ${total} does not agree with ${expectedSum}`,
    );
    const printed = (await row.locator('.composition__value').innerText()).trim();
    expectEqual(printed, (top.score * 100).toFixed(2), 'printed score');
    expectEqual(
      await pane(3).locator('.composition__legend-item').count(),
      5,
      'legend items',
    );
    return `${top.iso3}: 5 segments, sum ${drawnTotal.toFixed(6)}, printed ${printed}, legend 5`;
  });

  await check('pane 3 has a View as table with 50 country-pillar rows', async () => {
    const top = block(DEFAULT_METHOD).composition[0];
    const rows = await pane(3).locator('table tbody tr').count();
    expectEqual(rows, 50, 'table rows');
    // The disclosure is closed, so read textContent, not rendered innerText.
    const headers = (await pane(3).locator('thead th').allTextContents()).map((text) =>
      text.trim(),
    );
    expectEqual(headers.join('|'), 'Rank|Country|Pillar|Contribution|Score', 'columns');
    const cells = (
      await pane(3).locator('table tbody tr').first().locator('td').allTextContents()
    ).map((text) => text.trim());
    const expectedCells = [
      '1',
      'USA',
      top.pillars[0].id,
      (top.pillars[0].contribution * 100).toFixed(2),
      (top.score * 100).toFixed(2),
    ];
    expectEqual(cells.join('|'), expectedCells.join('|'), 'first row');
    return `50 rows; ${headers.join(' · ')}`;
  });

  await shot(overview, 'desktop-overview-pane3.png', true);

  /* ---------------------------------------------------------- pane 4 */
  await overview.goto(`${server.base}/?pane=4`, { waitUntil: 'load' });
  await settle(overview);
  await waitPane(4);

  await check('pane 4: 5 verdict rows, CONNECT rank 3, SUSTAINABILITY rank 42', async () => {
    const rows = pane(4).locator('[data-verdict]');
    expectEqual(await rows.count(), 5, 'verdict rows');
    expectEqual(
      await pane(4).locator('circle.verdict__dot').count(),
      5 * OVERVIEW.meta.countries,
      'strip dots',
    );

    const marker = (pillar) =>
      pane(4).locator(`[data-verdict="${pillar}"] .verdict__marker`);

    const india = block(DEFAULT_METHOD).india;
    const best = india.best;
    const worst = india.worst;
    const bestText = await pane(4).locator(`[data-verdict="${best.id}"]`).innerText();
    expectEqual(Number(await marker(best.id).getAttribute('data-rank')), best.rank, 'best rank');
    expectMatch(bestText.replace(/\s+/g, ' '), new RegExp(`${best.rank}\\s+of ${OVERVIEW.meta.countries}`), 'best row');

    const worstText = await pane(4).locator(`[data-verdict="${worst.id}"]`).innerText();
    expectEqual(Number(await marker(worst.id).getAttribute('data-rank')), worst.rank, 'worst rank');
    expectMatch(worstText.replace(/\s+/g, ' '), new RegExp(`${worst.rank}\\s+of ${OVERVIEW.meta.countries}`), 'worst row');

    expectEqual(best.id, 'CONNECT', 'strongest pillar id');
    expectEqual(worst.id, 'SUSTAINABILITY', 'weakest pillar id');
    expectEqual(best.rank, 3, 'CONNECT rank under z');
    expectEqual(worst.rank, 42, 'SUSTAINABILITY rank under z');
    return `${best.id} ${best.rank} · ${worst.id} ${worst.rank}; 355 strip dots`;
  });

  await check('pane 4 has a View as table with 5 pillar rows', async () => {
    const rows = await pane(4).locator('table tbody tr').count();
    expectEqual(rows, 5, 'table rows');
    const first = (await pane(4).locator('table tbody tr').first().textContent()).replace(
      /\s+/g,
      ' ',
    );
    return `5 rows; first ${first.trim()}`;
  });

  await shot(overview, 'desktop-overview-pane4.png', true);

  /* ---------------------------------------------------------- pane 5 */
  await overview.goto(`${server.base}/?pane=5`, { waitUntil: 'load' });
  await settle(overview);
  await waitPane(5);

  await check('pane 5: one dumbbell per country, caveat carries the live count', async () => {
    const count = block(DEFAULT_METHOD).movement.countries.length;
    const years = block(DEFAULT_METHOD).movement.years;
    expectEqual(
      await pane(5).locator('[data-dumbbell]').count(),
      count,
      'dumbbell rows',
    );
    const points = await pane(5).locator('[data-dumbbell-point]').count();
    expectEqual(points, count * years.length, 'dumbbell endpoints');

    const caveat = (await pane(5).locator('.movement-chart__caveat').innerText()).replace(
      /\s+/g,
      ' ',
    );
    expectMatch(
      caveat,
      new RegExp(`\\b${count} of ${OVERVIEW.meta.countries} countries`),
      'caveat text',
    );
    expectMatch(caveat, /scored in both editions/, 'caveat editions');

    // The five largest |Δ score|, computed from the same payload the build uses.
    const expected = block(DEFAULT_METHOD).movement.countries
      .map((country) => ({ ...country, delta: scoreDelta(DEFAULT_METHOD, country.iso3, years) }))
      .filter((country) => country.delta !== null)
      .sort(
        (a, b) =>
          Math.abs(b.delta) - Math.abs(a.delta) || a.country.localeCompare(b.country),
      )
      .slice(0, 5)
      .map((country) => country.iso3)
      .sort();
    const actual = (
      await pane(5)
        .locator('[data-dumbbell][data-highlighted="true"]')
        .evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-dumbbell')))
    ).sort();
    expectEqual(actual.join(','), expected.join(','), 'highlighted set (largest |Δ score|)');

    const paneText = (await pane(5).innerText()).replace(/\s+/g, ' ');
    expect(!/Rank 1 is at the top/i.test(paneText), 'rank axis label is still present');
    return `${count} dumbbells, ${points} endpoints; marked ${expected.join(', ')}; ${caveat}`;
  });

  await check('pane 5: a null edition breaks the line (synthetic)', async () => {
    const cases = [
      {
        name: 'gap between two scores',
        years: [2025, 2026, 2027],
        ranks: { 2025: 5, 2026: null, 2027: 9 },
        expected: 0,
      },
      {
        name: 'trailing null',
        years: [2025, 2026, 2027],
        ranks: { 2025: 5, 2026: 6, 2027: null },
        expected: 1,
      },
      {
        name: 'leading null',
        years: [2025, 2026],
        ranks: { 2025: null, 2026: 3 },
        expected: 0,
      },
      {
        name: 'all present, three editions',
        years: [2025, 2026, 2027],
        ranks: { 2025: 5, 2026: 6, 2027: 4 },
        expected: 2,
      },
    ];
    const results = [];
    for (const item of cases) {
      const runs = movementRuns(item.years, item.ranks);
      expectEqual(runs.length, item.expected, item.name);
      for (const run of runs) {
        expect(
          run.fromRank !== null && run.toRank !== null,
          `${item.name}: a segment touches a null`,
        );
        expect(run.toYear > run.fromYear, `${item.name}: year order`);
      }
      results.push(`${item.name} ${runs.length}`);
    }
    return results.join(' · ');
  });

  await check('pane 5 table: score and rank per edition, Δ points and Δ rank', async () => {
    const disclosure = pane(5).locator('details[data-pane-table]');
    await disclosure.locator('summary').click();
    const movement = block(DEFAULT_METHOD).movement;
    const rows = await pane(5).locator('table tbody tr').count();
    expectEqual(rows, movement.countries.length, 'table rows');
    const years = movement.years;
    const headers = (await pane(5).locator('thead th').allTextContents()).map((text) =>
      text.trim(),
    );
    expectEqual(
      headers.join('|'),
      [
        'Country',
        ...years.map((year) => `${year} score`),
        'Δ points',
        ...years.map((year) => `${year} rank`),
        'Δ rank',
      ].join('|'),
      'columns',
    );
    const saudi = movement.countries.find((row) => row.iso3 === 'SAU');
    const firstScore = saudi.scores[String(years[0])];
    const lastScore = saudi.scores[String(years[years.length - 1])];
    const deltaPoints = Math.round((lastScore - firstScore) * 1000) / 10;
    const deltaRank = saudi.ranks[String(years[years.length - 1])] - saudi.ranks[String(years[0])];
    const expected = [
      (firstScore * 100).toFixed(2),
      (lastScore * 100).toFixed(2),
      deltaPoints > 0 ? `+${deltaPoints.toFixed(1)}` : `−${Math.abs(deltaPoints).toFixed(1)}`,
      String(saudi.ranks[String(years[years.length - 1])]),
      deltaRank > 0 ? `+${deltaRank}` : `−${Math.abs(deltaRank)}`,
    ];
    const saudiRow = pane(5).locator('table tbody tr', { hasText: 'Saudi Arabia' });
    const cells = (await saudiRow.locator('td').allInnerTexts()).map((text) => text.trim());
    expectEqual(cells[1], expected[0], 'Saudi first-edition score');
    expectEqual(cells[2], expected[1], 'Saudi last-edition score');
    expectEqual(cells[3], expected[2], 'Saudi Δ points');
    expectEqual(cells[5], expected[3], 'Saudi last-edition rank');
    expectEqual(cells[6], expected[4], 'Saudi Δ rank');
    await disclosure.locator('summary').click();
    return `${rows} rows; ${headers.join(' · ')}; Saudi ${cells.slice(1).join(' / ')}`;
  });

  await shot(overview, 'desktop-overview-pane5.png', true);

  /* ---------------------------------------------------------- pane 6 */
  await overview.goto(`${server.base}/?pane=6`, { waitUntil: 'load' });
  await settle(overview);
  await waitPane(6);

  await check('pane 6: 10 diverging rows, the largest is Saudi Arabia at 19', async () => {
    expectEqual(
      await pane(6).locator('[data-diverge]').count(),
      10,
      'diverging rows',
    );
    const largest = pane(6).locator('[data-diverge]').first();
    expectEqual(await largest.getAttribute('data-diverge'), 'SAU', 'largest row');
    expectEqual(Number(await largest.getAttribute('data-delta')), -19, 'largest delta');
    const text = (await largest.innerText()).replace(/\s+/g, ' ');
    expectMatch(text, /55 → 36/, 'both ranks');
    return `10 rows; largest SAU ${text.trim()}`;
  });

  await check('pane 6 states the 64-of-71 headline in the pane', async () => {
    const text = (await pane(6).innerText()).replace(/\s+/g, ' ');
    expectMatch(text, /64 of 71 countries change rank/, 'headline');
    expectMatch(text, /Saudi Arabia moves 19 places/i, 'largest mover');
    const changed = OVERVIEW.scaleMovement.movers.filter((row) => row.delta !== 0).length;
    expectEqual(changed, 64, 'payload changed count');
    return '64 of 71 · Saudi Arabia moves 19 places';
  });

  await check('pane 6 table: all 71 countries with both ranks and Δ rank', async () => {
    const disclosure = pane(6).locator('details[data-pane-table]');
    await disclosure.locator('summary').click();
    const rows = await pane(6).locator('table tbody tr').count();
    expectEqual(rows, OVERVIEW.scaleMovement.movers.length, 'table rows');
    const headers = (await pane(6).locator('thead th').allTextContents()).map((text) =>
      text.trim(),
    );
    expectMatch(headers.join('|'), /Min–max rank\|Z-score rank\|Δ rank/, 'columns');
    const saudi = pane(6).locator('table tbody tr', { hasText: 'Saudi Arabia' });
    const cells = (await saudi.locator('td').allInnerTexts()).map((text) => text.trim());
    expectEqual(cells.slice(1).join(' / '), '55 / 36 / −19', 'Saudi row');
    await disclosure.locator('summary').click();
    return `${rows} rows; ${headers.join(' · ')}`;
  });

  await shot(overview, 'desktop-overview-pane6.png', true);

  /* ---------------------------------------------------------- pane 7 */
  await overview.goto(`${server.base}/?pane=7`, { waitUntil: 'load' });
  await settle(overview);
  await waitPane(7);

  const xTickNodes = () =>
    pane(7).locator('.scatter-chart--sizeScore text.chart__tick-label');

  await check('pane 7: 71 points on a log GDP axis with magnitude tick labels', async () => {
    expectEqual(await pane(7).locator('[data-scatter]').count(), 71, 'points');
    const texts = (await xTickNodes().allTextContents()).map((text) => text.trim());
    const money = texts.filter((text) => /^\$\d+(?:\.\d+)?(?:bn|tn)$/.test(text));
    expectEqual(money.length, 4, 'GDP tick labels');
    expect(money.includes('$50bn') && money.includes('$5tn'), `unexpected ticks ${texts}`);
    expect(
      !texts.some((text) => /^\d{6,}$/.test(text)),
      `raw numbers used as tick labels: ${texts}`,
    );

    // Equal decade gaps are what a log axis does; a linear axis would not.
    const positions = await xTickNodes().evaluateAll((nodes) =>
      nodes
        .filter((node) => /^\$\d/.test((node.textContent || '').trim()))
        .map((node) => Number.parseFloat(node.getAttribute('x'))),
    );
    const sorted = [...new Set(positions)].sort((a, b) => a - b);
    expectEqual(sorted.length, 4, 'distinct tick positions');
    const gaps = sorted.slice(1).map((value, index) => value - sorted[index]);
    expect(
      Math.abs(gaps[0] - gaps[1]) < 2,
      `tick gaps are not logarithmic: ${JSON.stringify(gaps)}`,
    );
    return `${money.join(' · ')}; gaps ${gaps.map((gap) => gap.toFixed(1)).join('/')}`;
  });

  await check('pane 7 names India, the USA, China and a smaller high scorer', async () => {
    const labels = (
      await pane(7).locator('.scatter-chart--sizeScore text.chart__label').allTextContents()
    ).map((text) => text.trim());
    for (const name of ['India', 'United States', 'China']) {
      expect(labels.includes(name), `${name} is not labelled (${labels.join(', ')})`);
    }
    expect(labels.length >= 4, `expected a fourth label, got ${labels.join(', ')}`);
    return labels.join(' · ');
  });

  await check('pane 7 table: all 71 countries with compact GDP', async () => {
    const disclosure = pane(7).locator('details[data-pane-table]');
    await disclosure.locator('summary').click();
    const rows = await pane(7).locator('table tbody tr').count();
    expectEqual(rows, 71, 'table rows');
    const usa = pane(7).locator('table tbody tr', { hasText: 'United States' });
    const cells = (await usa.locator('td').allInnerTexts()).map((text) => text.trim());
    expectMatch(cells[3], /^\$\d+(?:\.\d+)?(?:bn|tn)$/, 'compact GDP');
    await disclosure.locator('summary').click();
    return `${rows} rows; USA ${cells.slice(0, 4).join(' / ')}`;
  });

  await shot(overview, 'desktop-overview-pane7.png', true);

  /* ---------------------------------------------------------- pane 8 */
  await overview.goto(`${server.base}/?pane=8`, { waitUntil: 'load' });
  await settle(overview);
  await waitPane(8);

  await check('pane 8: 71 points, 9 marked below 80% coverage', async () => {
    expectEqual(await pane(8).locator('[data-scatter]').count(), 71, 'points');
    expectEqual(
      await pane(8).locator('[data-scatter][data-below="true"]').count(),
      9,
      'below-threshold marks',
    );
    const expected = block(DEFAULT_METHOD).coverage.filter((row) => row.coverage < 0.8).length;
    expectEqual(expected, 9, 'payload below-threshold count');
    const text = (await pane(8).innerText()).replace(/\s+/g, ' ');
    expectMatch(text, /9 of 71 countries sit below 80% coverage/, 'callout');
    expectMatch(text, /26 country × sub-pillar cells are unscored/, 'unscored cells');
    return '71 points, 9 marked, 26 unscored cells in the pane';
  });

  await check('pane 8 table: all 71 countries with coverage', async () => {
    const disclosure = pane(8).locator('details[data-pane-table]');
    await disclosure.locator('summary').click();
    const rows = await pane(8).locator('table tbody tr').count();
    expectEqual(rows, 71, 'table rows');
    const headers = (await pane(8).locator('thead th').allInnerTexts()).map((text) =>
      text.trim(),
    );
    expectMatch(headers.join('|'), /Coverage\|Indicators/, 'columns');
    await disclosure.locator('summary').click();
    return `${rows} rows; ${headers.join(' · ')}`;
  });

  await shot(overview, 'desktop-overview-pane8.png', true);

  /* ---------------------------------------------------------- flags */
  const paneMethodUrl = (paneNumber, methodId) =>
    `${server.base}/?pane=${paneNumber}${methodId === DEFAULT_METHOD ? '' : `&scale=${methodId}`}`;

  const openPane = async (paneNumber, methodId) => {
    await overview.goto(paneMethodUrl(paneNumber, methodId), { waitUntil: 'load' });
    await settle(overview);
    await waitPane(paneNumber);
  };

  const flagMarks = (paneNumber) => pane(paneNumber).locator('.flag-mark');
  const flagOrder = (paneNumber) =>
    flagMarks(paneNumber).evaluateAll((nodes) => nodes.map((node) => node.dataset.iso3));

  await check('pane 1: exactly 10 flag marks per method, the top 10, rank 1 last', async () => {
    const details = [];
    for (const methodId of METHOD_IDS) {
      await openPane(1, methodId);
      const expected = topFlagIso3s(methodId);
      expectEqual(await flagMarks(1).count(), 10, `${methodId} flag marks`);
      // Everything below the top 10 stays a dot; every country is still marked.
      expectEqual(await pane(1).locator('circle[data-dot]').count(), 61, `${methodId} dots`);
      expectEqual(await pane(1).locator('[data-field]').count(), 71, `${methodId} marks`);

      const order = await flagOrder(1);
      expectEqual(
        [...order].sort().join(','),
        [...expected].sort().join(','),
        `${methodId} flagged set`,
      );
      // Paint order is document order: rank 10 first, rank 1 last.
      expectEqual(order[0], expected[9], `${methodId} first-painted flag (rank 10)`);
      expectEqual(order[order.length - 1], expected[0], `${methodId} rank 1 is last`);

      const marks = await flagMarks(1).evaluateAll((nodes) =>
        nodes.map((node) => ({
          iso3: node.dataset.iso3,
          label: node.getAttribute('aria-label'),
          tabindex: node.getAttribute('tabindex'),
          title: node.querySelector('title')?.textContent ?? '',
        })),
      );
      for (const mark of marks) {
        const row = countryIn(methodId, mark.iso3);
        const name = row.shortName || row.country;
        expectEqual(mark.label, `${name}, score ${scoreText(row.score)}`, `${mark.iso3} label`);
        expectMatch(mark.label, new RegExp(`^${name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}, score `), `${mark.iso3} name`);
        expectEqual(mark.title, mark.label, `${mark.iso3} <title>`);
        expectEqual(mark.tabindex, '0', `${mark.iso3} tabindex`);
      }
      details.push(`${methodId}: ${expected[0]} on top, ${expected[9]} beneath`);
    }
    return details.join(' · ');
  });

  await check('pane 1: focusing a buried mark reveals its labelled overlay', async () => {
    await openPane(1, DEFAULT_METHOD);
    const expected = topFlagIso3s(DEFAULT_METHOD);
    const buried = expected[9]; // rank 10, painted first, under the stack
    const overlay = pane(1).locator(`.flag-overlay[data-overlay="${buried}"]`);
    const opacity = () =>
      overlay.evaluate((node) => Number(getComputedStyle(node).opacity));
    expectEqual(await opacity(), 0, 'overlay hidden before focus');
    await pane(1).locator(`.flag-mark[data-iso3="${buried}"]`).focus();
    expectEqual(await opacity(), 1, 'overlay opacity after focus');
    const text = (await overlay.textContent()).replace(/\s+/g, ' ').trim();
    const row = countryIn(DEFAULT_METHOD, buried);
    expectEqual(text, `${row.shortName || row.country}, score ${scoreText(row.score)}`, 'overlay text');
    await pane(1).locator(`.flag-mark[data-iso3="${buried}"]`).blur();
    expectEqual(await opacity(), 0, 'overlay hidden again after blur');
    return `rank 10 "${buried}" → "${text}" (opacity 0 → 1 → 0)`;
  });

  await check('pane 2: 15 flags per method, each centred on its stem tip', async () => {
    const details = [];
    for (const methodId of METHOD_IDS) {
      await openPane(2, methodId);
      const expected = top15Iso3s(methodId);
      expectEqual(
        await pane(2).locator('.lollipop__row .flag-mark').count(),
        TOP15_COUNT,
        `${methodId} flags`,
      );
      expectEqual(await pane(2).locator('.lollipop__dot').count(), 0, `${methodId} tip dots`);

      const rows = await pane(2).evaluate(() => {
        const items = [...document.querySelectorAll('[data-lollipop]')];
        return items.map((row) => {
          const track = row.querySelector('.lollipop__track');
          const line = row.querySelector('.lollipop__line');
          const mark = row.querySelector('.flag-mark');
          const use = mark?.querySelector('use');
          const trackBox = track.getBoundingClientRect();
          const flagBox = use?.getBoundingClientRect();
          // The stem tip is the line's x2 at y=9; percentages resolve against
          // the track's viewport width, which is its layout width in px.
          const pct = Number.parseFloat(line.getAttribute('x2'));
          const tip = {
            x: trackBox.left + (pct / 100) * trackBox.width,
            y: trackBox.top + 9,
          };
          return {
            iso3: row.dataset.lollipop,
            hidden: mark?.getAttribute('aria-hidden'),
            tabindex: mark?.hasAttribute('tabindex'),
            name: row.querySelector('.lollipop__name')?.textContent?.trim() ?? '',
            diameter: flagBox ? Number(flagBox.width.toFixed(2)) : 0,
            centre: flagBox
              ? {
                  x: flagBox.x + flagBox.width / 2,
                  y: flagBox.y + flagBox.height / 2,
                }
              : null,
            tip,
          };
        });
      });

      expectEqual(rows.map((row) => row.iso3).join(','), expected.join(','), `${methodId} rows`);
      for (const row of rows) {
        expect(row.centre, `${row.iso3} has no flag`);
        const dx = Math.abs(row.centre.x - row.tip.x);
        const dy = Math.abs(row.centre.y - row.tip.y);
        expect(
          dx <= 1 && dy <= 1,
          `${row.iso3} flag centre is ${dx.toFixed(2)},${dy.toFixed(2)}px from the stem tip`,
        );
        expectEqual(row.hidden, 'true', `${row.iso3} aria-hidden`);
        expectEqual(row.tabindex, false, `${row.iso3} takes no tab stop`);
        expect(row.name.length > 1, `${row.iso3} row lost its name text`);
      }

      // No overlap: consecutive flag centres must clear the flag diameter.
      const centres = rows.map((row) => row.centre.y).sort((a, b) => a - b);
      let tightest = Infinity;
      for (let index = 1; index < centres.length; index += 1) {
        tightest = Math.min(tightest, centres[index] - centres[index - 1]);
      }
      const diameter = rows[0].diameter;
      expect(diameter >= 14.5 && diameter <= 15.5, `${methodId} desktop flag ${diameter}px`);
      expect(
        tightest >= diameter,
        `${methodId} flags overlap: tightest gap ${tightest.toFixed(2)}px < ${diameter}px`,
      );
      details.push(
        `${methodId}: ${TOP15_COUNT} flags at ${diameter}px, tightest gap ${tightest.toFixed(2)}px`,
      );
    }
    return details.join(' · ');
  });

  await check('pane 1 and 2 render with flags in both methods', async () => {
    await openPane(1, DEFAULT_METHOD);
    await shot(overview, 'desktop-overview-pane1.png', true);
    const buried = topFlagIso3s(DEFAULT_METHOD)[9];
    await pane(1).locator(`.flag-mark[data-iso3="${buried}"]`).focus();
    await shot(overview, 'desktop-overview-pane1-flag-focus.png', true);
    await openPane(1, OTHER_METHOD);
    await shot(overview, 'desktop-overview-pane1-minmax.png', true);
    await openPane(2, DEFAULT_METHOD);
    await shot(overview, 'desktop-overview-pane2.png', true);
    await openPane(2, OTHER_METHOD);
    await shot(overview, 'desktop-overview-pane2-minmax.png', true);
    return `pane 1 z + min–max (one overlay), pane 2 z + min–max`;
  });

  await check('pane 1: flags that touch a dot are reported, not nudged', async () => {
    const details = [];
    for (const methodId of METHOD_IDS) {
      await openPane(1, methodId);
      const report = await pane(1).evaluate(() => {
        const hits = (a, b) =>
          a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
        const dots = [...document.querySelectorAll('.field-chart circle[data-dot]')].map((dot) => ({
          iso3: dot.dataset.dot,
          box: dot.getBoundingClientRect(),
        }));
        const flags = [...document.querySelectorAll('.field-chart .flag-mark')].map((mark) => ({
          iso3: mark.dataset.iso3,
          box: mark.querySelector('use').getBoundingClientRect(),
        }));
        const dotOverlaps = flags
          .map((flag) => ({
            iso3: flag.iso3,
            hits: dots.filter((dot) => hits(flag.box, dot.box)).map((dot) => dot.iso3),
          }))
          .filter((flag) => flag.hits.length > 0)
          .map((flag) => `${flag.iso3}→${flag.hits.join('+')}`);
        const flagOverlaps = [];
        for (let i = 0; i < flags.length; i += 1) {
          for (let j = i + 1; j < flags.length; j += 1) {
            if (hits(flags[i].box, flags[j].box)) {
              flagOverlaps.push(`${flags[i].iso3}×${flags[j].iso3}`);
            }
          }
        }
        return { dotOverlaps, flagOverlaps };
      });
      // Position accuracy wins: the flags stay on their exact data position even
      // when a neighbour sits under them. This records the cost rather than
      // nudging the mark off its data point.
      const dotText =
        report.dotOverlaps.length === 0
          ? 'no flag over a dot'
          : `${report.dotOverlaps.length} flag/dot: ${report.dotOverlaps.join(', ')}`;
      const flagText =
        report.flagOverlaps.length === 0
          ? 'no flag over a flag'
          : `${report.flagOverlaps.length} flag/flag: ${report.flagOverlaps.join(', ')}`;
      details.push(`${methodId} → ${dotText} · ${flagText}`);
    }
    return details.join(' | ');
  });

  for (const paneNumber of [7, 8]) {
    await check(`pane ${paneNumber}: exactly 10 flag marks follow the top 10 by score`, async () => {
      const details = [];
      for (const methodId of METHOD_IDS) {
        await openPane(paneNumber, methodId);
        expectEqual(await flagMarks(paneNumber).count(), 10, `${methodId} flag marks`);
        // The dot count still accounts for every country, flags included.
        expectEqual(
          await pane(paneNumber).locator('[data-scatter]').count(),
          71,
          `${methodId} marks`,
        );
        const order = await flagOrder(paneNumber);
        const expected = topFlagIso3s(methodId);
        expectEqual(
          [...order].sort().join(','),
          [...expected].sort().join(','),
          `${methodId} flagged set`,
        );
        // Paint order is document order: rank 10 first, rank 1 last.
        expectEqual(order[0], expected[9], `${methodId} first-painted flag (rank 10)`);
        expectEqual(
          order[order.length - 1],
          expected[0],
          `${methodId} last-painted flag (rank 1)`,
        );
        details.push(`${methodId}: ${expected[0]} on top, ${expected[9]} beneath`);
      }
      return details.join(' · ');
    });

    await check(`pane ${paneNumber}: each flag announces the country and score`, async () => {
      for (const methodId of METHOD_IDS) {
        await openPane(paneNumber, methodId);
        const marks = await flagMarks(paneNumber).evaluateAll((nodes) =>
          nodes.map((node) => ({
            iso3: node.dataset.iso3,
            label: node.getAttribute('aria-label'),
            role: node.getAttribute('role'),
            tabindex: node.getAttribute('tabindex'),
            title: node.querySelector('title')?.textContent ?? '',
            ring: (() => {
              const ring = node.querySelector('.flag-mark__ring').getBoundingClientRect();
              const flag = node.querySelector('use').getBoundingClientRect();
              return {
                dx: flag.x + flag.width / 2 - (ring.x + ring.width / 2),
                dy: flag.y + flag.height / 2 - (ring.y + ring.height / 2),
              };
            })(),
          })),
        );
        expectEqual(marks.length, 10, `${methodId} marks`);
        for (const mark of marks) {
          const source = (block(methodId).coverage ?? []).find(
            (row) => row.iso3 === mark.iso3,
          ) ?? countryIn(methodId, mark.iso3);
          expect(source, `${mark.iso3} missing from the payload`);
          const name = mark.label?.split(', score ')[0] ?? '';
          expect(
            source.country.startsWith(name) || name === source.country,
            `${mark.iso3} aria-label name "${name}" does not match ${source.country}`,
          );
          expectEqual(mark.label, `${name}, score ${scoreText(source.score)}`, `${mark.iso3} aria-label`);
          expectEqual(mark.title, mark.label, `${mark.iso3} <title>`);
          expectEqual(mark.role, 'img', `${mark.iso3} role`);
          expectEqual(mark.tabindex, '0', `${mark.iso3} tabindex`);
          // The mark is centred on the data position: flag and ring agree.
          expect(
            Math.abs(mark.ring.dx) < 0.75 && Math.abs(mark.ring.dy) < 0.75,
            `${mark.iso3} flag is off-centre by ${mark.ring.dx.toFixed(2)},${mark.ring.dy.toFixed(2)}px`,
          );
        }
      }
      return '10 labelled, focusable marks per method, all centred on the data position';
    });
  }

  await check('flags: Tab reaches a mark, announces it and shows the overlay', async () => {
    await openPane(7, DEFAULT_METHOD);
    // The carousel bar is the last stop before the pane; one Tab moves into
    // the chart, where the first focusable mark is the buried rank 10.
    await overview.getByRole('button', { name: 'Next pane' }).focus();
    let found = null;
    for (let attempt = 0; attempt < 6 && !found; attempt += 1) {
      await overview.keyboard.press('Tab');
      found = await overview.evaluate(() => {
        const element = document.activeElement;
        if (!element || !element.classList?.contains('flag-mark')) return null;
        const code = element.querySelector('use')?.getAttribute('href')?.replace('#flag-', '');
        const overlay = document.querySelector(
          `[data-pane="7"] .flag-overlay--${code}`,
        );
        return {
          label: element.getAttribute('aria-label'),
          iso3: element.dataset.iso3,
          overlay: overlay ? Number(getComputedStyle(overlay).opacity) : null,
          ring: Number(
            getComputedStyle(element.querySelector('.flag-mark__focus')).opacity,
          ),
        };
      });
    }
    expect(found, 'Tab never reached a flag mark');
    expect(found.label, 'flag mark has no announced label');
    expectMatch(found.label, /score \d+\.\d{2}$/, 'announced label');
    expectEqual(found.overlay, 1, 'overlay opacity while tab-focused');
    expectEqual(found.ring, 1, ':focus-visible ring opacity');
    return `Tab → ${found.label} (overlay 1, ring 1)`;
  });

  await check('flags: hovering a mark shows the same overlay', async () => {
    await openPane(8, DEFAULT_METHOD);
    const expected = topFlagIso3s(DEFAULT_METHOD);
    // Rank 2, near the top of the stack and not buried by anything later.
    const target = expected[1];
    const overlay = pane(8).locator(`.flag-overlay[data-overlay="${target}"]`);
    const opacity = () =>
      overlay.evaluate((node) => Number(getComputedStyle(node).opacity));
    expectEqual(await opacity(), 0, 'overlay hidden before hover');
    await pane(8).locator(`.flag-mark[data-iso3="${target}"]`).hover();
    expectEqual(await opacity(), 1, 'overlay opacity while hovered');
    await overview.mouse.move(2, 2);
    expectEqual(await opacity(), 0, 'overlay hidden after the pointer leaves');
    return `${target} overlay 0 → 1 → 0 on hover`;
  });

  await check('flags: one sprite symbol per distinct flag, defined once per page', async () => {
    await openPane(7, DEFAULT_METHOD);
    const sprite = await overview.evaluate(() => {
      const svgs = document.querySelectorAll('svg.flag-sprite');
      const ids = [...document.querySelectorAll('symbol[id^="flag-"]')].map((node) => node.id);
      return {
        sprites: svgs.length,
        ids,
        duplicates: ids.length - new Set(ids).size,
        hidden: [...svgs].every((node) => node.getAttribute('aria-hidden') === 'true'),
      };
    });
    expectEqual(sprite.sprites, 1, 'sprite roots on the page');
    expectEqual(sprite.duplicates, 0, 'duplicate symbol ids');
    expect(sprite.hidden, 'sprite is not hidden from assistive tech');
    // The sprite must carry the union panes 1, 2, 7 and 8 draw in both
    // methods — pane 2's 15 rows included, not just the top 10.
    const expected = new Set();
    for (const methodId of METHOD_IDS) {
      for (const iso3 of methodFlags(methodId)) expected.add(iso2For(iso3));
    }
    const want = [...expected].sort().map((iso2) => `flag-${iso2}`);
    expectEqual([...sprite.ids].sort().join(','), want.join(','), 'symbol set');
    expectEqual(sprite.ids.length, expected.size, 'one symbol per distinct flag');
    // 45 marks on the page (10 + 15 + 10 + 10) but one symbol each.
    expectEqual(await flagMarks(1).count(), 10, 'pane 1 marks');
    expectEqual(await flagMarks(2).count(), 15, 'pane 2 marks');
    expectEqual(await flagMarks(7).count(), 10, 'pane 7 marks');
    expectEqual(await flagMarks(8).count(), 10, 'pane 8 marks');
    return `${sprite.ids.length} symbols (${want.length} expected) for 45 marks in four panes`;
  });

  await check('flags: focusing a buried mark reveals its labelled overlay', async () => {
    await openPane(7, DEFAULT_METHOD);
    const expected = topFlagIso3s(DEFAULT_METHOD);
    const buried = expected[9]; // rank 10, painted first, under the stack
    const mark = pane(7).locator(`.flag-mark[data-iso3="${buried}"]`);
    const overlay = pane(7).locator(`.flag-overlay[data-overlay="${buried}"]`);
    const opacity = () =>
      overlay.evaluate((node) => Number(getComputedStyle(node).opacity));
    expectEqual(await opacity(), 0, 'overlay hidden before focus');
    const pointer = await overlay.evaluate((node) => getComputedStyle(node).pointerEvents);
    expectEqual(pointer, 'none', 'hidden overlay blocks pointer events');

    await mark.focus();
    expectEqual(await opacity(), 1, 'overlay opacity after focus');
    const text = (await overlay.textContent()).replace(/\s+/g, ' ').trim();
    const row = countryIn(DEFAULT_METHOD, buried);
    const name = text.split(', score ')[0];
    expect(
      row.country.startsWith(name),
      `overlay name "${name}" does not match ${row.country}`,
    );
    expectEqual(text, `${name}, score ${scoreText(row.score)}`, 'overlay label text');
    expect(
      text.length > 6 && !text.startsWith('score'),
      `overlay label is not real text: "${text}"`,
    );

    await mark.blur();
    expectEqual(await opacity(), 0, 'overlay hidden again after blur');
    return `rank 10 "${buried}" → "${text}" (opacity 0 → 1 → 0)`;
  });

  await check('min–max views of pane 8 render and screenshot', async () => {
    await openPane(8, OTHER_METHOD);
    expectEqual(
      await overview.locator('input[name="overview-scale"]:checked').inputValue(),
      OTHER_METHOD,
      'pane 8 scale',
    );
    const order = await flagOrder(8);
    expectEqual(order[order.length - 1], topFlagIso3s(OTHER_METHOD)[0], 'min–max top flag');
    await shot(overview, 'desktop-overview-pane8-minmax.png', true);
    return `min–max: ${order.join(' ← ')}`;
  });

  await check('overlay visible: focused flag screenshot', async () => {
    await openPane(7, DEFAULT_METHOD);
    const buried = topFlagIso3s(DEFAULT_METHOD)[9];
    await pane(7).locator(`.flag-mark[data-iso3="${buried}"]`).focus();
    await shot(overview, 'desktop-overview-pane7-flag-focus.png', true);
    return `focused ${buried}`;
  });

  await check('min–max views of panes 4, 5 and 7 render and screenshot', async () => {
    const widths = [];
    for (const n of [4, 5, 7]) {
      await overview.goto(`${server.base}/?pane=${n}&scale=minmax`, { waitUntil: 'load' });
      await settle(overview);
      await waitPane(n);
      await shot(overview, `desktop-overview-pane${n}-minmax.png`, true);
      const checked = await overview
        .locator('input[name="overview-scale"]:checked')
        .inputValue();
      expectEqual(checked, OTHER_METHOD, `pane ${n} scale`);
      widths.push(`${n}:${checked}`);
    }
    return widths.join(' ');
  });

  await check('Prev returns to pane 1 and drops ?pane from the URL', async () => {
    await overview.goto(`${server.base}/?pane=2`, { waitUntil: 'load' });
    await settle(overview);
    await waitPane(2);
    await overview.getByRole('button', { name: 'Previous pane' }).click();
    await waitPane(1);
    expect(!overview.url().includes('pane='), `URL still carries pane=: ${overview.url()}`);
    expectEqual(await counterText(), '1 / 8', 'counter');
    return `${new URL(overview.url()).pathname}${new URL(overview.url()).search}`;
  });

  await check('arrow keys move panes; Home and End jump to the ends', async () => {
    await overview.getByRole('button', { name: 'Next pane' }).click();
    await waitPane(2);
    await overview.keyboard.press('ArrowRight');
    await waitPane(3);
    await overview.keyboard.press('ArrowLeft');
    await waitPane(2);
    await overview.keyboard.press('End');
    await waitPane(8);
    const last = await livePane();
    await overview.keyboard.press('Home');
    await waitPane(1);
    expectEqual(last, '8', 'End pane');
    return '→ 3, ← 2, End 8, Home 1';
  });

  await check('?pane=5 reloads with pane 5 open and announced', async () => {
    await overview.goto(`${server.base}/?pane=5`, { waitUntil: 'load' });
    await settle(overview);
    await waitPane(5);
    expectEqual(await counterText(), '5 / 8', 'counter');
    expectEqual(await announcement(), 'Pane 5 of 8: Movement', 'live region');
    const current = await overview.locator('.carousel__dot[aria-current="true"]').getAttribute('aria-label');
    expectMatch(current, /pane 5: Movement/, 'active dot');
    return '?pane=5 → pane 5, "Pane 5 of 8: Movement"';
  });

  await check('moving panes does not steal focus', async () => {
    await overview.goto(`${server.base}/`, { waitUntil: 'load' });
    await settle(overview);
    const next = overview.getByRole('button', { name: 'Next pane' });
    // WebKit (like Safari) does not focus a button on a mouse click, so move
    // the pane the way a keyboard user would: activate the focused button.
    await next.focus();
    await next.press('Enter');
    await waitPane(2);
    const focused = await overview.evaluate(
      () => document.activeElement?.getAttribute('aria-label') ?? null,
    );
    expectEqual(focused, 'Next pane', 'focused element');
    return 'focus stayed on the Next button';
  });

  await check('no autoplay: the pane does not change on its own', async () => {
    await overview.goto(`${server.base}/`, { waitUntil: 'load' });
    await settle(overview);
    const before = await livePane();
    await overview.waitForTimeout(900);
    expectEqual(await livePane(), before, 'pane after 900ms');
    expect(!overview.url().includes('pane='), 'URL grew a pane parameter');
    return 'still on pane 1 after 900ms';
  });

  await check('prefers-reduced-motion removes the pane transition', async () => {
    const reduced = await newPage(desktopViewport);
    await reduced.emulateMedia({ reducedMotion: 'reduce' });
    await reduced.goto(`${server.base}/`, { waitUntil: 'load' });
    await settle(reduced);
    const name = await reduced
      .locator('[data-pane="1"]')
      .evaluate((element) => getComputedStyle(element).animationName);
    expectEqual(name, 'none', 'animation-name');
    await reduced.close();
    return 'animation-name: none';
  });

  await check('every pane has a View as table disclosure', async () => {
    const details = await overview.locator('details[data-pane-table]').count();
    expectEqual(details, 8, 'disclosure count');
    const summaries = await overview.locator('details[data-pane-table] > summary').allInnerTexts();
    const bad = summaries.filter((text) => !/View as table/.test(text));
    expect(bad.length === 0, `summaries without the label: ${JSON.stringify(bad)}`);
    return '8 disclosures, all labelled View as table';
  });

  await check('all eight panes carry a real chart and a real table', async () => {
    expectEqual(await overview.locator('.pane__placeholder').count(), 0, 'placeholders');
    const fallbacks = await overview.locator('.pane__table-fallback').count();
    expectEqual(fallbacks, 0, 'table fallbacks');
    const counts = [];
    for (let n = 1; n <= 8; n += 1) {
      const rows = await pane(n).locator('table tbody tr').count();
      expect(rows > 0, `pane ${n} has no table rows`);
      counts.push(`${n}:${rows}`);
    }
    return `no placeholders; table rows ${counts.join(' ')}`;
  });

  /* ------------------------------------------------- desktop: `/rankings` */
  const page = await newPage(desktopViewport);
  await page.goto(`${server.base}/rankings`, { waitUntil: 'load' });
  await settle(page);

  await check('/rankings renders 71 data rows', async () => {
    await rowsOf(page).first().waitFor();
    const n = await rowsOf(page).count();
    expectEqual(n, 71, 'table tbody tr count');
    return '71 rows';
  });

  await check('/rankings links to 71 /country/{ISO3} pages', async () => {
    const n = await page.locator('a[href^="/country/"]').count();
    expectEqual(n, 71, 'country link count');
    return '71 links';
  });

  await check('/rankings defaults to z-score with no scale param', async () => {
    const checked = await page.locator('input[name="scale"]:checked').inputValue();
    expectEqual(checked, DEFAULT_METHOD, 'checked scale');
    expectEqual(checked, 'z', 'default method is z');
    expect(!page.url().includes('scale='), `URL should not carry scale=, got ${page.url()}`);
    return 'z, no scale param';
  });

  await check('Saudi Arabia row (z): rank 36, score 46.20', async () => {
    const text = await saudiRow(page).innerText();
    const cells = await saudiRow(page).locator('td').allInnerTexts();
    expectEqual(num(cells[0]), 36, 'rank');
    expectEqual(num(cells[2]), 46.2, 'score');
    return `${cells[0].trim()} / ${cells[2].trim()} (${text.split('\n')[1]})`;
  });

  await check('movement header names the other method: Rank vs min–max', async () => {
    const header = await page.locator('thead th.movement-col abbr').innerText();
    expectEqual(header.trim(), 'Rank vs min–max', 'movement header (z active)');
    return header.trim();
  });

  await shot(page, 'desktop-rankings-z.png', true);

  await check('click Min–max → URL gains scale=minmax, Saudi rank 55', async () => {
    await page.getByRole('radio', { name: 'Min–max' }).check();
    await settle(page);
    expectMatch(page.url(), /[?&]scale=minmax(&|$)/, 'URL');
    const cells = await saudiRow(page).locator('td').allInnerTexts();
    expectEqual(num(cells[0]), 55, 'rank');
    expectEqual(num(cells[2]), 18.03, 'score');
    const header = await page.locator('thead th.movement-col abbr').innerText();
    expectEqual(header.trim(), 'Rank vs z', 'movement header (min–max active)');
    return `${page.url().replace(server.base, '')} · 55 / 18.03 · "${header.trim()}"`;
  });

  await check('min–max: rank-movement cell reads −19 against z', async () => {
    const cell = saudiRow(page).locator('td.movement-col');
    await cell.waitFor();
    const text = await cell.innerText();
    expectMatch(text.replace(/\s+/g, ' '), /−19/, 'movement cell text');
    return JSON.stringify(text.replace(/\s+/g, ' ').trim());
  });

  await shot(page, 'desktop-rankings-minmax.png', true);

  await check('reload /rankings?scale=minmax keeps min–max active', async () => {
    await page.goto(`${server.base}/rankings?scale=minmax`, { waitUntil: 'load' });
    await settle(page);
    const checked = await page.locator('input[name="scale"]:checked').inputValue();
    expectEqual(checked, OTHER_METHOD, 'checked scale after reload');
    const cells = await saudiRow(page).locator('td').allInnerTexts();
    expectEqual(num(cells[0]), 55, 'rank after reload');
    return 'min–max active, rank 55';
  });

  await check('switch back to Z-score drops scale from the URL', async () => {
    await page.getByRole('radio', { name: 'Z-score' }).check();
    await settle(page);
    expect(!page.url().includes('scale='), `URL still carries scale=: ${page.url()}`);
    const checked = await page.locator('input[name="scale"]:checked').inputValue();
    expectEqual(checked, 'z', 'checked scale');
    const header = await page.locator('thead th.movement-col abbr').innerText();
    expectEqual(header.trim(), 'Rank vs min–max', 'movement header back to z');
    return `${new URL(page.url()).pathname}${new URL(page.url()).search}`;
  });

  await check('filter "ind" drops row count and live region announces it', async () => {
    const before = await rowsOf(page).count();
    await page.getByRole('searchbox', { name: 'Filter countries' }).fill('ind');
    await settle(page);
    await page.locator('table tbody tr').first().waitFor();
    const after = await rowsOf(page).count();
    expect(after > 0 && after < before, `row count did not drop: ${before} -> ${after}`);
    const announced = (await liveRegion(page).innerText()).trim();
    expectMatch(announced, new RegExp(`\\b${after} of 71 countries`), 'live region text');
    return `${before} → ${after} rows; live: ${JSON.stringify(announced)}`;
  });

  await check('sort by score: aria-sort="descending", first row USA', async () => {
    await page.getByRole('searchbox', { name: 'Filter countries' }).fill('');
    await settle(page);
    const scoreHeader = page.locator('thead th.score-col');
    await page.getByRole('button', { name: /CHIPS score/ }).click();
    await settle(page);
    const ariaSort = await scoreHeader.getAttribute('aria-sort');
    expectEqual(ariaSort, 'descending', 'score th aria-sort');
    const first = (await rowsOf(page).first().innerText()).split('\n').map((s) => s.trim()).filter(Boolean);
    expect(first.includes('USA'), `first row is ${JSON.stringify(first)}, not USA`);
    return `aria-sort=${ariaSort}; first row ${first.join(' ')}`;
  });

  await check('"Show pillars" adds 5 pillar columns', async () => {
    const before = await page.locator('thead th').count();
    await page.getByRole('checkbox', { name: 'Show pillars' }).check();
    await settle(page);
    const after = await page.locator('thead th').count();
    expectEqual(after - before, 5, 'added column count');
    const headers = (await page.locator('thead th').allInnerTexts()).map((s) => s.trim()).filter(Boolean);
    return `${before} → ${after} columns (${headers.slice(-5).join(' ')})`;
  });

  await shot(page, 'desktop-rankings-pillars.png', true);

  /* ------------------------------------------------------ desktop: country */
  const country = await newPage(desktopViewport);
  await country.goto(`${server.base}/country/IND`, { waitUntil: 'load' });
  await settle(country);

  const defaultMethod = CHIPS.meta.defaultMethod;
  const indiaDefault = CHIPS.methods[defaultMethod].scores.find((r) => r.iso3 === 'IND');
  const indiaMinMax = CHIPS.methods.full_minmax.scores.find((r) => r.iso3 === 'IND');
  const expectedComposite = (indiaDefault.overall * 100).toFixed(2);
  const expectedMinMax = (indiaMinMax.overall * 100).toFixed(2);

  await check(
    `/country/IND renders India, rank 3, composite ${expectedComposite} on the default (${defaultMethod}) scale`,
    async () => {
      const h1 = (await country.locator('h1').innerText()).trim();
      expectEqual(h1, 'India', 'h1');
      const head = await country.locator('.country-head').innerText();
      expectMatch(head.replace(/\s+/g, ' '), /Rank 3 of 71/, 'rank line');
      const score = (await country.locator('.country-head__score .display-xl').innerText()).trim();
      expectEqual(score, expectedComposite, 'composite score');

      // The other method must still be reachable and must change the headline.
      await country.goto(`${server.base}/country/IND?scale=minmax`, { waitUntil: 'load' });
      await settle(country);
      const minMaxScore = (
        await country.locator('.country-head__score .display-xl').innerText()
      ).trim();
      expectEqual(minMaxScore, expectedMinMax, 'min–max composite');
      return `India · rank 3 · ${score} default, ${minMaxScore} min–max`;
    },
  );

  await shot(country, 'desktop-country-ind.png', true);

  const cardButton = (id) =>
    country.locator(`.pillar-card[data-pillar="${id}"] .pillar-card__toggle`);
  const pillarPanel = (id) => country.locator(`.pillar-detail[data-pillar="${id}"]`);
  const waitOpen = (id) =>
    country.waitForFunction(
      (pillarId) =>
        document
          .querySelector(`.pillar-card[data-pillar="${pillarId}"] .pillar-card__toggle`)
          ?.getAttribute('aria-expanded') === 'true',
      id,
    );

  await check('CONNECT expands to 4 sub-pillar rows', async () => {
    await cardButton('CONNECT').click();
    await waitOpen('CONNECT');
    const rows = await pillarPanel('CONNECT').locator('tr[data-subpillar]').count();
    expectEqual(rows, 4, 'CONNECT sub-pillar rows');
    const rowText = (await pillarPanel('CONNECT').innerText()).replace(/\s+/g, ' ');
    expectMatch(rowText, /\d+ of 71/, 'sub-pillar world rank');
    expectMatch(country.url(), /[?&]open=connect(&|$)/, 'CONNECT URL');
    expectEqual(await cardButton('CONNECT').getAttribute('aria-expanded'), 'true', 'expanded');
    return `4 sub-pillars; ${new URL(country.url()).search}`;
  });

  await check('HARNESS · AI expands to 4 indicator rows', async () => {
    await cardButton('HARNESS').click();
    await waitOpen('HARNESS');
    await pillarPanel('HARNESS')
      .locator('tr[data-subpillar="HARNESS · AI"] .subpillar-toggle')
      .click();
    await country.waitForFunction(
      () =>
        document.querySelector(
          '.pillar-detail[data-pillar="HARNESS"] tr[data-subpillar="HARNESS · AI"] .subpillar-toggle',
        )?.getAttribute('aria-expanded') === 'true',
    );
    const rows = await pillarPanel('HARNESS').locator('tr[data-indicator]').count();
    expectEqual(rows, 4, 'HARNESS · AI indicator rows');
    const indicatorText = (await pillarPanel('HARNESS').locator('.indicator-table').innerText())
      .replace(/\s+/g, ' ');
    expectMatch(indicatorText, /25%/, 'local indicator weight');
    expect(!/1\.25%/.test(indicatorText), 'global effectiveWeight leaked into the share column');
    expectMatch(country.url(), /[?&]open=harness\.ai(&|$)/, 'HARNESS · AI URL');
    return `4 indicators; ${new URL(country.url()).search}`;
  });

  await shot(country, 'desktop-country-ind-open.png', true);

  await check('sub-pillar rank in the DOM equals chips.json (full and z)', async () => {
    const key = 'HARNESS · AI';
    const full = jsonSubPillar('full_minmax', 'IND', key);
    const fullOf = jsonSubPillarOf('full_minmax', key);
    const z = jsonSubPillar('z', 'IND', key);
    const zOf = jsonSubPillarOf('z', key);

    await country.goto(`${server.base}/country/IND?open=harness.ai&scale=minmax`, {
      waitUntil: 'load',
    });
    await settle(country);
    await waitOpen('HARNESS');
    const fullText = (
      await pillarPanel('HARNESS')
        .locator('tr[data-subpillar="HARNESS · AI"] td')
        .nth(1)
        .innerText()
    ).trim();
    expectEqual(fullText, `${full.rank} of ${fullOf}`, 'full_minmax rank text');

    await country.goto(`${server.base}/country/IND?open=harness.ai&scale=z`, {
      waitUntil: 'load',
    });
    await settle(country);
    await waitOpen('HARNESS');
    const zText = (
      await pillarPanel('HARNESS')
        .locator('tr[data-subpillar="HARNESS · AI"] td')
        .nth(1)
        .innerText()
    ).trim();
    expectEqual(zText, `${z.rank} of ${zOf}`, 'z-score rank text');

    return `full_minmax ${fullText}; z ${zText}`;
  });

  await check('?open=harness reloads with HARNESS expanded', async () => {
    await country.goto(`${server.base}/country/IND?open=harness`, { waitUntil: 'load' });
    await settle(country);
    await waitOpen('HARNESS');
    expectEqual(await cardButton('HARNESS').getAttribute('aria-expanded'), 'true', 'HARNESS open');
    expectEqual(await cardButton('CONNECT').getAttribute('aria-expanded'), 'false', 'CONNECT closed');
    return 'HARNESS open after reload';
  });

  await check('opening INNOVATE closes the previous pillar', async () => {
    await country.goto(`${server.base}/country/IND`, { waitUntil: 'load' });
    await settle(country);
    await cardButton('CONNECT').click();
    await waitOpen('CONNECT');
    await cardButton('INNOVATE').click();
    await waitOpen('INNOVATE');
    expectEqual(await cardButton('CONNECT').getAttribute('aria-expanded'), 'false', 'CONNECT closed');
    expectEqual(await cardButton('INNOVATE').getAttribute('aria-expanded'), 'true', 'INNOVATE open');
    return 'CONNECT closed, INNOVATE open';
  });

  await check('SUSTAINABILITY skips the sub-pillar level and shows 6 indicators', async () => {
    await country.goto(`${server.base}/country/IND`, { waitUntil: 'load' });
    await settle(country);
    await cardButton('SUSTAINABILITY').click();
    await waitOpen('SUSTAINABILITY');
    const panel = pillarPanel('SUSTAINABILITY');
    expectEqual(await panel.locator('.subpillar-table').count(), 0, 'sub-pillar tables');
    const rows = await panel.locator('.indicator-table tbody tr').count();
    expectEqual(rows, 6, 'SUSTAINABILITY indicator rows');
    return '0 sub-pillar tables, 6 indicator rows';
  });

  await check('Costa Rica dropped sub-pillar says Not scored, never 0', async () => {
    await country.goto(`${server.base}/country/CRI?open=harness.ai`, { waitUntil: 'load' });
    await settle(country);
    await waitOpen('HARNESS');
    const row = pillarPanel('HARNESS').locator('tr[data-subpillar="HARNESS · AI"]');
    const rowText = (await row.innerText()).replace(/\s+/g, ' ');
    expectMatch(rowText, /Not scored/, 'sub-pillar row');
    expectMatch(rowText, /0% \(redistributed\)/, 'redistributed weight');
    const indicators = await pillarPanel('HARNESS').locator('tr[data-indicator]').count();
    expectEqual(indicators, 4, 'indicator rows');
    const indicatorText = (await pillarPanel('HARNESS').locator('tr[data-indicator]').allInnerTexts())
      .join(' ')
      .replace(/\s+/g, ' ');
    expectMatch(indicatorText, /Not scored/, 'indicator rows');
    expectMatch(indicatorText, /Open data score/i, 'present indicator');
    return 'Not scored + 0% (redistributed) + 4 indicator rows';
  });

  await shot(country, 'desktop-country-cri-missing.png', true);

  await check('?open and ?scale coexist', async () => {
    await country.goto(`${server.base}/country/IND?open=harness&scale=z`, {
      waitUntil: 'load',
    });
    await settle(country);
    await waitOpen('HARNESS');
    const scaleText = (await country.locator('.country-head > p').innerText()).trim();
    expectEqual(scaleText, 'Z-score scale', 'active scale');
    expectMatch(country.url(), /open=harness/, 'open param');
    expectMatch(country.url(), /scale=z/, 'scale param');
    return 'HARNESS open and z active';
  });

  await check('focus stays on a sub-pillar toggle when its panel closes', async () => {
    await country.goto(`${server.base}/country/IND?open=harness`, { waitUntil: 'load' });
    await settle(country);
    await waitOpen('HARNESS');
    const toggle = pillarPanel('HARNESS').locator(
      'tr[data-subpillar="HARNESS · AI"] .subpillar-toggle',
    );
    await toggle.click();
    await toggle.click();
    const focused = await country.evaluate(
      () =>
        document.activeElement?.classList.contains('subpillar-toggle') &&
        document.activeElement?.getAttribute('aria-expanded') === 'false',
    );
    expect(focused, 'focus left the toggle after closing the panel');
    return 'focus retained on the closed sub-pillar toggle';
  });

  await check('Enter and Space toggle a pillar header', async () => {
    await country.goto(`${server.base}/country/IND`, { waitUntil: 'load' });
    await settle(country);
    await cardButton('CONNECT').focus();
    await country.keyboard.press('Enter');
    await waitOpen('CONNECT');
    await country.waitForFunction(
      () =>
        document
          .querySelector('.pillar-card[data-pillar="CONNECT"] .pillar-card__toggle')
          ?.getAttribute('aria-expanded') === 'true',
    );
    await country.keyboard.press('Space');
    await country.waitForFunction(
      () =>
        document
          .querySelector('.pillar-card[data-pillar="CONNECT"] .pillar-card__toggle')
          ?.getAttribute('aria-expanded') === 'false',
    );
    return 'Enter opened, Space closed';
  });

  await check('open panel controls are focusable and operate from the keyboard', async () => {
    await country.goto(`${server.base}/country/IND?open=harness`, { waitUntil: 'load' });
    await settle(country);
    await waitOpen('HARNESS');
    const firstToggle = pillarPanel('HARNESS').locator('.subpillar-toggle').first();
    await firstToggle.focus();
    const focused = await country.evaluate(() =>
      document.activeElement?.classList.contains('subpillar-toggle'),
    );
    expect(focused, 'sub-pillar toggle did not take focus');
    await country.keyboard.press('Enter');
    await country.waitForFunction(
      () =>
        document
          .querySelector('.pillar-detail[data-pillar="HARNESS"] .subpillar-toggle')
          ?.getAttribute('aria-expanded') === 'true',
    );
    const order = await country.evaluate(() => {
      const tabbable = Array.from(
        document.querySelectorAll(
          'a[href], button:not([disabled]), input:not([disabled]), summary, [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((element) => element.getClientRects().length > 0);
      const header = document.querySelector(
        '.pillar-card[data-pillar="HARNESS"] .pillar-card__toggle',
      );
      const first = document.querySelector(
        '.pillar-detail[data-pillar="HARNESS"] .subpillar-toggle',
      );
      return { header: tabbable.indexOf(header), first: tabbable.indexOf(first) };
    });
    expect(
      order.header >= 0 && order.first > order.header,
      `panel controls not after the header in the focus order: ${JSON.stringify(order)}`,
    );
    // Headless WebKit's default Tab cycle skips buttons (the Safari
    // "Tab highlights each item" setting), so this checks focusability and
    // document order rather than synthesising Tab.
    return `focused and opened with Enter; focus order ${order.header} → ${order.first}`;
  });

  narrowPage = await newPage({ width: 320, height: 800 });
  await narrowPage.goto(`${server.base}/country/IND?open=harness.ai`, {
    waitUntil: 'load',
  });
  await settle(narrowPage);
  await narrowPage.waitForFunction(
    () =>
      document.querySelector(
        '.pillar-detail[data-pillar="HARNESS"] tr[data-subpillar="HARNESS · AI"] .subpillar-toggle',
      )?.getAttribute('aria-expanded') === 'true',
  );
  await check('320px: open profile has no horizontal scroll', async () => {
    const [scrollWidth, innerWidth, weightDisplay, rowSubDisplay] = await narrowPage.evaluate(
      () => [
        document.documentElement.scrollWidth,
        window.innerWidth,
        getComputedStyle(document.querySelector('.indicator-table .weight-col')).display,
        getComputedStyle(document.querySelector('.indicator-table .row-sub')).display,
      ],
    );
    expect(
      scrollWidth <= innerWidth,
      `scrollWidth ${scrollWidth} > innerWidth ${innerWidth}`,
    );
    expectEqual(weightDisplay, 'none', 'weight column display');
    expectEqual(rowSubDisplay, 'block', 'row weight display');
    return `${scrollWidth} <= ${innerWidth}; weight column replaced by row-sub`;
  });
  await shot(narrowPage, 'mobile-country-ind.png', true);

  /* -------------------------------------------------------- desktop: method */
  const method = await newPage(desktopViewport);
  await method.goto(`${server.base}/methodology`, { waitUntil: 'load' });
  await settle(method);

  await check('/methodology mentions both scaling methods', async () => {
    const text = (await method.locator('main').innerText()).replace(/\s+/g, ' ');
    expectMatch(text, /min[–-]max/i, 'method page text (min–max)');
    expectMatch(text, /z[–-]score/i, 'method page text (z-score)');
    return 'min–max and z-score both present';
  });

  await shot(method, 'desktop-methodology.png', true);

  /* ------------------------------------------------------------ keyboard */
  await check('every sortable header is <button> inside <th>', async () => {
    const info = await page.evaluate(() => {
      const heads = Array.from(document.querySelectorAll('thead th[aria-sort]'));
      return heads.map((th) => ({
        text: th.textContent.replace(/\s+/g, ' ').trim(),
        tag: th.firstElementChild?.tagName ?? null,
        buttons: th.querySelectorAll('button').length,
      }));
    });
    expect(info.length >= 3, `expected >=3 sortable headers, found ${info.length}`);
    const bad = info.filter((h) => h.tag !== 'BUTTON' || h.buttons !== 1);
    expect(bad.length === 0, `not button-in-th: ${JSON.stringify(bad)}`);
    return info.map((h) => `«${h.text}»`).join(', ');
  });

  const tab = await newPage(desktopViewport);
  await tab.goto(`${server.base}/rankings`, { waitUntil: 'load' });
  await settle(tab);

  await check('Tab from top of /rankings reaches the filter input within 10 stops', async () => {
    tabTrace = [];
    let reached = -1;
    for (let i = 1; i <= 10; i++) {
      await tab.keyboard.press('Tab');
      const stop = await tab.evaluate(() => {
        const el = document.activeElement;
        if (!el || el === document.body) return { id: '', tag: 'body', label: '(document)' };
        const label = (
          el.getAttribute('aria-label') ||
          (el.id ? document.querySelector(`label[for="${el.id}"]`)?.textContent : '') ||
          el.textContent ||
          ''
        )
          .replace(/\s+/g, ' ')
          .trim()
          .slice(0, 40);
        return { id: el.id, tag: el.tagName.toLowerCase(), label };
      });
      tabTrace.push(`${stop.tag}${stop.id ? `#${stop.id}` : ''}${stop.label ? ` «${stop.label}»` : ''}`);
      if (stop.id === 'country-filter') {
        reached = i;
        break;
      }
    }
    expect(reached !== -1, `filter input not reached in 10 stops: ${tabTrace.join(' → ')}`);
    return `stop ${reached}: ${tabTrace[reached - 1]}`;
  });

  /* --------------------------------------------------------------- mobile */
  mobilePage = await newPage(mobileViewport);
  await mobilePage.goto(`${server.base}/rankings`, { waitUntil: 'load' });
  await settle(mobilePage);

  await check('390px: rankings has no horizontal scroll', async () => {
    const [scrollWidth, innerWidth, bodyScroll] = await mobilePage.evaluate(() => [
      document.documentElement.scrollWidth,
      window.innerWidth,
      document.body.scrollWidth,
    ]);
    expect(
      scrollWidth <= innerWidth,
      `documentElement.scrollWidth ${scrollWidth} > window.innerWidth ${innerWidth} (body ${bodyScroll})`,
    );
    return `${scrollWidth} <= ${innerWidth}`;
  });

  await shot(mobilePage, 'mobile-rankings.png', false);

  const mobileOverview = await newPage(mobileViewport);
  await mobileOverview.goto(`${server.base}/`, { waitUntil: 'load' });
  await settle(mobileOverview);

  await check('390px: overview carousel has no horizontal scroll', async () => {
    const [scrollWidth, innerWidth, bodyScroll] = await mobileOverview.evaluate(() => [
      document.documentElement.scrollWidth,
      window.innerWidth,
      document.body.scrollWidth,
    ]);
    expect(
      scrollWidth <= innerWidth,
      `documentElement.scrollWidth ${scrollWidth} > window.innerWidth ${innerWidth} (body ${bodyScroll})`,
    );
    return `${scrollWidth} <= ${innerWidth}`;
  });

  await check('390px: carousel controls stay usable (≥24px targets)', async () => {
    const sizes = await mobileOverview.evaluate(() =>
      [...document.querySelectorAll('.carousel__button, .carousel__dot')].map((element) => {
        const box = element.getBoundingClientRect();
        return { w: Math.round(box.width), h: Math.round(box.height) };
      }),
    );
    const small = sizes.filter((box) => box.w < 24 || box.h < 24);
    expect(small.length === 0, `targets below 24px: ${JSON.stringify(small)}`);
    expect(sizes.length === 10, `expected 10 controls, found ${sizes.length}`);
    return `${sizes.length} controls, smallest ${Math.min(...sizes.map((b) => Math.min(b.w, b.h)))}px`;
  });

  await check('390px: the scale toggle has two ≥24px targets', async () => {
    const sizes = await mobileOverview.evaluate(() =>
      [...document.querySelectorAll('.carousel__scale .segmented__option span')].map(
        (element) => {
          const box = element.getBoundingClientRect();
          return { text: element.textContent.trim(), w: Math.round(box.width), h: Math.round(box.height) };
        },
      ),
    );
    expectEqual(sizes.length, 2, 'scale options');
    const small = sizes.filter((box) => box.w < 24 || box.h < 24);
    expect(small.length === 0, `scale targets below 24px: ${JSON.stringify(small)}`);
    const checked = await mobileOverview
      .locator('input[name="overview-scale"]:checked')
      .inputValue();
    expectEqual(checked, DEFAULT_METHOD, 'default scale on mobile');
    return sizes.map((box) => `${box.text} ${box.w}×${box.h}`).join(' · ');
  });

  await check('390px: min–max overview has no horizontal scroll', async () => {
    await mobileOverview.goto(`${server.base}/?scale=minmax`, { waitUntil: 'load' });
    await settle(mobileOverview);
    const [scrollWidth, innerWidth] = await mobileOverview.evaluate(() => [
      document.documentElement.scrollWidth,
      window.innerWidth,
    ]);
    expect(
      scrollWidth <= innerWidth,
      `scrollWidth ${scrollWidth} > innerWidth ${innerWidth}`,
    );
    await mobileOverview.goto(`${server.base}/`, { waitUntil: 'load' });
    await settle(mobileOverview);
    return `${scrollWidth} <= ${innerWidth}`;
  });

  await check('390px: flags shrink to 14px and stay on the data position', async () => {
    await mobileOverview.goto(`${server.base}/?pane=7`, { waitUntil: 'load' });
    await settle(mobileOverview);
    const info = await mobileOverview.evaluate(() => {
      const scope = '[data-pane="7"]:not([hidden])';
      const mark = document.querySelector(`${scope} .flag-mark`);
      const flag = mark.querySelector('use').getBoundingClientRect();
      const ring = mark.querySelector('.flag-mark__ring').getBoundingClientRect();
      return {
        w: Number(flag.width.toFixed(2)),
        h: Number(flag.height.toFixed(2)),
        dx: Number((flag.x + flag.width / 2 - (ring.x + ring.width / 2)).toFixed(2)),
        dy: Number((flag.y + flag.height / 2 - (ring.y + ring.height / 2)).toFixed(2)),
      };
    });
    expectEqual(info.w, 14, 'mobile flag width');
    expectEqual(info.h, 14, 'mobile flag height');
    expect(info.dx === 0 && info.dy === 0, `flag off centre by ${info.dx},${info.dy}px`);
    await mobileOverview.goto(`${server.base}/`, { waitUntil: 'load' });
    await settle(mobileOverview);
    return `14×14 px, centred (${info.dx}, ${info.dy})`;
  });

  await check('390px: pane 1 flags 14px, pane 2 flags 13px, both on position', async () => {
    const measured = {};
    for (const paneNumber of [1, 2]) {
      await mobileOverview.goto(`${server.base}/?pane=${paneNumber}`, { waitUntil: 'load' });
      await settle(mobileOverview);
      measured[paneNumber] = await mobileOverview.evaluate((n) => {
        const pane = document.querySelector(`[data-pane="${n}"]:not([hidden])`);
        const marks = [...pane.querySelectorAll('.flag-mark')];
        const sizes = marks.map((mark) => {
          const use = mark.querySelector('use').getBoundingClientRect();
          return {
            w: Number(use.width.toFixed(2)),
            h: Number(use.height.toFixed(2)),
            cy: use.y + use.height / 2,
          };
        });
        const centres = sizes.map((size) => size.cy).sort((a, b) => a - b);
        let gap = Infinity;
        for (let index = 1; index < centres.length; index += 1) {
          gap = Math.min(gap, centres[index] - centres[index - 1]);
        }
        return { count: marks.length, sizes, gap: Number(gap.toFixed(2)) };
      }, paneNumber);
    }

    expectEqual(measured[1].count, 10, 'pane 1 mobile flags');
    expect(measured[1].sizes.every((size) => size.w === 14 && size.h === 14), 'pane 1 is 14px');
    expectEqual(measured[2].count, 15, 'pane 2 mobile flags');
    expect(measured[2].sizes.every((size) => size.w === 13 && size.h === 13), 'pane 2 is 13px');

    // Centring on the stem tip, at 13px, in the pane that changed size most.
    await mobileOverview.goto(`${server.base}/?pane=2`, { waitUntil: 'load' });
    await settle(mobileOverview);
    const tip = await mobileOverview.evaluate(() => {
      const row = document.querySelector('[data-pane="2"]:not([hidden]) [data-lollipop]');
      const track = row.querySelector('.lollipop__track');
      const line = row.querySelector('.lollipop__line');
      const use = row.querySelector('.flag-mark use').getBoundingClientRect();
      const box = track.getBoundingClientRect();
      const pct = Number.parseFloat(line.getAttribute('x2'));
      return {
        dx: Number((use.x + use.width / 2 - (box.left + (pct / 100) * box.width)).toFixed(2)),
        dy: Number((use.y + use.height / 2 - (box.top + 9)).toFixed(2)),
      };
    });
    expect(tip.dx === 0 && tip.dy === 0, `mobile flag off centre by ${tip.dx},${tip.dy}px`);

    await mobileOverview.goto(`${server.base}/`, { waitUntil: 'load' });
    await settle(mobileOverview);
    return `pane 1 14px · pane 2 13px, gap ${measured[2].gap}px, centred (${tip.dx}, ${tip.dy})`;
  });

  await shot(mobileOverview, 'mobile-overview.png', true);

  await mobileOverview.getByRole('button', { name: 'Next pane' }).click();
  await mobileOverview.waitForFunction(
    () => document.querySelector('[data-pane="2"]')?.hasAttribute('hidden') === false,
  );
  await shot(mobileOverview, 'mobile-overview-pane2.png', true);

  await check('390px: panes 1–8 have no horizontal scroll', async () => {
    const widths = [];
    for (const n of [1, 2, 3, 4, 5, 6, 7, 8]) {
      await mobileOverview.goto(`${server.base}/?pane=${n}`, { waitUntil: 'load' });
      await settle(mobileOverview);
      const [scrollWidth, innerWidth] = await mobileOverview.evaluate(() => [
        document.documentElement.scrollWidth,
        window.innerWidth,
      ]);
      expect(
        scrollWidth <= innerWidth,
        `pane ${n}: scrollWidth ${scrollWidth} > innerWidth ${innerWidth}`,
      );
      widths.push(`${n}: ${scrollWidth}/${innerWidth}`);
      await shot(mobileOverview, `mobile-overview-pane${n}.png`, true);
    }
    return widths.join(' · ');
  });

  /* ------------------------------------------------------------------ axe */
  for (const label of [
    '/',
    '/?scale=minmax',
    '/?pane=3',
    '/?pane=4',
    '/?pane=5',
    '/?pane=6',
    '/?pane=7',
    '/?pane=8',
    '/?pane=4&scale=minmax',
    '/?pane=5&scale=minmax',
    '/?pane=7&scale=minmax',
    '/?pane=8&scale=minmax',
    '/rankings',
    '/rankings?scale=minmax',
    '/country/IND',
    '/country/IND?open=harness.ai',
    '/country/CRI?open=harness.ai',
    '/methodology',
    '/about',
  ]) {
    const target = await newPage(desktopViewport);
    await target.goto(`${server.base}${label}`, { waitUntil: 'load' });
    await settle(target);
    if (label.includes('open=')) {
      await target.waitForFunction(
        () =>
          document
            .querySelector(
              '.pillar-detail[data-pillar="HARNESS"] tr[data-subpillar="HARNESS · AI"] .subpillar-toggle',
            )
            ?.getAttribute('aria-expanded') === 'true',
      );
    }
    const result = await new AxeBuilder({ page: target }).analyze();
    axeReport.push({
      page: label,
      violations: result.violations.map((v) => ({
        id: v.id,
        impact: v.impact ?? 'unknown',
        help: v.help,
        nodes: v.nodes.map((n) => ({
          target: n.target.join(' '),
          summary: n.failureSummary?.split('\n')[0] ?? '',
        })),
      })),
      incomplete: result.incomplete.map((v) => ({
        id: v.id,
        impact: v.impact ?? 'unknown',
        nodes: v.nodes.map((n) => n.target.join(' ')),
      })),
    });
    await target.close();
  }

  await check('axe: overview (/) has no violations', async () => {
    const entry = axeReport.find((item) => item.page === '/');
    expect(entry, 'overview axe entry missing');
    expectEqual(entry.violations.length, 0, 'overview violations');
    return '0 axe violations';
  });

  await check('axe: /?scale=minmax has no violations', async () => {
    const entry = axeReport.find((item) => item.page === '/?scale=minmax');
    expect(entry, '/?scale=minmax axe entry missing');
    expectEqual(entry.violations.length, 0, 'min–max overview violations');
    return '0 axe violations';
  });

  await check('axe: /rankings has no violations', async () => {
    const entry = axeReport.find((item) => item.page === '/rankings');
    expect(entry, 'rankings axe entry missing');
    expectEqual(entry.violations.length, 0, 'rankings violations');
    return '0 axe violations';
  });

  await check('axe: overview panes 3–8 have no violations in both methods', async () => {
    for (const page of [
      '/?pane=3',
      '/?pane=4',
      '/?pane=5',
      '/?pane=6',
      '/?pane=7',
      '/?pane=8',
      '/?pane=4&scale=minmax',
      '/?pane=5&scale=minmax',
      '/?pane=7&scale=minmax',
      '/?pane=8&scale=minmax',
    ]) {
      const entry = axeReport.find((item) => item.page === page);
      expect(entry, `${page} axe entry missing`);
      expectEqual(entry.violations.length, 0, `${page} violations`);
    }
    return '0 axe violations on panes 3–8 (z and min–max)';
  });

  await check('axe: /rankings?scale=minmax has no violations', async () => {
    const entry = axeReport.find((item) => item.page === '/rankings?scale=minmax');
    expect(entry, 'min–max rankings axe entry missing');
    expectEqual(entry.violations.length, 0, 'min–max rankings violations');
    return '0 axe violations';
  });

  await check('axe: no aria-prohibited-attr on the expanded profile', async () => {
    const entry = axeReport.find((item) => item.page === '/country/IND?open=harness.ai');
    expect(entry, 'expanded profile axe entry missing');
    const flagged = [...entry.violations, ...entry.incomplete].filter(
      (item) => item.id === 'aria-prohibited-attr',
    );
    expect(
      flagged.length === 0,
      `aria-prohibited-attr still present: ${JSON.stringify(flagged)}`,
    );
    return 'aria-prohibited-attr absent (violations + needs review)';
  });

  await check('axe: expanded profile has no violations', async () => {
    const entry = axeReport.find((item) => item.page === '/country/IND?open=harness.ai');
    expectEqual(entry.violations.length, 0, 'expanded profile violations');
    return '0 axe violations';
  });

  await check('axe: missing-data profile has no violations', async () => {
    const entry = axeReport.find((item) => item.page === '/country/CRI?open=harness.ai');
    expectEqual(entry.violations.length, 0, 'Costa Rica violations');
    const prohibited = [...entry.violations, ...entry.incomplete].filter(
      (item) => item.id === 'aria-prohibited-attr',
    );
    expect(prohibited.length === 0, 'aria-prohibited-attr on the missing-data page');
    return '0 axe violations';
  });

  await check('Partial data chip carries coverage in text', async () => {
    const chip = page.locator('.chip--partial').first();
    await chip.waitFor();
    const aria = await chip.getAttribute('aria-label');
    const text = (await chip.textContent()).replace(/\s+/g, ' ');
    expect(aria === null, `chip still has aria-label=${aria}`);
    expectMatch(text, /coverage \d+%/i, 'chip text');
    return text.trim();
  });

  await check('orange (#FF5E00) is never used as text', async () => {
    const bad = [];
    for (const url of [
      '/',
      '/?scale=minmax',
      '/?pane=4&scale=minmax',
      '/?pane=5',
      '/?pane=6',
      '/?pane=7',
      '/?pane=8',
      '/rankings',
      '/country/IND',
    ]) {
      const target = await newPage(desktopViewport);
      await target.goto(`${server.base}${url}`, { waitUntil: 'load' });
      await settle(target);
      const hits = await target.evaluate(() => {
        const found = [];
        for (const element of document.querySelectorAll('*')) {
          if (getComputedStyle(element).color === 'rgb(255, 94, 0)') {
            found.push({
              tag: element.tagName,
              cls: String(element.className).slice(0, 60),
              text: (element.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 50),
            });
          }
        }
        return found;
      });
      if (hits.length > 0) bad.push({ url, hits: hits.slice(0, 5) });
      await target.close();
    }
    expect(bad.length === 0, `computed color rgb(255, 94, 0) found: ${JSON.stringify(bad)}`);
    return '0 elements resolve to rgb(255, 94, 0) on /, panes 5–8, /rankings or /country/IND';
  });

  await tab.close();
  await page.close();
  await overview.close();
  await mobileOverview.close();
  await country.close();
  await method.close();
  if (narrowPage) await narrowPage.close();
} finally {
  await browser.close().catch(() => {});
  await server.close();
}

/* ------------------------------------------------------------------ report */

const failed = checks.filter((c) => !c.ok);
const PASS = '\u001b[32mPASS\u001b[0m';
const FAIL = '\u001b[31mFAIL\u001b[0m';

console.log('');
console.log('SIDE / CHIPS — browser verification');
console.log(`  engine   Playwright WebKit ${engineVersion} · headless only (no Firefox, no Chrome, no headed window)`);
console.log(`  axe-core ${axe.version}`);
console.log(`  server   ${server.base} → web/dist`);
console.log('');
console.log('Behaviour');
for (const c of checks) {
  console.log(`  ${c.ok ? PASS : FAIL}  ${c.name}${c.detail ? `\n        ${c.detail}` : ''}`);
}

console.log('');
console.log('Accessibility — axe-core (violations are reported, not fatal)');
const byImpact = {};
let violationTotal = 0;
for (const { page, violations, incomplete } of axeReport) {
  if (violations.length === 0) {
    console.log(`  ${page}: 0 violations`);
  } else {
    console.log(`  ${page}: ${violations.length} rule${violations.length === 1 ? '' : 's'} violated`);
    for (const v of violations) {
      violationTotal += 1;
      byImpact[v.impact] = (byImpact[v.impact] ?? 0) + 1;
      console.log(`    ${v.impact.padEnd(9)} ${v.id} — ${v.help} (${v.nodes.length} node${v.nodes.length === 1 ? '' : 's'})`);
      for (const n of v.nodes.slice(0, 4)) {
        console.log(`              ${n.target}`);
        if (n.summary) console.log(`              ↳ ${n.summary}`);
      }
      if (v.nodes.length > 4) console.log(`              … ${v.nodes.length - 4} more node(s)`);
    }
  }
  if (incomplete.length) {
    console.log(
      `    needs review: ${incomplete.map((v) => `${v.id} (${v.impact}, ${v.nodes.length} node${v.nodes.length === 1 ? '' : 's'})`).join(' · ')}`,
    );
  }
}
console.log('');
console.log(
  `  totals by impact: ${
    Object.keys(byImpact).length
      ? Object.entries(byImpact).map(([k, v]) => `${k} ${v}`).join(' · ')
      : 'none'
  } (${violationTotal} rule violation${violationTotal === 1 ? '' : 's'} across ${axeReport.length} pages)`,
);

console.log('');
console.log('Screenshots (web/.verify/)');
for (const s of shots) {
  console.log(`  ${s.name.padEnd(28)} ${(s.bytes / 1024).toFixed(1)} KiB`);
}

console.log('');
if (failed.length) {
  console.log(`${failed.length} of ${checks.length} behaviour checks FAILED:`);
  for (const f of failed) console.log(`  ✗ ${f.name} — ${f.detail}`);
} else {
  console.log(`All ${checks.length} behaviour checks passed.`);
}
if (tabTrace.length) {
  console.log('');
  console.log('Tab trace on /rankings (WebKit tabs form controls here; macOS Safari does not');
  console.log('include links unless "Tab highlights each item on webpage" is on):');
  tabTrace.forEach((stop, i) => console.log(`  ${i + 1}. ${stop}`));
}

await writeFile(
  path.join(OUT, 'report.json'),
  JSON.stringify({ checks, axe: axeReport, screenshots: shots, tabTrace }, null, 2),
);

console.log('');
process.exit(failed.length ? 1 : 0);
