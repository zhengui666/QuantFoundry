import { lstat, readFile, readdir } from 'node:fs/promises';
import { dirname, extname, isAbsolute, relative, resolve, sep } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
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
  { path: 'docs/PRD/V1.0.0.md', kind: 'file' },
  { path: 'docs/UI设计方案/QuantFoundry_UI_Design_V1.0.0.md', kind: 'file' },
  {
    path: 'docs/前端技术方案/QuantFoundry_Frontend_Technical_Design_V1.0.0.md',
    kind: 'file',
  },
  {
    path: 'docs/全栈测试方案/QuantFoundry_Full_Stack_Test_Plan_V1.0.0.md',
    kind: 'file',
  },
  { path: 'docs/治理', kind: 'directory' },
  {
    path: 'docs/UI设计方案/QuantFoundry_UI_Interaction_Redesign_Brief_V1.0.0.md',
    kind: 'file',
  },
  { path: 'docs/后端系统技术方案/contracts', kind: 'directory' },
  { path: 'docs/后端系统技术方案/contracts/openapi-v1.yaml', kind: 'file' },
  { path: 'docs/后端系统技术方案/contracts/tools', kind: 'directory' },
  { path: 'frontend', kind: 'directory' },
];
const collect = async (path) => {
  const entries = await readdir(path, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    if (ignoredDirectories.has(entry.name)) continue;
    const child = resolve(path, entry.name);
    if (entry.isFile()) files.push(child);
    else if (entry.isDirectory()) files.push(...(await collect(child)));
    else if (entry.isSymbolicLink())
      throw new Error(`Formal public-ID source contains an unsupported symlink: ${child}`);
  }
  return files;
};

export const collectFormalPublicIdFiles = async (
  repositoryRoot,
  sources = formalPublicIdSources,
) => {
  const root = resolve(repositoryRoot);
  const files = new Set();
  const coverage = new Map();

  for (const source of sources) {
    const absolutePath = resolve(root, source.path);
    const relativePath = relative(root, absolutePath);
    if (isAbsolute(relativePath) || relativePath === '..' || relativePath.startsWith(`..${sep}`))
      throw new Error(`Formal public-ID source escapes repository root: ${source.path}`);
    const metadata = await lstat(absolutePath).catch(() => null);
    if (!metadata) throw new Error(`Formal public-ID source is missing: ${source.path}`);
    if (metadata.isSymbolicLink())
      throw new Error(`Formal public-ID source contains an unsupported symlink: ${absolutePath}`);
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

const tokenPattern = /\b([A-Za-z][A-Za-z0-9]*)-([A-Za-z0-9_-]+)/g;
const assignmentPattern =
  /(?:^|[\s,{(])[A-Za-z_$][A-Za-z0-9_$.-]*\s*[:=]\s*(?:"([^"]*)"|'([^']*)'|`([^`]*)`|([^\s,;}\])]+))/g;
const emptyFixturePattern =
  /(?:\b(?:fixture|example|value|id|token|input)\b|\b[A-Za-z_$][A-Za-z0-9_$]*(?:id|_id|Id|ID)\b)\s*[:=]\s*[`'"]([A-Za-z][A-Za-z0-9]*)-[`'"]/gi;
const intentionalRejection = (token, context) => {
  const normalized = token.toUpperCase();
  const directivePattern =
    /(?:reject_fixture|must\s+reject|public-id-prose)\s*:?[ \t]+([A-Za-z][A-Za-z0-9]*-[A-Za-z0-9_-]*)/gi;
  return [...context.matchAll(directivePattern)].some((match) => {
    const marker = match[1].toUpperCase();
    return marker.endsWith('-')
      ? normalized.startsWith(marker)
      : normalized === marker || normalized.startsWith(`${marker}-`);
  });
};

const grammarNotation = (token, context, file, key = '') => {
  const proseDirectivePattern = /\bpublic-id-prose\s*:?\s+([A-Za-z][A-Za-z0-9]*-[A-Za-z0-9_-]*)/gi;
  if (
    [...context.matchAll(proseDirectivePattern)].some(
      (match) => match[1].toUpperCase() === token.toUpperCase(),
    )
  )
    return true;
  if (
    /\bpublic-id-prose\b/i.test(context) &&
    !/\bpublic-id-prose\s*:?\s+[A-Za-z][A-Za-z0-9]*-[A-Za-z0-9_-]*/i.test(context)
  )
    return true;
  const extension = extname(file).toLowerCase();
  const proseField = /^(?:description|constraint|constraints|comment|comments|note|notes)$/i.test(
    key,
  );
  const proseSource = extension === '.md';
  const structuredProse =
    (extension === '.yaml' ||
      extension === '.yml' ||
      (extension === '.json' && /(?:manifest|schema)/i.test(file))) &&
    proseField;
  if (!proseSource && !structuredProse) return false;
  if (proseSource && !/\b(?:grammar|notation|locator|prefix|placeholder)\b/i.test(context))
    return false;
  const escaped = token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return (
    new RegExp('(?:`' + escaped + '`|' + escaped + '@(?:[A-Za-z]|version)\\b)', 'i').test(
      context,
    ) || new RegExp(`\\b${escaped}\\b[^\\n]*(?:notation|grammar)`, 'i').test(context)
  );
};

const jsonIdKeys = /^(?:id|value|token|key|[a-z0-9]+_(?:id|ref|token|key))$/i;

const invalidTokens = (text, context, location, matchers, key = '', file = location) => {
  const failures = [];
  const reported = new Set();
  const report = (token) => {
    if (!reported.has(token) && !intentionalRejection(token, context)) {
      reported.add(token);
      failures.push(`${location}: unmarked invalid public-ID fixture ${token}`);
    }
  };
  if (jsonIdKeys.test(key)) {
    const fieldMatch = text.match(/^\s*([A-Za-z][A-Za-z0-9]*)-/);
    const canonical = fieldMatch && matchers.get(fieldMatch[1].toUpperCase());
    if (canonical && !canonical.some((matcher) => matcher.test(text))) {
      report(text);
      return failures;
    }
  }
  for (const match of text.matchAll(assignmentPattern)) {
    const value = match.slice(1).find((candidate) => candidate !== undefined);
    if (!value || !value.includes('-') || /[${}]/.test(value)) continue;
    const assignmentKey = match[0].match(/(?:^|[\s,{(])([A-Za-z_$][A-Za-z0-9_$.-]*)\s*[:=]/)?.[1];
    if (!assignmentKey || !jsonIdKeys.test(assignmentKey)) continue;
    const rawPrefix = value.split('-', 1)[0];
    const prefix = rawPrefix.toUpperCase();
    const canonical = matchers.get(prefix);
    const suffix = value.slice(rawPrefix.length + 1);
    const recognized =
      canonical !== undefined &&
      (rawPrefix === prefix ||
        (suffix.length >= 20 && /^[A-Za-z0-9_-]+$/.test(suffix) && /[0-9]/.test(suffix)));
    if (recognized && !canonical.some((matcher) => matcher.test(value))) report(value);
  }
  const matches = [
    ...text.matchAll(tokenPattern),
    ...text.matchAll(emptyFixturePattern).map((match) => {
      match[0] = `${match[1]}-`;
      match[2] = '';
      return match;
    }),
  ];
  for (const match of matches) {
    const token = match[0];
    const rawPrefix = match[1] ?? '';
    const prefix = rawPrefix.toUpperCase();
    const canonical = matchers.get(prefix);
    const suffix = match[2] ?? '';
    const recognized =
      (canonical !== undefined &&
        (rawPrefix === prefix ||
          (suffix.length >= 20 && /^[A-Za-z0-9_-]+$/.test(suffix) && /[0-9]/.test(suffix)))) ||
      (prefix === 'MEM' && rawPrefix === prefix);
    if (!recognized || canonical?.some((matcher) => matcher.test(token))) continue;
    if (match[2] !== '' && grammarNotation(token, context, file, key)) continue;
    report(token);
  }
  if (
    jsonIdKeys.test(key) &&
    /^([A-Za-z][A-Za-z0-9]*)-$/.test(text) &&
    matchers.has(text.slice(0, -1).toUpperCase())
  ) {
    const token = text;
    const prefix = token.slice(0, -1).toUpperCase();
    const canonical = matchers.get(prefix);
    if (canonical && !canonical.some((matcher) => matcher.test(token))) report(token);
  }
  return failures;
};

const scanLines = (file, content, matchers) => {
  const failures = [];
  const lines = content.split(/\r?\n/);
  let marker = '';
  for (const [index, line] of lines.entries()) {
    failures.push(
      ...invalidTokens(
        line,
        marker ? `${marker} ${line}` : line,
        `${file}:${index + 1}`,
        matchers,
        '',
        file,
      ),
    );
    marker = /(?:reject_fixture|must\s+reject|public-id-prose)\s*:?\s+[A-Za-z][A-Za-z0-9]*-/i.test(
      line,
    )
      ? line
      : '';
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
  const visit = (node, path, key = '') => {
    if (typeof node === 'string') {
      failures.push(
        ...invalidTokens(node, `${key}: ${node}`, `${file}:${path}`, matchers, key, file),
      );
      return;
    }
    if (Array.isArray(node)) {
      node.forEach((entry, index) => visit(entry, `${path}[${index}]`, String(index)));
      return;
    }
    if (!node || typeof node !== 'object') return;
    for (const [key, entry] of Object.entries(node)) {
      failures.push(...invalidTokens(key, key, `${file}:${path}.${key} (key)`, matchers, '', file));
      visit(entry, `${path}.${key}`, key);
    }
  };
  visit(value, '$');
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
  const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
  const contractPath = resolve(repositoryRoot, 'docs/后端系统技术方案/contracts/openapi-v1.yaml');
  const document = load(await readFile(contractPath, 'utf8'));
  const extension = document?.info?.['x-quantfoundry-public-id-schemas'];
  if (!extension) throw new Error('Canonical public-ID schemas were not found');

  const schemas = Object.entries(extension).filter(([name]) => name !== 'any_public_semantic_id');
  if (schemas.length !== 34)
    throw new Error(`Expected 34 public-ID classes, found ${schemas.length}`);
  const matchers = new Map();
  for (const [name, schema] of schemas) {
    const examples = schema.examples ?? [];
    const prefixes = new Set(examples.map((example) => example.split('-')[0]));
    const prefix = [...prefixes][0];
    if (!prefix || examples.length !== 2 || schema.oneOf?.length !== 2)
      throw new Error(`Malformed public-ID schema ${name}`);
    if (
      !/^[A-Z][A-Z0-9]*$/.test(prefix) ||
      examples.some((example) => !example.startsWith(`${prefix}-`))
    )
      throw new Error(`Public-ID schema ${name} must use a canonical uppercase prefix`);
    const patterns = schema.oneOf.map((branch) => {
      if (
        typeof branch.pattern !== 'string' ||
        !branch.pattern.startsWith('^') ||
        !branch.pattern.endsWith('$')
      )
        throw new Error(`Public-ID schema ${name} must use full-string patterns`);
      return new RegExp(branch.pattern);
    });
    const matches = patterns.map(
      (pattern) => examples.map((example) => pattern.test(example)).filter(Boolean).length,
    );
    if (prefixes.size !== 1 || matches.some((count) => count !== 1))
      throw new Error(`Public-ID schema ${name} has inconsistent examples/patterns`);
    const matchedExampleIndexes = patterns.map((pattern) =>
      examples.findIndex((example) => pattern.test(example)),
    );
    if (new Set(matchedExampleIndexes).size !== examples.length)
      throw new Error(`Public-ID schema ${name} has inconsistent examples/patterns`);
    if (matchers.has(prefix)) throw new Error(`Duplicate public-ID prefix ${prefix}`);
    matchers.set(prefix, patterns);
  }

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
