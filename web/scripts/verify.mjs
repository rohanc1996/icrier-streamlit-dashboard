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

const WEB_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DIST = path.join(WEB_ROOT, 'dist');
const OUT = path.join(WEB_ROOT, '.verify');

// The same generated payload the site built from (prebuild copies it to src/).
const CHIPS = JSON.parse(
  await readFile(path.join(WEB_ROOT, 'src', 'data', '2026', 'chips.json'), 'utf8'),
);

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
  /* ---------------------------------------------------------- desktop: `/` */
  const page = await newPage(desktopViewport);
  await page.goto(`${server.base}/`, { waitUntil: 'networkidle' });
  await settle(page);

  await check('/ renders 71 data rows', async () => {
    await rowsOf(page).first().waitFor();
    const n = await rowsOf(page).count();
    expectEqual(n, 71, 'table tbody tr count');
    return '71 rows';
  });

  await check('/ links to 71 /country/{ISO3} pages', async () => {
    const n = await page.locator('a[href^="/country/"]').count();
    expectEqual(n, 71, 'country link count');
    return '71 links';
  });

  await check('default scale is full_minmax', async () => {
    const checked = await page.locator('input[name="scale"]:checked').inputValue();
    expectEqual(checked, 'full_minmax', 'checked scale');
    expect(!page.url().includes('scale='), `URL should not carry scale=, got ${page.url()}`);
    return 'full_minmax, no scale param';
  });

  await check('Saudi Arabia row: rank 55, score 18.03', async () => {
    const text = await saudiRow(page).innerText();
    const cells = await saudiRow(page).locator('td').allInnerTexts();
    expectEqual(num(cells[0]), 55, 'rank');
    expectEqual(num(cells[2]), 18.03, 'score');
    return `${cells[0].trim()} / ${cells[2].trim()} (${text.split('\n')[1]})`;
  });

  await shot(page, 'desktop-rankings.png', true);

  await check('click Z-score → URL gains scale=z', async () => {
    await page.getByRole('radio', { name: 'Z-score' }).check();
    await settle(page);
    expectMatch(page.url(), /[?&]scale=z(&|$)/, 'URL');
    return page.url().replace(server.base, '');
  });

  await check('Z-score: Saudi Arabia rank 36, score 46.20', async () => {
    const cells = await saudiRow(page).locator('td').allInnerTexts();
    expectEqual(num(cells[0]), 36, 'rank');
    expectEqual(num(cells[2]), 46.2, 'score');
    expectEqual(cells[2].trim(), '46.20', 'score text');
    return '36 / 46.20';
  });

  await check('Z-score: rank-movement cell reads +19', async () => {
    const cell = saudiRow(page).locator('td.movement-col');
    await cell.waitFor();
    const text = await cell.innerText();
    expectMatch(text.replace(/\s+/g, ' '), /\+19/, 'movement cell text');
    return JSON.stringify(text.replace(/\s+/g, ' ').trim());
  });

  await shot(page, 'desktop-rankings-z.png', true);

  await check('reload ?scale=z keeps Z-score active', async () => {
    await page.goto(`${server.base}/?scale=z`, { waitUntil: 'networkidle' });
    await settle(page);
    const checked = await page.locator('input[name="scale"]:checked').inputValue();
    expectEqual(checked, 'z', 'checked scale after reload');
    const cells = await saudiRow(page).locator('td').allInnerTexts();
    expectEqual(num(cells[0]), 36, 'rank after reload');
    return 'z active, rank 36';
  });

  await check('switch back to min–max drops scale=z from URL', async () => {
    await page.getByRole('radio', { name: 'Min–max' }).check();
    await settle(page);
    expect(!page.url().includes('scale='), `URL still carries scale=: ${page.url()}`);
    const checked = await page.locator('input[name="scale"]:checked').inputValue();
    expectEqual(checked, 'full_minmax', 'checked scale');
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
  await country.goto(`${server.base}/country/IND`, { waitUntil: 'networkidle' });
  await settle(country);

  await check('/country/IND renders India, rank 3, composite 40.41', async () => {
    const h1 = (await country.locator('h1').innerText()).trim();
    expectEqual(h1, 'India', 'h1');
    const head = await country.locator('.country-head').innerText();
    expectMatch(head.replace(/\s+/g, ' '), /Rank 3 of 71/, 'rank line');
    const score = (await country.locator('.country-head__score .display-xl').innerText()).trim();
    expectEqual(score, '40.41', 'composite score');
    return `India · rank 3 of 71 · score ${score}`;
  });

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

    await country.goto(`${server.base}/country/IND?open=harness.ai`, {
      waitUntil: 'networkidle',
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
      waitUntil: 'networkidle',
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
    await country.goto(`${server.base}/country/IND?open=harness`, { waitUntil: 'networkidle' });
    await settle(country);
    await waitOpen('HARNESS');
    expectEqual(await cardButton('HARNESS').getAttribute('aria-expanded'), 'true', 'HARNESS open');
    expectEqual(await cardButton('CONNECT').getAttribute('aria-expanded'), 'false', 'CONNECT closed');
    return 'HARNESS open after reload';
  });

  await check('opening INNOVATE closes the previous pillar', async () => {
    await country.goto(`${server.base}/country/IND`, { waitUntil: 'networkidle' });
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
    await country.goto(`${server.base}/country/IND`, { waitUntil: 'networkidle' });
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
    await country.goto(`${server.base}/country/CRI?open=harness.ai`, { waitUntil: 'networkidle' });
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
      waitUntil: 'networkidle',
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
    await country.goto(`${server.base}/country/IND?open=harness`, { waitUntil: 'networkidle' });
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
    await country.goto(`${server.base}/country/IND`, { waitUntil: 'networkidle' });
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
    await country.goto(`${server.base}/country/IND?open=harness`, { waitUntil: 'networkidle' });
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
    waitUntil: 'networkidle',
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
  await method.goto(`${server.base}/methodology`, { waitUntil: 'networkidle' });
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
  await tab.goto(`${server.base}/`, { waitUntil: 'networkidle' });
  await settle(tab);

  await check('Tab from top of / reaches the filter input within 10 stops', async () => {
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
  await mobilePage.goto(`${server.base}/`, { waitUntil: 'networkidle' });
  await settle(mobilePage);

  await check('390px: no horizontal scroll', async () => {
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

  /* ------------------------------------------------------------------ axe */
  for (const label of [
    '/',
    '/country/IND',
    '/country/IND?open=harness.ai',
    '/country/CRI?open=harness.ai',
    '/methodology',
    '/about',
  ]) {
    const target = await newPage(desktopViewport);
    await target.goto(`${server.base}${label}`, { waitUntil: 'networkidle' });
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

  await tab.close();
  await page.close();
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
  console.log('Tab trace on / (WebKit tabs form controls here; macOS Safari does not');
  console.log('include links unless "Tab highlights each item on webpage" is on):');
  tabTrace.forEach((stop, i) => console.log(`  ${i + 1}. ${stop}`));
}

await writeFile(
  path.join(OUT, 'report.json'),
  JSON.stringify({ checks, axe: axeReport, screenshots: shots, tabTrace }, null, 2),
);

console.log('');
process.exit(failed.length ? 1 : 0);
