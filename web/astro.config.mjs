// @ts-check
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

// Local prototype only: no adapter, no deploy target, no integrations beyond React.
export default defineConfig({
  integrations: [react()],
  devToolbar: { enabled: false },
});
