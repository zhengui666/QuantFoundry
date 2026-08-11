import { readdir, stat } from 'node:fs/promises';
import { resolve } from 'node:path';

const assets = resolve(process.cwd(), 'dist/assets');
const maximumBytes = 500 * 1024;
const files = (await readdir(assets)).filter((file) => file.endsWith('.js'));
const sizes = await Promise.all(
  files.map(async (file) => ({ file, bytes: (await stat(resolve(assets, file))).size })),
);
const oversized = sizes.filter(({ bytes }) => bytes > maximumBytes);
if (oversized.length > 0)
  throw new Error(
    `Production bundle limit exceeded: ${oversized.map(({ file, bytes }) => `${file}=${bytes}`).join(', ')}`,
  );
for (const { file, bytes } of sizes.sort((left, right) => right.bytes - left.bytes))
  process.stdout.write(`${file}: ${bytes} bytes\n`);
