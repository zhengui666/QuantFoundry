import { readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { load } from 'js-yaml';
import { format, resolveConfig } from 'prettier';

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const contractPath = resolve(frontendRoot, '../docs/后端系统技术方案/contracts/openapi-v1.yaml');
const outputPath = resolve(frontendRoot, 'src/api/generated/operation-map.ts');
const document = load(await readFile(contractPath, 'utf8'));
const methods = new Set(['get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace']);
const resolveReference = (reference, expectedPrefix) => {
  if (typeof reference !== 'string' || !reference.startsWith(`${expectedPrefix}/`))
    throw new Error(`Unsupported local reference: ${String(reference)}`);
  const tokens = reference
    .slice(2)
    .split('/')
    .map((token) => token.replaceAll('~1', '/').replaceAll('~0', '~'));
  let value = document;
  for (const token of tokens) value = value?.[token];
  if (value === undefined) throw new Error(`Unresolved local reference: ${reference}`);
  return value;
};
const parameter = (entry) => {
  if (entry?.$ref) return resolveReference(entry.$ref, '#/components/parameters');
  return entry;
};
const operations = Object.entries(document.paths ?? {}).flatMap(([path, pathItem]) =>
  Object.entries(pathItem)
    .filter(([method]) => methods.has(method))
    .map(([method, operation]) => {
      if (!operation.operationId)
        throw new Error(`Operation at ${method.toUpperCase()} ${path} has no id`);
      const parametersByKey = new Map();
      for (const entry of [...(pathItem.parameters ?? []), ...(operation.parameters ?? [])]) {
        const resolved = parameter(entry);
        if (!resolved?.in || !resolved.name)
          throw new Error(`Parameter at ${method.toUpperCase()} ${path} is malformed`);
        parametersByKey.set(`${resolved.in}\0${resolved.name}`, resolved);
      }
      const parameters = [...parametersByKey.values()];
      const headers = parameters
        .filter((entry) => entry?.in === 'header')
        .map((entry) => entry.name)
        .sort();
      const query = parameters
        .filter((entry) => entry?.in === 'query')
        .map((entry) => ({
          name: entry.name,
          required: entry.required === true,
          value: entry.schema?.const,
        }));
      const security = operation.security === undefined ? document.security : operation.security;
      const authenticated =
        Array.isArray(security) &&
        security.length > 0 &&
        security.every((requirement) => Object.keys(requirement ?? {}).length > 0);
      return {
        id: operation.operationId,
        method: method.toUpperCase(),
        path,
        headers,
        query,
        authenticated,
      };
    }),
);
if (operations.length !== 66)
  throw new Error(`Expected 66 canonical operations, found ${operations.length}`);
const ids = new Set(operations.map((operation) => operation.id));
if (ids.size !== operations.length) throw new Error('Canonical operation IDs must be unique');
const quote = (value) => JSON.stringify(value);
const content = `/**\n * This file is generated from docs/后端系统技术方案/contracts/openapi-v1.yaml.\n * Do not edit directly.\n */\nimport type { operations } from '../generated';\n\nexport type CanonicalOperation = {\n  readonly method: string;\n  readonly path: string;\n  readonly headers: readonly string[];\n  readonly query: readonly { readonly name: string; readonly required: boolean; readonly value?: string | number | boolean }[];\n  readonly authenticated: boolean;\n};\n\nexport const operationMap = {\n${operations
  .map(
    (operation) =>
      `  ${quote(operation.id)}: { method: ${quote(operation.method)}, path: ${quote(operation.path)}, headers: [${operation.headers.map(quote).join(', ')}], query: ${quote(operation.query)}, authenticated: ${operation.authenticated} },`,
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
} else await writeFile(outputPath, formatted);
