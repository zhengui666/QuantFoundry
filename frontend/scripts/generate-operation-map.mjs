import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { load } from 'js-yaml';
import { format } from 'prettier';

const contractPath = resolve(process.cwd(), '../docs/后端系统技术方案/contracts/openapi-v1.yaml');
const outputPath = resolve(process.cwd(), 'src/api/generated/operation-map.ts');
const document = load(await readFile(contractPath, 'utf8'));
const methods = new Set(['get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace']);
const parameter = (entry) => {
  if (entry.$ref) {
    const name = entry.$ref.split('/').at(-1);
    return document.components?.parameters?.[name];
  }
  return entry;
};
const operations = Object.entries(document.paths ?? {}).flatMap(([path, pathItem]) =>
  Object.entries(pathItem)
    .filter(([method]) => methods.has(method))
    .map(([method, operation]) => {
      if (!operation.operationId) throw new Error(`Operation at ${method.toUpperCase()} ${path} has no id`);
      const parameters = [...(pathItem.parameters ?? []), ...(operation.parameters ?? [])].map(parameter);
      const headers = parameters
        .filter((entry) => entry?.in === 'header')
        .map((entry) => entry.name)
        .sort();
      const query = parameters
        .filter((entry) => entry?.in === 'query')
        .map((entry) => ({ name: entry.name, required: entry.required === true, value: entry.schema?.const }));
      const authenticated = operation.security === undefined ? document.security?.length > 0 : operation.security.length > 0;
      return { id: operation.operationId, method: method.toUpperCase(), path, headers, query, authenticated };
    }),
);
if (operations.length !== 45) throw new Error(`Expected 45 canonical operations, found ${operations.length}`);
const ids = new Set(operations.map((operation) => operation.id));
if (ids.size !== operations.length) throw new Error('Canonical operation IDs must be unique');
const quote = (value) => JSON.stringify(value);
const content = `/**\n * This file is generated from docs/后端系统技术方案/contracts/openapi-v1.yaml.\n * Do not edit directly.\n */\nimport type { operations } from '../generated';\n\nexport type CanonicalOperation = {\n  readonly method: string;\n  readonly path: string;\n  readonly headers: readonly string[];\n  readonly query: readonly { readonly name: string; readonly required: boolean; readonly value?: string | number | boolean }[];\n  readonly authenticated: boolean;\n};\n\nexport const operationMap = {\n${operations
  .map(
    (operation) =>
      `  ${quote(operation.id)}: { method: ${quote(operation.method)}, path: ${quote(operation.path)}, headers: [${operation.headers.map(quote).join(', ')}], query: ${quote(operation.query)}, authenticated: ${operation.authenticated} },`,
  )
  .join('\n')}\n} as const satisfies Record<keyof operations, CanonicalOperation>;\n\nexport type CanonicalOperationId = keyof typeof operationMap;\n`;
const formatted = await format(content, { parser: 'typescript', filepath: outputPath });
if (process.argv.includes('--check')) {
  const existing = await readFile(outputPath, 'utf8');
  if (existing !== formatted) throw new Error('Generated operation map is stale. Run pnpm codegen.');
} else await writeFile(outputPath, formatted);
