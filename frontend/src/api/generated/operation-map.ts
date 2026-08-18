/**
 * This file is generated from docs/后端系统技术方案/contracts/openapi-v1.yaml.
 * Do not edit directly.
 */
import type { operations } from '../generated';

export type CanonicalOperation = {
  readonly method: string;
  readonly path: string;
  readonly headers: readonly { readonly name: string; readonly required: boolean }[];
  readonly query: readonly {
    readonly name: string;
    readonly required: boolean;
    readonly value?: string | number | boolean;
  }[];
  readonly authenticated: boolean;
};

export const operationMap = {
  getSystemHealth: {
    method: 'GET',
    path: '/system/health',
    headers: [],
    query: [],
    authenticated: false,
  },
  loginWithGeneralAccessKey: {
    method: 'POST',
    path: '/auth/login',
    headers: [],
    query: [],
    authenticated: false,
  },
  getCurrentOwnerSession: {
    method: 'GET',
    path: '/auth/session',
    headers: [],
    query: [],
    authenticated: true,
  },
  logoutOwnerSession: {
    method: 'POST',
    path: '/auth/logout',
    headers: [{ name: 'X-CSRF-Token', required: true }],
    query: [],
    authenticated: true,
  },
  listGeneralAccessKeys: {
    method: 'GET',
    path: '/auth/access-keys',
    headers: [{ name: 'X-CSRF-Token', required: true }],
    query: [],
    authenticated: true,
  },
  createGeneralAccessKey: {
    method: 'POST',
    path: '/auth/access-keys',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  renameGeneralAccessKey: {
    method: 'PATCH',
    path: '/auth/access-keys/{key_id}',
    headers: [
      { name: 'If-Match', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  rotateGeneralAccessKey: {
    method: 'POST',
    path: '/auth/access-keys/{key_id}/rotate',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'If-Match', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  revokeGeneralAccessKey: {
    method: 'POST',
    path: '/auth/access-keys/{key_id}/revoke',
    headers: [
      { name: 'If-Match', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  expireGeneralAccessKey: {
    method: 'POST',
    path: '/auth/access-keys/{key_id}/expire',
    headers: [
      { name: 'If-Match', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  getConfigurationCatalog: {
    method: 'GET',
    path: '/configuration/catalog',
    headers: [],
    query: [],
    authenticated: true,
  },
  getActiveConfiguration: {
    method: 'GET',
    path: '/configuration/active',
    headers: [],
    query: [],
    authenticated: true,
  },
  putConfigurationCandidate: {
    method: 'PUT',
    path: '/configuration/candidate',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'If-Match', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  validateConfigurationCandidate: {
    method: 'POST',
    path: '/configuration/candidate/validate',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  activateConfiguration: {
    method: 'POST',
    path: '/configuration/activate',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'If-Match', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  rollbackConfiguration: {
    method: 'POST',
    path: '/configuration/rollback',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'If-Match', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  getDomainDatabaseConnection: {
    method: 'GET',
    path: '/database/connection',
    headers: [],
    query: [],
    authenticated: true,
  },
  putDomainDatabaseConnectionCandidate: {
    method: 'PUT',
    path: '/database/connection/candidate',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'If-Match', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  validateDomainDatabaseConnectionCandidate: {
    method: 'POST',
    path: '/database/connection/candidate/validate',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'X-Candidate-Revision', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  activateDomainDatabaseConnection: {
    method: 'POST',
    path: '/database/connection/activate',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'If-Match', required: true },
      { name: 'X-Candidate-Revision', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  revertDomainDatabaseConnection: {
    method: 'POST',
    path: '/database/connection/revert',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'If-Match', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  getSetupStatus: {
    method: 'GET',
    path: '/setup/status',
    headers: [],
    query: [],
    authenticated: true,
  },
  completeSetup: {
    method: 'POST',
    path: '/setup/complete',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'If-Match', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  getSetupCapabilities: {
    method: 'GET',
    path: '/setup/capabilities',
    headers: [],
    query: [],
    authenticated: true,
  },
  validateLiveConnector: {
    method: 'POST',
    path: '/setup/live-connectors/validate',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  validateSetupProviderConnection: {
    method: 'POST',
    path: '/setup/provider-connections/validate',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  getOverview: { method: 'GET', path: '/overview', headers: [], query: [], authenticated: true },
  listDataCapabilities: {
    method: 'GET',
    path: '/data/capabilities',
    headers: [],
    query: [],
    authenticated: true,
  },
  evaluateDataCapabilities: {
    method: 'POST',
    path: '/data/capabilities/evaluate',
    headers: [{ name: 'X-CSRF-Token', required: true }],
    query: [],
    authenticated: true,
  },
  validateDataset: {
    method: 'POST',
    path: '/data/datasets/{dataset_id}/validate',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  createDatasetSnapshot: {
    method: 'POST',
    path: '/data/datasets/{dataset_id}/snapshots',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  getDatasetSnapshot: {
    method: 'GET',
    path: '/data/snapshots/{snapshot_id}',
    headers: [],
    query: [],
    authenticated: true,
  },
  listResearch: {
    method: 'GET',
    path: '/research',
    headers: [{ name: 'X-CSRF-Token', required: true }],
    query: [
      { name: 'cursor', required: false },
      { name: 'limit', required: false },
    ],
    authenticated: true,
  },
  createResearch: {
    method: 'POST',
    path: '/research',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  getResearch: {
    method: 'GET',
    path: '/research/{research_id}',
    headers: [],
    query: [
      { name: 'tab', required: false },
      { name: 'cursor', required: false },
      { name: 'limit', required: false },
    ],
    authenticated: true,
  },
  startResearch: {
    method: 'POST',
    path: '/research/{research_id}/start',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'If-Match', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  createExperiment: {
    method: 'POST',
    path: '/experiments',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  getExperiment: {
    method: 'GET',
    path: '/experiments/{experiment_id}',
    headers: [],
    query: [],
    authenticated: true,
  },
  reproduceExperiment: {
    method: 'POST',
    path: '/experiments/{experiment_id}/reproduce',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  createFactor: {
    method: 'POST',
    path: '/factors',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  analyzeFactor: {
    method: 'POST',
    path: '/factors/{factor_id}/analyses',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  createStrategy: {
    method: 'POST',
    path: '/strategies',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  getStrategyVersion: {
    method: 'GET',
    path: '/strategies/{strategy_id}/versions/{version}',
    headers: [],
    query: [],
    authenticated: true,
  },
  getCurrentStrategyVersion: {
    method: 'GET',
    path: '/strategies/{strategy_id}/current-version',
    headers: [],
    query: [],
    authenticated: true,
  },
  runFastBacktest: {
    method: 'POST',
    path: '/strategies/{strategy_id}/versions/{version}/backtests',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  freezeStrategy: {
    method: 'POST',
    path: '/strategies/{strategy_id}/versions/{version}/freeze',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'If-Match', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  createValidation: {
    method: 'POST',
    path: '/validations',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  getValidation: {
    method: 'GET',
    path: '/validations/{validation_id}',
    headers: [],
    query: [],
    authenticated: true,
  },
  getHoldoutGate: {
    method: 'GET',
    path: '/validations/{validation_id}/holdout',
    headers: [],
    query: [],
    authenticated: true,
  },
  requestHoldoutApproval: {
    method: 'POST',
    path: '/validations/{validation_id}/holdout-approval-requests',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'If-Match', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  runHoldout: {
    method: 'POST',
    path: '/validations/{validation_id}/holdout-runs',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'If-Match', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  getHoldoutResult: {
    method: 'GET',
    path: '/validations/{validation_id}/holdout/result',
    headers: [],
    query: [],
    authenticated: true,
  },
  generateMemo: {
    method: 'POST',
    path: '/memos',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  getMemo: { method: 'GET', path: '/memos/{memo_id}', headers: [], query: [], authenticated: true },
  exportMemo: {
    method: 'GET',
    path: '/memos/{memo_id}/export',
    headers: [],
    query: [{ name: 'format', required: true, value: 'MARKDOWN' }],
    authenticated: true,
  },
  listApprovals: {
    method: 'GET',
    path: '/approvals',
    headers: [],
    query: [
      { name: 'cursor', required: false },
      { name: 'limit', required: false },
    ],
    authenticated: true,
  },
  getApproval: {
    method: 'GET',
    path: '/approvals/{approval_id}',
    headers: [],
    query: [],
    authenticated: true,
  },
  approveApproval: {
    method: 'POST',
    path: '/approvals/{approval_id}/approve',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'If-Match', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  rejectApproval: {
    method: 'POST',
    path: '/approvals/{approval_id}/reject',
    headers: [
      { name: 'Idempotency-Key', required: true },
      { name: 'If-Match', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  listAgents: { method: 'GET', path: '/agents', headers: [], query: [], authenticated: true },
  getAgentConfig: {
    method: 'GET',
    path: '/agents/{role}/config',
    headers: [{ name: 'X-CSRF-Token', required: true }],
    query: [],
    authenticated: true,
  },
  updateAgentConfig: {
    method: 'PUT',
    path: '/agents/{role}/config',
    headers: [
      { name: 'If-Match', required: true },
      { name: 'X-CSRF-Token', required: true },
    ],
    query: [],
    authenticated: true,
  },
  getAgentRun: {
    method: 'GET',
    path: '/agent-runs/{agent_run_id}',
    headers: [],
    query: [],
    authenticated: true,
  },
  getToolCall: {
    method: 'GET',
    path: '/tool-calls/{tool_call_id}',
    headers: [],
    query: [],
    authenticated: true,
  },
  getJob: { method: 'GET', path: '/jobs/{job_id}', headers: [], query: [], authenticated: true },
  streamEvents: {
    method: 'GET',
    path: '/events/stream',
    headers: [{ name: 'Last-Event-ID', required: false }],
    query: [],
    authenticated: true,
  },
} as const satisfies Record<keyof operations, CanonicalOperation>;

export type CanonicalOperationId = keyof typeof operationMap;
