/* eslint-disable */
/* tslint:disable */

/**
 * Mock Service Worker.
 * @see https://github.com/mswjs/msw
 * - Please do NOT modify this file.
 */

const PACKAGE_VERSION = '2.15.0'
const INTEGRITY_CHECKSUM = '03cb67ac84128e63d7cd722a6e5b7f1e'
const IS_MOCKED_RESPONSE = Symbol('isMockedResponse')
const activeClientIds = new Set()
const MESSAGE_TIMEOUT = 10_000
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS'])
let lifecycleGeneration = 0

async function reconcileActiveClients(sender, excludedClientId) {
  const generation = ++lifecycleGeneration
  const allClients = await self.clients.matchAll({
    type: 'window',
    includeUncontrolled: true,
  })
  if (sender?.id && !allClients.some((client) => client.id === sender.id)) {
    allClients.push(sender)
  }
  const liveClientIds = new Set(allClients.map((client) => client.id).filter((id) => id !== excludedClientId))
  if (generation !== lifecycleGeneration) return allClients
  const remainingClients = allClients.filter((client) => client.id !== excludedClientId)

  for (const clientId of activeClientIds) {
    if (!liveClientIds.has(clientId)) activeClientIds.delete(clientId)
  }

  if (activeClientIds.size === 0 && remainingClients.length === 0) {
    await new Promise((resolve) => setTimeout(resolve, 0))
    const remainingClients = await self.clients.matchAll({
      type: 'window',
      includeUncontrolled: true,
    })
    if (generation === lifecycleGeneration && activeClientIds.size === 0 && remainingClients.length === 0) {
      await self.registration.unregister()
    }
  }

  return allClients
}

addEventListener('install', function () {
  self.skipWaiting()
})

addEventListener('activate', function (event) {
  event.waitUntil(self.clients.claim())
})

let lifecycleMessageQueue = Promise.resolve()

addEventListener('message', function (event) {
  const message = lifecycleMessageQueue.then(() => handleMessage(event))
  lifecycleMessageQueue = message.catch(() => {})
  event.waitUntil(message)
})

async function handleMessage(event) {
  await reconcileActiveClients(event.source)

  const clientId = Reflect.get(event.source || {}, 'id')

  if (event.data === 'CLIENT_CLOSED' && clientId && self.clients) {
    activeClientIds.delete(clientId)
    await reconcileActiveClients(undefined, clientId)
    return
  }

  if (!clientId || !self.clients) {
    return
  }

  const client = await self.clients.get(clientId)

  if (!client) {
    return
  }

  switch (event.data) {
    case 'KEEPALIVE_REQUEST': {
      await sendToClient(client, {
        type: 'KEEPALIVE_RESPONSE',
      }).catch(() => {})
      break
    }

    case 'INTEGRITY_CHECK_REQUEST': {
      await sendToClient(client, {
        type: 'INTEGRITY_CHECK_RESPONSE',
        payload: {
          packageVersion: PACKAGE_VERSION,
          checksum: INTEGRITY_CHECKSUM,
        },
      }).catch(() => {})
      break
    }

    case 'MOCK_ACTIVATE': {
      lifecycleGeneration++
      activeClientIds.add(clientId)

      await sendToClient(client, {
        type: 'MOCKING_ENABLED',
        payload: {
          client: {
            id: client.id,
            frameType: client.frameType,
          },
        },
      }).catch(() => {})
      break
    }

    case 'CLIENT_CLOSED': {
      activeClientIds.delete(clientId)

      await reconcileActiveClients()

      break
    }
  }
}

addEventListener('fetch', function (event) {
  const requestInterceptedAt = Date.now()

  // Bypass navigation requests.
  if (event.request.mode === 'navigate') {
    return
  }

  // Opening the DevTools triggers the "only-if-cached" request
  // that cannot be handled by the worker. Bypass such requests.
  if (
    event.request.cache === 'only-if-cached' &&
    event.request.mode !== 'same-origin'
  ) {
    return
  }

  // Bypass all requests when there are no active clients.
  // Prevents the self-unregistered worked from handling requests
  // after it's been terminated (still remains active until the next reload).
  if (activeClientIds.size === 0) {
    return
  }

  const requestId = crypto.randomUUID()
  event.respondWith(handleRequest(event, requestId, requestInterceptedAt))
})

/**
 * @param {FetchEvent} event
 * @param {string} requestId
 * @param {number} requestInterceptedAt
 */
async function handleRequest(event, requestId, requestInterceptedAt) {
  const originatedFromActiveClient = Boolean(event.clientId && activeClientIds.has(event.clientId))
  await reconcileActiveClients()
  const client = await resolveMainClient(event)
  const requestCloneForEvents = event.request.clone()
  const response = await getResponse(
    event,
    client,
    requestId,
    requestInterceptedAt,
    originatedFromActiveClient,
  )

  // Send back the response clone for the "response:*" life-cycle events.
  // Ensure MSW is active and ready to handle the message, otherwise
  // this message will pend indefinitely.
  if (client && activeClientIds.has(client.id)) {
    try {
    const serializedRequest = await serializeRequest(requestCloneForEvents)

    // Omit the body of server-sent event stream responses.
    // Cloning such responses would prevent client-side stream cancelations
    // from reaching the original stream (a teed stream only cancels its
    // source once both of its branches cancel) and would buffer the
    // entire stream into the unconsumed clone indefinitely.
    const isEventStreamResponse = response.headers
      .get('content-type')
      ?.toLowerCase()
      .startsWith('text/event-stream')

    // Clone the response so both the client and the library could consume it.
    const responseClone = isEventStreamResponse ? null : response.clone()

    void sendToClient(
      client,
      {
        type: 'RESPONSE',
        payload: {
          isMockedResponse: IS_MOCKED_RESPONSE in response,
          request: {
            id: requestId,
            ...serializedRequest,
          },
          response: {
            type: response.type,
            status: response.status,
            statusText: response.statusText,
            headers: Object.fromEntries(response.headers.entries()),
            body: responseClone ? responseClone.body : null,
          },
        },
      },
      responseClone && responseClone.body
        ? [serializedRequest.body, responseClone.body]
        : [],
    ).catch(() => {})
    } catch {}
  }

  return response
}

/**
 * Resolve the main client for the given event.
 * Client that issues a request doesn't necessarily equal the client
 * that registered the worker. It's with the latter the worker should
 * communicate with during the response resolving phase.
 * @param {FetchEvent} event
 * @returns {Promise<Client | undefined>}
 */
async function resolveMainClient(event) {
  const client = await self.clients.get(event.clientId)

  if (activeClientIds.has(event.clientId)) return client
  return undefined
}

/**
 * @param {FetchEvent} event
 * @param {Client | undefined} client
 * @param {string} requestId
 * @param {number} requestInterceptedAt
 * @returns {Promise<Response>}
 */
async function getResponse(event, client, requestId, requestInterceptedAt, originatedFromActiveClient) {
  // Clone the request because it might've been already used
  // (i.e. its body has been read and sent to the client).
  const requestClone = event.request.clone()

  function passthrough() {
    // Cast the request headers to a new Headers instance
    // so the headers can be manipulated with.
    const headers = new Headers(requestClone.headers)

    // Remove the "accept" header value that marked this request as passthrough.
    // This prevents request alteration and also keeps it compliant with the
    // user-defined CORS policies.
    const acceptHeader = headers.get('accept')
    if (acceptHeader) {
      const values = acceptHeader.split(',').map((value) => value.trim())
      const filteredValues = values.filter(
        (value) => value !== 'msw/passthrough',
      )

      if (filteredValues.length > 0) {
        headers.set('accept', filteredValues.join(', '))
      } else {
        headers.delete('accept')
      }
    }

    return fetch(requestClone, { headers })
  }

  function failClosed() {
    return SAFE_METHODS.has(event.request.method) ? passthrough() : Response.error()
  }

  // Bypass mocking when the client is not active.
  if (!client) {
    return originatedFromActiveClient ? failClosed() : passthrough()
  }

  // Bypass initial page load requests (i.e. static assets).
  // The absence of the immediate/parent client in the map of the active clients
  // means that MSW hasn't dispatched the "MOCK_ACTIVATE" event yet
  // and is not ready to handle requests.
  if (!activeClientIds.has(client.id)) {
    return originatedFromActiveClient ? failClosed() : passthrough()
  }

  // Notify the client that a request has been intercepted.
  const serializedRequest = await serializeRequest(event.request)
  let clientMessage
  try {
    clientMessage = await sendToClient(
    client,
    {
      type: 'REQUEST',
      payload: {
        id: requestId,
        interceptedAt: requestInterceptedAt,
        ...serializedRequest,
      },
    },
    [serializedRequest.body],
    )
  } catch {
    return failClosed()
  }

  if (!clientMessage || typeof clientMessage !== 'object') return failClosed()

  switch (clientMessage.type) {
    case 'MOCK_RESPONSE': {
      return respondWithMock(clientMessage.data)
    }

    case 'PASSTHROUGH': {
      return passthrough()
    }
  }

  return failClosed()
}

/**
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
}

/**
 * @param {Response} response
 * @returns {Response}
 */
function respondWithMock(response) {
  // Setting response status code to 0 is a no-op.
  // However, when responding with a "Response.error()", the produced Response
  // instance will have status code set to 0. Since it's not possible to create
  // a Response instance with status code 0, handle that use-case separately.
  if (response.status === 0) {
    return Response.error()
  }

  const mockedResponse = new Response(response.body, response)

  Reflect.defineProperty(mockedResponse, IS_MOCKED_RESPONSE, {
    value: true,
    enumerable: true,
  })

  return mockedResponse
}

/**
 * @param {Request} request
 */
async function serializeRequest(request) {
  return {
    url: request.url,
    mode: request.mode,
    method: request.method,
    headers: Object.fromEntries(request.headers.entries()),
    cache: request.cache,
    credentials: request.credentials,
    destination: request.destination,
    integrity: request.integrity,
    redirect: request.redirect,
    referrer: request.referrer,
    referrerPolicy: request.referrerPolicy,
    body: await request.arrayBuffer(),
    keepalive: request.keepalive,
  }
}
