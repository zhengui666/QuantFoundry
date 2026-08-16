import js from '@eslint/js';
import reactHooks from 'eslint-plugin-react-hooks';
import tseslint from 'typescript-eslint';

const typedSourceFiles = ['src/**/*.{ts,tsx}'];
const nonProductionFiles = [
  '**/*.test.*',
  '**/*.stories.*',
  'src/testing/**',
  'src/api/generated/**',
  'src/api/generated.ts',
];
const policyIgnores = [...nonProductionFiles, 'src/api/**'];
const typeChecked = tseslint.configs.recommendedTypeChecked.map((config) =>
  config.languageOptions
    ? {
        ...config,
        files: typedSourceFiles,
        ignores: nonProductionFiles,
        languageOptions: {
          ...config.languageOptions,
          parserOptions: {
            ...config.languageOptions.parserOptions,
            projectService: true,
            tsconfigRootDir: import.meta.dirname,
          },
        },
      }
    : { ...config, files: typedSourceFiles, ignores: nonProductionFiles },
);

export default tseslint.config(
  js.configs.recommended,
  ...typeChecked,
  {
    files: typedSourceFiles,
    ignores: nonProductionFiles,
    plugins: { 'react-hooks': reactHooks },
    rules: {
      'no-console': 'error',
      'react-hooks/exhaustive-deps': 'error',
      'react-hooks/rules-of-hooks': 'error',
      '@typescript-eslint/no-base-to-string': 'off',
      '@typescript-eslint/no-misused-promises': 'off',
      '@typescript-eslint/no-unnecessary-type-assertion': 'off',
      '@typescript-eslint/prefer-promise-reject-errors': 'off',
    },
  },
  {
    ignores: [
      'dist',
      '.next/**',
      'storybook-static',
      'test-results',
      'playwright-report',
      'src/api/generated.ts',
      'src/api/generated/**',
    ],
  },
  {
    files: ['scripts/*.mjs'],
    languageOptions: { globals: { process: 'readonly' } },
  },
  {
    files: typedSourceFiles,
    ignores: policyIgnores,
    rules: {
      'no-restricted-syntax': [
        'error',
        {
          selector: "CallExpression[callee.name='fetch']",
          message: 'Use the canonical operation client in src/api instead of raw fetch.',
        },
        {
          selector: "JSXAttribute[name.name='dangerouslySetInnerHTML']",
          message: 'Render structured text; dangerouslySetInnerHTML is forbidden.',
        },
        {
          selector: 'MemberExpression[property.name=/^(localStorage|sessionStorage|indexedDB)$/]',
          message:
            'Use the allowlisted transient-storage adapter; client storage is not server truth.',
        },
      ],
    },
  },
  {
    files: ['src/api/**/*.{ts,tsx}'],
    ignores: ['**/*.test.*'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          paths: [
            { name: 'react', message: 'The API layer must remain framework-agnostic.' },
            { name: 'react-dom', message: 'The API layer must remain framework-agnostic.' },
          ],
          patterns: [
            {
              group: ['**/routes/**', '**/features/**', '**/domain/**', '**/ui'],
              message: 'The API layer cannot depend on UI or domain implementation modules.',
            },
          ],
        },
      ],
    },
  },
  {
    files: ['src/domain/**/*.{ts,tsx}'],
    ignores: ['**/*.test.*', '**/*.stories.*'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['**/routes/**', '**/features/**'],
              message: 'Domain modules cannot depend on routes or feature implementation modules.',
            },
          ],
        },
      ],
    },
  },
);
