import http from "node:http";

import { MockDropError, MockDropStore } from "./mockdrop-store.js";

const MAX_BODY_BYTES = 1_000_000;

function json(response, status, body) {
  response.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store"
  });
  response.end(`${JSON.stringify(body)}\n`);
}

async function readJson(request) {
  const chunks = [];
  let size = 0;

  for await (const chunk of request) {
    size += chunk.length;
    if (size > MAX_BODY_BYTES) {
      throw new MockDropError(413, "PAYLOAD_TOO_LARGE", "Request body exceeds 1 MB");
    }
    chunks.push(chunk);
  }

  if (chunks.length === 0) {
    return {};
  }

  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw new MockDropError(400, "INVALID_JSON", "Request body must be valid JSON");
  }
}

function authorizeWrite(request, apiToken) {
  if (!apiToken) {
    return;
  }

  if (request.headers.authorization !== `Bearer ${apiToken}`) {
    throw new MockDropError(401, "UNAUTHORIZED", "A valid bearer token is required");
  }
}

function idempotencyKey(request) {
  const value = request.headers["idempotency-key"];
  return Array.isArray(value) ? value[0] : value;
}

export function createMockDropServer({
  store = new MockDropStore(),
  apiToken = process.env.MOCKDROP_API_TOKEN,
  logger = console
} = {}) {
  const server = http.createServer(async (request, response) => {
    const requestUrl = new URL(request.url, "http://localhost");

    try {
      if (request.method === "GET" && requestUrl.pathname === "/healthz") {
        return json(response, 200, { status: "ok", service: "mockdrop" });
      }

      if (request.method === "POST" && requestUrl.pathname === "/v1/demo/reset") {
        authorizeWrite(request, apiToken);
        return json(response, 200, { account: store.reset() });
      }

      const accountMatch = requestUrl.pathname.match(/^\/v1\/accounts\/([^/]+)$/);
      if (request.method === "GET" && accountMatch) {
        return json(response, 200, { account: store.getAccount(decodeURIComponent(accountMatch[1])) });
      }

      if (request.method === "POST" && requestUrl.pathname === "/v1/appeals") {
        authorizeWrite(request, apiToken);
        const body = await readJson(request);
        return json(response, 202, store.submitAppeal(body, idempotencyKey(request)));
      }

      const actionMatch = requestUrl.pathname.match(/^\/v1\/actions\/by-idempotency\/([^/]+)$/);
      if (request.method === "GET" && actionMatch) {
        return json(
          response,
          200,
          store.getActionByIdempotencyKey(decodeURIComponent(actionMatch[1]))
        );
      }

      const supplementMatch = requestUrl.pathname.match(
        /^\/v1\/appeals\/([^/]+)\/supplements$/
      );
      if (request.method === "POST" && supplementMatch) {
        authorizeWrite(request, apiToken);
        const body = await readJson(request);
        return json(
          response,
          200,
          store.submitSupplement(
            decodeURIComponent(supplementMatch[1]),
            body,
            idempotencyKey(request)
          )
        );
      }

      const appealMatch = requestUrl.pathname.match(/^\/v1\/appeals\/([^/]+)$/);
      if (request.method === "GET" && appealMatch) {
        return json(response, 200, {
          appeal: store.getAppeal(decodeURIComponent(appealMatch[1]))
        });
      }

      return json(response, 404, {
        error: {
          code: "NOT_FOUND",
          message: `${request.method} ${requestUrl.pathname} is not a MockDrop route`
        }
      });
    } catch (error) {
      if (!(error instanceof MockDropError)) {
        logger.error("Unhandled MockDrop request error", {
          method: request.method,
          path: requestUrl.pathname,
          error: error instanceof Error ? error.message : String(error)
        });
      }

      const status = error instanceof MockDropError ? error.status : 500;
      return json(response, status, {
        error: {
          code: error instanceof MockDropError ? error.code : "INTERNAL_ERROR",
          message:
            error instanceof MockDropError ? error.message : "MockDrop could not process the request",
          ...(error instanceof MockDropError && error.details
            ? { details: error.details }
            : {})
        }
      });
    }
  });

  server.store = store;
  return server;
}
