import { readFile, stat } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { URL, fileURLToPath, pathToFileURL } from 'node:url';

const frontendRoot = join(dirname(fileURLToPath(import.meta.url)), '..');
const typographyPath = join(frontendRoot, 'src/design-system/tokens/typography.css');
const css = (await readFile(typographyPath, 'utf8')).replace(/\/\*[\s\S]*?\*\//g, '');
const expected = [
  ['400', 'noto-sans-cjk-sc-subset.woff2'],
  ['500', 'noto-sans-cjk-sc-medium-subset.woff2'],
  ['600', 'noto-sans-cjk-sc-semibold-subset.woff2'],
  ['700', 'noto-sans-cjk-sc-bold-subset.woff2'],
];

const declarations = (face) =>
  Object.fromEntries(
    [...face.matchAll(/([\w-]+)\s*:\s*([^;{}]+)\s*;?/g)].map(([, key, value]) => [
      key,
      value.trim(),
    ]),
  );
const unquote = (value) => value.trim().replace(/^(?:"([\s\S]*)"|'([\s\S]*)')$/, '$1$2');
const faces = [...css.matchAll(/@font-face\s*{([^{}]*)}/g)].map(([, face]) => declarations(face));
for (const [weight, asset] of expected) {
  const face = faces.find((value) => {
    if (
      unquote(value['font-family'] ?? '') !== 'Noto Sans CJK SC' ||
      value['font-weight'] !== weight
    )
      return false;
    return [...(value.src ?? '').matchAll(/url\(\s*(['"]?)(.*?)\1\s*\)/gi)].some(([, , source]) => {
      const resolvedUrl = new URL(source, pathToFileURL(typographyPath));
      return (
        resolvedUrl.protocol === 'file:' &&
        fileURLToPath(resolvedUrl) === join(frontendRoot, 'src/assets/fonts', asset)
      );
    });
  });
  if (!face) throw new Error(`Missing Noto Sans CJK SC ${weight} face for ${asset}`);
  const fontPath = join(frontendRoot, 'src/assets/fonts', asset);
  const metadata = await stat(fontPath);
  const font = await readFile(fontPath);
  if (!metadata.isFile() || font.length < 48) throw new Error(`Invalid font asset: ${asset}`);
  if (
    font.subarray(0, 4).toString('ascii') !== 'wOF2' ||
    font.readUInt32BE(8) !== font.length ||
    font.readUInt16BE(12) === 0 ||
    font.readUInt16BE(14) !== 0 ||
    font.readUInt32BE(16) === 0
  )
    throw new Error(`Font asset is not a structurally valid WOFF2 file: ${asset}`);
}

process.stdout.write('Font asset gate passed: Noto Sans CJK SC 400/500/600/700 faces and files.\n');
