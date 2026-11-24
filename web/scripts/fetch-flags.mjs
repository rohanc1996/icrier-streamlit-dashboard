#!/usr/bin/env node
/**
 * Dev-time only: vendor the round country flags the overview panes draw.
 *
 *   node scripts/fetch-flags.mjs
 *
 * Not part of the build. The SVGs it writes are committed, so a build (or a
 * clone with no network) never reaches for a CDN. The set is exactly the union
 * `allFlagIso2s()` puts in the page sprite — every country the editions carry,
 * because a grouping flags all of its members (and a custom grouping can name
 * any country). Panes 1 and 7 draw flags and the scale and group controls swap
 * what they flag. The rule lives in `src/lib/flags.mjs` so this script cannot
 * drift from the build.
 *
 * Upstream: https://github.com/HatScripts/circle-flags — MIT.
 */
import { access, mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { editionsFlagIso3s } from '../src/lib/flags.mjs';
import { iso2For } from '../src/lib/iso.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const EDITIONS = path.join(ROOT, '..', 'data', 'derived', 'web', 'editions.json');
const OUT_DIR = path.join(ROOT, 'src', 'assets', 'flags');
const BASE = 'https://hatscripts.github.io/circle-flags/flags';

const payload = JSON.parse(await readFile(EDITIONS, 'utf8'));
const wanted = editionsFlagIso3s(payload.editions);
if (wanted.length === 0) {
  throw new Error('no flagged countries; run pipeline/export_editions.py first');
}

const missingIso2 = wanted.filter((iso3) => iso2For(iso3) === null);
if (missingIso2.length > 0) {
  throw new Error(`no alpha-2 code for ${missingIso2.join(', ')} — extend src/lib/iso.mjs`);
}

await mkdir(OUT_DIR, { recursive: true });

let fetched = 0;
let bytes = 0;
for (const iso3 of wanted) {
  const iso2 = iso2For(iso3);
  const file = path.join(OUT_DIR, `${iso2}.svg`);
  try {
    await access(file);
    console.log(`  ${iso2}.svg  ${iso3}  (already vendored)`);
    continue;
  } catch {
    // Not vendored yet: fetch it below.
  }
  const url = `${BASE}/${iso2}.svg`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url} → HTTP ${response.status}`);
  }
  const svg = await response.text();
  if (!svg.startsWith('<svg') || !svg.includes('viewBox="0 0 512 512"')) {
    throw new Error(`${url} is not a 512×512 circle-flag SVG`);
  }
  await writeFile(file, svg, 'utf8');
  const size = Buffer.byteLength(svg, 'utf8');
  bytes += size;
  fetched += 1;
  console.log(`  ${iso2}.svg  ${iso3}  ${size} B`);
}

console.log(`\n${wanted.length} flags needed · ${fetched} fetched · ${bytes} B → src/assets/flags/`);
