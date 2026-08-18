import { readdir, stat } from 'node:fs/promises';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const assets = resolve(frontendRoot, 'dist/assets');
const maximumBytes = 500 * 1024;
const maximumTotalBytes = 4 * 1024 * 1024;
const collectJavaScript = async (directory) => {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) files.push(...(await collectJavaScript(path)));
    else if (entry.isFile() && entry.name.endsWith('.js')) files.push(path);
  }
  return files;
};
const files = await collectJavaScript(assets);
if (files.length === 0) throw new Error('Production bundle check found no JavaScript assets.');
const sizes = await Promise.all(
  files.map(async (file) => ({ file, bytes: (await stat(file)).size })),
);
const oversized = sizes.filter(({ bytes }) => bytes > maximumBytes);
if (oversized.length > 0)
  throw new Error(
    `Production bundle limit exceeded: ${oversized.map(({ file, bytes }) => `${file}=${bytes}`).join(', ')}`,
  );
const totalBytes = sizes.reduce((total, { bytes }) => total + bytes, 0);
if (totalBytes > maximumTotalBytes)
  throw new Error(`Production bundle aggregate limit exceeded: ${totalBytes} bytes > ${maximumTotalBytes} bytes`);
for (const { file, bytes } of sizes.sort((left, right) => right.bytes - left.bytes))
  process.stdout.write(`${relative(frontendRoot, file)}: ${bytes} bytes\n`);
