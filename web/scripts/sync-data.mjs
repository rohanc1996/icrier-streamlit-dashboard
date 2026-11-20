// Copies the exporter's generated JSON into the Astro root.
// The source of truth is ../data/derived/web — never edit it from here.
// src/data/ is gitignored: run via the predev / prebuild scripts.
import { cp, mkdir, readFile, rm } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const webRoot = fileURLToPath(new URL('..', import.meta.url));
const repoRoot = path.resolve(webRoot, '..');
const source = path.join(repoRoot, 'data', 'derived', 'web');
const target = path.join(webRoot, 'src', 'data');

const chipsPath = path.join(source, '2026', 'chips.json');

let chips;
try {
  chips = JSON.parse(await readFile(chipsPath, 'utf8'));
} catch (error) {
  console.error(`[sync-data] Could not read ${chipsPath}`);
  console.error(`[sync-data] ${error instanceof Error ? error.message : error}`);
  process.exit(1);
}

// Contract v2: method-split payloads. Fail loudly instead of shipping a
// half-populated table if the exporter has not been regenerated yet.
const problems = [];
if (!chips.meta || typeof chips.meta !== 'object') problems.push('missing meta');
if (!chips.framework || !Array.isArray(chips.framework.pillars)) problems.push('missing framework.pillars');
if (!chips.methods || typeof chips.methods !== 'object') {
  problems.push('missing methods{} (contract v2)');
} else {
  const ids = Object.keys(chips.methods);
  if (ids.length === 0) problems.push('methods{} is empty');
  for (const id of ids) {
    const payload = chips.methods[id];
    if (!Array.isArray(payload?.scores)) problems.push(`methods.${id}.scores is not an array`);
    if (!Array.isArray(payload?.indicators)) problems.push(`methods.${id}.indicators is not an array`);
  }
  if (!chips.meta.defaultMethod || !ids.includes(chips.meta.defaultMethod)) {
    problems.push('meta.defaultMethod does not name a key in methods');
  }
}
if (problems.length > 0) {
  console.error('[sync-data] data/derived/web/2026/chips.json is not contract v2:');
  for (const problem of problems) console.error(`[sync-data]   - ${problem}`);
  console.error('[sync-data] Ask the data agent to regenerate the exporter output. Not copying.');
  process.exit(1);
}

await rm(target, { recursive: true, force: true });
await mkdir(target, { recursive: true });
await cp(source, target, { recursive: true });

// Raw-data downloads are served as static files, so they live in public/.
const downloadsSource = path.join(source, 'downloads');
const downloadsTarget = path.join(webRoot, 'public', 'data');
await rm(downloadsTarget, { recursive: true, force: true });
try {
  await cp(downloadsSource, downloadsTarget, { recursive: true });
  console.log('[sync-data] copied downloads -> public/data');
} catch {
  console.warn('[sync-data] no downloads/ folder yet — run pipeline/export_editions.py');
}

// editions.json is the filter bar's payload: every year × basis × method.
const editionsPath = path.join(source, 'editions.json');
try {
  const editions = JSON.parse(await readFile(editionsPath, 'utf8'));
  const problems = [];
  if (!Array.isArray(editions.meta?.years) || editions.meta.years.length === 0) {
    problems.push('missing meta.years');
  }
  if (!editions.meta?.basisAvailability) problems.push('missing meta.basisAvailability');
  if (!editions.meta?.groups) problems.push('missing meta.groups');
  if (!editions.editions) problems.push('missing editions{}');
  if (!editions.tracker) problems.push('missing tracker{}');
  for (const [year, bases] of Object.entries(editions.editions ?? {})) {
    for (const [basis, block] of Object.entries(bases)) {
      if (!block?.methods?.full_minmax?.field?.values) {
        problems.push(`editions.${year}.${basis}.methods.full_minmax.field.values missing`);
      }
      if (!Array.isArray(block?.robustness)) {
        problems.push(`editions.${year}.${basis}.robustness missing`);
      }
    }
  }
  if (problems.length > 0) {
    console.error('[sync-data] editions.json is not the editions contract:');
    for (const problem of problems) console.error(`[sync-data]   - ${problem}`);
    process.exit(1);
  }
  console.log(
    `[sync-data] editions.json: years ${editions.meta.years.join(', ')} · ` +
      `bases ${Object.entries(editions.meta.basisAvailability)
        .map(([year, list]) => `${year}:${list.join('/')}`)
        .join(' ')}`,
  );
} catch (error) {
  console.error('[sync-data] Could not read editions.json — run pipeline/export_editions.py');
  console.error(`[sync-data] ${error instanceof Error ? error.message : error}`);
  process.exit(1);
}

// overview.json feeds the `/` carousel. It is produced alongside chips.json
// and is optional in this wave: without it the site derives the two built
// panes from chips.json and says so in the build log.
const overviewPath = path.join(source, 'overview.json');
let overview = null;
try {
  overview = JSON.parse(await readFile(overviewPath, 'utf8'));
} catch {
  overview = null;
}

if (overview) {
  const problems = [];
  if (typeof overview.meta?.edition !== 'string') problems.push('missing meta.edition');
  if (!overview.meta?.defaultMethod) problems.push('missing meta.defaultMethod');
  if (!overview.methods || typeof overview.methods !== 'object') {
    problems.push('missing methods{} (method-split overview)');
  } else {
    const ids = Object.keys(overview.methods);
    if (ids.length === 0) problems.push('methods{} is empty');
    for (const id of ids) {
      const block = overview.methods[id];
      if (!Array.isArray(block?.field?.values)) problems.push(`methods.${id}.field.values is not an array`);
      if (!Array.isArray(block?.top15)) problems.push(`methods.${id}.top15 is not an array`);
      if (!Array.isArray(block?.movement?.years)) problems.push(`methods.${id}.movement.years is not an array`);
    }
    if (overview.meta?.defaultMethod && !ids.includes(overview.meta.defaultMethod)) {
      problems.push('meta.defaultMethod does not name a key in methods');
    }
  }
  if (!Array.isArray(overview.scaleMovement?.movers)) {
    problems.push('missing scaleMovement.movers');
  }
  if (problems.length > 0) {
    console.error('[sync-data] data/derived/web/overview.json is not the overview contract:');
    for (const problem of problems) console.error(`[sync-data]   - ${problem}`);
    console.error('[sync-data] Ask the data agent to regenerate the exporter output. Not copying.');
    process.exit(1);
  }
  const ids = overview.meta.methods ?? Object.keys(overview.methods);
  const lead = overview.methods[overview.meta.defaultMethod];
  console.log(
    `[sync-data] overview.json: edition ${overview.meta.edition}, methods ${ids.join(', ')} ` +
      `(default ${overview.meta.defaultMethod}), ${lead.field.values.length} scores per method, ` +
      `movement years ${lead.movement.years.join(', ')} ` +
      `(${lead.movement.countries.length} countries)`,
  );
} else {
  console.log(
    '[sync-data] no overview.json yet — the overview carousel will fall back to chips.json for panes 1–2',
  );
}

console.log(`[sync-data] copied ${path.relative(webRoot, source)} -> src/data`);
console.log(
  `[sync-data] edition ${chips.meta.edition}, ${chips.meta.countries} countries, ` +
    `${chips.meta.leaves} indicators, methods: ${Object.keys(chips.methods).join(', ')}`,
);
