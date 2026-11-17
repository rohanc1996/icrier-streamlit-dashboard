#!/usr/bin/env node
/**
 * Dev-time only: vendor the ICRIER logo the header lockup draws.
 *
 *   node scripts/fetch-brand.mjs
 *
 * Not part of the build. The PNG it writes is committed, so a build (or a clone
 * with no network) never reaches for icrier.org. Same arrangement as
 * `fetch-flags.mjs`.
 *
 * Upstream: https://icrier.org/wp-content/themes/icrier/img/logo.png
 *   — the only logo the site serves: 180×97 RGBA PNG, transparent background,
 *   no padding around the mark. There is no SVG and no monochrome variant, so
 *   do not scale it past ~40px tall; ask ICRIER for a vector instead.
 *
 * Licensing: this is ICRIER's trademark, not an open-licence asset. It is fine
 * on this local, pre-publication prototype and must not be redistributed
 * separately or shipped to a public deploy without sign-off.
 *
 * The dimensions are pinned below because the layout reserves space from them
 * (`width`/`height` on the <img>). If ICRIER redesigns the mark, this script
 * fails rather than silently swapping in a different shape — re-check the
 * header at 320px and update EXPECTED first.
 */
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT_DIR = path.join(ROOT, 'public', 'brand');
const OUT_FILE = path.join(OUT_DIR, 'icrier-logo.png');
const URL_SRC = 'https://icrier.org/wp-content/themes/icrier/img/logo.png';
const EXPECTED = { width: 180, height: 97 };

const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

/** Read width/height straight out of the IHDR chunk; no image library needed. */
function pngSize(buffer) {
  if (buffer.length < 24 || !buffer.subarray(0, 8).equals(PNG_SIGNATURE)) {
    return null;
  }
  if (buffer.toString('ascii', 12, 16) !== 'IHDR') {
    return null;
  }
  return {
    width: buffer.readUInt32BE(16),
    height: buffer.readUInt32BE(20),
  };
}

const response = await fetch(URL_SRC);
if (!response.ok) {
  throw new Error(`${URL_SRC} → HTTP ${response.status}`);
}

const type = response.headers.get('content-type') ?? '';
if (!type.startsWith('image/png')) {
  throw new Error(`${URL_SRC} → content-type ${type || '(none)'}, expected image/png`);
}

const buffer = Buffer.from(await response.arrayBuffer());
const size = pngSize(buffer);
if (size === null) {
  throw new Error(`${URL_SRC} is not a PNG`);
}
if (size.width !== EXPECTED.width || size.height !== EXPECTED.height) {
  throw new Error(
    `${URL_SRC} is ${size.width}×${size.height}, expected ` +
      `${EXPECTED.width}×${EXPECTED.height} — the header reserves space from these`,
  );
}

await mkdir(OUT_DIR, { recursive: true });
await writeFile(OUT_FILE, buffer);

console.log(
  `icrier-logo.png  ${size.width}×${size.height}  ${buffer.length} B ` +
    `→ public/brand/`,
);
