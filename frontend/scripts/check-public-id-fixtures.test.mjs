import { mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import {
  collectFormalPublicIdFiles,
  findInvalidPublicIdFixtures,
  formalPublicIdSources,
  scanFormalPublicIdSources,
} from './check-public-id-fixtures.mjs';

const matchers = new Map([
  [
    'STRAT',
    [
      /^STRAT-[0-7][0-9A-HJKMNP-TV-Z]{25}$/,
      /^STRAT-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    ],
  ],
]);
const invalidStrategyId = ['STRAT', 'ID'].join('-');

const scan = (file, value) =>
  findInvalidPublicIdFixtures(file, JSON.stringify(value, null, 2), matchers);

describe('public-ID repository fixture scanner', () => {
  it('declares every QF-PID-014 formal fact source explicitly', () => {
    expect(formalPublicIdSources).toEqual([
      { path: 'PROJECT_BACKGROUND.md', kind: 'file' },
      { path: 'AGENTS.md', kind: 'file' },
      { path: 'backend', kind: 'directory' },
      {
        path: 'docs/后端系统技术方案/QuantFoundry_Backend_System_Technical_Design_V1.0.0.md',
        kind: 'file',
      },
      {
        path: 'docs/Agent技术方案/QuantFoundry_Agent_Technical_Design_V1.0.0.md',
        kind: 'file',
      },
      { path: 'docs/PRD/V1.0.0.md', kind: 'file' },
      { path: 'docs/UI设计方案/QuantFoundry_UI_Design_V1.0.0.md', kind: 'file' },
      {
        path: 'docs/前端技术方案/QuantFoundry_Frontend_Technical_Design_V1.0.0.md',
        kind: 'file',
      },
      { path: 'docs/全栈测试方案/QuantFoundry_Full_Stack_Test_Plan_V1.0.0.md', kind: 'file' },
      { path: 'docs/治理', kind: 'directory' },
      {
        path: 'docs/UI设计方案/QuantFoundry_UI_Interaction_Redesign_Brief_V1.0.0.md',
        kind: 'file',
      },
      { path: 'docs/后端系统技术方案/contracts', kind: 'directory' },
      { path: 'docs/后端系统技术方案/contracts/openapi-v1.yaml', kind: 'file' },
      { path: 'docs/后端系统技术方案/contracts/tools', kind: 'directory' },
      { path: 'frontend', kind: 'directory' },
    ]);
  });

  it('allows grammar notation only in schema/manifest description and constraint prose', () => {
    expect(
      scan('/repo/backend/schema/section14_manifest.json', {
        description: `A Strategy locator is written ${invalidStrategyId}@version.`,
        constraints: `CHECK closed \`${invalidStrategyId}@version\` locator`,
        nested: { constraint: `${invalidStrategyId} is notation, not a fixture` },
      }),
    ).toEqual([]);
  });

  it.each(['example', 'examples', 'default', 'enum', 'fixture', 'fixtures'])(
    'still rejects an invalid manifest %s literal',
    (field) => {
      expect(
        scan('/repo/backend/schema/section14_manifest.json', { [field]: invalidStrategyId }),
      ).toEqual([
        expect.stringContaining(
          `$.${field}: unmarked invalid public-ID fixture ${invalidStrategyId}`,
        ),
      ]);
    },
  );

  it('does not relax runtime, API, test, or MSW JSON content', () => {
    for (const file of [
      '/repo/frontend/src/runtime.json',
      '/repo/frontend/src/api.fixture.json',
      '/repo/frontend/tests/request.json',
      '/repo/frontend/mocks/msw.json',
    ]) {
      expect(scan(file, { description: invalidStrategyId }), file).toEqual([
        expect.stringContaining(
          `$.description: unmarked invalid public-ID fixture ${invalidStrategyId}`,
        ),
      ]);
    }
  });

  it('requires every declared formal source to exist and records it as scanned', async () => {
    const root = await mkdtemp(join(tmpdir(), 'qf-pid-formal-'));
    try {
      await mkdir(join(root, 'docs/PRD'), { recursive: true });
      await writeFile(join(root, 'docs/PRD/V1.0.0'), 'canonical prose without fixtures');
      const sources = [{ path: 'docs/PRD/V1.0.0', kind: 'file' }];

      const result = await collectFormalPublicIdFiles(root, sources);
      expect(result.files).toEqual([join(root, 'docs/PRD/V1.0.0')]);
      expect(result.coverage.get('docs/PRD/V1.0.0')).toBe(1);
      await expect(
        collectFormalPublicIdFiles(root, [{ path: 'missing', kind: 'file' }]),
      ).rejects.toThrow('Formal public-ID source is missing: missing');
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it('scans an explicit extensionless PRD and blocks an unmarked injected invalid ID', async () => {
    const root = await mkdtemp(join(tmpdir(), 'qf-pid-extensionless-'));
    try {
      await mkdir(join(root, 'docs/PRD'), { recursive: true });
      const file = join(root, 'docs/PRD/V1.0.0');
      await writeFile(file, `Unmarked runtime example: ${invalidStrategyId}`);

      const result = await scanFormalPublicIdSources({
        repositoryRoot: root,
        matchers,
        sources: [{ path: 'docs/PRD/V1.0.0', kind: 'file' }],
      });
      expect(result.scannedFiles).toEqual([file]);
      expect(result.failures).toEqual([
        expect.stringContaining(`unmarked invalid public-ID fixture ${invalidStrategyId}`),
      ]);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it('recurses through supported files while ignoring unsupported and ignored entries', async () => {
    const root = await mkdtemp(join(tmpdir(), 'qf-pid-directory-'));
    try {
      await mkdir(join(root, 'source/nested'), { recursive: true });
      await mkdir(join(root, 'source/node_modules'), { recursive: true });
      await writeFile(join(root, 'source/a.ts'), 'const a = 1;');
      await writeFile(join(root, 'source/nested/b.yaml'), 'value: 1');
      await writeFile(join(root, 'source/readme.txt'), 'ignored extension');
      await writeFile(join(root, 'source/node_modules/c.ts'), 'ignored directory');
      const result = await collectFormalPublicIdFiles(root, [
        { path: 'source', kind: 'directory' },
      ]);
      expect(result.files).toEqual([join(root, 'source/a.ts'), join(root, 'source/nested/b.yaml')]);
      expect(result.coverage.get('source')).toBe(2);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });
});
