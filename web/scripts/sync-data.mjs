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

console.log(`[sync-data] copied ${path.relative(webRoot, source)} -> src/data`);
console.log(
  `[sync-data] edition ${chips.meta.edition}, ${chips.meta.countries} countries, ` +
    `${chips.meta.leaves} indicators, methods: ${Object.keys(chips.methods).join(', ')}`,
);
