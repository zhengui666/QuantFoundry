import type { components, operations } from './generated';
import { operationMap, type CanonicalOperationId } from './generated/operation-map';
import { transientStorage } from '../shared/transient-storage';
import {
  ApiProblemSchema,
  ConfigurationCandidateRequestSchema,
  ConfigurationCatalogSchema,
  ConfigurationActiveSchema,
  ConfigurationCandidateSchema,
  ConfigurationValidationResultSchema,
  DatabaseConnectionCandidateRequestSchema,
  DatabaseConnectionCandidateSchema,
  DatabaseConnectionValidationResultSchema,
  DatabaseConnectionStatusSchema,
  GeneralAccessKeyCreateRequestSchema,
  GeneralAccessKeyIssuedSchema,
  GeneralAccessKeyListSchema,
  GeneralAccessKeyLoginRequestSchema,
  GeneralAccessKeyMetadataSchema,
  OwnerSessionViewSchema,
  SessionBootstrapResponseSchema,
  AgentConfigListSchema,
  AgentConfigSchema,
  AgentConfigUpdateSchema,
  ApprovalDecisionRequestSchema,
  ApprovalDecisionResultSchema,
  ApprovalDetailSchema,
  ApprovalPageSchema,
  ApprovalRejectRequestSchema,
  BacktestRequestSchema,
  DataCapabilityListSchema,
  ExperimentCreateRequestSchema,
  ExperimentDetailSchema,
  ExperimentReproduceRequestSchema,
  ExperimentReproduceAcceptedSchema,
  FreezeStrategyRequestSchema,
  HoldoutApprovalRequestSchema,
  HoldoutGateSchema,
  HoldoutResultSchema,
  HoldoutRunRequestSchema,
  JobAcceptedSchema,
  JobDetailSchema,
  LiveConnectorValidationRequestSchema,
  LiveConnectorValidationResultSchema,
  MemoDetailSchema,
  MemoGenerateRequestSchema,
  OverviewReadModelSchema,
  PublicIdSchemas,
  type PublicIdType,
  ResearchCreateRequestSchema,
  ResearchDetailSchema,
  ResearchPageSchema,
  ResearchStartRequestSchema,
  SetupCapabilityCatalogSchema,
  SetupCompleteRequestSchema,
  SetupProviderConnectionValidationRequestSchema,
  SetupProviderConnectionValidationResultSchema,
  SetupStatusSchema,
  SseEnvelopeSchema,
  StrategyCreateRequestSchema,
  StrategyVersionDetailSchema,
  ValidationCreateRequestSchema,
  ValidationDetailSchema,
} from './generated/runtime-schemas';

export type Schema<K extends keyof components['schemas']> = components['schemas'][K];
export type ApiProblem = Schema<'ApiProblem'>;
export type CanonicalErrorCode = Schema<'CanonicalErrorCode'>;
export type ExperimentReproduceBody = Schema<'ExperimentReproduceRequest'>;
export type ApiResult<T> = {
  body: T;
  status: number;
  etag: string | null;
  contentLocation: string | null;
  location: string | null;
};

export class ApiError extends Error {
  constructor(public readonly problem: ApiProblem) {
    super(problem.title);
  }
}

export class ContractError extends Error {}

export function parsePublicId<T extends PublicIdType>(type: T, value: string): string {
  const parsed = PublicIdSchemas[type].safeParse(value);
  if (!parsed.success) throw new ContractError(`Invalid canonical ${type} public ID.`);
  return parsed.data;
}

export function isPublicId<T extends PublicIdType>(type: T, value: string): boolean {
  return PublicIdSchemas[type].safeParse(value).success;
}

const eventCursorPrefix = 'qf.sse.cursor:';
const nextOpaqueScope = (): string => `owner:${crypto.randomUUID()}`;
const clearEventCursor = (scope: string): void => {
  transientStorage.remove(`${eventCursorPrefix}${scope}`);
};
const clearStaleEventCursors = (): void => {
  transientStorage.removeByPrefix(eventCursorPrefix);
};

// A browser reload creates a fresh, non-reusable memory epoch. Persisted cursors from the
// preceding authorization/workspace epoch must never cross that boundary.
clearStaleEventCursors();
let sessionMarker = '';
let csrfToken = '';
let authScopeKey = nextOpaqueScope();
const tokenListeners = new Set<() => void>();
export const auth = {
  get() {
    return sessionMarker;
  },
  set(token = 'session') {
    if (!token && !sessionMarker) return;
    const previousScope = authScopeKey;
    clearEventCursor(previousScope);
    sessionMarker = token ? 'session' : '';
    if (!token) csrfToken = '';
    authScopeKey = nextOpaqueScope();
    tokenListeners.forEach((listener) => listener());
  },
  clear() {
    this.set('');
  },
  subscribe(listener: () => void) {
    tokenListeners.add(listener);
    return () => {
      tokenListeners.delete(listener);
    };
  },
  scope() {
    return authScopeKey;
  },
  csrf() {
    return csrfToken;
  },
  establish(session: Schema<'OwnerSessionView'>) {
    csrfToken = session.csrf_token;
    auth.set();
  },
};

export const workspaceQueryKey = (...segments: readonly unknown[]): readonly unknown[] => [
  auth.scope(),
  ...segments,
];

export const idempotency = (): string => crypto.randomUUID();
type OperationPathParams = Readonly<Record<string, string | number>>;

function pathFor(operationId: CanonicalOperationId, pathParams: OperationPathParams = {}): string {
  const operation = operationMap[operationId];
  const path = operation.path.replace(/\{([^}]+)\}/g, (_match, parameter: string) => {
    const value = pathParams[parameter];
    if (value === undefined)
      throw new ContractError(`Missing canonical path parameter ${parameter} for ${operationId}.`);
    return encodeURIComponent(String(value));
  });
  const query = new URLSearchParams();
  for (const parameter of operation.query) {
    const value = parameter.value ?? pathParams[parameter.name];
    if (value === undefined && parameter.required)
      throw new ContractError(
        `Missing canonical query parameter ${parameter.name} for ${operationId}.`,
      );
    if (value !== undefined) query.set(parameter.name, String(value));
  }
  return `/api/v1${path}${query.size === 0 ? '' : `?${query.toString()}`}`;
}

function headersFor(operationId: CanonicalOperationId, init: RequestInit) {
  const operation = operationMap[operationId];
  const headers = new Headers(init.headers);
  const canonicalHeaders: readonly string[] = operation.headers;
  for (const header of ['If-Match', 'Idempotency-Key', 'Last-Event-ID'])
    if (headers.has(header) && !canonicalHeaders.includes(header))
      throw new ContractError(`${header} is not defined by canonical operation ${operationId}.`);
  if (!headers.has('Accept')) headers.set('Accept', 'application/json');
  if (init.body) headers.set('Content-Type', 'application/json');
  if (
    operation.authenticated &&
    !['GET', 'HEAD', 'OPTIONS'].includes(operation.method) &&
    csrfToken
  )
    headers.set('X-CSRF-Token', csrfToken);
  return headers;
}

async function readProblem(response: Response): Promise<ApiProblem> {
  try {
    const parsed = ApiProblemSchema.safeParse(await response.json());
    if (parsed.success) return parsed.data as ApiProblem;
  } catch {
    // Fall through to a closed local transport problem without exposing response text.
  }
  return {
    type: 'about:blank',
    title: response.statusText || 'Invalid Problem response',
    status: response.status,
    code: 'INTERNAL_ERROR',
    detail: null,
    instance: null,
    request_id: response.headers.get('X-Request-ID') ?? 'unavailable',
    retryable: false,
    field_errors: [],
    context: {},
  };
}

async function throwProblem(response: Response): Promise<never> {
  const problem = await readProblem(response);
  if (problem.status === 401 && problem.code === 'UNAUTHENTICATED') auth.clear();
  throw new ApiError(problem);
}

async function request<T>(
  operationId: CanonicalOperationId,
  init: RequestInit = {},
  pathParams: OperationPathParams = {},
): Promise<ApiResult<T>> {
  const response = await fetch(pathFor(operationId, pathParams), {
    ...init,
    method: operationMap[operationId].method,
    headers: headersFor(operationId, init),
    credentials: 'include',
  });
  if (!response.ok) return throwProblem(response);
  return {
    body: (response.status === 204 ? undefined : await response.json()) as T,
    status: response.status,
    etag: response.headers.get('ETag'),
    contentLocation: response.headers.get('Content-Location'),
    location: response.headers.get('Location'),
  };
}

async function requestText(
  operationId: CanonicalOperationId,
  pathParams: OperationPathParams,
  signal?: AbortSignal,
): Promise<ApiResult<string>> {
  const init = { headers: { Accept: 'text/markdown' } };
  const response = await fetch(pathFor(operationId, pathParams), {
    method: operationMap[operationId].method,
    headers: headersFor(operationId, init),
    credentials: 'include',
    signal: signal ?? null,
  });
  if (!response.ok) return throwProblem(response);
  return {
    body: await response.text(),
    status: response.status,
    etag: response.headers.get('ETag'),
    contentLocation: response.headers.get('Content-Location'),
    location: response.headers.get('Location'),
  };
}

function validateResult<T>(
  result: ApiResult<unknown>,
  schema: {
    safeParse(value: unknown): { success: true; data: unknown } | { success: false };
  },
  label: string,
): ApiResult<T> {
  const parsed = schema.safeParse(result.body);
  if (!parsed.success) throw new ContractError(`Invalid canonical ${label} response.`);
  return { ...result, body: parsed.data as T };
}

function validateInput<T>(
  value: unknown,
  schema: {
    safeParse(value: unknown): { success: true; data: unknown } | { success: false };
  },
  label: string,
): T {
  const parsed = schema.safeParse(value);
  if (!parsed.success) throw new ContractError(`Invalid canonical ${label} request.`);
  return parsed.data as T;
}

function positiveVersion(value: number): number {
  if (!Number.isSafeInteger(value) || value < 1)
    throw new ContractError('Invalid canonical strategy version.');
  return value;
}

function sameCanonicalValue(left: unknown, right: unknown): boolean {
  if (Object.is(left, right)) return true;
  if (Array.isArray(left) && Array.isArray(right))
    return (
      left.length === right.length &&
      left.every((value, index) => sameCanonicalValue(value, right[index]))
    );
  if (
    left !== null &&
    right !== null &&
    typeof left === 'object' &&
    typeof right === 'object' &&
    !Array.isArray(left) &&
    !Array.isArray(right)
  ) {
    const leftRecord = left as Record<string, unknown>;
    const rightRecord = right as Record<string, unknown>;
    const keys = Object.keys(leftRecord);
    return (
      keys.length === Object.keys(rightRecord).length &&
      keys.every(
        (key) =>
          Object.hasOwn(rightRecord, key) && sameCanonicalValue(leftRecord[key], rightRecord[key]),
      )
    );
  }
  return false;
}

const strategyMirrorKeys = [
  'thesis',
  'universe',
  'signals',
  'rules',
  'cost_model_id',
  'benchmark',
  'research_period',
  'validation_period',
  'holdout_period',
  'known_failure_modes',
  'spec_sha256',
] as const satisfies readonly (keyof Schema<'StrategyVersionDetail'>)[];

function validateStrategyDetail(
  result: ApiResult<unknown>,
  expectedId?: string,
  expectedVersion?: number,
  requireCanonicalLocation = false,
): ApiResult<Schema<'StrategyVersionDetail'>> {
  const canonical = validateResult<Schema<'StrategyVersionDetail'>>(
    result,
    StrategyVersionDetailSchema,
    'StrategyVersionDetail',
  );
  const body = canonical.body;
  if (
    (expectedId !== undefined && body.strategy_id !== expectedId) ||
    (expectedVersion !== undefined && body.version !== expectedVersion)
  )
    throw new ContractError('Strategy response identity does not match the requested version.');
  if (strategyMirrorKeys.some((key) => !sameCanonicalValue(body[key], body.specification[key])))
    throw new ContractError('Strategy specification does not mirror its canonical projection.');
  if (requireCanonicalLocation) {
    const expectedPath = pathFor('getStrategyVersion', {
      strategy_id: body.strategy_id,
      version: body.version,
    });
    let locationPath: string | null = canonical.contentLocation;
    if (locationPath?.startsWith('http://') || locationPath?.startsWith('https://'))
      locationPath = new URL(locationPath).pathname;
    if (locationPath !== expectedPath)
      throw new ContractError('Strategy Content-Location does not match the resolved version.');
  }
  return canonical;
}

export const api = {
  login: async (key: string) => {
    const body = validateInput<Schema<'GeneralAccessKeyLoginRequest'>>(
      { key },
      GeneralAccessKeyLoginRequestSchema,
      'GeneralAccessKeyLogin',
    );
    const result = validateResult<Schema<'SessionBootstrapResponse'>>(
      await request<unknown>('loginWithGeneralAccessKey', { body: JSON.stringify(body) }),
      SessionBootstrapResponseSchema,
      'SessionBootstrapResponse',
    );
    auth.establish(result.body.session);
    return result;
  },
  session: async (signal?: AbortSignal) => {
    const result = validateResult<Schema<'OwnerSessionView'>>(
      await request<unknown>('getCurrentOwnerSession', { signal: signal ?? null }),
      OwnerSessionViewSchema,
      'OwnerSessionView',
    );
    auth.establish(result.body);
    return result;
  },
  logout: async () => {
    const result = await request<undefined>('logoutOwnerSession');
    auth.clear();
    return result;
  },
  accessKeys: async (signal?: AbortSignal) =>
    validateResult<Schema<'GeneralAccessKeyList'>>(
      await request<unknown>('listGeneralAccessKeys', { signal: signal ?? null }),
      GeneralAccessKeyListSchema,
      'GeneralAccessKeyList',
    ),
  createAccessKey: async (
    body: Schema<'GeneralAccessKeyCreateRequest'>,
    idempotencyKey = idempotency(),
  ) => {
    const canonicalBody = validateInput<Schema<'GeneralAccessKeyCreateRequest'>>(
      body,
      GeneralAccessKeyCreateRequestSchema,
      'GeneralAccessKeyCreate',
    );
    return validateResult<Schema<'GeneralAccessKeyIssued'>>(
      await request<unknown>('createGeneralAccessKey', {
        headers: { 'Idempotency-Key': idempotencyKey },
        body: JSON.stringify(canonicalBody),
      }),
      GeneralAccessKeyIssuedSchema,
      'GeneralAccessKeyIssued',
    );
  },
  renameAccessKey: async (keyId: string, label: string, etag: string) => {
    const canonicalBody = validateInput<Schema<'GeneralAccessKeyCreateRequest'>>(
      { label, expires_at: null },
      GeneralAccessKeyCreateRequestSchema,
      'GeneralAccessKeyRename',
    );
    return validateResult<Schema<'GeneralAccessKeyMetadata'>>(
      await request<unknown>(
        'renameGeneralAccessKey',
        {
          headers: { 'If-Match': etag },
          body: JSON.stringify({ label: canonicalBody.label }),
        },
        { key_id: keyId },
      ),
      GeneralAccessKeyMetadataSchema,
      'GeneralAccessKeyMetadata',
    );
  },
  rotateAccessKey: async (keyId: string, etag: string, idempotencyKey = idempotency()) =>
    validateResult<Schema<'GeneralAccessKeyIssued'>>(
      await request<unknown>(
        'rotateGeneralAccessKey',
        { headers: { 'If-Match': etag, 'Idempotency-Key': idempotencyKey } },
        { key_id: keyId },
      ),
      GeneralAccessKeyIssuedSchema,
      'GeneralAccessKeyIssued',
    ),
  revokeAccessKey: async (keyId: string, etag: string) =>
    request<undefined>(
      'revokeGeneralAccessKey',
      { headers: { 'If-Match': etag } },
      { key_id: keyId },
    ),
  expireAccessKey: async (keyId: string, etag: string) =>
    request<undefined>(
      'expireGeneralAccessKey',
      { headers: { 'If-Match': etag } },
      { key_id: keyId },
    ),
  configurationCatalog: async (signal?: AbortSignal) =>
    validateResult<Schema<'ConfigurationCatalog'>>(
      await request<unknown>('getConfigurationCatalog', { signal: signal ?? null }),
      ConfigurationCatalogSchema,
      'ConfigurationCatalog',
    ),
  configurationActive: async (signal?: AbortSignal) =>
    validateResult<Schema<'ConfigurationActive'>>(
      await request<unknown>('getActiveConfiguration', { signal: signal ?? null }),
      ConfigurationActiveSchema,
      'ConfigurationActive',
    ),
  putConfigurationCandidate: async (
    body: Schema<'ConfigurationCandidateRequest'>,
    etag: string,
    idempotencyKey = idempotency(),
  ) => {
    const canonicalBody = validateInput(
      body,
      ConfigurationCandidateRequestSchema,
      'ConfigurationCandidate',
    );
    return validateResult<Schema<'ConfigurationCandidate'>>(
      await request<unknown>('putConfigurationCandidate', {
        headers: { 'If-Match': etag, 'Idempotency-Key': idempotencyKey },
        body: JSON.stringify(canonicalBody),
      }),
      ConfigurationCandidateSchema,
      'ConfigurationCandidate',
    );
  },
  validateConfigurationCandidate: async (idempotencyKey = idempotency()) =>
    validateResult<Schema<'ConfigurationValidationResult'>>(
      await request<unknown>('validateConfigurationCandidate', {
        headers: { 'Idempotency-Key': idempotencyKey },
      }),
      ConfigurationValidationResultSchema,
      'ConfigurationValidationResult',
    ),
  activateConfiguration: async (revision: number, etag: string, idempotencyKey = idempotency()) =>
    validateResult<Schema<'ConfigurationActive'>>(
      await request<unknown>('activateConfiguration', {
        headers: { 'If-Match': etag, 'Idempotency-Key': idempotencyKey },
        body: JSON.stringify({ revision }),
      }),
      ConfigurationActiveSchema,
      'ConfigurationActive',
    ),
  databaseConnection: async (signal?: AbortSignal) =>
    validateResult<Schema<'DatabaseConnectionStatus'>>(
      await request<unknown>('getDomainDatabaseConnection', { signal: signal ?? null }),
      DatabaseConnectionStatusSchema,
      'DatabaseConnectionStatus',
    ),
  putDatabaseConnectionCandidate: async (
    body: Schema<'DatabaseConnectionCandidateRequest'>,
    etag: string,
    idempotencyKey = idempotency(),
  ) => {
    const canonicalBody = validateInput(
      body,
      DatabaseConnectionCandidateRequestSchema,
      'DatabaseConnectionCandidate',
    );
    return validateResult<Schema<'DatabaseConnectionCandidate'>>(
      await request<unknown>('putDomainDatabaseConnectionCandidate', {
        headers: { 'If-Match': etag, 'Idempotency-Key': idempotencyKey },
        body: JSON.stringify(canonicalBody),
      }),
      DatabaseConnectionCandidateSchema,
      'DatabaseConnectionCandidate',
    );
  },
  validateDatabaseConnectionCandidate: async (
    candidateRevision: number,
    idempotencyKey = idempotency(),
  ) =>
    validateResult<Schema<'DatabaseConnectionValidationResult'>>(
      await request<unknown>('validateDomainDatabaseConnectionCandidate', {
        headers: {
          'Idempotency-Key': idempotencyKey,
          'X-Candidate-Revision': String(candidateRevision),
        },
      }),
      DatabaseConnectionValidationResultSchema,
      'DatabaseConnectionValidationResult',
    ),
  activateDatabaseConnection: async (
    etag: string,
    candidateRevision: number,
    idempotencyKey = idempotency(),
  ) =>
    validateResult<Schema<'DatabaseConnectionStatus'>>(
      await request<unknown>('activateDomainDatabaseConnection', {
        headers: {
          'If-Match': etag,
          'Idempotency-Key': idempotencyKey,
          'X-Candidate-Revision': String(candidateRevision),
        },
      }),
      DatabaseConnectionStatusSchema,
      'DatabaseConnectionStatus',
    ),
  setupStatus: async (signal?: AbortSignal) =>
    validateResult<Schema<'SetupStatus'>>(
      await request<unknown>('getSetupStatus', { signal: signal ?? null }),
      SetupStatusSchema,
      'SetupStatus',
    ),
  setupCapabilities: async (signal?: AbortSignal) =>
    validateResult<Schema<'SetupCapabilityCatalog'>>(
      await request<unknown>('getSetupCapabilities', { signal: signal ?? null }),
      SetupCapabilityCatalogSchema,
      'SetupCapabilityCatalog',
    ),
  validateSetupConnection: async (
    body: Schema<'SetupProviderConnectionValidationRequest'>,
    idempotencyKey = idempotency(),
  ) => {
    const canonicalBody = validateInput<Schema<'SetupProviderConnectionValidationRequest'>>(
      body,
      SetupProviderConnectionValidationRequestSchema,
      'SetupProviderConnectionValidation',
    );
    return validateResult<Schema<'SetupProviderConnectionValidationResult'>>(
      await request<unknown>('validateSetupProviderConnection', {
        headers: { 'Idempotency-Key': idempotencyKey },
        body: JSON.stringify(canonicalBody),
      }),
      SetupProviderConnectionValidationResultSchema,
      'SetupProviderConnectionValidationResult',
    );
  },
  validateLiveConnector: async (
    body: Schema<'LiveConnectorValidationRequest'>,
    idempotencyKey = idempotency(),
  ) => {
    const canonicalBody = validateInput<Schema<'LiveConnectorValidationRequest'>>(
      body,
      LiveConnectorValidationRequestSchema,
      'LiveConnectorValidation',
    );
    return validateResult<Schema<'LiveConnectorValidationResult'>>(
      await request<unknown>('validateLiveConnector', {
        headers: { 'Idempotency-Key': idempotencyKey },
        body: JSON.stringify(canonicalBody),
      }),
      LiveConnectorValidationResultSchema,
      'LiveConnectorValidationResult',
    );
  },
  completeSetup: async (
    body: Schema<'SetupCompleteRequest'> | Record<string, unknown>,
    etag: string,
    idempotencyKey = idempotency(),
  ) => {
    const canonicalBody = validateInput<Schema<'SetupCompleteRequest'>>(
      body,
      SetupCompleteRequestSchema,
      'SetupComplete',
    );
    return validateResult<Schema<'ConfigurationActive'>>(
      await request<unknown>('completeSetup', {
        headers: { 'If-Match': etag, 'Idempotency-Key': idempotencyKey },
        body: JSON.stringify(canonicalBody),
      }),
      ConfigurationActiveSchema,
      'ConfigurationActive',
    );
  },
  overview: async (signal?: AbortSignal) =>
    validateResult<Schema<'OverviewReadModel'>>(
      await request<unknown>('getOverview', { signal: signal ?? null }),
      OverviewReadModelSchema,
      'OverviewReadModel',
    ),
  dataCapabilities: async (signal?: AbortSignal) =>
    validateResult<Schema<'DataCapabilityList'>>(
      await request<unknown>('listDataCapabilities', { signal: signal ?? null }),
      DataCapabilityListSchema,
      'DataCapabilityList',
    ),
  research: async (signal?: AbortSignal) =>
    validateResult<Schema<'ResearchPage'>>(
      await request<unknown>('listResearch', { signal: signal ?? null }),
      ResearchPageSchema,
      'ResearchPage',
    ),
  researchDetail: async (id: string, signal?: AbortSignal) => {
    const researchId = parsePublicId('research', id);
    return validateResult<Schema<'ResearchDetail'>>(
      await request<unknown>(
        'getResearch',
        { signal: signal ?? null },
        { research_id: researchId },
      ),
      ResearchDetailSchema,
      'ResearchDetail',
    );
  },
  createResearch: async (body: Schema<'ResearchCreateRequest'>, idempotencyKey = idempotency()) => {
    const canonicalBody = validateInput<Schema<'ResearchCreateRequest'>>(
      body,
      ResearchCreateRequestSchema,
      'ResearchCreate',
    );
    return validateResult<Schema<'ResearchDetail'>>(
      await request<unknown>('createResearch', {
        headers: { 'Idempotency-Key': idempotencyKey },
        body: JSON.stringify(canonicalBody),
      }),
      ResearchDetailSchema,
      'ResearchDetail',
    );
  },
  startResearch: async (
    id: string,
    etag: string,
    body: Schema<'ResearchStartRequest'>,
    idempotencyKey = idempotency(),
  ) => {
    const researchId = parsePublicId('research', id);
    const canonicalBody = validateInput<Schema<'ResearchStartRequest'>>(
      body,
      ResearchStartRequestSchema,
      'ResearchStart',
    );
    return validateResult<Schema<'JobAccepted'>>(
      await request<unknown>(
        'startResearch',
        {
          headers: { 'If-Match': etag, 'Idempotency-Key': idempotencyKey },
          body: JSON.stringify(canonicalBody),
        },
        { research_id: researchId },
      ),
      JobAcceptedSchema,
      'JobAccepted',
    );
  },
  experiment: async (id: string, signal?: AbortSignal) => {
    const experimentId = parsePublicId('experiment', id);
    return validateResult<Schema<'ExperimentDetail'>>(
      await request<unknown>(
        'getExperiment',
        { signal: signal ?? null },
        { experiment_id: experimentId },
      ),
      ExperimentDetailSchema,
      'ExperimentDetail',
    );
  },
  createExperiment: async (
    body: Schema<'ExperimentCreateRequest'>,
    idempotencyKey = idempotency(),
  ) => {
    const canonicalBody = validateInput<Schema<'ExperimentCreateRequest'>>(
      body,
      ExperimentCreateRequestSchema,
      'ExperimentCreate',
    );
    return validateResult<Schema<'JobAccepted'>>(
      await request<unknown>('createExperiment', {
        headers: { 'Idempotency-Key': idempotencyKey },
        body: JSON.stringify(canonicalBody),
      }),
      JobAcceptedSchema,
      'JobAccepted',
    );
  },
  reproduceExperiment: async (
    id: string,
    body: ExperimentReproduceBody,
    idempotencyKey: string,
  ) => {
    const experimentId = parsePublicId('experiment', id);
    const requestedMode =
      'mode' in body && body.mode === 'CONTROLLED_OVERRIDE' ? 'CONTROLLED_OVERRIDE' : 'EXACT';
    const canonicalBody = validateInput<ExperimentReproduceBody>(
      body,
      ExperimentReproduceRequestSchema,
      'ExperimentReproduce',
    );
    const result = await request<unknown>(
      'reproduceExperiment',
      {
        headers: { 'Idempotency-Key': idempotencyKey },
        body: JSON.stringify(canonicalBody),
      },
      { experiment_id: experimentId },
    );
    if (result.status !== 202) throw new ContractError('Reproduce must return HTTP 202.');
    const parsed = ExperimentReproduceAcceptedSchema.safeParse(result.body);
    if (!parsed.success)
      throw new ContractError('Invalid canonical ExperimentReproduceAccepted response.');
    const accepted = parsed.data;
    const expectedLocation = pathFor('getExperiment', { experiment_id: accepted.resource_ref.id });
    const locationPath = result.location
      ? result.location.startsWith('http://') || result.location.startsWith('https://')
        ? new URL(result.location).pathname
        : result.location
      : null;
    if (
      locationPath !== expectedLocation ||
      accepted.resource_ref.type !== 'experiment' ||
      accepted.resource_ref.version !== null ||
      accepted.resource_ref.revision !== 1 ||
      accepted.source_experiment_id !== experimentId ||
      accepted.reproduce_mode !== requestedMode
    )
      throw new ContractError(
        'Reproduce Location or lineage does not match the accepted Experiment.',
      );
    return { ...result, body: accepted };
  },
  strategyVersion: async (id: string, version: number, signal?: AbortSignal) => {
    const strategyId = parsePublicId('strategy', id);
    const strategyVersion = positiveVersion(version);
    return validateStrategyDetail(
      await request<unknown>(
        'getStrategyVersion',
        { signal: signal ?? null },
        { strategy_id: strategyId, version: strategyVersion },
      ),
      strategyId,
      strategyVersion,
    );
  },
  currentStrategyVersion: async (id: string, signal?: AbortSignal) => {
    const strategyId = parsePublicId('strategy', id);
    return validateStrategyDetail(
      await request<unknown>(
        'getCurrentStrategyVersion',
        { signal: signal ?? null },
        { strategy_id: strategyId },
      ),
      strategyId,
      undefined,
      true,
    );
  },
  createStrategy: async (body: Schema<'StrategyCreateRequest'>, idempotencyKey = idempotency()) => {
    const canonicalBody = validateInput<Schema<'StrategyCreateRequest'>>(
      body,
      StrategyCreateRequestSchema,
      'StrategyCreate',
    );
    return validateStrategyDetail(
      await request<unknown>('createStrategy', {
        headers: { 'Idempotency-Key': idempotencyKey },
        body: JSON.stringify(canonicalBody),
      }),
    );
  },
  freezeStrategy: async (
    id: string,
    version: number,
    etag: string,
    body: Schema<'FreezeStrategyRequest'>,
    idempotencyKey = idempotency(),
  ) => {
    const strategyId = parsePublicId('strategy', id);
    const strategyVersion = positiveVersion(version);
    const canonicalBody = validateInput<Schema<'FreezeStrategyRequest'>>(
      body,
      FreezeStrategyRequestSchema,
      'FreezeStrategy',
    );
    return validateStrategyDetail(
      await request<unknown>(
        'freezeStrategy',
        {
          headers: { 'If-Match': etag, 'Idempotency-Key': idempotencyKey },
          body: JSON.stringify(canonicalBody),
        },
        { strategy_id: strategyId, version: strategyVersion },
      ),
      strategyId,
      strategyVersion,
    );
  },
  runFastBacktest: async (
    id: string,
    version: number,
    body: Schema<'BacktestRequest'>,
    idempotencyKey = idempotency(),
  ) => {
    const strategyId = parsePublicId('strategy', id);
    const strategyVersion = positiveVersion(version);
    const canonicalBody = validateInput<Schema<'BacktestRequest'>>(
      body,
      BacktestRequestSchema,
      'Backtest',
    );
    return validateResult<Schema<'JobAccepted'>>(
      await request<unknown>(
        'runFastBacktest',
        {
          headers: { 'Idempotency-Key': idempotencyKey },
          body: JSON.stringify(canonicalBody),
        },
        { strategy_id: strategyId, version: strategyVersion },
      ),
      JobAcceptedSchema,
      'JobAccepted',
    );
  },
  createValidation: async (
    body: Schema<'ValidationCreateRequest'>,
    idempotencyKey = idempotency(),
  ) => {
    const canonicalBody = validateInput<Schema<'ValidationCreateRequest'>>(
      body,
      ValidationCreateRequestSchema,
      'ValidationCreate',
    );
    return validateResult<Schema<'JobAccepted'>>(
      await request<unknown>('createValidation', {
        headers: { 'Idempotency-Key': idempotencyKey },
        body: JSON.stringify(canonicalBody),
      }),
      JobAcceptedSchema,
      'JobAccepted',
    );
  },
  validation: async (id: string, signal?: AbortSignal) => {
    const validationId = parsePublicId('validation', id);
    return validateResult<Schema<'ValidationDetail'>>(
      await request<unknown>(
        'getValidation',
        { signal: signal ?? null },
        { validation_id: validationId },
      ),
      ValidationDetailSchema,
      'ValidationDetail',
    );
  },
  holdoutGate: async (id: string, signal?: AbortSignal) => {
    const validationId = parsePublicId('validation', id);
    return validateResult<Schema<'HoldoutGate'>>(
      await request<unknown>(
        'getHoldoutGate',
        { signal: signal ?? null },
        { validation_id: validationId },
      ),
      HoldoutGateSchema,
      'HoldoutGate',
    );
  },
  holdoutResult: async (id: string, signal?: AbortSignal) => {
    const validationId = parsePublicId('validation', id);
    return validateResult<Schema<'HoldoutResult'>>(
      await request<unknown>(
        'getHoldoutResult',
        { signal: signal ?? null },
        { validation_id: validationId },
      ),
      HoldoutResultSchema,
      'HoldoutResult',
    );
  },
  requestHoldoutApproval: async (
    id: string,
    etag: string,
    body: Schema<'HoldoutApprovalRequest'>,
    idempotencyKey = idempotency(),
  ) => {
    const validationId = parsePublicId('validation', id);
    const canonicalBody = validateInput<Schema<'HoldoutApprovalRequest'>>(
      body,
      HoldoutApprovalRequestSchema,
      'HoldoutApproval',
    );
    return validateResult<Schema<'ApprovalDetail'>>(
      await request<unknown>(
        'requestHoldoutApproval',
        {
          headers: { 'If-Match': etag, 'Idempotency-Key': idempotencyKey },
          body: JSON.stringify(canonicalBody),
        },
        { validation_id: validationId },
      ),
      ApprovalDetailSchema,
      'ApprovalDetail',
    );
  },
  runHoldout: async (
    id: string,
    etag: string,
    body: Schema<'HoldoutRunRequest'>,
    idempotencyKey = idempotency(),
  ) => {
    const validationId = parsePublicId('validation', id);
    const canonicalBody = validateInput<Schema<'HoldoutRunRequest'>>(
      body,
      HoldoutRunRequestSchema,
      'HoldoutRun',
    );
    return validateResult<Schema<'JobAccepted'>>(
      await request<unknown>(
        'runHoldout',
        {
          headers: { 'If-Match': etag, 'Idempotency-Key': idempotencyKey },
          body: JSON.stringify(canonicalBody),
        },
        { validation_id: validationId },
      ),
      JobAcceptedSchema,
      'JobAccepted',
    );
  },
  approvals: async (signal?: AbortSignal) =>
    validateResult<Schema<'ApprovalPage'>>(
      await request<unknown>('listApprovals', { signal: signal ?? null }),
      ApprovalPageSchema,
      'ApprovalPage',
    ),
  approval: async (id: string, signal?: AbortSignal) => {
    const approvalId = parsePublicId('approval', id);
    return validateResult<Schema<'ApprovalDetail'>>(
      await request<unknown>(
        'getApproval',
        { signal: signal ?? null },
        { approval_id: approvalId },
      ),
      ApprovalDetailSchema,
      'ApprovalDetail',
    );
  },
  approveApproval: async (
    id: string,
    etag: string,
    body: Schema<'ApprovalDecisionRequest'>,
    idempotencyKey = idempotency(),
  ) => {
    const approvalId = parsePublicId('approval', id);
    const canonicalBody = validateInput<Schema<'ApprovalDecisionRequest'>>(
      body,
      ApprovalDecisionRequestSchema,
      'ApprovalDecision',
    );
    return validateResult<Schema<'ApprovalDecisionResult'>>(
      await request<unknown>(
        'approveApproval',
        {
          headers: { 'If-Match': etag, 'Idempotency-Key': idempotencyKey },
          body: JSON.stringify(canonicalBody),
        },
        { approval_id: approvalId },
      ),
      ApprovalDecisionResultSchema,
      'ApprovalDecisionResult',
    );
  },
  rejectApproval: async (
    id: string,
    etag: string,
    body: Schema<'ApprovalRejectRequest'>,
    idempotencyKey = idempotency(),
  ) => {
    const approvalId = parsePublicId('approval', id);
    const canonicalBody = validateInput<Schema<'ApprovalRejectRequest'>>(
      body,
      ApprovalRejectRequestSchema,
      'ApprovalReject',
    );
    return validateResult<Schema<'ApprovalDecisionResult'>>(
      await request<unknown>(
        'rejectApproval',
        {
          headers: { 'If-Match': etag, 'Idempotency-Key': idempotencyKey },
          body: JSON.stringify(canonicalBody),
        },
        { approval_id: approvalId },
      ),
      ApprovalDecisionResultSchema,
      'ApprovalDecisionResult',
    );
  },
  generateMemo: async (body: Schema<'MemoGenerateRequest'>, idempotencyKey = idempotency()) => {
    const canonicalBody = validateInput<Schema<'MemoGenerateRequest'>>(
      body,
      MemoGenerateRequestSchema,
      'MemoGenerate',
    );
    return validateResult<Schema<'JobAccepted'>>(
      await request<unknown>('generateMemo', {
        headers: { 'Idempotency-Key': idempotencyKey },
        body: JSON.stringify(canonicalBody),
      }),
      JobAcceptedSchema,
      'JobAccepted',
    );
  },
  memo: async (id: string, signal?: AbortSignal) => {
    const memoId = parsePublicId('memo', id);
    return validateResult<Schema<'MemoDetail'>>(
      await request<unknown>('getMemo', { signal: signal ?? null }, { memo_id: memoId }),
      MemoDetailSchema,
      'MemoDetail',
    );
  },
  exportMemo: (id: string, signal?: AbortSignal) => {
    const memoId = parsePublicId('memo', id);
    return requestText('exportMemo', { memo_id: memoId }, signal);
  },
  agents: async (signal?: AbortSignal) =>
    validateResult<Schema<'AgentConfigList'>>(
      await request<unknown>('listAgents', { signal: signal ?? null }),
      AgentConfigListSchema,
      'AgentConfigList',
    ),
  agentConfig: async (role: Schema<'AgentRoleKey'>, signal?: AbortSignal) =>
    validateResult<Schema<'AgentConfig'>>(
      await request<unknown>('getAgentConfig', { signal: signal ?? null }, { role }),
      AgentConfigSchema,
      'AgentConfig',
    ),
  updateAgent: async (
    role: Schema<'AgentRoleKey'>,
    etag: string,
    body: Schema<'AgentConfigUpdate'>,
  ) => {
    const canonicalBody = validateInput<Schema<'AgentConfigUpdate'>>(
      body,
      AgentConfigUpdateSchema,
      'AgentConfigUpdate',
    );
    return validateResult<Schema<'AgentConfig'>>(
      await request<unknown>(
        'updateAgentConfig',
        { headers: { 'If-Match': etag }, body: JSON.stringify(canonicalBody) },
        { role },
      ),
      AgentConfigSchema,
      'AgentConfig',
    );
  },
  job: async (id: string, signal?: AbortSignal) => {
    const jobId = parsePublicId('job', id);
    return validateResult<Schema<'JobDetail'>>(
      await request<unknown>('getJob', { signal: signal ?? null }, { job_id: jobId }),
      JobDetailSchema,
      'JobDetail',
    );
  },
};

export type EventEnvelope = Schema<'SseEnvelope'>;
export type EventType = Schema<'EventType'>;
export type EventQueryKey = readonly unknown[];
export type QueryInvalidationPlan = {
  queryKeys: readonly EventQueryKey[];
  resyncActiveMutable: boolean;
};
type QueryInvalidationRule = (event: EventEnvelope) => QueryInvalidationPlan;

const plan = (
  queryKeys: readonly EventQueryKey[],
  resyncActiveMutable = false,
): QueryInvalidationPlan => ({ queryKeys, resyncActiveMutable });
const overview = (): EventQueryKey => workspaceQueryKey('overview');
const researchList = (): EventQueryKey => workspaceQueryKey('research');
const researchDetail = (researchId: string): EventQueryKey =>
  workspaceQueryKey('research', researchId);
const owningResearch = (event: EventEnvelope): readonly EventQueryKey[] =>
  event.payload.research_id ? [researchDetail(event.payload.research_id)] : [];
const strategyKeys = (event: EventEnvelope): readonly EventQueryKey[] => [
  workspaceQueryKey('strategy', event.object_id, 'current'),
  ...(event.object_version === null
    ? []
    : ([workspaceQueryKey('strategy', event.object_id, event.object_version)] as const)),
  overview(),
];
const approvalKeys = (event: EventEnvelope): readonly EventQueryKey[] => [
  workspaceQueryKey('approvals'),
  workspaceQueryKey('approval', event.object_id),
  overview(),
];
const dataKeys = (): readonly EventQueryKey[] => [
  workspaceQueryKey('setup-capabilities'),
  workspaceQueryKey('data-capabilities'),
  overview(),
];

export const EVENT_QUERY_RULES = {
  'job.updated': (event) =>
    plan([
      ...(event.job_id ? ([workspaceQueryKey('job', event.job_id)] as const) : []),
      ...owningResearch(event),
      overview(),
    ]),
  'research.created': () => plan([researchList(), overview()]),
  'research.updated': (event) =>
    plan([researchDetail(event.object_id), researchList(), overview()]),
  'research.conclusion.created': (event) =>
    plan([researchDetail(event.object_id), researchList(), overview()]),
  'experiment.created': (event) =>
    plan([
      ...owningResearch(event),
      researchList(),
      workspaceQueryKey('experiment', event.object_id),
      overview(),
    ]),
  'experiment.updated': (event) =>
    plan([workspaceQueryKey('experiment', event.object_id), ...owningResearch(event), overview()]),
  'factor.updated': (event) => plan([...owningResearch(event), overview()]),
  'strategy.created': (event) => plan(strategyKeys(event)),
  'strategy.updated': (event) => plan(strategyKeys(event)),
  'validation.created': (event) =>
    plan([workspaceQueryKey('validation', event.object_id), overview()]),
  'validation.updated': (event) =>
    plan([workspaceQueryKey('validation', event.object_id), overview()]),
  'validation.holdout.updated': (event) =>
    plan([
      workspaceQueryKey('validation', event.object_id),
      workspaceQueryKey('holdout', event.object_id),
      workspaceQueryKey('holdout-result', event.object_id),
    ]),
  'approval.created': (event) => plan(approvalKeys(event)),
  'approval.updated': (event) => plan(approvalKeys(event)),
  'paper.created': () => plan([overview()]),
  'paper.updated': () => plan([overview()]),
  'paper.run.updated': () => plan([overview()]),
  'review.created': () => plan([overview()]),
  'review.updated': () => plan([overview()]),
  'data.provider.updated': () => plan(dataKeys()),
  'data.capability.updated': () => plan(dataKeys()),
  'data.quality.updated': () => plan(dataKeys()),
  'agent.run.updated': (event) =>
    plan([
      ...(event.agent_run_id
        ? ([workspaceQueryKey('agent-run', event.agent_run_id)] as const)
        : []),
      ...owningResearch(event),
      overview(),
    ]),
  'tool.call.updated': (event) =>
    plan([
      ...(event.tool_call_id
        ? ([workspaceQueryKey('tool-call', event.tool_call_id)] as const)
        : []),
      overview(),
    ]),
  'memo.created': (event) => plan([workspaceQueryKey('memo', event.object_id), overview()]),
  'memo.updated': (event) => plan([workspaceQueryKey('memo', event.object_id), overview()]),
  'setup.completed': () => plan([workspaceQueryKey('setup-status'), overview()]),
  'configuration.updated': () => plan([workspaceQueryKey('settings'), overview()]),
  'configuration.apply_failed': () => plan([workspaceQueryKey('settings')]),
  'database.connection.updated': () => plan([workspaceQueryKey('settings')]),
  'database.connection.failed': () => plan([workspaceQueryKey('settings')]),
  'notification.created': () => plan([overview()]),
  'notification.updated': () => plan([overview()]),
  'system.health.updated': () => plan([workspaceQueryKey('system-health'), overview()]),
  'system.resync_required': () => plan([], true),
} satisfies Record<EventType, QueryInvalidationRule>;

export const queryPlanForEvent = (event: EventEnvelope): QueryInvalidationPlan => {
  const base = EVENT_QUERY_RULES[event.event_type](event);
  const queryKeys = event.payload.waiting_on
    ? [...base.queryKeys, workspaceQueryKey('job', event.payload.waiting_on.job_id)]
    : [...base.queryKeys];
  const seen = new Set<string>();
  return {
    ...base,
    queryKeys: queryKeys.filter((queryKey) => {
      const identity = JSON.stringify(queryKey);
      if (seen.has(identity)) return false;
      seen.add(identity);
      return true;
    }),
  };
};
export const queryKeysForEvent = (event: EventEnvelope): readonly EventQueryKey[] =>
  queryPlanForEvent(event).queryKeys;

const MUTABLE_QUERY_ROOTS = new Set([
  'overview',
  'setup-status',
  'setup-capabilities',
  'data-capabilities',
  'research',
  'experiment',
  'strategy',
  'validation',
  'holdout',
  'holdout-result',
  'approvals',
  'approval',
  'memo',
  'job',
  'agent-run',
  'tool-call',
  'system-health',
  'agents',
  'agent',
  'settings',
]);
export const isMutableEventQueryKey = (queryKey: readonly unknown[]): boolean => {
  if (queryKey[0] !== auth.scope() || !MUTABLE_QUERY_ROOTS.has(String(queryKey[1]))) return false;
  return !(queryKey[1] === 'strategy' && typeof queryKey[3] === 'number');
};

export type EventStreamState =
  | 'connected'
  | 'reconnecting'
  | 'resynchronizing'
  | 'degraded'
  | 'client-update-required'
  | 'reauthentication-required'
  | 'permission-denied';

export const isSafeHoldoutNotification = (event: EventEnvelope): boolean => {
  if (event.event_type !== 'validation.holdout.updated') return true;
  const allowed = new Set(['status', 'state', 'reason_code']);
  return Object.keys(event.payload).every((key) => allowed.has(key));
};

/** A wire frame is not trusted until both the SSE cursor and generated envelope agree. */
export type DecodedSseFrame = Readonly<{
  cursor: number;
  event: EventEnvelope;
}>;

export function decodeCanonicalSseFrame(frame: string): DecodedSseFrame | undefined {
  const lines = frame.split(/\r?\n/);
  const idLine = lines.find((line) => line.startsWith('id:'));
  const dataLine = lines.find((line) => line.startsWith('data:'));
  if (!dataLine) return undefined; // heartbeat/comment-only frame
  if (!idLine) throw new ContractError('Canonical SSE data frame is missing its sequence cursor.');
  const cursor = Number(idLine.slice(3).trim());
  if (!Number.isSafeInteger(cursor) || cursor < 1)
    throw new ContractError('Canonical SSE frame cursor is not a positive safe integer.');
  let decoded: unknown;
  try {
    decoded = JSON.parse(dataLine.slice(5).trim());
  } catch {
    throw new ContractError('Canonical SSE data is not JSON.');
  }
  const parsed = SseEnvelopeSchema.safeParse(decoded);
  if (!parsed.success)
    throw new ContractError('Actual SSE frame failed the generated closed schema.');
  const event = parsed.data as EventEnvelope;
  if (event.sequence !== cursor)
    throw new ContractError('SSE frame id does not match the generated envelope sequence.');
  return { cursor, event };
}

export function splitCanonicalSseFrames(buffer: string): {
  decoded: DecodedSseFrame[];
  remainder: string;
} {
  const frames = buffer.split(/\r?\n\r?\n/);
  const remainder = frames.pop() ?? '';
  return {
    decoded: frames
      .map((frame) => decodeCanonicalSseFrame(frame))
      .filter((frame): frame is DecodedSseFrame => frame !== undefined),
    remainder,
  };
}

export function streamEvents(
  onEvent: (event: EventEnvelope) => void,
  onResync: () => void | Promise<void>,
  onState?: (state: EventStreamState) => void,
  onProblem?: (error: ApiError) => void,
): () => void {
  let streamScope = auth.scope();
  const cursorKey = () => `qf.sse.cursor:${streamScope}`;
  let last = Number(transientStorage.get(cursorKey()) ?? '0');
  let active: AbortController | undefined;
  let stopped = false;
  let authorizationBlocked = false;
  let contractBlocked = false;
  let consecutiveContractSkews = 0;
  let attempts = 0;
  let reconnectTimer: number | undefined;
  const reconnect = () => {
    if (stopped || authorizationBlocked || contractBlocked) return;
    active?.abort();
    active = new AbortController();
    const controller = active;
    void (async () => {
      try {
        const headers: Record<string, string> = { Accept: 'text/event-stream' };
        if (last) headers['Last-Event-ID'] = String(last);
        const response = await fetch(pathFor('streamEvents'), {
          method: operationMap.streamEvents.method,
          headers: headersFor('streamEvents', { headers }),
          credentials: 'include',
          signal: controller.signal,
        });
        if (!response.ok) {
          const error = new ApiError(await readProblem(response));
          if (
            (error.problem.status === 401 && error.problem.code === 'UNAUTHENTICATED') ||
            (error.problem.status === 403 && error.problem.code === 'PERMISSION_DENIED')
          ) {
            authorizationBlocked = true;
            onProblem?.(error);
            if (error.problem.status === 401) {
              onState?.('reauthentication-required');
              auth.clear();
            } else onState?.('permission-denied');
            return;
          }
          throw error;
        }
        if (!response.body) throw new Error('event stream unavailable');
        attempts = 0;
        onState?.('connected');
        const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
        let buffer = '';
        while (!stopped && !controller.signal.aborted) {
          const part = await reader.read();
          if (part.done) break;
          buffer += part.value;
          const rawFrames = buffer.split(/\r?\n\r?\n/);
          buffer = rawFrames.pop() ?? '';
          for (const rawFrame of rawFrames) {
            let event: EventEnvelope | undefined;
            try {
              event = decodeCanonicalSseFrame(rawFrame)?.event;
            } catch {
              consecutiveContractSkews += 1;
              await onResync();
              if (consecutiveContractSkews >= 3) {
                contractBlocked = true;
                onState?.('client-update-required');
                controller.abort();
                return;
              }
              onState?.('resynchronizing');
              continue;
            }
            if (!event || !isSafeHoldoutNotification(event)) {
              consecutiveContractSkews += 1;
              await onResync();
              if (consecutiveContractSkews >= 3) {
                contractBlocked = true;
                onState?.('client-update-required');
                controller.abort();
                return;
              }
              onState?.('resynchronizing');
              continue;
            }
            consecutiveContractSkews = 0;
            if (event.sequence <= last) continue;
            const hasGap = last > 0 && event.sequence > last + 1;
            if (event.event_type === 'system.resync_required') {
              await onResync();
              last = event.sequence;
              transientStorage.set(cursorKey(), String(last));
              continue;
            }
            if (hasGap) await onResync();
            onEvent(event);
            last = event.sequence;
            transientStorage.set(cursorKey(), String(last));
          }
        }
      } catch (error) {
        if (error instanceof ApiError && !error.problem.retryable) {
          onProblem?.(error);
          onState?.('degraded');
          return;
        }
        if (!stopped && !controller.signal.aborted) {
          onState?.('degraded');
          await onResync();
        }
      }
      if (!stopped && !authorizationBlocked && !contractBlocked && !controller.signal.aborted) {
        attempts += 1;
        if (consecutiveContractSkews === 0) onState?.('reconnecting');
        reconnectTimer = window.setTimeout(
          () => {
            reconnectTimer = undefined;
            reconnect();
          },
          Math.min(1000 * 2 ** Math.min(attempts, 5), 30_000),
        );
      }
    })();
  };
  const unsubscribe = auth.subscribe(() => {
    if (reconnectTimer !== undefined) {
      window.clearTimeout(reconnectTimer);
      reconnectTimer = undefined;
    }
    active?.abort();
    streamScope = auth.scope();
    last = Number(transientStorage.get(cursorKey()) ?? '0');
    if (!auth.get()) return;
    authorizationBlocked = false;
    reconnect();
  });
  reconnect();
  return () => {
    stopped = true;
    unsubscribe();
    if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer);
    active?.abort();
  };
}

export type Operation = keyof operations;
