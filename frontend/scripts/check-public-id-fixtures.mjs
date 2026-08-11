import { readFile, readdir, stat } from 'node:fs/promises';
import { extname, relative, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { load } from 'js-yaml';

const ignoredDirectories = new Set([
  '.git',
  '.mypy_cache',
  '.pytest_cache',
  '.ruff_cache',
  '.venv',
  '__pycache__',
  'node_modules',
  'dist',
  'storybook-static',
  'test-results',
]);
const sourceExtensions = new Set([
  '',
  '.css',
  '.html',
  '.ini',
  '.js',
  '.json',
  '.md',
  '.mjs',
  '.py',
  '.sh',
  '.sql',
  '.toml',
  '.ts',
  '.tsx',
  '.yaml',
  '.yml',
]);

export const formalPublicIdSources = [
  { path: 'PROJECT_BACKGROUND.md', kind: 'file' },
  { path: 'AGENTS.md', kind: 'file' },
  { path: 'backend', kind: 'directory' },
  {
    path: 'docs/后端系统技术方案/QuantFoundry_Backend_System_Technical_Design_V1.0.0.md',
    kind: 'file',
  },
  {
    path: 'docs/Agent技术方案/QuantFoundry_Agent_Technical_Design_V1.0.0.md',
    kind: 'file',
  },
  { path: 'docs/PRD/V1.0.0', kind: 'file' },
  { path: 'docs/UI设计方案/QuantFoundry_UI_Design_V1.0.0.md', kind: 'file' },
  {
    path: 'docs/前端技术方案/QuantFoundry_Frontend_Technical_Design_V1.0.0.md',
    kind: 'file',
  },
  {
    path: 'docs/全栈测试方案/QuantFoundry_Full_Stack_Test_Plan_V1.0.0.md',
    kind: 'file',
  },
  { path: 'docs/后端系统技术方案/contracts/openapi-v1.yaml', kind: 'file' },
  { path: 'docs/后端系统技术方案/contracts/tools', kind: 'directory' },
  { path: 'frontend', kind: 'directory' },
];
const collect = async (path) => {
  const entries = await readdir(path, { withFileTypes: true }).catch(() => null);
  if (!entries) return [path];
  const nested = await Promise.all(
    entries
      .filter((entry) => !ignoredDirectories.has(entry.name))
      .map((entry) => collect(resolve(path, entry.name))),
  );
  return nested.flat();
};

export const collectFormalPublicIdFiles = async (
  repositoryRoot,
  sources = formalPublicIdSources,
) => {
  const files = new Set();
  const coverage = new Map();

  for (const source of sources) {
    const absolutePath = resolve(repositoryRoot, source.path);
    const metadata = await stat(absolutePath).catch(() => null);
    if (!metadata) throw new Error(`Formal public-ID source is missing: ${source.path}`);
    if (source.kind === 'file' && !metadata.isFile())
      throw new Error(`Formal public-ID source is not a file: ${source.path}`);
    if (source.kind === 'directory' && !metadata.isDirectory())
      throw new Error(`Formal public-ID source is not a directory: ${source.path}`);

    const candidates = source.kind === 'file' ? [absolutePath] : await collect(absolutePath);
    const scanned = candidates.filter(
      (file) => source.kind === 'file' || sourceExtensions.has(extname(file).toLowerCase()),
    );
    if (!scanned.length) throw new Error(`Formal public-ID source was not scanned: ${source.path}`);
    scanned.forEach((file) => files.add(file));
    coverage.set(source.path, scanned.length);
  }

  return { files: [...files].sort(), coverage };
};

const tokenPattern = /\b(?:[A-Z][A-Z0-9]{1,7})-[A-Za-z0-9][A-Za-z0-9-]*\b/g;
const intentionalRejection =
  /reject_fixture|must reject|reject|invalid|illegal|wrong|legacy|禁止|非法|错误|不合法|必须拒绝|短\s*ID|旧(?:格式|前缀|日期|序号)/i;

const schemaOrManifestJson = (file) =>
  /(?:^|[/\\])schemas?(?:[/\\]|$)/i.test(file) || /(?:manifest|schema)[^/\\]*\.json$/i.test(file);
const jsonProseKeys = new Set(['constraint', 'constraints', 'description', 'descriptions']);

const invalidTokens = (text, context, location, matchers) => {
  const failures = [];
  for (const match of text.matchAll(tokenPattern)) {
    const token = match[0];
    const prefix = token.split('-')[0];
    const canonical = matchers.get(prefix);
    const recognized = canonical !== undefined || prefix === 'MEM';
    if (!recognized || canonical?.some((matcher) => matcher.test(token))) continue;
    if (!intentionalRejection.test(context))
      failures.push(`${location}: unmarked invalid public-ID fixture ${token}`);
  }
  return failures;
};

const scanLines = (file, content, matchers) => {
  const failures = [];
  const lines = content.split(/\r?\n/);
  for (const [index, line] of lines.entries()) {
    const context = lines.slice(Math.max(0, index - 1), index + 2).join(' ');
    failures.push(...invalidTokens(line, context, `${file}:${index + 1}`, matchers));
  }
  return failures;
};

const scanJson = (file, content, matchers) => {
  let value;
  try {
    value = JSON.parse(content);
  } catch {
    return scanLines(file, content, matchers);
  }

  const failures = [];
  const skipProse = schemaOrManifestJson(file);
  const visit = (node, path, parentContext) => {
    if (typeof node === 'string') {
      failures.push(...invalidTokens(node, parentContext, `${file}:${path}`, matchers));
      return;
    }
    if (Array.isArray(node)) {
      node.forEach((entry, index) => visit(entry, `${path}[${index}]`, JSON.stringify(node)));
      return;
    }
    if (!node || typeof node !== 'object') return;
    const context = JSON.stringify(node);
    for (const [key, entry] of Object.entries(node)) {
      if (skipProse && jsonProseKeys.has(key.toLowerCase())) continue;
      visit(entry, `${path}.${key}`, context);
    }
  };
  visit(value, '$', content);
  return failures;
};

export const findInvalidPublicIdFixtures = (file, content, matchers) =>
  extname(file).toLowerCase() === '.json'
    ? scanJson(file, content, matchers)
    : scanLines(file, content, matchers);

export const scanFormalPublicIdSources = async ({ repositoryRoot, matchers, sources }) => {
  const { files, coverage } = await collectFormalPublicIdFiles(repositoryRoot, sources);
  const failures = [];
  for (const file of files) {
    const label = relative(repositoryRoot, file) || file;
    failures.push(...findInvalidPublicIdFixtures(label, await readFile(file, 'utf8'), matchers));
  }
  return { failures, scannedFiles: files, coverage };
};

const main = async () => {
  const repositoryRoot = resolve(process.cwd(), '..');
  const contractPath = resolve(repositoryRoot, 'docs/后端系统技术方案/contracts/openapi-v1.yaml');
  const document = load(await readFile(contractPath, 'utf8'));
  const extension = document?.info?.['x-quantfoundry-public-id-schemas'];
  if (!extension) throw new Error('Canonical public-ID schemas were not found');

  const schemas = Object.entries(extension).filter(([name]) => name !== 'any_public_semantic_id');
  if (schemas.length !== 34)
    throw new Error(`Expected 34 public-ID classes, found ${schemas.length}`);
  const matchers = new Map(
    schemas.map(([name, schema]) => {
      const prefix = schema.examples?.[0]?.split('-')[0];
      if (!prefix || schema.oneOf?.length !== 2)
        throw new Error(`Malformed public-ID schema ${name}`);
      return [prefix, schema.oneOf.map((branch) => new RegExp(branch.pattern))];
    }),
  );

  const { failures, scannedFiles, coverage } = await scanFormalPublicIdSources({
    repositoryRoot,
    matchers,
  });

  if (failures.length) throw new Error(failures.join('\n'));
  if (coverage.size !== formalPublicIdSources.length)
    throw new Error('Not every formal public-ID source was scanned');
  process.stdout.write(
    `Public-ID fixture scan passed for ${schemas.length} canonical classes across ${coverage.size} formal sources (${scannedFiles.length} files).\n`,
  );
};

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) await main();
