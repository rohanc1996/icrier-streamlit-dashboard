#!/usr/bin/env node
/**
 * Dev-time only: vendor the round country flags the overview panes draw.
 *
 *   node scripts/fetch-flags.mjs
 *
 * Not part of the build. The SVGs it writes are committed, so a build (or a
 * clone with no network) never reaches for a CDN. The set is exactly the union
 * `overviewFlagIso2s()` puts in the page sprite — the top 15 by score in each
 * method, unioned with each method's top-15 list — because panes 1, 2, 7 and 8
 * all draw flags and the scale toggle swaps the whole pane block. The rule
 * lives in `src/lib/flags.mjs` so this script cannot drift from the build.
 *
 * Upstream: https://github.com/HatScripts/circle-flags — MIT.
 */
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { pageFlagIso3s, methodFlagIso3s } from '../src/lib/flags.mjs';
import { iso2For } from '../src/lib/iso.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OVERVIEW = path.join(ROOT, '..', 'data', 'derived', 'web', 'overview.json');
const OUT_DIR = path.join(ROOT, 'src', 'assets', 'flags');
const BASE = 'https://hatscripts.github.io/circle-flags/flags';

const overview = JSON.parse(await readFile(OVERVIEW, 'utf8'));

const wanted = pageFlagIso3s(overview.methods);
if (wanted.length === 0) {
  throw new Error('no flagged countries; run npm run sync-data first');
}

for (const [id, method] of Object.entries(overview.methods ?? {})) {
  const iso3s = methodFlagIso3s(method?.field?.values, method?.top15);
  if (iso3s.length === 0) {
    throw new Error(`no field values for method ${id}; run npm run sync-data first`);
  }
  console.log(`${id.padEnd(12)} ${iso3s.join(' ')}`);
}

const missing = wanted.filter((iso3) => iso2For(iso3) === null);
if (missing.length > 0) {
  throw new Error(`no alpha-2 code for ${missing.join(', ')} — extend src/lib/iso.mjs`);
}

await mkdir(OUT_DIR, { recursive: true });

let bytes = 0;
for (const iso3 of wanted) {
  const iso2 = iso2For(iso3);
  const url = `${BASE}/${iso2}.svg`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url} → HTTP ${response.status}`);
  }
  const svg = await response.text();
  if (!svg.startsWith('<svg') || !svg.includes('viewBox="0 0 512 512"')) {
    throw new Error(`${url} is not a 512×512 circle-flag SVG`);
  }
  const file = path.join(OUT_DIR, `${iso2}.svg`);
  await writeFile(file, svg, 'utf8');
  const size = Buffer.byteLength(svg, 'utf8');
  bytes += size;
  console.log(`  ${iso2}.svg  ${iso3}  ${size} B`);
}

console.log(`\n${wanted.length} flags · ${bytes} B raw → src/assets/flags/`);
