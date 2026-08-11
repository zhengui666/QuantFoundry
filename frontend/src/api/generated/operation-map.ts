/**
 * This file is generated from docs/后端系统技术方案/contracts/openapi-v1.yaml.
 * Do not edit directly.
 */
import type { operations } from "../generated";

export type CanonicalOperation = {
  readonly method: string;
  readonly path: string;
  readonly headers: readonly string[];
  readonly query: readonly {
    readonly name: string;
    readonly required: boolean;
    readonly value?: string | number | boolean;
  }[];
  readonly authenticated: boolean;
};

export const operationMap = {
  getSystemHealth: {
    method: "GET",
    path: "/system/health",
    headers: [],
    query: [],
    authenticated: false,
  },
  getSetupStatus: {
    method: "GET",
    path: "/setup/status",
    headers: [],
    query: [],
    authenticated: true,
  },
  completeSetup: {
    method: "POST",
    path: "/setup/complete",
    headers: ["Idempotency-Key"],
    query: [],
    authenticated: true,
  },
  getSetupCapabilities: {
    method: "GET",
    path: "/setup/capabilities",
    headers: [],
    query: [],
    authenticated: true,
  },
  validateSetupProviderConnection: {
    method: "POST",
    path: "/setup/provider-connections/validate",
    headers: ["Idempotency-Key"],
    query: [],
    authenticated: true,
  },
  getOverview: {
    method: "GET",
    path: "/overview",
    headers: [],
    query: [],
    authenticated: true,
  },
  listDataCapabilities: {
    method: "GET",
    path: "/data/capabilities",
    headers: [],
    query: [],
    authenticated: true,
  },
  evaluateDataCapabilities: {
    method: "POST",
    path: "/data/capabilities/evaluate",
    headers: [],
    query: [],
    authenticated: true,
  },
  validateDataset: {
    method: "POST",
    path: "/data/datasets/{dataset_id}/validate",
    headers: ["Idempotency-Key"],
    query: [],
    authenticated: true,
  },
  createDatasetSnapshot: {
    method: "POST",
    path: "/data/datasets/{dataset_id}/snapshots",
    headers: ["Idempotency-Key"],
    query: [],
    authenticated: true,
  },
  getDatasetSnapshot: {
    method: "GET",
    path: "/data/snapshots/{snapshot_id}",
    headers: [],
    query: [],
    authenticated: true,
  },
  listResearch: {
    method: "GET",
    path: "/research",
    headers: [],
    query: [],
    authenticated: true,
  },
  createResearch: {
    method: "POST",
    path: "/research",
    headers: ["Idempotency-Key"],
    query: [],
    authenticated: true,
  },
  getResearch: {
    method: "GET",
    path: "/research/{research_id}",
    headers: [],
    query: [],
    authenticated: true,
  },
  startResearch: {
    method: "POST",
    path: "/research/{research_id}/start",
    headers: ["Idempotency-Key", "If-Match"],
    query: [],
    authenticated: true,
  },
  createExperiment: {
    method: "POST",
    path: "/experiments",
    headers: ["Idempotency-Key"],
    query: [],
    authenticated: true,
  },
  getExperiment: {
    method: "GET",
    path: "/experiments/{experiment_id}",
    headers: [],
    query: [],
    authenticated: true,
  },
  reproduceExperiment: {
    method: "POST",
    path: "/experiments/{experiment_id}/reproduce",
    headers: ["Idempotency-Key"],
    query: [],
    authenticated: true,
  },
  createFactor: {
    method: "POST",
    path: "/factors",
    headers: ["Idempotency-Key"],
    query: [],
    authenticated: true,
  },
  analyzeFactor: {
    method: "POST",
    path: "/factors/{factor_id}/analyses",
    headers: ["Idempotency-Key"],
    query: [],
    authenticated: true,
  },
  createStrategy: {
    method: "POST",
    path: "/strategies",
    headers: ["Idempotency-Key"],
    query: [],
    authenticated: true,
  },
  getStrategyVersion: {
    method: "GET",
    path: "/strategies/{strategy_id}/versions/{version}",
    headers: [],
    query: [],
    authenticated: true,
  },
  getCurrentStrategyVersion: {
    method: "GET",
    path: "/strategies/{strategy_id}/current-version",
    headers: [],
    query: [],
    authenticated: true,
  },
  runFastBacktest: {
    method: "POST",
    path: "/strategies/{strategy_id}/versions/{version}/backtests",
    headers: ["Idempotency-Key"],
    query: [],
    authenticated: true,
  },
  freezeStrategy: {
    method: "POST",
    path: "/strategies/{strategy_id}/versions/{version}/freeze",
    headers: ["Idempotency-Key", "If-Match"],
    query: [],
    authenticated: true,
  },
  createValidation: {
    method: "POST",
    path: "/validations",
    headers: ["Idempotency-Key"],
    query: [],
    authenticated: true,
  },
  getValidation: {
    method: "GET",
    path: "/validations/{validation_id}",
    headers: [],
    query: [],
    authenticated: true,
  },
  getHoldoutGate: {
    method: "GET",
    path: "/validations/{validation_id}/holdout",
    headers: [],
    query: [],
    authenticated: true,
  },
  requestHoldoutApproval: {
    method: "POST",
    path: "/validations/{validation_id}/holdout-approval-requests",
    headers: ["Idempotency-Key", "If-Match"],
    query: [],
    authenticated: true,
  },
  runHoldout: {
    method: "POST",
    path: "/validations/{validation_id}/holdout-runs",
    headers: ["Idempotency-Key", "If-Match"],
    query: [],
    authenticated: true,
  },
  getHoldoutResult: {
    method: "GET",
    path: "/validations/{validation_id}/holdout/result",
    headers: [],
    query: [],
    authenticated: true,
  },
  generateMemo: {
    method: "POST",
    path: "/memos",
    headers: ["Idempotency-Key"],
    query: [],
    authenticated: true,
  },
  getMemo: {
    method: "GET",
    path: "/memos/{memo_id}",
    headers: [],
    query: [],
    authenticated: true,
  },
  exportMemo: {
    method: "GET",
    path: "/memos/{memo_id}/export",
    headers: [],
    query: [{ name: "format", required: true, value: "MARKDOWN" }],
    authenticated: true,
  },
  listApprovals: {
    method: "GET",
    path: "/approvals",
    headers: [],
    query: [],
    authenticated: true,
  },
  getApproval: {
    method: "GET",
    path: "/approvals/{approval_id}",
    headers: [],
    query: [],
    authenticated: true,
  },
  approveApproval: {
    method: "POST",
    path: "/approvals/{approval_id}/approve",
    headers: ["Idempotency-Key", "If-Match"],
    query: [],
    authenticated: true,
  },
  rejectApproval: {
    method: "POST",
    path: "/approvals/{approval_id}/reject",
    headers: ["Idempotency-Key", "If-Match"],
    query: [],
    authenticated: true,
  },
  listAgents: {
    method: "GET",
    path: "/agents",
    headers: [],
    query: [],
    authenticated: true,
  },
  getAgentConfig: {
    method: "GET",
    path: "/agents/{role}/config",
    headers: [],
    query: [],
    authenticated: true,
  },
  updateAgentConfig: {
    method: "PUT",
    path: "/agents/{role}/config",
    headers: ["If-Match"],
    query: [],
    authenticated: true,
  },
  getAgentRun: {
    method: "GET",
    path: "/agent-runs/{agent_run_id}",
    headers: [],
    query: [],
    authenticated: true,
  },
  getToolCall: {
    method: "GET",
    path: "/tool-calls/{tool_call_id}",
    headers: [],
    query: [],
    authenticated: true,
  },
  getJob: {
    method: "GET",
    path: "/jobs/{job_id}",
    headers: [],
    query: [],
    authenticated: true,
  },
  streamEvents: {
    method: "GET",
    path: "/events/stream",
    headers: ["Last-Event-ID"],
    query: [],
    authenticated: true,
  },
} as const satisfies Record<keyof operations, CanonicalOperation>;

export type CanonicalOperationId = keyof typeof operationMap;
