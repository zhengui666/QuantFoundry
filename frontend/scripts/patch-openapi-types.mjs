import { readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const targetPath = resolve(frontendRoot, 'src/api/generated.ts');
const explicitInput = process.argv.slice(2).find((value) => !value.startsWith('-'));
const inputPath = explicitInput ? resolve(explicitInput) : targetPath;
const check = process.argv.includes('--check');

const objectRefBranches = [
  ['research_policy', 'RP'],
  ['risk_policy', 'RISK'],
  ['cost_model', 'COST'],
  ['credential', 'CRED'],
  ['capability', 'CAP'],
  ['dataset', 'DSSET'],
  ['snapshot', 'DS'],
  ['data_quality_run', 'DQ'],
  ['data_quality_issue', 'DQI'],
  ['research', 'RSCH'],
  ['evidence', 'EVID'],
  ['conclusion', 'CONC'],
  ['experiment', 'EXP'],
  ['factor', 'FAC'],
  ['strategy', 'STRAT'],
  ['validation', 'VAL'],
  ['exposure', 'HOLD'],
  ['red_team_run', 'RTRUN'],
  ['portfolio', 'PORT'],
  ['memo', 'MEMO'],
  ['approval', 'APR'],
  ['paper', 'PAPER'],
  ['paper_run', 'PRUN'],
  ['paper_order', 'PORD'],
  ['paper_fill', 'PFILL'],
  ['review', 'REV'],
  ['agent_run', 'ARUN'],
  ['tool_call', 'TCALL'],
  ['job', 'JOB'],
  ['domain_event', 'EVT'],
  ['audit_event', 'AUD'],
  ['artifact', 'ART'],
  ['notification', 'NOTIF'],
  ['provenance', 'PROV'],
];

const header = `type CanonicalPublicId<Prefix extends string> = \`\${Prefix}-\${string}\`;
type ConfigurationValue = string | number | boolean | Record<string, unknown> | unknown[] | null;
type StrictConfigurationValueWrite =
  | { key: string; value: ConfigurationValue; secret?: never }
  | { key: string; secret: string; value?: never };
type ObjectRefFor<Type extends string, Prefix extends string> = {
  type: Type;
  id: CanonicalPublicId<Prefix>;
  version: number | null;
  revision: number;
};
type StrictObjectRef = ${objectRefBranches
  .map(([type, prefix]) => `ObjectRefFor<${JSON.stringify(type)}, ${JSON.stringify(prefix)}>`)
  .join(' | ')};

`;

const replaceBlock = (source, name, nextName, replacement) => {
  const pattern = new RegExp(`^        ${name}:[\\s\\S]*?(?=^        ${nextName}:)`, 'm');
  if (!pattern.test(source)) throw new Error(`Generated schema block not found: ${name}`);
  return source.replace(pattern, `${replacement}\n`);
};

const source = await readFile(inputPath, 'utf8');
let patched = source;
if (!patched.includes('type CanonicalPublicId<Prefix extends string>')) {
  const marker = ' */\n\n';
  if (!patched.includes(marker)) throw new Error('Generated OpenAPI header marker not found');
  patched = patched.replace(marker, `${marker}${header}`);
}
patched = replaceBlock(
  patched,
  'ConfigurationValueWrite',
  'ConfigurationValueView',
  '        ConfigurationValueWrite: StrictConfigurationValueWrite;',
);
patched = replaceBlock(
  patched,
  'ObjectRef',
  'VersionedHashRef',
  '        ObjectRef: StrictObjectRef;',
);
const sseEnvelopeType = '"text/event-stream": components["schemas"]["SseEnvelope"];';
const sseStreamType = '"text/event-stream": string;';
if (patched.split(sseEnvelopeType).length - 1 !== 1)
  throw new Error('Generated SSE response type not found exactly once');
patched = patched.replace(sseEnvelopeType, sseStreamType);

if (check) {
  const expected = await readFile(targetPath, 'utf8');
  if (expected !== patched) throw new Error('Generated OpenAPI types are stale; run pnpm codegen');
} else {
  await writeFile(targetPath, patched, 'utf8');
}
