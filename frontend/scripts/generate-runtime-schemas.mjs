import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { load } from 'js-yaml';
import { format } from 'prettier';

const contractPath = resolve(process.cwd(), '../docs/后端系统技术方案/contracts/openapi-v1.yaml');
const outputPath = resolve(process.cwd(), 'src/api/generated/runtime-schemas.ts');
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
if (operationCount !== 66)
  throw new Error(`Expected 66 canonical operations, found ${operationCount}`);
if (Object.keys(schemas).length !== 188)
  throw new Error(`Expected 188 canonical schemas, found ${Object.keys(schemas).length}`);
if (schemas.CanonicalErrorCode?.enum?.length !== 75)
  throw new Error(
    `Expected 75 canonical errors, found ${schemas.CanonicalErrorCode?.enum?.length}`,
  );
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
const refName = (ref) => ref.split('/').at(-1);
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
      ".refine((items) => new Set(items.map((item) => JSON.stringify(item))).size === items.length, { message: 'Array items must be unique' })";
  return result;
};

const zodFor = (schema, schemaName) => {
  if (!schema) return 'z.unknown()';
  if (schema.$ref) return `${refName(schema.$ref)}Schema`;
  if (schema.allOf?.length && (!schema.properties || Object.keys(schema.properties).length === 0)) {
    const [first, ...rest] = schema.allOf.map((branch) => zodFor(branch));
    return rest.reduce((left, right) => `z.intersection(${left}, ${right})`, first);
  }
  if (schema.oneOf && !schema.properties)
    return `z.union([${schema.oneOf.map((branch) => zodFor(branch)).join(', ')}])`;
  if (schema.anyOf) return `z.union([${schema.anyOf.map((branch) => zodFor(branch)).join(', ')}])`;
  if (schema.allOf && !schema.type && !schema.properties) {
    const [first, ...rest] = schema.allOf.map((branch) => zodFor(branch));
    return rest.reduce((left, right) => `z.intersection(${left}, ${right})`, first);
  }
  if (schema.const !== undefined) return `z.literal(${quote(schema.const)})`;
  if (schema.enum) return literalUnion(schema.enum);

  const types = Array.isArray(schema.type) ? schema.type : [schema.type];
  const nullable = types.includes('null');
  const type = types.find((candidate) => candidate !== 'null');
  if (type === undefined && nullable) return 'z.null()';

  let expression;
  if (type === 'string') {
    expression =
      schema.format === 'date-time'
        ? 'z.iso.datetime()'
        : schema.format === 'date'
          ? 'z.iso.date()'
          : 'z.string()';
    if (schema.minLength !== undefined) expression += `.min(${schema.minLength})`;
    if (schema.maxLength !== undefined) expression += `.max(${schema.maxLength})`;
    if (schema.pattern) expression += `.regex(new RegExp(${quote(schema.pattern)}))`;
  } else if (type === 'integer' || type === 'number') {
    expression = type === 'integer' ? 'z.number().int()' : 'z.number()';
    if (schema.minimum !== undefined) expression += `.min(${schema.minimum})`;
    if (schema.maximum !== undefined) expression += `.max(${schema.maximum})`;
  } else if (type === 'boolean') expression = 'z.boolean()';
  else if (type === 'array')
    expression = addArrayConstraints(`z.array(${zodFor(schema.items)})`, schema);
  else if (type === 'object' || schema.properties) {
    const required = new Set(schema.required ?? []);
    const properties = Object.entries(schema.properties ?? {}).map(([name, property]) => {
      const value = zodFor(property) + (required.has(name) ? '' : '.optional()');
      return `${quote(name)}: ${value}`;
    });
    expression = `z.object({${properties.join(',')}})`;
    if (schema.additionalProperties === false) expression += '.strict()';
    else if (typeof schema.additionalProperties === 'object')
      expression += `.catchall(${zodFor(schema.additionalProperties)})`;
    else expression += '.passthrough()';
    if (schema.minProperties !== undefined)
      expression += `.refine((value) => Object.keys(value).length >= ${schema.minProperties}, { message: 'Object requires at least ${schema.minProperties} properties' })`;
  } else throw new Error(`Unsupported runtime schema: ${JSON.stringify(schema)}`);

  if (schema.oneOf?.length && schema.properties)
    expression += `.refine((value) => ${JSON.stringify(schema.oneOf.map((branch) => branch.required ?? []))}.some((required) => required.every((key) => (value as Record<string, unknown>)[key] !== undefined)), { message: 'Object must satisfy one canonical variant' })`;

  if (schemaName === 'ExperimentSearchRangeDimension')
    expression += `.superRefine((value, context) => {
      const minimum = Number(value.minimum);
      const maximum = Number(value.maximum);
      const step = Number(value.step);
      if (!(minimum < maximum)) context.addIssue({ code: 'custom', message: 'minimum must be less than maximum' });
      if (!(step > 0)) context.addIssue({ code: 'custom', message: 'step must be positive' });
      if (value.value_type === 'INTEGER' && ![minimum, maximum, step].every(Number.isInteger))
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
      if (!PublicIdSchemas[value.type].safeParse(value.id).success)
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
          const result = EventObjectLocatorSchemas[value.object_type].safeParse(value);
          if (!result.success)
            context.addIssue({ code: 'custom', message: 'Event payload object locator is invalid' });
        }
      }
    })`;
  if (schemaName === 'SseEnvelope')
    expression += `.superRefine((value, context) => {
      if (EventTypeObjectTypeMap[value.event_type] !== value.object_type)
        context.addIssue({ code: 'custom', path: ['object_type'], message: 'Event type and object type must agree' });
      if (!EventObjectLocatorSchemas[value.object_type].safeParse(value).success)
        context.addIssue({ code: 'custom', path: ['object_id'], message: 'Event object locator is invalid' });
    })`;
  return nullable ? `${expression}.nullable()` : expression;
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
    return `${quote(name)}: { ulid: ${quote(schema.examples[0])}, uuid: ${quote(schema.examples[1])} }`;
  })
  .join(',');
const anyPublicIdUnion = publicIdEntries.map(([name]) => `${pascalCase(name)}IdSchema`).join(',');
const output = await format(
  `// Generated from canonical openapi-v1.yaml. Do not edit.\nimport { z } from 'zod';\n${publicIdDeclarations}\nexport const PublicIdSchemas = {${publicIdSchemaObject}} as const;\nexport const PublicIdExamples = {${publicIdExampleObject}} as const;\nexport type PublicIdType = keyof typeof PublicIdSchemas;\nexport const AnyPublicSemanticIdSchema = z.union([${anyPublicIdUnion}]);\n${eventObjectDeclarations}\n${declarations}\n`,
  { parser: 'typescript', printWidth: 100, singleQuote: true, trailingComma: 'all' },
);

if (process.argv.includes('--check')) {
  const current = await readFile(outputPath, 'utf8').catch(() => '');
  if (current !== output) throw new Error('Generated runtime schemas drifted; run pnpm codegen');
} else {
  await writeFile(outputPath, output);
}
