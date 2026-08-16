import { execFileSync } from 'node:child_process';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const workerName = 'mockServiceWorker.js';
const workerBinary = resolve(frontendRoot, 'node_modules/.bin/msw');

const replaceOnce = (source, needle, replacement, label) => {
  const occurrences = source.split(needle).length - 1;
  if (occurrences !== 1) throw new Error(`MSW generator patch target changed: ${label}`);
  return source.replace(needle, replacement);
};

export const patchWorker = (source) => {
  const listenerPrefix = "addEventListener('message', async function (event) {\n";
  const listenerClosing = '\n})';
  const listenerSuffix = `${listenerClosing}\n\naddEventListener('fetch', function (event) {`;
  const listenerStart = source.indexOf(listenerPrefix);
  const listenerEnd = source.indexOf(listenerSuffix, listenerStart);
  if (listenerStart < 0 || listenerEnd < 0)
    throw new Error('Unsupported MSW worker message listener');

  const messageBody = source.slice(listenerStart + listenerPrefix.length, listenerEnd);
  const safeMessageBody = messageBody
    .replaceAll('    sendToClient(', '    void sendToClient(')
    .replaceAll('      })\n      break', '      }).catch(() => {})\n      break');
  if (safeMessageBody === messageBody)
    throw new Error('MSW worker notification calls were not found');

  let patched = `${source.slice(0, listenerStart)}addEventListener('message', function (event) {\n  event.waitUntil(handleMessage(event))\n})\n\nasync function handleMessage(event) {\n${safeMessageBody}\n}${source.slice(listenerEnd + listenerClosing.length)}`;
  patched = replaceOnce(
    patched,
    'const activeClientIds = new Set()\n',
    'const activeClientIds = new Set()\nconst MESSAGE_TIMEOUT = 10_000\n',
    'message timeout constant',
  );

  const responseCallStart =
    "\n    sendToClient(\n      client,\n      {\n        type: 'RESPONSE',";
  patched = replaceOnce(
    patched,
    responseCallStart,
    responseCallStart.replace('sendToClient', 'void sendToClient'),
    'response notification start',
  );
  patched = replaceOnce(
    patched,
    '\n    )\n  }\n\n  return response',
    '\n    ).catch(() => {})\n  }\n\n  return response',
    'response notification completion',
  );

  const requestCallStart = '  const clientMessage = await sendToClient(\n';
  patched = replaceOnce(
    patched,
    requestCallStart,
    '  let clientMessage\n  try {\n    clientMessage = await sendToClient(\n',
    'request delegation start',
  );
  patched = replaceOnce(
    patched,
    '\n  )\n\n  switch (clientMessage.type)',
    '\n    )\n  } catch {\n    return passthrough()\n  }\n\n  switch (clientMessage.type)',
    'request delegation completion',
  );

  const sendStart = '/**\n * @param {Client} client\n';
  const sendEnd = '\n}\n\n/**\n * @param {Response} response';
  const sendStartIndex = patched.indexOf(sendStart);
  const sendEndIndex = patched.indexOf(sendEnd, sendStartIndex);
  if (sendStartIndex < 0 || sendEndIndex < 0)
    throw new Error('Unsupported MSW worker sendToClient function');
  const sendFunction = `/**
 * @param {Client} client
 * @param {any} message
 * @param {Array<Transferable>} transferrables
 * @returns {Promise<any>}
 */
function sendToClient(client, message, transferrables = []) {
  return new Promise((resolve, reject) => {
    const channel = new MessageChannel()
    let settled = false

    const finish = (callback, value) => {
      if (settled) return
      settled = true
      clearTimeout(timeout)
      channel.port1.close()
      channel.port2.close()
      callback(value)
    }

    const timeout = setTimeout(() => {
      finish(reject, new Error('MSW client message timed out'))
    }, MESSAGE_TIMEOUT)

    channel.port1.onmessage = (event) => {
      if (event.data && event.data.error) {
        return finish(reject, event.data.error)
      }

      finish(resolve, event.data)
    }

    try {
      client.postMessage(message, [
        channel.port2,
        ...transferrables.filter(Boolean),
      ])
    } catch (error) {
      finish(reject, error)
    }
  })
}`;
  patched = `${patched.slice(0, sendStartIndex)}${sendFunction}${patched.slice(sendEndIndex + 2)}`;
  return patched;
};

const generate = async (directory) => {
  execFileSync(workerBinary, ['init', directory], {
    cwd: frontendRoot,
    stdio: 'ignore',
  });
  const path = resolve(directory, workerName);
  const patched = patchWorker(await readFile(path, 'utf8'));
  await writeFile(path, patched, 'utf8');
  return patched;
};

const main = async () => {
  if (process.argv.includes('--check')) {
    const temporaryRoot = await mkdtemp(join(tmpdir(), 'qf-msw-'));
    try {
      const expected = await generate(temporaryRoot);
      const actual = await readFile(resolve(frontendRoot, 'public', workerName), 'utf8');
      if (actual !== expected)
        throw new Error('Generated mockServiceWorker.js is stale; run pnpm msw:generate');
      return;
    } finally {
      await rm(temporaryRoot, { force: true, recursive: true });
    }
  }

  await generate(resolve(frontendRoot, 'public'));
};

if (process.argv[1] && import.meta.url === `file://${process.argv[1]}`) await main();
