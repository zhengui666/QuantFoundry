import { execFileSync } from 'node:child_process';
import { mkdtemp, readFile, rename, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

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
  let safeMessageBody = messageBody
    .replaceAll('    sendToClient(', '    await sendToClient(')
    .replaceAll('      })\n      break', '      }).catch(() => {})\n      break');
  if (safeMessageBody === messageBody)
    throw new Error('MSW worker notification calls were not found');

  safeMessageBody = replaceOnce(
    safeMessageBody,
    "    case 'MOCK_ACTIVATE': {\n      activeClientIds.add",
    "    case 'MOCK_ACTIVATE': {\n      lifecycleGeneration++\n      activeClientIds.add",
    'activation invalidates pending unregister',
  );

  safeMessageBody = replaceOnce(
    safeMessageBody,
    "  const clientId = Reflect.get(event.source || {}, 'id')\n",
    "  await reconcileActiveClients(event.source)\n\n  const clientId = Reflect.get(event.source || {}, 'id')\n",
    'active client reconciliation',
  );
  safeMessageBody = replaceOnce(
    safeMessageBody,
    `  const allClients = await self.clients.matchAll({\n    type: 'window',\n  })\n\n`,
    '',
    'message client list removal',
  );
  safeMessageBody = replaceOnce(
    safeMessageBody,
    `      const remainingClients = allClients.filter((client) => {\n        return client.id !== clientId\n      })\n\n      // Unregister itself when there are no more clients\n      if (remainingClients.length === 0) {\n        self.registration.unregister()\n      }`,
    '      await reconcileActiveClients()',
    'client close reconciliation',
  );

  let patched = `${source.slice(0, listenerStart)}addEventListener('message', function (event) {\n  event.waitUntil(handleMessage(event))\n})\n\nasync function handleMessage(event) {\n${safeMessageBody}\n}${source.slice(listenerEnd + listenerClosing.length)}`;
  patched = replaceOnce(
    patched,
    'const activeClientIds = new Set()\n',
    `const activeClientIds = new Set()\nconst MESSAGE_TIMEOUT = 10_000\nconst SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS'])\nlet lifecycleGeneration = 0\n\nasync function reconcileActiveClients() {\n  const generation = ++lifecycleGeneration\n  const allClients = await self.clients.matchAll({\n    type: 'window',\n  })\n  const liveClientIds = new Set(allClients.map((client) => client.id))\n\n  for (const clientId of activeClientIds) {\n    if (!liveClientIds.has(clientId)) activeClientIds.delete(clientId)\n  }\n\n  if (activeClientIds.size === 0 && allClients.length === 0) {\n    await new Promise((resolve) => setTimeout(resolve, 0))\n    const remainingClients = await self.clients.matchAll({\n      type: 'window',\n      includeUncontrolled: true,\n    })\n    if (generation === lifecycleGeneration && activeClientIds.size === 0 && remainingClients.length === 0) {\n      await self.registration.unregister()\n    }\n  }\n\n  return allClients\n}\n`,
    'active client reconciliation helper',
  );
  patched = replaceOnce(
    patched,
    `async function reconcileActiveClients() {
  const generation = ++lifecycleGeneration
  const allClients = await self.clients.matchAll({
    type: 'window',
  })
  const liveClientIds = new Set(allClients.map((client) => client.id))
`,
    `async function reconcileActiveClients(sender, excludedClientId) {
  const generation = ++lifecycleGeneration
  const allClients = await self.clients.matchAll({
    type: 'window',
    includeUncontrolled: true,
  })
  if (sender?.id && !allClients.some((client) => client.id === sender.id)) {
    allClients.push(sender)
  }
  const liveClientIds = new Set(allClients.map((client) => client.id).filter((id) => id !== excludedClientId))
  const remainingClients = allClients.filter((client) => client.id !== excludedClientId)
`,
    'uncontrolled active client reconciliation',
  );
  patched = replaceOnce(
    patched,
    '  const liveClientIds = new Set(allClients.map((client) => client.id).filter((id) => id !== excludedClientId))\n  const remainingClients = allClients.filter((client) => client.id !== excludedClientId)\n\n  for (const clientId of activeClientIds) {',
    '  const liveClientIds = new Set(allClients.map((client) => client.id).filter((id) => id !== excludedClientId))\n  if (generation !== lifecycleGeneration) return allClients\n  const remainingClients = allClients.filter((client) => client.id !== excludedClientId)\n\n  for (const clientId of activeClientIds) {',
    'stale reconciliation guard',
  );
  patched = replaceOnce(
    patched,
    '  if (activeClientIds.size === 0 && allClients.length === 0) {',
    '  if (activeClientIds.size === 0 && remainingClients.length === 0) {',
    'closing client liveness exclusion',
  );
  patched = replaceOnce(
    patched,
    "  const clientId = Reflect.get(event.source || {}, 'id')\n\n  if (!clientId || !self.clients) {\n    return\n  }\n\n  const client = await self.clients.get(clientId)",
    "  const clientId = Reflect.get(event.source || {}, 'id')\n\n  if (event.data === 'CLIENT_CLOSED' && clientId && self.clients) {\n    activeClientIds.delete(clientId)\n    await reconcileActiveClients(undefined, clientId)\n    return\n  }\n\n  if (!clientId || !self.clients) {\n    return\n  }\n\n  const client = await self.clients.get(clientId)",
    'closed client before lookup',
  );

  patched = replaceOnce(
    patched,
    '  if (client && activeClientIds.has(client.id)) {\n    const serializedRequest = await serializeRequest(requestCloneForEvents)',
    '  if (client && activeClientIds.has(client.id)) {\n    try {\n    const serializedRequest = await serializeRequest(requestCloneForEvents)',
    'response notification guard',
  );
  patched = replaceOnce(
    patched,
    'async function handleRequest(event, requestId, requestInterceptedAt) {\n  const client = await resolveMainClient(event)',
    'async function handleRequest(event, requestId, requestInterceptedAt) {\n  await reconcileActiveClients()\n  const client = await resolveMainClient(event)',
    'fetch active client reconciliation',
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
    '\n    ).catch(() => {})\n    } catch {}\n  }\n\n  return response',
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
    "\n    )\n  } catch {\n    return failClosed()\n  }\n\n  if (!clientMessage || typeof clientMessage !== 'object') return failClosed()\n\n  switch (clientMessage.type)",
    'request delegation completion',
  );

  patched = replaceOnce(
    patched,
    '    return fetch(requestClone, { headers })\n  }\n\n  // Bypass mocking',
    '    return fetch(requestClone, { headers })\n  }\n\n  function failClosed() {\n    return SAFE_METHODS.has(event.request.method) ? passthrough() : Response.error()\n  }\n\n  // Bypass mocking',
    'request fail-closed helper',
  );
  patched = replaceOnce(
    patched,
    '  if (!client) {\n    return passthrough()\n  }',
    '  if (!client) {\n    return passthrough()\n  }',
    'inactive client fail-closed behavior',
  );
  patched = replaceOnce(
    patched,
    '  return passthrough()\n}\n\n/**\n * @param {Client} client',
    '  return failClosed()\n}\n\n/**\n * @param {Client} client',
    'unknown request message fail-closed',
  );

  patched = replaceOnce(
    patched,
    `  if (activeClientIds.has(event.clientId)) {
    return client
  }

  if (client?.frameType === 'top-level') {
    return client
  }

  const allClients = await self.clients.matchAll({
    type: 'window',
  })

  return allClients
    .filter((client) => {
      // Get only those clients that are currently visible.
      return client.visibilityState === 'visible'
    })
    .find((client) => {
      // Find the client ID that's recorded in the
      // set of clients that have registered the worker.
      return activeClientIds.has(client.id)
    })`,
    `  if (activeClientIds.has(event.clientId)) return client
  return undefined`,
    'cross-client fallback removal',
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
  const path = resolve(directory, workerName);
  const temporaryDirectory = await mkdtemp(resolve(directory, '.qf-msw-'));
  const temporaryPath = resolve(temporaryDirectory, workerName);
  try {
    execFileSync(workerBinary, ['init', temporaryDirectory], {
      cwd: frontendRoot,
      stdio: 'ignore',
    });
    const patched = patchWorker(await readFile(temporaryPath, 'utf8'));
    await writeFile(temporaryPath, patched, 'utf8');
    await rename(temporaryPath, path);
    return patched;
  } finally {
    await rm(temporaryDirectory, { force: true, recursive: true });
  }
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

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) await main();
