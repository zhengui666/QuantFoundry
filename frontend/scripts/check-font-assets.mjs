import { access, readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendRoot = join(dirname(fileURLToPath(import.meta.url)), '..');
const css = await readFile(join(frontendRoot, 'src/design-system/tokens/typography.css'), 'utf8');
const expected = [
  ['400', 'noto-sans-cjk-sc-subset.woff2'],
  ['500', 'noto-sans-cjk-sc-medium-subset.woff2'],
  ['600', 'noto-sans-cjk-sc-semibold-subset.woff2'],
  ['700', 'noto-sans-cjk-sc-bold-subset.woff2'],
];

const faces = [...css.matchAll(/@font-face\s*{([^}]+)}/g)].map(([, face]) => face);
for (const [weight, asset] of expected) {
  const face = faces.find(
    (value) =>
      value.includes("font-family: 'Noto Sans CJK SC'") &&
      value.includes(`url('../../assets/fonts/${asset}')`) &&
      new RegExp(`font-weight:\\s*${weight};`).test(value),
  );
  if (!face) throw new Error(`Missing Noto Sans CJK SC ${weight} face for ${asset}`);
  await access(join(frontendRoot, 'src/assets/fonts', asset));
}

process.stdout.write('Font asset gate passed: Noto Sans CJK SC 400/500/600/700 faces and files.\n');
