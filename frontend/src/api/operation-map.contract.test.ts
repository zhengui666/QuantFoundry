// @vitest-environment node
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { operationMap } from './generated/operation-map';

describe('canonical generated REST operation boundary', () => {
  it('covers every canonical OpenAPI operation exactly once', async () => {
    const contract = await readFile(
      resolve(process.cwd(), '../docs/后端系统技术方案/contracts/openapi-v1.yaml'),
      'utf8',
    );
    const operationIds = Object.keys(operationMap).sort();
    const generatedIds = Array.from(
      contract.matchAll(/^\s+operationId:\s*(\S+)$/gm),
      (match) => match[1],
    )
      .filter((operationId): operationId is string => operationId !== undefined)
      .sort();
    expect(operationIds).toEqual(generatedIds);
  });

  it('keeps canonical authorization, concurrency, idempotency, and SSE headers in the map', () => {
    expect(operationMap.getSystemHealth.authenticated).toBe(false);
    expect(operationMap.startResearch.headers).toEqual([
      'Idempotency-Key',
      'If-Match',
      'X-CSRF-Token',
    ]);
    expect(operationMap.updateAgentConfig.headers).toEqual(['If-Match', 'X-CSRF-Token']);
    expect(operationMap.streamEvents.headers).toEqual(['Last-Event-ID']);
    expect(operationMap.exportMemo.query).toEqual([
      { name: 'format', required: true, value: 'MARKDOWN' },
    ]);
  });

  it('allows client.ts to derive REST paths and methods only through the generated map', async () => {
    const source = await readFile(resolve(process.cwd(), 'src/api/client.ts'), 'utf8');
    const restLiteral = /['"][^'"]*\/api\/v1\/(?!['"])/;
    expect(source).not.toMatch(restLiteral);
    expect(source).not.toMatch(/method:\s*['"](?:GET|POST|PUT|PATCH|DELETE)['"]/);
    expect(source.match(/fetch\(/g)).toHaveLength(3);
    expect(source).toContain('pathFor(operationId, pathParams)');
    expect(source).toContain("pathFor('streamEvents')");
  });
});
