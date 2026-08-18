import { readFile, rename, unlink, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { load } from 'js-yaml';
import { format, resolveConfig } from 'prettier';

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const contractPath = resolve(frontendRoot, '../docs/后端系统技术方案/contracts/openapi-v1.yaml');
const outputPath = resolve(frontendRoot, 'src/api/generated/operation-map.ts');
const document = load(await readFile(contractPath, 'utf8'));
const methods = new Set(['get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace']);
const resolveReference = (reference, expectedPrefix, seen = new Set()) => {
  if (typeof reference !== 'string' || !reference.startsWith(`${expectedPrefix}/`))
    throw new Error(`Unsupported local reference: ${String(reference)}`);
  if (seen.has(reference)) throw new Error(`Cyclic local reference: ${reference}`);
  const nextSeen = new Set(seen).add(reference);
  const tokens = reference
    .slice(2)
    .split('/')
    .map((token) => token.replaceAll('~1', '/').replaceAll('~0', '~'));
  let value = document;
  for (const token of tokens) value = value?.[token];
  if (value === undefined) throw new Error(`Unresolved local reference: ${reference}`);
  return value?.$ref && Object.keys(value).length === 1
    ? resolveReference(value.$ref, expectedPrefix, nextSeen)
    : value;
};
const parameter = (entry) => {
  if (entry?.$ref) return resolveReference(entry.$ref, '#/components/parameters');
  return entry;
};
const schema = (entry) => {
  if (entry?.$ref) {
    const resolved = resolveReference(entry.$ref, '#/components/schemas');
    const siblings = Object.fromEntries(Object.entries(entry).filter(([key]) => key !== '$ref'));
    return Object.keys(siblings).length ? { allOf: [resolved, siblings] } : resolved;
  }
  return entry;
};
const fixedConst = (entry, seen = new Set()) => {
  const resolved = schema(entry);
  if (!resolved || typeof resolved !== 'object') return undefined;
  if (seen.has(resolved))
    throw new Error('Cyclic schema composition while inferring fixed query value');
  const nextSeen = new Set(seen).add(resolved);
  if (Object.hasOwn(resolved, 'const')) {
    const value = resolved.const;
    if (
      value === null ||
      (typeof value !== 'string' && typeof value !== 'number' && typeof value !== 'boolean')
    )
      throw new Error('Fixed query parameter const must be a string, number, or boolean');
    return value;
  }
  const allOfValues = (resolved.allOf ?? [])
    .map((variant) => fixedConst(variant, nextSeen))
    .filter((value) => value !== undefined);
  if (allOfValues.length) {
    if (!allOfValues.every((value) => value === allOfValues[0]))
      throw new Error('Conflicting fixed query parameter constraints');
    return allOfValues[0];
  }
  for (const variants of [resolved.oneOf, resolved.anyOf]) {
    if (!variants) continue;
    const values = variants.map((variant) => fixedConst(variant, nextSeen));
    if (values.some((value) => value === undefined)) return undefined;
    if (values.every((value) => value === values[0])) return values[0];
    throw new Error('Ambiguous fixed query parameter schema');
  }
  return undefined;
};
const securityMetadata = (security, operationId) => {
  if (security === undefined) return false;
  if (!Array.isArray(security)) throw new Error(`Malformed security for ${operationId}`);
  const schemes = document.components?.securitySchemes ?? {};
  for (const requirement of security) {
    if (!requirement || typeof requirement !== 'object' || Array.isArray(requirement))
      throw new Error(`Malformed security requirement for ${operationId}`);
    for (const [name, scopes] of Object.entries(requirement)) {
      if (!Object.hasOwn(schemes, name) || !Array.isArray(scopes))
        throw new Error(`Unknown security scheme for ${operationId}: ${name}`);
    }
  }
  return (
    security.length > 0 && security.every((requirement) => Object.keys(requirement).length > 0)
  );
};
const parameterEntries = (entries, scope) => {
  const result = new Map();
  for (const entry of entries) {
    const resolved = parameter(entry);
    if (!resolved?.in || !resolved.name) throw new Error(`Parameter in ${scope} is malformed`);
    const key = `${resolved.in}\0${resolved.name}`;
    if (result.has(key)) throw new Error(`Duplicate parameter in ${scope}: ${key}`);
    result.set(key, resolved);
  }
  return result;
};
const operations = Object.entries(document.paths ?? {}).flatMap(([path, rawPathItem]) => {
  if (rawPathItem?.$ref && Object.keys(rawPathItem).some((key) => key !== '$ref'))
    throw new Error(`Path Item reference has siblings: ${path}`);
  const pathItem = rawPathItem?.$ref
    ? resolveReference(rawPathItem.$ref, '#/components/pathItems')
    : rawPathItem;
  return Object.entries(pathItem)
    .filter(([method]) => methods.has(method))
    .map(([method, operation]) => {
      if (!operation.operationId)
        throw new Error(`Operation at ${method.toUpperCase()} ${path} has no id`);
      const parametersByKey = parameterEntries(pathItem.parameters ?? [], `path ${path}`);
      for (const [key, resolved] of parameterEntries(
        operation.parameters ?? [],
        `${method.toUpperCase()} ${path}`,
      ))
        parametersByKey.set(key, resolved);
      const parameters = [...parametersByKey.values()];
      const headers = parameters
        .filter((entry) => entry?.in === 'header')
        .map((entry) => ({ name: entry.name, required: entry.required === true }))
        .sort((left, right) => left.name.localeCompare(right.name));
      const query = parameters
        .filter((entry) => entry?.in === 'query')
        .map((entry) => ({
          name: entry.name,
          required: entry.required === true,
          value: fixedConst(entry.schema),
        }));
      const security = operation.security === undefined ? document.security : operation.security;
      const authenticated = securityMetadata(security, operation.operationId);
      return {
        id: operation.operationId,
        method: method.toUpperCase(),
        path,
        headers,
        query,
        authenticated,
      };
    });
});
if (operations.length !== 66)
  throw new Error(`Expected 66 canonical operations, found ${operations.length}`);
const ids = new Set(operations.map((operation) => operation.id));
if (ids.size !== operations.length) throw new Error('Canonical operation IDs must be unique');
const quote = (value) => JSON.stringify(value);
const content = `/**\n * This file is generated from docs/后端系统技术方案/contracts/openapi-v1.yaml.\n * Do not edit directly.\n */\nimport type { operations } from '../generated';\n\nexport type CanonicalOperation = {\n  readonly method: string;\n  readonly path: string;\n  readonly headers: readonly { readonly name: string; readonly required: boolean }[];\n  readonly query: readonly { readonly name: string; readonly required: boolean; readonly value?: string | number | boolean }[];\n  readonly authenticated: boolean;\n};\n\nexport const operationMap = {\n${operations
  .map(
    (operation) =>
      `  ${quote(operation.id)}: { method: ${quote(operation.method)}, path: ${quote(operation.path)}, headers: ${quote(operation.headers)}, query: ${quote(operation.query)}, authenticated: ${operation.authenticated} },`,
  )
  .join(
    '\n',
  )}\n} as const satisfies Record<keyof operations, CanonicalOperation>;\n\nexport type CanonicalOperationId = keyof typeof operationMap;\n`;
const prettierConfig = await resolveConfig(outputPath);
const formatted = await format(content, {
  ...prettierConfig,
  parser: 'typescript',
  filepath: outputPath,
});
if (process.argv.includes('--check')) {
  const existing = await readFile(outputPath, 'utf8');
  if (existing !== formatted)
    throw new Error('Generated operation map is stale. Run pnpm codegen.');
} else {
  const temporaryPath = `${outputPath}.${process.pid}.${randomUUID()}.tmp`;
  try {
    await writeFile(temporaryPath, formatted);
    await rename(temporaryPath, outputPath);
  } finally {
    await unlink(temporaryPath).catch(() => undefined);
  }
}
