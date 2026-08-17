import { readFile, rename, unlink, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { load } from 'js-yaml';
import { format } from 'prettier';

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const contractPath = resolve(frontendRoot, '../docs/后端系统技术方案/contracts/openapi-v1.yaml');
const outputPath = resolve(frontendRoot, 'src/api/generated/runtime-schemas.ts');
const document = load(await readFile(contractPath, 'utf8'));
const schemas = document?.components?.schemas;
if (!schemas) throw new Error('Canonical OpenAPI component schemas were not found');
const publicIdSchemas = document?.info?.['x-quantfoundry-public-id-schemas'];
const publicIdPolicy = document?.info?.['x-quantfoundry-public-id-policy'];
if (!publicIdSchemas || !publicIdPolicy)
  throw new Error('Canonical public-ID schemas/policy were not found');
const publicIdEntries = Object.entries(publicIdSchemas).filter(
  ([name]) => name !== 'any_public_semantic_id',
);
if (publicIdEntries.length !== 34)
  throw new Error(`Expected 34 concrete public-ID schemas, found ${publicIdEntries.length}`);

const operationCount = Object.values(document.paths ?? {}).reduce(
  (count, path) =>
    count +
    Object.keys(path).filter((method) =>
      ['get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace'].includes(method),
    ).length,
  0,
);
if (operationCount !== document.info?.['x-quantfoundry-operation-count'])
  throw new Error(`Canonical operation metadata does not match paths: ${operationCount}`);
if (Object.keys(schemas).length !== document.info?.['x-quantfoundry-schema-count'])
  throw new Error(
    `Canonical schema metadata does not match components: ${Object.keys(schemas).length}`,
  );
const canonicalErrorCount = schemas.CanonicalErrorCode?.enum?.length;
if (canonicalErrorCount !== 75)
  throw new Error(`Expected 75 canonical errors, found ${canonicalErrorCount}`);
if (canonicalErrorCount !== document.info?.['x-quantfoundry-error-count'])
  throw new Error('Canonical error metadata does not match CanonicalErrorCode');
for (const name of ['EventPayload', 'EventWaitingOn', 'SseEnvelope'])
  if (schemas[name]?.additionalProperties !== false)
    throw new Error(`${name} must remain a closed schema`);
if (schemas.EventType?.enum?.length !== 35)
  throw new Error(`Expected 35 canonical event types, found ${schemas.EventType?.enum?.length}`);
if (schemas.EventType.enum.some((eventType) => eventType !== eventType.toLowerCase()))
  throw new Error('Canonical event types must remain exact lowercase values');
const eventObjectPairRules = document?.info?.['x-quantfoundry-event-object-pair-rules'];
const eventObjectTypes = document?.info?.['x-quantfoundry-event-object-type']?.enum;
if (!Array.isArray(eventObjectPairRules) || !Array.isArray(eventObjectTypes))
  throw new Error('Canonical event object-pair rules were not found');
const objectLocatorRules = eventObjectPairRules.filter(
  (branch) => branch?.if?.properties?.object_type?.const !== undefined,
);
const eventLocatorRules = eventObjectPairRules.filter(
  (branch) =>
    branch?.if?.properties?.event_type?.const !== undefined ||
    branch?.if?.properties?.event_type?.enum !== undefined,
);
if (
  objectLocatorRules.length !== eventObjectTypes.length ||
  JSON.stringify(
    objectLocatorRules.map((branch) => branch.if.properties.object_type.const).sort(),
  ) !== JSON.stringify([...eventObjectTypes].sort())
)
  throw new Error('Canonical event object locator rules are not exhaustive');
const eventTypeObjectTypeEntries = eventLocatorRules.flatMap((branch) => {
  const condition = branch.if.properties.event_type;
  const eventTypes = condition.enum ?? [condition.const];
  const objectType = branch.then?.properties?.object_type?.const;
  if (!objectType) throw new Error('Malformed canonical event/object-type rule');
  return eventTypes.map((eventType) => [eventType, objectType]);
});
if (
  eventTypeObjectTypeEntries.length !== schemas.EventType.enum.length ||
  JSON.stringify(eventTypeObjectTypeEntries.map(([eventType]) => eventType).sort()) !==
    JSON.stringify([...schemas.EventType.enum].sort())
)
  throw new Error('Canonical event/object-type rules are not exhaustive');
const objectRefTypes = schemas.ObjectRef?.properties?.type?.enum ?? [];
const objectRefConditionalTypes = (schemas.ObjectRef?.allOf ?? []).map(
  (branch) => branch?.if?.properties?.type?.const,
);
const publicIdTypeNames = publicIdEntries.map(([name]) => name);
if (
  objectRefTypes.length !== 34 ||
  objectRefConditionalTypes.length !== 34 ||
  JSON.stringify([...objectRefTypes].sort()) !== JSON.stringify([...publicIdTypeNames].sort()) ||
  JSON.stringify([...objectRefConditionalTypes].sort()) !==
    JSON.stringify([...publicIdTypeNames].sort())
)
  throw new Error('ObjectRef type/conditional mapping drifted from the 34 public-ID schemas');

const quote = (value) => JSON.stringify(value);
const refName = (ref) => {
  if (typeof ref !== 'string' || !ref.startsWith('#/components/schemas/'))
    throw new Error(`Unsupported runtime schema reference: ${String(ref)}`);
  const tokens = ref
    .slice(2)
    .split('/')
    .map((token) => token.replaceAll('~1', '/').replaceAll('~0', '~'));
  const name = tokens.at(-1);
  if (!name || schemas[name] === undefined)
    throw new Error(`Unresolved runtime schema reference: ${String(ref)}`);
  return name;
};
const pascalCase = (value) =>
  value
    .split('_')
    .map((part) => `${part[0].toUpperCase()}${part.slice(1)}`)
    .join('');
const literalUnion = (values) => {
  const literals = values.map((value) => `z.literal(${quote(value)})`);
  return literals.length === 1 ? literals[0] : `z.union([${literals.join(', ')}])`;
};

const addArrayConstraints = (expression, schema) => {
  let result = expression;
  if (schema.minItems !== undefined) result += `.min(${schema.minItems})`;
  if (schema.maxItems !== undefined) result += `.max(${schema.maxItems})`;
  if (schema.uniqueItems)
    result +=
      ".refine((items) => new Set(items.map(canonicalJson)).size === items.length, { message: 'Array items must be unique' })";
  return result;
};

const zodFor = (schema, schemaName) => {
  if (!schema) return 'z.unknown()';
  if (schema.$ref) {
    const reference = refName(schema.$ref);
    const siblings = { ...schema };
    delete siblings.$ref;
    if (Object.keys(siblings).length === 0) return `${reference}Schema`;
    return zodFor({ allOf: [{ $ref: schema.$ref }, siblings] }, schemaName);
  }
  const {
    allOf = [],
    anyOf = [],
    oneOf = [],
    if: condition,
    then: thenSchema,
    else: elseSchema,
    not: notSchema,
    ...baseSchema
  } = schema;
  const supportedKeywords = new Set([
    'additionalProperties',
    'const',
    'default',
    'dependentRequired',
    'description',
    'deprecated',
    'discriminator',
    'enum',
    'examples',
    'format',
    'items',
    'maxItems',
    'maxLength',
    'maximum',
    'minItems',
    'minLength',
    'minProperties',
    'minimum',
    'pattern',
    'properties',
    'readOnly',
    'required',
    'title',
    'type',
    'uniqueItems',
    'writeOnly',
  ]);
  const unsupportedKeywords = Object.keys(baseSchema).filter(
    (keyword) => !supportedKeywords.has(keyword),
  );
  if (unsupportedKeywords.length)
    throw new Error(`Unsupported constrained schema keywords: ${unsupportedKeywords.join(', ')}`);
  if (
    baseSchema.format !== undefined &&
    !new Set(['date-time', 'date', 'uri', 'int64']).has(baseSchema.format)
  )
    throw new Error(`Unsupported schema format: ${String(baseSchema.format)}`);
  let expression;
  const types = Array.isArray(baseSchema.type) ? baseSchema.type : [baseSchema.type];
  const type = types.find((candidate) => candidate !== 'null');
  const objectLike =
    type === 'object' ||
    baseSchema.properties ||
    baseSchema.required ||
    baseSchema.additionalProperties !== undefined;
  const scalarLiteral = !objectLike && (baseSchema.const !== undefined || baseSchema.enum);
  if (scalarLiteral)
    expression =
      baseSchema.const !== undefined
        ? `z.literal(${quote(baseSchema.const)})`
        : literalUnion(baseSchema.enum);

  const nullable = types.includes('null');
  if (!expression && types.length > 1) {
    const branches = types.flatMap((candidate) => {
      if (candidate === 'null') {
        if (baseSchema.const !== undefined && baseSchema.const !== null) return [];
        if (Array.isArray(baseSchema.enum) && !baseSchema.enum.includes(null)) return [];
        return ['z.null()'];
      }
      return [zodFor({ ...baseSchema, type: candidate }, schemaName)];
    });
    if (!branches.length) throw new Error('Schema type union has no valid branches');
    expression = branches.length === 1 ? branches[0] : `z.union([${branches.join(', ')}])`;
  } else if (!expression && (type === 'null' || (type === undefined && nullable))) {
    expression = 'z.null()';
  }

  if (!expression && type === 'string') {
    expression =
      baseSchema.format === 'date-time'
        ? 'z.iso.datetime({ offset: true })'
        : baseSchema.format === 'date'
          ? 'z.iso.date()'
          : baseSchema.format === 'uri'
            ? 'z.url()'
            : 'z.string()';
    if (baseSchema.minLength !== undefined) expression += `.min(${baseSchema.minLength})`;
    if (baseSchema.maxLength !== undefined) expression += `.max(${baseSchema.maxLength})`;
    if (baseSchema.pattern) expression += `.regex(new RegExp(${quote(baseSchema.pattern)}))`;
  } else if (!expression && (type === 'integer' || type === 'number')) {
    expression = type === 'integer' ? 'z.number().int()' : 'z.number()';
    if (baseSchema.minimum !== undefined) expression += `.min(${baseSchema.minimum})`;
    if (baseSchema.maximum !== undefined) expression += `.max(${baseSchema.maximum})`;
    if (baseSchema.format === 'int64')
      expression +=
        ".refine(Number.isSafeInteger, { message: 'Integer must be exactly representable in JavaScript' })";
  } else if (!expression && type === 'boolean') expression = 'z.boolean()';
  else if (!expression && type === 'array')
    expression = addArrayConstraints(`z.array(${zodFor(baseSchema.items)})`, baseSchema);
  else if (
    !expression &&
    objectLike &&
    allOf.length === 1 &&
    allOf[0]?.$ref &&
    Object.keys(baseSchema.properties ?? {}).length === 0 &&
    !baseSchema.required?.length
  )
    expression = `${refName(allOf[0].$ref)}Schema`;
  else if (!expression && objectLike) {
    const required = new Set(baseSchema.required ?? []);
    const compositionBranches = [...allOf, ...anyOf, ...oneOf];
    const propertyNames = new Set([
      ...Object.keys(baseSchema.properties ?? {}),
      ...required,
      ...compositionBranches.flatMap((branch) => Object.keys(branch?.properties ?? {})),
    ]);
    const properties = [...propertyNames].map((name) => {
      const propertySchema =
        schemaName === 'ObjectRef' && name === 'id' ? {} : (baseSchema.properties?.[name] ?? {});
      const value = zodFor(propertySchema) + (required.has(name) ? '' : '.optional()');
      return `${quote(name)}: ${value}`;
    });
    expression = `z.object({${properties.join(',')}})`;
    if (baseSchema.additionalProperties === false) expression += '.strict()';
    else if (typeof baseSchema.additionalProperties === 'object')
      expression += `.catchall(${zodFor(baseSchema.additionalProperties)})`;
    else expression += '.passthrough()';
    for (const name of required) {
      expression += `.refine((value) => Object.hasOwn(value, ${quote(name)}), { path: [${quote(name)}], message: 'Required property is missing' })`;
    }
    if (baseSchema.minProperties !== undefined)
      expression += `.refine((value) => Object.keys(value).length >= ${baseSchema.minProperties}, { message: 'Object requires at least ${baseSchema.minProperties} properties' })`;
  } else if (!expression) expression = 'z.unknown()';

  if (!scalarLiteral && baseSchema.const !== undefined)
    expression += `.and(z.literal(${quote(baseSchema.const)}))`;
  else if (!scalarLiteral && baseSchema.enum)
    expression += `.and(${literalUnion(baseSchema.enum)})`;

  const addBranchIssues = (condition) =>
    `.superRefine((value, context) => { ${condition} for (const issue of result.error.issues) context.addIssue({ code: 'custom', path: issue.path as (string | number)[], message: issue.message }); } } })`;
  if (allOf.length && schemaName !== 'ObjectRef') {
    const branches = allOf.map((branch) => zodFor(branch));
    expression += addBranchIssues(
      `for (const result of [${branches.map((branch) => `${branch}.safeParse(value)`).join(', ')}]) { if (!result.success) {`,
    );
  }
  if (anyOf.length) {
    const branches = anyOf.map((branch) => zodFor(branch));
    expression += `.superRefine((value, context) => { const matches = [${branches
      .map((branch) => `${branch}.safeParse(value).success`)
      .join(
        ', ',
      )}].filter(Boolean).length; if (matches === 0) context.addIssue({ code: 'custom', message: 'Value must match at least one canonical variant' }); })`;
  }
  if (oneOf.length && schemaName !== 'ObjectRef') {
    const branches = oneOf.map((branch) => zodFor(branch));
    expression += `.superRefine((value, context) => { const matches = [${branches
      .map((branch) => `${branch}.safeParse(value).success`)
      .join(
        ', ',
      )}].filter(Boolean).length; if (matches !== 1) context.addIssue({ code: 'custom', message: 'Value must match exactly one canonical variant' }); })`;
  }
  if (baseSchema.dependentRequired) {
    for (const [trigger, dependencies] of Object.entries(baseSchema.dependentRequired)) {
      expression += `.superRefine((value, context) => { if (Object.hasOwn(value, ${quote(trigger)})) for (const key of ${quote(dependencies)} as string[]) if (!Object.hasOwn(value, key)) context.addIssue({ code: 'custom', path: [key], message: 'Dependent property is required' }); })`;
    }
  }
  if (condition) {
    const conditionExpression = zodFor(condition);
    const thenExpression = thenSchema ? zodFor(thenSchema) : null;
    const elseExpression = elseSchema ? zodFor(elseSchema) : null;
    expression += `.superRefine((value, context) => { const conditional = ${conditionExpression}.safeParse(value).success; const result = (conditional ? ${thenExpression ?? 'z.unknown()'} : ${elseExpression ?? 'z.unknown()'}).safeParse(value); if (!result.success) for (const issue of result.error.issues) context.addIssue({ code: 'custom', path: issue.path as (string | number)[], message: issue.message }); })`;
  }
  if (notSchema) {
    const notExpression = zodFor(notSchema);
    expression += `.refine((value) => !${notExpression}.safeParse(value).success, { message: 'Value must not match the excluded schema' })`;
  }

  if (schemaName === 'ExperimentSearchRangeDimension')
    expression += `.superRefine((value, context) => {
      if (compareCanonicalDecimal(value.minimum, value.maximum) >= 0)
        context.addIssue({ code: 'custom', message: 'minimum must be less than maximum' });
      if (compareCanonicalDecimal(value.step, '0') <= 0)
        context.addIssue({ code: 'custom', message: 'step must be positive' });
      if (value.value_type === 'INTEGER' && ![value.minimum, value.maximum, value.step].every(isCanonicalInteger))
        context.addIssue({ code: 'custom', message: 'INTEGER ranges require integral bounds and step' });
    })`;
  if (schemaName === 'SetupStatus')
    expression += `.superRefine((value, context) => {
      const coupled = [
        ['ai_provider_configured', 'ai_connection_id'],
        ['research_policy_active', 'research_policy_id'],
        ['risk_policy_active', 'risk_policy_id'],
        ['cost_model_active', 'cost_model_id'],
      ] as const;
      for (const [activeKey, referenceKey] of coupled) {
        const active = value[activeKey];
        const reference = value[referenceKey];
        if ((active && !reference) || (!active && reference !== null))
          context.addIssue({ code: 'custom', path: [referenceKey], message: 'readiness and reference must agree' });
      }
      const expectedFallback = !value.ai_provider_configured
        ? 'AI_PROVIDER'
        : !value.cost_model_active
          ? 'RESEARCH_DEFAULTS'
          : !value.research_policy_active || !value.risk_policy_active
            ? 'RESEARCH_CONSTITUTION'
            : null;
      if (value.fallback_step !== expectedFallback)
        context.addIssue({ code: 'custom', path: ['fallback_step'], message: 'fallback precedence mismatch' });
      if (
        value.completed &&
        (!value.owner_session_ready ||
          !value.ai_provider_configured ||
          !value.ai_connection_id ||
          !value.research_policy_active ||
          !value.research_policy_id ||
          !value.risk_policy_active ||
          !value.risk_policy_id ||
          !value.cost_model_active ||
          !value.cost_model_id ||
          value.fallback_step !== null)
      )
        context.addIssue({ code: 'custom', path: ['completed'], message: 'completed readiness contradiction' });
    })`;
  if (schemaName === 'ObjectRef')
    expression += `.superRefine((value, context) => {
      const schema = PublicIdSchemas[value.type as keyof typeof PublicIdSchemas];
      if (schema && !schema.safeParse(value.id).success)
        context.addIssue({ code: 'custom', path: ['id'], message: 'ObjectRef type and ID prefix must agree' });
    })`;
  if (schemaName === 'EventPayload')
    expression += `.superRefine((value, context) => {
      const locatorKeys = ['object_type', 'object_id', 'object_version', 'object_revision'] as const;
      const present = locatorKeys.filter((key) => value[key] !== undefined);
      if (present.length > 0 && present.length !== locatorKeys.length)
        context.addIssue({ code: 'custom', message: 'Event payload locator fields are dependent' });
      if (present.length === locatorKeys.length) {
        if (value.object_type === null) {
          if (value.object_id !== null || value.object_version !== null || value.object_revision !== null)
            context.addIssue({ code: 'custom', message: 'Null event payload locator must be wholly null' });
        } else if (value.object_type !== undefined) {
        const result = EventObjectLocatorSchemas[value.object_type as keyof typeof EventObjectLocatorSchemas].safeParse(value);
          if (!result.success)
            context.addIssue({ code: 'custom', message: 'Event payload object locator is invalid' });
        }
      }
    })`;
  if (schemaName === 'SseEnvelope')
    expression += `.superRefine((value, context) => {
      if (EventTypeObjectTypeMap[value.event_type] !== value.object_type)
        context.addIssue({ code: 'custom', path: ['object_type'], message: 'Event type and object type must agree' });
      if (!EventObjectLocatorSchemas[value.object_type as keyof typeof EventObjectLocatorSchemas].safeParse(value).success)
        context.addIssue({ code: 'custom', path: ['object_id'], message: 'Event object locator is invalid' });
    })`;
  return types.length === 1 && nullable ? `${expression}.nullable()` : expression;
};

const canonicalUuidV4 = '550e8400-e29b-41d4-a716-446655440000';
const exampleForSchema = (schema) => {
  if (schema.const !== undefined) return schema.const;
  if (schema.examples?.length) return schema.examples[0];
  if (schema.enum?.length) return schema.enum[0];
  if (schema.oneOf) {
    for (const branch of schema.oneOf) {
      const example = exampleForSchema(branch);
      if (example !== undefined) return example;
    }
  }
  if (schema.pattern && new RegExp(schema.pattern).test(canonicalUuidV4)) return canonicalUuidV4;
  return undefined;
};
const eventTypeObjectTypeObject = eventTypeObjectTypeEntries
  .map(([eventType, objectType]) => `${quote(eventType)}: ${quote(objectType)}`)
  .join(',');
const eventObjectLocatorSchemaObject = objectLocatorRules
  .map((branch) => {
    const objectType = branch.if.properties.object_type.const;
    const properties = branch.then?.properties ?? {};
    if (!properties.object_id) throw new Error(`Missing object_id locator rule for ${objectType}`);
    return `${quote(objectType)}: z.object({
      object_id: ${zodFor(properties.object_id)},
      object_version: ${zodFor(properties.object_version ?? { type: ['integer', 'null'], minimum: 1 })},
      object_revision: ${zodFor(properties.object_revision ?? { type: ['integer', 'null'], minimum: 1 })},
    }).passthrough()`;
  })
  .join(',');
const eventObjectExampleObject = objectLocatorRules
  .map((branch) => {
    const objectType = branch.if.properties.object_type.const;
    const properties = branch.then?.properties ?? {};
    const objectId = exampleForSchema(properties.object_id);
    if (objectId === undefined)
      throw new Error(`Missing canonical event object example for ${objectType}`);
    const objectVersion = properties.object_version?.type === 'null' ? null : 1;
    const objectRevision = properties.object_revision?.type === 'null' ? null : 1;
    return `${quote(objectType)}: { object_id: ${quote(objectId)}, object_version: ${quote(objectVersion)}, object_revision: ${quote(objectRevision)} }`;
  })
  .join(',');
const eventObjectDeclarations = `
export const EventTypeObjectTypeMap = {${eventTypeObjectTypeObject}} as const;
export const EventObjectLocatorSchemas = {${eventObjectLocatorSchemaObject}} as const;
export const EventObjectExamples = {${eventObjectExampleObject}} as const;
`;

const roots = [
  'CanonicalErrorCode',
  'ApiProblem',
  'GeneralAccessKeyLoginRequest',
  'GeneralAccessKeyList',
  'GeneralAccessKeyCreateRequest',
  'GeneralAccessKeyIssued',
  'OwnerSessionView',
  'SessionBootstrapResponse',
  'ConfigurationCatalog',
  'ConfigurationCandidateRequest',
  'ConfigurationCandidate',
  'ConfigurationValidationResult',
  'ConfigurationActivateRequest',
  'ConfigurationRollbackRequest',
  'DatabaseConnectionStatus',
  'DatabaseConnectionCandidateRequest',
  'DatabaseConnectionValidationResult',
  'SetupStatus',
  'SetupCapabilityCatalog',
  'LiveConnectorValidationRequest',
  'LiveConnectorValidationResult',
  'SetupProviderConnectionValidationRequest',
  'SetupProviderConnectionValidationResult',
  'SetupCompleteRequest',
  'SettingsDetail',
  'OverviewReadModel',
  'DataCapabilityList',
  'ResearchPage',
  'ResearchCreateRequest',
  'ResearchStartRequest',
  'ResearchDetail',
  'ExperimentCreateRequest',
  'ExperimentReproduceExactRequest',
  'ExperimentReproduceControlledOverrideRequest',
  'ExperimentReproduceRequest',
  'ExperimentDetail',
  'StrategyCreateRequest',
  'FreezeStrategyRequest',
  'BacktestRequest',
  'StrategyVersionDetail',
  'ExperimentReproduceAccepted',
  'ValidationCreateRequest',
  'ValidationDetail',
  'HoldoutGate',
  'HoldoutResult',
  'HoldoutApprovalRequest',
  'HoldoutRunRequest',
  'ApprovalPage',
  'ApprovalDetail',
  'ApprovalDecisionRequest',
  'ApprovalRejectRequest',
  'ApprovalDecisionResult',
  'MemoGenerateRequest',
  'MemoDetail',
  'AgentConfigList',
  'AgentConfig',
  'AgentConfigUpdate',
  'JobAccepted',
  'JobDetail',
  'ObjectRef',
  'VersionRef',
  'EventType',
  'EventWaitingOn',
  'EventPayload',
  'SseEnvelope',
];
const dependencies = (schema) => {
  const found = new Set();
  const visit = (value) => {
    if (!value || typeof value !== 'object') return;
    if (typeof value.$ref === 'string') found.add(refName(value.$ref));
    for (const nested of Object.values(value)) visit(nested);
  };
  visit(schema);
  return [...found];
};
const ordered = [];
const visited = new Set();
const visiting = new Set();
const include = (name) => {
  if (visited.has(name)) return;
  if (!schemas[name]) throw new Error(`Missing referenced canonical schema ${name}`);
  if (visiting.has(name)) throw new Error(`Cyclic runtime schema dependency at ${name}`);
  visiting.add(name);
  for (const dependency of dependencies(schemas[name])) include(dependency);
  visiting.delete(name);
  visited.add(name);
  ordered.push(name);
};
for (const root of roots) include(root);

const declarations = ordered
  .map((name) => `export const ${name}Schema = ${zodFor(schemas[name], name)};`)
  .join('\n');
const publicIdDeclarations = publicIdEntries
  .map(
    ([name, schema]) =>
      `export const ${pascalCase(name)}IdSchema = ${zodFor(schema, `${pascalCase(name)}Id`)};`,
  )
  .join('\n');
const publicIdSchemaObject = publicIdEntries
  .map(([name]) => `${quote(name)}: ${pascalCase(name)}IdSchema`)
  .join(',');
const publicIdExampleObject = publicIdEntries
  .map(([name, schema]) => {
    if (schema.examples?.length !== 2)
      throw new Error(`${name} must publish exactly one ULID and one UUIDv4 example`);
    const branches = schema.oneOf ?? [];
    const uuidPattern = /[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
    const classified = schema.examples.map((example) => {
      const matches = branches
        .map((branch) => new RegExp(branch.pattern).test(example))
        .map((matched, index) => (matched ? index : -1))
        .filter((index) => index >= 0);
      if (matches.length !== 1) throw new Error(`${name} example does not map to one branch`);
      return { example, branch: matches[0], kind: uuidPattern.test(example) ? 'uuid' : 'ulid' };
    });
    if (
      classified.filter((entry) => entry.kind === 'ulid').length !== 1 ||
      classified.filter((entry) => entry.kind === 'uuid').length !== 1 ||
      classified[0].branch === classified[1].branch
    )
      throw new Error(`${name} examples do not map one-to-one to canonical ID branches`);
    const ulid = classified.find((entry) => entry.kind === 'ulid').example;
    const uuid = classified.find((entry) => entry.kind === 'uuid').example;
    return `${quote(name)}: { ulid: ${quote(ulid)}, uuid: ${quote(uuid)} }`;
  })
  .join(',');
const anyPublicIdUnion = publicIdEntries.map(([name]) => `${pascalCase(name)}IdSchema`).join(',');
const output = (
  await format(
    `// Generated from canonical openapi-v1.yaml. Do not edit.\nimport { z } from 'zod';\n\nconst normalizeCanonicalDecimal = (value: string) => {\n  const [integer, fraction = ''] = value.split('.');\n  const negative = integer.startsWith('-');\n  const digits = (negative ? integer.slice(1) : integer).replace(/^0+(?=\\d)/, '');\n  const trimmedFraction = fraction.replace(/0+$/, '');\n  return {\n    negative: (negative && (digits !== '0' || trimmedFraction !== '')),\n    integer: digits,\n    fraction: trimmedFraction,\n  };\n};\nconst compareCanonicalDecimal = (left: string, right: string) => {\n  const a = normalizeCanonicalDecimal(left);\n  const b = normalizeCanonicalDecimal(right);\n  if (a.negative !== b.negative) return a.negative ? -1 : 1;\n  const sign = a.negative ? -1 : 1;\n  if (a.integer.length !== b.integer.length) return (a.integer.length - b.integer.length) * sign;\n  if (a.integer !== b.integer) return (a.integer < b.integer ? -1 : 1) * sign;\n  const width = Math.max(a.fraction.length, b.fraction.length);\n  const af = a.fraction.padEnd(width, '0');\n  const bf = b.fraction.padEnd(width, '0');\n  return (af === bf ? 0 : af < bf ? -1 : 1) * sign;\n};\nconst isCanonicalInteger = (value: string) => !normalizeCanonicalDecimal(value).fraction;\n${publicIdDeclarations}\nexport const PublicIdSchemas = {${publicIdSchemaObject}} as const;\nexport const PublicIdExamples = {${publicIdExampleObject}} as const;\nexport type PublicIdType = keyof typeof PublicIdSchemas;\nexport const AnyPublicSemanticIdSchema = z.union([${anyPublicIdUnion}]);\n${eventObjectDeclarations}\n${declarations}\n`,
    { parser: 'typescript', printWidth: 100, singleQuote: true, trailingComma: 'all' },
  )
)
  .replace(
    "import { z } from 'zod';\n\n",
    "import { z } from 'zod';\n\nconst canonicalJson = (value: unknown): string => {\n  if (Array.isArray(value)) return '[' + value.map(canonicalJson).join(',') + ']';\n  if (value && typeof value === 'object') {\n    const object = value as Record<string, unknown>;\n    return '{' + Object.keys(object).sort().map((key) => JSON.stringify(key) + ':' + canonicalJson(object[key])).join(',') + '}';\n  }\n  return JSON.stringify(value);\n};\n\n",
  )
  .replace(
    "const [integer, fraction = ''] = value.split('.');",
    "const [integer = '', fraction = ''] = value.split('.');",
  );

if (process.argv.includes('--check')) {
  const current = await readFile(outputPath, 'utf8').catch(() => '');
  if (current !== output) throw new Error('Generated runtime schemas drifted; run pnpm codegen');
} else {
  const temporaryPath = `${outputPath}.${process.pid}.tmp`;
  try {
    await writeFile(temporaryPath, output);
    await rename(temporaryPath, outputPath);
  } finally {
    await unlink(temporaryPath).catch(() => undefined);
  }
}
