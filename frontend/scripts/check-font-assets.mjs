import { execFile } from 'node:child_process';
import { readFile, stat } from 'node:fs/promises';
import { promisify } from 'node:util';
import { dirname, join } from 'node:path';
import { URL, fileURLToPath, pathToFileURL } from 'node:url';
import { generate, parse, walk } from 'css-tree';

const execFileAsync = promisify(execFile);
const frontendRoot = join(dirname(fileURLToPath(import.meta.url)), '..');
const typographyPath = join(frontendRoot, 'src/design-system/tokens/typography.css');
const css = await readFile(typographyPath, 'utf8');
const expected = [
  ['400', 'noto-sans-cjk-sc-subset.woff2'],
  ['500', 'noto-sans-cjk-sc-medium-subset.woff2'],
  ['600', 'noto-sans-cjk-sc-semibold-subset.woff2'],
  ['700', 'noto-sans-cjk-sc-bold-subset.woff2'],
];

const declarations = [];
const stylesheet = parse(css, { context: 'stylesheet' });
walk(stylesheet, (node) => {
  if (node.type !== 'Atrule' || node.name !== 'font-face' || !node.block) return;
  const values = {};
  node.block.children.forEach((child) => {
    if (child.type === 'Declaration') values[child.property] = generate(child.value).trim();
  });
  declarations.push(values);
});

const unquote = (value) => value.trim().replace(/^(?:"([\s\S]*)"|'([\s\S]*)')$/, '$1$2');
const fontPathFor = (asset) => join(frontendRoot, 'src/assets/fonts', asset);

for (const [weight, asset] of expected) {
  const face = declarations.find((value) => {
    if (
      unquote(value['font-family'] ?? '') !== 'Noto Sans CJK SC' ||
      value['font-weight'] !== weight
    )
      return false;
    const src = value.src ?? '';
    const urls = [...src.matchAll(/url\(\s*(['"]?)(.*?)\1\s*\)/gi)];
    return urls.some(([, , source]) => {
      const resolvedUrl = new URL(source, pathToFileURL(typographyPath));
      return resolvedUrl.protocol === 'file:' && fileURLToPath(resolvedUrl) === fontPathFor(asset);
    });
  });
  if (!face) throw new Error(`Missing Noto Sans CJK SC ${weight} face for ${asset}`);

  const fontPath = fontPathFor(asset);
  const metadata = await stat(fontPath);
  if (!metadata.isFile()) throw new Error(`Invalid font asset: ${asset}`);
  try {
    await execFileAsync('uv', [
      '--directory',
      join(frontendRoot, '..', 'backend'),
      'run',
      '--frozen',
      'python',
      '-c',
      [
        'from fontTools.ttLib import TTFont',
        'import sys',
        'font = TTFont(sys.argv[1], lazy=False, checkChecksums=2)',
        'expected_weight = int(sys.argv[2])',
        'required = {"name", "OS/2"}',
        'missing = required.difference(font.reader.keys())',
        'if missing: raise ValueError(f"font is missing required tables: {sorted(missing)}")',
        'names = {record.toUnicode() for record in font["name"].names if record.nameID == 1}',
        'if not ("Noto Sans CJK SC" in names or any(name.startswith("Noto Sans CJK SC ") for name in names)): raise ValueError("font family metadata is invalid")',
        'if font["OS/2"].usWeightClass != expected_weight: raise ValueError("OS/2 weight metadata is invalid")',
      ].join('\\n'),
      fontPath,
      weight,
    ]);
  } catch (error) {
    throw new Error(`Font decoder rejected ${asset}: ${error.message}`, { cause: error });
  }
}

process.stdout.write(
  'Font asset gate passed: parsed CSS, decoded WOFF2, and verified Noto Sans CJK SC 400/500/600/700 faces.\n',
);
