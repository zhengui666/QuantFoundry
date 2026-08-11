import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ContractError, type Schema } from './client';
import { PublicIdExamples, type PublicIdType } from './generated/runtime-schemas';
import { canonicalPublicIdForms, publicIdNegativeCases } from './public-id-test-cases';

const researchStart = {
  research_revision_no: 1,
  capability_evaluation_confirmed: true,
} satisfies Schema<'ResearchStartRequest'>;
const freeze = { expected_spec_sha256: 'a'.repeat(64) } satisfies Schema<'FreezeStrategyRequest'>;
const backtest = {
  snapshot_id: PublicIdExamples.snapshot.ulid,
  cost_model_id: PublicIdExamples.cost_model.ulid,
  engine_key: 'canonical',
  engine_version: '1.0.0',
  parameters: [],
} satisfies Schema<'BacktestRequest'>;

type BoundaryCase = {
  name: string;
  type: PublicIdType;
  invoke: (id: string) => Promise<unknown>;
};

const cases: readonly BoundaryCase[] = [
  { name: 'research detail', type: 'research', invoke: (id) => api.researchDetail(id) },
  {
    name: 'research start',
    type: 'research',
    invoke: (id) => api.startResearch(id, 'W/"research:1"', researchStart),
  },
  { name: 'experiment detail', type: 'experiment', invoke: (id) => api.experiment(id) },
  {
    name: 'experiment reproduce',
    type: 'experiment',
    invoke: (id) => api.reproduceExperiment(id, { mode: 'EXACT' }, 'intent-key'),
  },
  { name: 'strategy current', type: 'strategy', invoke: (id) => api.currentStrategyVersion(id) },
  { name: 'strategy version', type: 'strategy', invoke: (id) => api.strategyVersion(id, 1) },
  {
    name: 'strategy freeze',
    type: 'strategy',
    invoke: (id) => api.freezeStrategy(id, 1, 'W/"strategy:1"', freeze),
  },
  {
    name: 'strategy backtest',
    type: 'strategy',
    invoke: (id) => api.runFastBacktest(id, 1, backtest),
  },
  { name: 'validation detail', type: 'validation', invoke: (id) => api.validation(id) },
  { name: 'holdout gate', type: 'validation', invoke: (id) => api.holdoutGate(id) },
  { name: 'holdout result', type: 'validation', invoke: (id) => api.holdoutResult(id) },
  {
    name: 'holdout approval',
    type: 'validation',
    invoke: (id) => api.requestHoldoutApproval(id, 'W/"validation:1"', { reason: 'reviewed' }),
  },
  {
    name: 'holdout run',
    type: 'validation',
    invoke: (id) =>
      api.runHoldout(id, 'W/"validation:1"', { approval_id: PublicIdExamples.approval.ulid }),
  },
  { name: 'approval detail', type: 'approval', invoke: (id) => api.approval(id) },
  {
    name: 'approval approve',
    type: 'approval',
    invoke: (id) =>
      api.approveApproval(id, 'W/"approval:1"', {
        acknowledged_subject_sha256: 'a'.repeat(64),
      }),
  },
  {
    name: 'approval reject',
    type: 'approval',
    invoke: (id) =>
      api.rejectApproval(id, 'W/"approval:1"', {
        reason: 'not ready',
        acknowledged_subject_sha256: 'a'.repeat(64),
      }),
  },
  { name: 'memo detail', type: 'memo', invoke: (id) => api.memo(id) },
  { name: 'memo export', type: 'memo', invoke: (id) => api.exportMemo(id) },
  { name: 'job detail', type: 'job', invoke: (id) => api.job(id) },
] as const;

afterEach(() => vi.unstubAllGlobals());

describe('QF-PID route/API boundary', () => {
  it('accepts both canonical forms at all 19 path boundaries and reaches resource network', async () => {
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            type: 'about:blank',
            title: 'Not found',
            status: 404,
            code: 'RESOURCE_NOT_FOUND',
            detail: null,
            instance: null,
            request_id: 'REQ-QF-PID-POSITIVE',
            retryable: false,
            field_errors: [],
            context: {},
          } satisfies Schema<'ApiProblem'>),
          { status: 404, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    );
    vi.stubGlobal('fetch', fetchMock);
    for (const boundary of cases)
      for (const id of canonicalPublicIdForms(boundary.type)) {
        const before = fetchMock.mock.calls.length;
        await expect(boundary.invoke(id)).rejects.toMatchObject({
          problem: { code: 'RESOURCE_NOT_FOUND' },
        });
        expect(fetchMock.mock.calls.length, `${boundary.name}:${id}`).toBe(before + 1);
      }
    expect(fetchMock).toHaveBeenCalledTimes(19 * 2);
  });

  it('QF-PID-003..011 rejects every applicable case at all 19 boundaries before network', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    let rejections = 0;
    for (const boundary of cases)
      for (const invalid of publicIdNegativeCases(boundary.type)) {
        const before = fetchMock.mock.calls.length;
        rejections += 1;
        await expect(
          Promise.resolve().then(() => boundary.invoke(invalid.value)),
          `${boundary.name}:${invalid.caseId}:${invalid.mutation}`,
        ).rejects.toBeInstanceOf(ContractError);
        expect(
          fetchMock.mock.calls.length,
          `${boundary.name}:${invalid.caseId}:${invalid.mutation}`,
        ).toBe(before);
      }
    expect(rejections).toBeGreaterThanOrEqual(19 * 25);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
