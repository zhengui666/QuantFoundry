import { readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const css = await readFile(
  join(dirname(fileURLToPath(import.meta.url)), '../src/design-system/tokens/semantic.css'),
  'utf8',
);

function token(name) {
  const match = css.match(new RegExp(`--${name}:\\s*(#[0-9a-f]{6})`, 'i'));
  if (!match) throw new Error(`Missing color token: --${name}`);
  return match[1];
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

const focus = token('qf-color-focus');
const backgrounds = ['qf-color-sidebar', 'qf-color-surface-canvas', 'qf-color-surface-panel'];
const failures = backgrounds
  .map((background) => [background, contrastRatio(focus, token(background))])
  .filter(([, ratio]) => ratio < 3);

if (failures.length > 0)
  throw new Error(
    failures
      .map(([background, ratio]) => `${focus} vs ${background}: ${ratio.toFixed(2)}:1`)
      .join('; '),
  );

process.stdout.write(
  `Focus contrast gate passed: ${backgrounds.map((background) => `${background} ${contrastRatio(focus, token(background)).toFixed(2)}:1`).join(', ')}`,
);
