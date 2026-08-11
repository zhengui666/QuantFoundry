import js from '@eslint/js';
import tseslint from 'typescript-eslint';
export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    ignores: [
      'dist',
      '.next/**',
      'storybook-static',
      'test-results',
      'playwright-report',
      'src/api/generated.ts',
    ],
  },
  {
    files: ['scripts/*.mjs'],
    languageOptions: { globals: { process: 'readonly' } },
  },
);
