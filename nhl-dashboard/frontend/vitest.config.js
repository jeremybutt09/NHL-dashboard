import { defineConfig } from 'vitest/config';

export default defineConfig({
  esbuild: {
    jsxImportSource: 'react',
    jsx: 'automatic',
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
});
