import { readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { generate, parse, walk } from 'css-tree';

const css = await readFile(
  join(dirname(fileURLToPath(import.meta.url)), '../src/design-system/tokens/semantic.css'),
  'utf8',
);
const stylesheet = parse(css, { context: 'stylesheet' });
const rootTokens = new Map();
walk(stylesheet, (node) => {
  if (node.type !== 'Rule' || generate(node.prelude).trim() !== ':root' || !node.block) return;
  node.block.children.forEach((child) => {
    if (child.type === 'Declaration' && child.property.startsWith('--'))
      rootTokens.set(child.property, generate(child.value).trim());
  });
});

function token(name) {
  const values = rootTokens.has(`--${name}`) ? [rootTokens.get(`--${name}`)] : [];
  if (values.length !== 1 || !/^#[0-9a-f]{6}$/i.test(values[0]))
    throw new Error(`Expected exactly one valid root color token: --${name}`);
  return values[0];
}

function relativeLuminance(hex) {
  const channels = hex.match(/[0-9a-f]{2}/gi).map((channel) => parseInt(channel, 16) / 255);
  return channels
    .map((channel) => (channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4))
    .reduce((sum, channel, index) => sum + channel * [0.2126, 0.7152, 0.0722][index], 0);
}

function contrastRatio(first, second) {
  const firstLuminance = relativeLuminance(first);
  const secondLuminance = relativeLuminance(second);
  return (
    (Math.max(firstLuminance, secondLuminance) + 0.05) /
    (Math.min(firstLuminance, secondLuminance) + 0.05)
  );
}

const checks = [
  ['qf-color-focus', 'qf-color-sidebar', 3],
  ['qf-color-focus-on-dark', 'qf-color-sidebar', 3],
  ['qf-color-focus-on-dark', 'qf-color-sidebar-active', 3],
  ['qf-color-focus-on-dark', 'qf-color-action', 3],
  ['qf-color-focus-on-dark', 'qf-color-action-hover', 3],
  ['qf-color-focus', 'qf-color-surface-canvas', 3],
  ['qf-color-focus', 'qf-color-surface-panel', 3],
  ['qf-color-sidebar-active-text', 'qf-color-sidebar-active', 4.5],
  ['qf-color-on-accent', 'qf-color-sidebar', 4.5],
  ['qf-color-on-accent', 'qf-color-action', 4.5],
  ['qf-color-on-accent', 'qf-color-action-hover', 4.5],
  ['qf-color-disabled-text', 'qf-color-disabled-surface', 4.5],
];
const failures = checks
  .map(([foreground, background, minimum]) => [
    foreground,
    background,
    minimum,
    contrastRatio(token(foreground), token(background)),
  ])
  .filter(([, , minimum, ratio]) => ratio < minimum);

if (failures.length > 0)
  throw new Error(
    failures
      .map(
        ([foreground, background, minimum, ratio]) =>
          `${foreground} vs ${background}: ${ratio.toFixed(2)}:1 (minimum ${minimum}:1)`,
      )
      .join('; '),
  );

process.stdout.write(
  `Contrast gate passed: ${checks.map(([foreground, background]) => `${foreground}/${background} ${contrastRatio(token(foreground), token(background)).toFixed(2)}:1`).join(', ')}`,
);
