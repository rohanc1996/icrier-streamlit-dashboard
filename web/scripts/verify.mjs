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

  await check('/ renders seven panes, exactly one visible', async () => {
    const panes = await overview.locator('.carousel__pane').count();
    expectEqual(panes, 7, 'carousel pane count');
    expectEqual(await overview.locator('.carousel__pane:not([hidden])').count(), 1, 'visible panes');
    expectEqual(await overview.locator('[data-pane="8"]').count(), 0, 'pane 8 still present');
    return '7 panes, pane 1 visible';
  });

  await check('the filter bar names the active view in text', async () => {
    const text = (await overview.locator('.filterbar__selection').innerText()).replace(/\s+/g, ' ');
    expectMatch(text, /Combined \(50–50\)/, 'basis in summary');
    expectMatch(text, /2026/, 'year in summary');
    expectMatch(text, /All countries/, 'group in summary');
    expectMatch(text, /Z-score/, 'normalization in summary');
    return JSON.stringify(text.trim());
  });

  await check('the bar is one compact row and pins below the header', async () => {
    const height = (await overview.locator('.filterbar').boundingBox()).height;
    expect(height <= 72, `filter bar is ${height}px tall`);
    const expanded = await overview.locator('.filterbar__toggle').getAttribute('aria-expanded');
    expectEqual(expanded, 'false', 'panel starts closed');

    await overview.evaluate(() => window.scrollTo(0, 900));
    await settle(overview);
    const alignment = await overview.evaluate(() => {
      const header = document.querySelector('.site-header')?.getBoundingClientRect();
      const bar = document.querySelector('.filterbar')?.getBoundingClientRect();
      return header && bar ? Math.round(bar.top - header.bottom) : null;
    });
    expect(alignment !== null && Math.abs(alignment) <= 2, `bar is ${alignment}px from the header`);
    await overview.evaluate(() => window.scrollTo(0, 0));
    return `${Math.round(height)}px; sticks ${alignment}px below the header`;
  });

  await check('Edit filters expands in flow, pushing the pane down', async () => {
    // The previous check ends with scrollTo(0, 0); let any smooth scroll
    // finish before measuring positions.
    await overview.evaluate(() => window.scrollTo(0, 0));
    await settle(overview);
    const closedHeight = (await overview.locator('.filterbar').boundingBox()).height;
    const closedTop = (await pane(1).boundingBox()).y;
    await overview.locator('.filterbar__toggle').click();
    await settle(overview);
    expect(await overview.locator('#view-filters-panel').isVisible(), 'panel did not open');
    const panelHeight = (await overview.locator('#view-filters-panel').boundingBox()).height;
    const openHeight = (await overview.locator('.filterbar').boundingBox()).height;
    const openTop = (await pane(1).boundingBox()).y;
    expect(openHeight - closedHeight > 50, `bar grew only ${openHeight - closedHeight}px`);
    expect(
      Math.abs(openHeight - closedHeight - panelHeight) <= 2,
      `bar grew ${openHeight - closedHeight}px but panel is ${panelHeight}px`,
    );
    expect(
      Math.abs(openTop - closedTop - panelHeight) <= 2,
      `pane moved ${openTop - closedTop}px but panel is ${panelHeight}px`,
    );

    await overview.keyboard.press('Escape');
    await settle(overview);
    expect(await overview.locator('#view-filters-panel').isHidden(), 'Escape did not close the panel');
    const restored = (await pane(1).boundingBox()).y;
    expect(Math.abs(restored - closedTop) <= 1, `pane did not return (${restored} vs ${closedTop})`);
    return `panel ${Math.round(panelHeight)}px pushes the pane down and back`;
  });

  await check('pane 1 draws every scored country and the median', async () => {
    const dots = await overview.locator('.field-chart__dot').count();
    const flags = await overview.locator('.field-chart .flag-mark').count();
    expectEqual(dots + flags, 71, 'field marks');
    expectEqual(await overview.locator('.field-chart__median').count(), 1, 'median line');
    return `${dots} dots + ${flags} flags, median tick`;
  });

  await check('pane 1 has a View data disclosure with 71 rows', async () => {
    await pane(1).locator('details.pane__table summary').click();
    const rows = await pane(1).locator('details.pane__table tbody tr').count();
    expectEqual(rows, 71, 'pane 1 table rows');
    return '71 rows';
  });

  await check('pane 2 defaults to all countries, not a silent top N', async () => {
    await overview.goto(`${server.base}/?pane=2`, { waitUntil: 'load' });
    await settle(overview);
    const rows = await pane(2).locator('.rank-bars__row').count();
    expectEqual(rows, 71, 'rank bar rows');
    expectEqual(await pane(2).locator('#rank-bar-count').inputValue(), 'all', 'default top-N');
    return '71 rows, show = All countries';
  });

  await check('pane 2 top-N control cuts explicitly', async () => {
    await pane(2).locator('#rank-bar-count').selectOption('10');
    await settle(overview);
    const rows = await pane(2).locator('.rank-bars__row').count();
    expectEqual(rows, 10, 'rows after Top 10');
    await pane(2).locator('#rank-bar-count').selectOption('all');
    return 'Top 10 → 10 rows, then back to all';
  });

  await check('pane 3 defaults to all and its control cuts explicitly', async () => {
    await overview.goto(`${server.base}/?pane=3`, { waitUntil: 'load' });
    await settle(overview);
    expectEqual(await pane(3).locator('.composition__row').count(), 71, 'composition rows');
    await pane(3).locator('#composition-count').selectOption('10');
    await settle(overview);
    expectEqual(await pane(3).locator('.composition__row').count(), 10, 'rows after Top 10');
    await pane(3).locator('#composition-count').selectOption('all');
    return '71 → 10 → 71';
  });

  await check('pane 4 follows the comparison country', async () => {
    await overview.goto(`${server.base}/?pane=4&compare=USA`, { waitUntil: 'load' });
    await settle(overview);
    const headline = await pane(4).locator('.verdicts__headline').innerText();
    expectMatch(headline, /United States/, 'verdict headline');
    expectEqual(await pane(4).locator('.verdicts__row').count(), 5, 'verdict rows');
    return headline.trim().split('\n')[0];
  });

  await check('pane 5 is ranks only — no score is compared across years', async () => {
    await overview.goto(`${server.base}/?pane=5&year=2025,2026`, { waitUntil: 'load' });
    await settle(overview);
    const headers = (await pane(5).locator('table thead').innerText()).replace(/\s+/g, ' ');
    expect(!/score/i.test(headers), `tracker header mentions score: ${headers}`);
    expectMatch(headers, /2025 rank/, '2025 rank column');
    expectMatch(headers, /2026 rank/, '2026 rank column');
    const callout = await pane(5).locator('.pane__callout').innerText();
    expectMatch(callout, /method, indicators and weights changed/i, 'caveat');
    return headers.trim();
  });

  await check('pane 5 re-ranks the 38-country intersection within the subset', async () => {
    const rows = await pane(5).locator('.tracker__table tbody tr').count();
    expectEqual(rows, 38, 'tracker rows');
    const first = pane(5).locator('.tracker__table tbody tr').first();
    const cells = (await first.locator('td').allInnerTexts()).map((value) =>
      value.replace(/\s+/g, ' ').trim(),
    );
    expectEqual((await first.locator('th').innerText()).trim(), 'USA', 'first row by latest rank');
    expect(cells[cells.length - 1].startsWith('1'), `USA latest rank is ${cells[cells.length - 1]}`);
    return `${rows} rows; USA ${cells.join(' | ')}`;
  });

  await check('pane 5 draws every country in every selected year', async () => {
    const lines = await pane(5).locator('[data-tracker]').count();
    expectEqual(lines, 38, 'country paths');
    const dots = await pane(5).locator('.tracker__dot').count();
    expectEqual(dots, 76, 'rank dots (38 × 2 years)');
    const labels = await pane(5).locator('.tracker__label').count();
    expect(labels > 0, 'no highlighted labels');
    return `${lines} paths, ${dots} dots, ${labels} labels`;
  });

  await check('pane 5 labels the movers at every year, not just the last', async () => {
    const labels = await pane(5)
      .locator('.tracker__label')
      .evaluateAll((nodes) => nodes.map((node) => node.textContent ?? ''));
    const years = await pane(5).locator('.tracker__year').allInnerTexts();
    expect(years.length >= 2, `only ${years.length} year markers`);
    expect(labels.every((text) => /\d/.test(text)), 'a label carries no rank');
    return `${labels.length} labels across ${years.join(' / ')}`;
  });

  await check('pane 6 defaults to the smallest absolute rank difference', async () => {
    await overview.goto(`${server.base}/?pane=6`, { waitUntil: 'load' });
    await settle(overview);
    const deltas = await pane(6).locator('.delta-pill').allInnerTexts();
    const numbers = deltas.map((text) => Math.abs(Number(text.replace('−', '-'))));
    expect(numbers[0] === 0, `first delta is ${deltas[0]}, not 0`);
    for (let i = 1; i < numbers.length; i += 1) {
      expect(numbers[i] >= numbers[i - 1], `deltas not ascending at ${i}: ${deltas[i]}`);
    }
    return `${deltas.length} rows, first three ${deltas.slice(0, 3).join(' / ')}`;
  });

  await check('pane 6 headers sort the table', async () => {
    await pane(6).getByRole('button', { name: /Difference/ }).click();
    await settle(overview);
    const deltas = await pane(6).locator('.delta-pill').allInnerTexts();
    const numbers = deltas.map((text) => Math.abs(Number(text.replace('−', '-'))));
    expect(numbers[0] >= numbers[numbers.length - 1], 'descending sort failed');
    return `largest first: ${deltas[0]}`;
  });

  await check('pane 6 states individual ranks do not move', async () => {
    const note = await pane(6).locator('.micro.hint').last().innerText();
    expectMatch(note, /monotone transform/i, 'monotonicity caption');
    return 'caption present';
  });

  await check('pane 7 draws all 71 countries on a GDP axis', async () => {
    await overview.goto(`${server.base}/?pane=7`, { waitUntil: 'load' });
    await settle(overview);
    const points = await pane(7).locator('[data-scatter]').count();
    expectEqual(points, 71, 'scatter marks');
    expectEqual(await pane(7).locator('.scatter-chart--sizeScore').count(), 1, 'size scatter');
    return '71 marks';
  });

  await check('deep link restores basis, years, group, comparison and pane', async () => {
    await overview.goto(
      `${server.base}/?year=2025,2026&basis=absolute&group=g20&compare=IND,USA&pane=2`,
      { waitUntil: 'load' },
    );
    await settle(overview);
    const summary = (await overview.locator('.filterbar__selection').innerText()).replace(/\s+/g, ' ');
    expectMatch(summary, /Absolute/, 'basis');
    expectMatch(summary, /2025 and 2026/, 'years');
    expectMatch(summary, /G20/, 'group');
    expectMatch(summary, /comparing IND vs USA/, 'comparison');
    expectEqual(await livePane(), '2', 'active pane');
    const rows = await pane(2).locator('.rank-bars__row').count();
    expectEqual(rows, 19, 'G20 rows');
    return JSON.stringify(summary.trim());
  });

  await check('a basis with no file for the year is disabled, not hidden', async () => {
    await overview.goto(`${server.base}/?year=2025&basis=relative`, { waitUntil: 'load' });
    await settle(overview);
    const relative = overview.locator('input[name="score-basis"][value="relative"]');
    expect(await relative.isDisabled(), 'Relative is enabled for 2025');
    const summary = await overview.locator('.filterbar__selection').innerText();
    expectMatch(summary, /Absolute/, 'basis fell back to Absolute');
    return 'Relative disabled on 2025, Absolute active';
  });

  await check('downloads are real CSV links', async () => {
    const links = await overview.locator('.downloads a').evaluateAll((nodes) =>
      nodes.map((node) => node.getAttribute('href')),
    );
    expect(links.length >= 3, `only ${links.length} download links`);
    for (const href of links) {
      const response = await overview.request.get(`${server.base}${href}`);
      expectEqual(response.status(), 200, `download ${href}`);
      const body = await response.text();
      expect(body.split('\n').length > 3, `download ${href} is empty`);
    }
    return `${links.length} CSVs resolve`;
  });

  for (let paneNumber = 1; paneNumber <= 7; paneNumber += 1) {
    await overview.goto(`${server.base}/?pane=${paneNumber}`, { waitUntil: 'load' });
    await settle(overview);
    await shot(overview, `desktop-overview-pane${paneNumber}.png`, true);
  }

  await check('Reset view returns to the defaults', async () => {
    await overview.goto(`${server.base}/?pane=2&group=g20&basis=absolute`, { waitUntil: 'load' });
    await settle(overview);
    await overview.locator('.filterbar__reset').click();
    await settle(overview);
    const summary = await overview.locator('.filterbar__selection').innerText();
    expectMatch(summary, /Combined \(50–50\)/, 'basis after reset');
    expectMatch(summary, /All countries/, 'group after reset');
    expectEqual(new URL(overview.url()).search, '', 'query string after reset');
    return 'back to combined / 2026 / all / min–max';
  });

  await check('arrow keys move panes and Home/End jump to the ends', async () => {
    await overview.goto(`${server.base}/`, { waitUntil: 'load' });
    await settle(overview);
    await overview.keyboard.press('ArrowRight');
    await settle(overview);
    expectEqual(await livePane(), '2', 'after ArrowRight');
    await overview.keyboard.press('End');
    await settle(overview);
    expectEqual(await livePane(), '7', 'after End');
    await overview.keyboard.press('Home');
    await settle(overview);
    expectEqual(await livePane(), '1', 'after Home');
    return '→ 2, End 7, Home 1';
  });

  /* -------------------------------------------------------- mobile: overview */
  const mobile = await newPage(mobileViewport);
  await mobile.goto(`${server.base}/`, { waitUntil: 'load' });
  await settle(mobile);

  await check('mobile: the bar is one compact row with a closed panel', async () => {
    const bar = mobile.locator('.filterbar__bar');
    const height = (await bar.boundingBox()).height;
    expect(height <= 72, `bar is ${height}px tall`);
    expect(await mobile.locator('#view-filters-panel').isHidden(), 'panel is visible by default');
    const overflow = await mobile.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expectEqual(overflow, 0, 'horizontal overflow');
    return `${Math.round(height)}px bar, panel closed, no horizontal scroll`;
  });

  await check('mobile: opening Edit filters reveals the controls', async () => {
    await mobile.locator('.filterbar__toggle').click();
    await settle(mobile);
    expect(await mobile.locator('#view-filters-panel').isVisible(), 'panel did not open');
    expect(await mobile.getByRole('radio', { name: 'Combined (50–50)' }).isVisible(), 'basis control hidden');
    expect(await mobile.getByRole('checkbox', { name: '2026' }).isVisible(), 'year control hidden');
    await shot(mobile, 'mobile-overview-filters.png', true);
    return 'controls visible';
  });

  await check('mobile: each pane has no horizontal scroll', async () => {
    const results = [];
    for (let n = 1; n <= 7; n += 1) {
      await mobile.goto(`${server.base}/?pane=${n}`, { waitUntil: 'load' });
      await settle(mobile);
      const overflow = await mobile.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      results.push(`${n}:${overflow}`);
      expectEqual(overflow, 0, `pane ${n} overflow`);
      await shot(mobile, `mobile-overview-pane${n}.png`, true);
    }
    return results.join(' ');
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
    expectEqual(checked, 'z', 'checked scale');
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
    expectEqual(checked, 'full_minmax', 'checked scale after reload');
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

  await check('390px: overview has no horizontal scroll', async () => {
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

  await check('390px: the filter bar stays one row and its targets stay usable', async () => {
    const barHeight = (await mobileOverview.locator('.filterbar__bar').boundingBox()).height;
    expect(barHeight <= 72, `bar is ${barHeight}px tall`);
    await mobileOverview.locator('.filterbar__toggle').click();
    await settle(mobileOverview);
    const sizes = await mobileOverview.evaluate(() => {
      const controls = Array.from(
        document.querySelectorAll(
          '.filterbar select, .filterbar button, .segmented__option span',
        ),
      ).filter((el) => el.getClientRects().length > 0);
      return controls.map((el) => {
        const box = el.getBoundingClientRect();
        return { w: Math.round(box.width), h: Math.round(box.height) };
      });
    });
    const small = sizes.filter((size) => size.h > 0 && size.h < 24);
    expect(small.length === 0, `${small.length} controls under 24px`);
    return `${sizes.length} controls, smallest height ${Math.min(...sizes.map((s) => s.h).filter((h) => h > 0))}px`;
  });

  await check('390px: all seven panes render without horizontal scroll', async () => {
    const widths = [];
    for (let n = 1; n <= 7; n += 1) {
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

  /* ------------------------------------------------------- 1366 × 768 */
  const laptop = await newPage({ width: 1366, height: 768 });
  await laptop.goto(`${server.base}/`, { waitUntil: 'load' });
  await settle(laptop);

  await check('1366×768: no pane is clipped or scrolls sideways', async () => {
    const widths = [];
    for (let n = 1; n <= 7; n += 1) {
      await laptop.goto(`${server.base}/?pane=${n}`, { waitUntil: 'load' });
      await settle(laptop);
      const [scrollWidth, innerWidth] = await laptop.evaluate(() => [
        document.documentElement.scrollWidth,
        window.innerWidth,
      ]);
      expect(scrollWidth <= innerWidth, `pane ${n} overflows at 1366px`);
      widths.push(`${n}:${scrollWidth}`);
    }
    await shot(laptop, 'laptop-overview-1366.png', true);
    return widths.join(' ');
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
    '/?pane=4&scale=z',
    '/?pane=5&scale=z',
    '/?pane=7&scale=z',
    '/?year=2025,2026&basis=absolute&group=g20&pane=5',
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

  await check('axe: overview panes 3–7 have no violations in both methods', async () => {
    for (const page of [
      '/?pane=3',
      '/?pane=4',
      '/?pane=5',
      '/?pane=6',
      '/?pane=7',
      '/?pane=4&scale=z',
      '/?pane=5&scale=z',
      '/?pane=7&scale=z',
      '/?year=2025,2026&basis=absolute&group=g20&pane=5',
    ]) {
      const entry = axeReport.find((item) => item.page === page);
      expect(entry, `${page} axe entry missing`);
      expectEqual(entry.violations.length, 0, `${page} violations`);
    }
    return '0 axe violations on panes 3–7 (both methods, tracker view)';
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

  await check('colour: page head, footer and pillar cards carry the structural washes', async () => {
    await overview.goto(`${server.base}/`, { waitUntil: 'load' });
    await settle(overview);
    const overviewColours = await overview.evaluate(() => {
      const strip = document.querySelector('.pillar-strip');
      return {
        head: getComputedStyle(document.querySelector('.page-head')).backgroundColor,
        headPadding: getComputedStyle(document.querySelector('.page-head')).paddingLeft,
        bar: getComputedStyle(document.querySelector('.carousel__bar')).backgroundColor,
        barPadding: getComputedStyle(document.querySelector('.carousel__bar')).paddingLeft,
        footer: getComputedStyle(document.querySelector('.site-footer')).backgroundColor,
        footerText: getComputedStyle(document.querySelector('.site-footer__status')).color,
        stripHeight: strip ? strip.getBoundingClientRect().height : 0,
        stripImage: strip ? getComputedStyle(strip).backgroundImage : '',
      };
    });
    expectEqual(overviewColours.head, 'rgb(239, 233, 221)', 'page-head wash');
    expectEqual(overviewColours.headPadding, '24px', 'page-head inset');
    expectEqual(overviewColours.bar, 'rgb(239, 233, 221)', 'carousel bar wash');
    expectEqual(overviewColours.barPadding, '16px', 'carousel bar inset');
    expectEqual(overviewColours.footer, 'rgb(39, 45, 79)', 'navy footer');
    expectEqual(overviewColours.footerText, 'rgb(250, 248, 245)', 'footer text');
    expectEqual(overviewColours.stripHeight, 4, 'pillar strip height');
    expectMatch(overviewColours.stripImage, /rgb\(15, 118, 110\)/, 'strip HARNESS stop');
    expectMatch(overviewColours.stripImage, /rgb\(184, 74, 0\)/, 'strip SUSTAINABILITY stop');

    await overview.goto(`${server.base}/country/IND`, { waitUntil: 'load' });
    await settle(overview);
    const countryColours = await overview.evaluate(() => ({
      head: getComputedStyle(document.querySelector('.country-masthead')).backgroundColor,
      headPadding: getComputedStyle(document.querySelector('.country-masthead')).paddingLeft,
      cards: Object.fromEntries(
        [...document.querySelectorAll('.pillar-card')].map((card) => [
          card.dataset.pillar,
          getComputedStyle(card).backgroundColor,
        ]),
      ),
    }));
    expectEqual(countryColours.head, 'rgb(239, 233, 221)', 'country masthead wash');
    expectEqual(countryColours.headPadding, '24px', 'country masthead inset');
    const cards = countryColours.cards;
    expectEqual(cards.CONNECT, 'rgb(233, 234, 240)', 'CONNECT tint');
    expectEqual(cards.HARNESS, 'rgb(230, 240, 238)', 'HARNESS tint');
    expectEqual(cards.SUSTAINABILITY, 'rgb(248, 235, 227)', 'SUSTAINABILITY tint');

    await overview.goto(`${server.base}/methodology`, { waitUntil: 'load' });
    await settle(overview);
    const methodology = await overview.evaluate(() => ({
      edge: getComputedStyle(
        document.querySelector('.pillar-details[data-pillar="HARNESS"]'),
      ).borderLeftColor,
      tickWidth: getComputedStyle(
        document.querySelector('.method-section h2'),
        '::before',
      ).width,
      tickColour: getComputedStyle(
        document.querySelector('.method-section h2'),
        '::before',
      ).backgroundColor,
    }));
    expectEqual(methodology.edge, 'rgb(15, 118, 110)', 'methodology pillar edge');
    expectEqual(methodology.tickWidth, '40px', 'section tick width');
    expectEqual(methodology.tickColour, 'rgb(255, 94, 0)', 'section tick colour');
    return 'sand head · navy footer · weighted pillar strip · five pillar tints';
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
