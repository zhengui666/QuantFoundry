import { ESLint } from 'eslint';
import { mkdir, rm, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const frontendRoot = resolve(import.meta.dirname, '..');
const cases = [
  {
    name: 'React Hooks',
    path: 'hooks.tsx',
    ruleId: 'react-hooks/rules-of-hooks',
    source: `import { useState } from 'react';
export function InvalidHook() {
  if (Math.random() > 0.5) useState(0);
  return null;
}
`,
  },
  {
    name: 'TypeScript unsafe',
    path: 'unsafe.ts',
    ruleId: '@typescript-eslint/no-unsafe-assignment',
    source: `const parsed = JSON.parse('{}');
const unsafeString: string = parsed;
export { unsafeString };
`,
  },
  {
    name: 'raw fetch',
    path: 'fetch.ts',
    ruleId: 'no-restricted-syntax',
    source: `export const invalidRequest = () => fetch('/api/v1/health');
`,
  },
  {
    name: 'dangerous HTML',
    path: 'html.tsx',
    ruleId: 'no-restricted-syntax',
    source: `export function InvalidHtml() {
  return <div dangerouslySetInnerHTML={{ __html: '<b>unsafe</b>' }} />;
}
`,
  },
  {
    name: 'production console',
    path: 'console.ts',
    ruleId: 'no-console',
    source: `console.log('must be routed through diagnostics');
`,
  },
  {
    name: 'client storage boundary',
    path: 'storage.ts',
    ruleId: 'no-restricted-syntax',
    source: `export const invalidStorage = window.sessionStorage.getItem('server-truth');
`,
  },
  {
    name: 'domain import boundary',
    directory: 'src/domain/__eslint_fixtures__',
    path: 'boundary.ts',
    ruleId: 'no-restricted-imports',
    source: `import { LoginPage } from '../../routes/LoginRoute';
export { LoginPage };
`,
  },
];

describe('frontend ESLint policy fixtures', () => {
  it('rejects every mandated policy violation', async () => {
    const fixturePaths = cases.map(({ directory, path }) =>
      resolve(frontendRoot, directory ?? 'src/__eslint_fixtures__', path),
    );
    const fixtureDirectories = [...new Set(fixturePaths.map((path) => resolve(path, '..')))];
    try {
      await Promise.all(
        cases.map(async ({ directory, path, source }) => {
          const nestedPath = resolve(frontendRoot, directory ?? 'src/__eslint_fixtures__', path);
          await mkdir(resolve(nestedPath, '..'), { recursive: true });
          await writeFile(nestedPath, source, 'utf8');
        }),
      );
      const eslint = new ESLint({
        cwd: frontendRoot,
        overrideConfigFile: resolve(frontendRoot, 'eslint.config.js'),
      });
      const results = await eslint.lintFiles(fixturePaths);
      for (const [index, result] of results.entries())
        expect(result.messages.map((message) => message.ruleId)).toContain(cases[index].ruleId);
    } finally {
      await Promise.all(
        fixtureDirectories.map((directory) => rm(directory, { recursive: true, force: true })),
      );
    }
  }, 20_000);
});
