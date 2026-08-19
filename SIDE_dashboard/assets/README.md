# assets/

Geodata used by the dashboard's world choropleths.

## world_india_official.geojson

Merged world GeoJSON used by both world maps. Every feature carries an `id`
used for matching with `featureidkey="id"`: the feature's ISO-3 code where one
exists, otherwise Natural Earth's `ADM0_A3` admin code (e.g. Somaliland =
`SOL`) or a name-based slug as a last resort. India's id is `IND`.

Unlike Plotly's built-in country geometry (Natural Earth, *de facto* borders),
the `IND` feature in this file is India's **official territorial extent** as
mapped by the Survey of India: all of Jammu & Kashmir (including PoK and
Siachen).

### Provenance

- **World (all other countries):** Natural Earth 1:110m admin-0 countries
  (public domain), Natural Earth's de-facto India feature removed.
- **India (`IND`):** union of the 36 state/UT polygons from
  `india-states-simplified.geojson` in
  https://github.com/AbhinavSwami28/india-official-geojson (MIT licence),
  built from Survey-of-India-derived open data.
- Built once by `scripts/build_official_world.py` (requires `shapely` at
  build time only; the runtime dashboard reads this file as plain JSON).
- **Neighbours clipped:** Natural Earth polygons that extend into India's
  official extent are clipped against it, so no other country's outline
  overlaps India. Pakistan loses PoK/Gilgit-Baltistan, China loses Aksai
  Chin, and small boundary slivers with Bangladesh, Nepal, Bhutan, Myanmar
  and Afghanistan are trimmed the same way.

### Attribution & caveats

- **© Survey of India** — the map of India and its territorial boundaries are
  the copyright of the Survey of India. Reproduce with attribution.
- This is an open-data re-derivation; **verify against the latest Survey of
  India map** before any formal publication.
- The GeoJSON contains only international-boundary outlines — it does **not**
  include the LoC/LAC "dashed line" internal styling used on official maps;
  the dashed administrative line would need separate line data.
- Natural Earth 1:110m omits Singapore and other micro-states; they are not
  rendered on these maps (same behaviour as Plotly's built-in world map).
