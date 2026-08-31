import assert from "node:assert/strict";
import { afterEach, beforeEach, describe, test } from "node:test";

import {
  DEVICE_LOG_SHA256,
  REQUIRED_DEVICE_LOG_FIELDS,
  RIDER_ACCOUNT_ID,
  SUPPLEMENT_TEMPLATE
} from "../src/fixtures.js";
import { createMockDropServer } from "../src/server.js";

describe("MockDrop API", () => {
  let server;
  let baseUrl;
  let publishedEvents;

  beforeEach(async () => {
    publishedEvents = [];
    server = createMockDropServer({
      logger: { error() {} },
      publisher: {
        enabled: false,
        async publish(event) {
          publishedEvents.push(event);
          return null;
        }
      }
    });
    await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
    const address = server.address();
    baseUrl = `http://127.0.0.1:${address.port}`;
  });

  afterEach(async () => {
    server.closeAllConnections();
    await new Promise((resolve, reject) => {
      if (!server.listening) {
        resolve();
        return;
      }

      server.close((error) => (error ? reject(error) : resolve()));
    });
  });

  async function request(method, path, { body, idempotencyKey } = {}) {
    const response = await fetch(`${baseUrl}${path}`, {
      method,
      headers: {
        ...(body ? { "content-type": "application/json" } : {}),
        ...(idempotencyKey ? { "idempotency-key": idempotencyKey } : {})
      },
      ...(body ? { body: JSON.stringify(body) } : {})
    });
    const payload = await response.json();
    return { response, payload };
  }

  async function submitAppeal(key = "appeal-key-1", overrides = {}) {
    return request("POST", "/v1/appeals", {
      idempotencyKey: key,
      body: {
        caseId: "case-ao-2048",
        accountId: RIDER_ACCOUNT_ID,
        allegationType: "ABNORMAL_LOCATION",
        claimIds: ["claim-network-handoff"],
        ...overrides
      }
    });
  }

  async function submitValidSupplement(appealId, key = "supplement-key-1") {
    return request("POST", `/v1/appeals/${appealId}/supplements`, {
      idempotencyKey: key,
      body: {
        artifactSha256: DEVICE_LOG_SHA256,
        template: SUPPLEMENT_TEMPLATE,
        disclosedFields: REQUIRED_DEVICE_LOG_FIELDS
      }
    });
  }

  test("moves a suspended rider through appeal, supplement, approval, and activation", async () => {
    const health = await request("GET", "/healthz");
    assert.equal(health.response.status, 200);
    assert.equal(health.payload.status, "ok");

    const reset = await request("POST", "/v1/demo/reset");
    assert.equal(reset.response.status, 200);
    assert.equal(reset.payload.account.status, "SUSPENDED");

    const submitted = await submitAppeal();
    assert.equal(submitted.response.status, 202);
    assert.equal(submitted.payload.replayed, false);
    assert.equal(submitted.payload.appeal.status, "SUPPLEMENT_REQUESTED");
    assert.equal(submitted.payload.outboundEvent.type, "SUPPLEMENT_REQUESTED");
    assert.equal(submitted.payload.receipt.platformState, "SUPPLEMENT_REQUESTED");

    const supplemented = await submitValidSupplement(submitted.payload.appeal.appealId);
    assert.equal(supplemented.response.status, 200);
    assert.equal(supplemented.payload.replayed, false);
    assert.equal(supplemented.payload.appeal.status, "APPROVED");
    assert.equal(supplemented.payload.account.status, "ACTIVE");
    assert.equal(supplemented.payload.outboundEvent.type, "DECISION_APPROVED");

    const appeal = await request("GET", `/v1/appeals/${submitted.payload.appeal.appealId}`);
    assert.equal(appeal.payload.appeal.status, "APPROVED");

    const account = await request("GET", `/v1/accounts/${RIDER_ACCOUNT_ID}`);
    assert.equal(account.payload.account.status, "ACTIVE");
    assert.equal(account.payload.account.version, 2);
  });

  test("exposes a Cloud Run-compatible /health endpoint", async () => {
    const health = await request("GET", "/health");
    assert.equal(health.response.status, 200);
    assert.deepEqual(health.payload, { status: "ok", service: "mockdrop" });
  });

  test("replays an identical initial appeal without creating another appeal", async () => {
    const first = await submitAppeal("same-appeal-key");
    const replay = await submitAppeal("same-appeal-key");

    assert.equal(first.response.status, 202);
    assert.equal(replay.response.status, 202);
    assert.equal(replay.payload.replayed, true);
    assert.equal(replay.payload.appeal.appealId, first.payload.appeal.appealId);
    assert.equal(replay.payload.receipt.receiptId, first.payload.receipt.receiptId);
    assert.equal(server.store.appeals.size, 1);
  });

  test("does not republish an outbound event on idempotent replay", async () => {
    await submitAppeal("no-republish-key");
    await submitAppeal("no-republish-key");

    assert.equal(publishedEvents.length, 1);
    assert.equal(publishedEvents[0].type, "SUPPLEMENT_REQUESTED");
  });

  test("rejects reuse of an idempotency key with a different request", async () => {
    await submitAppeal("conflicting-key");
    const conflict = await submitAppeal("conflicting-key", {
      claimIds: ["a-different-claim"]
    });

    assert.equal(conflict.response.status, 409);
    assert.equal(conflict.payload.error.code, "IDEMPOTENCY_KEY_REUSE");
    assert.match(conflict.payload.error.details.originalRequestHash, /^[a-f0-9]{64}$/);
    assert.match(conflict.payload.error.details.conflictingRequestHash, /^[a-f0-9]{64}$/);
  });

  test("replays an identical supplement without activating the account twice", async () => {
    const submitted = await submitAppeal();
    const appealId = submitted.payload.appeal.appealId;
    const first = await submitValidSupplement(appealId, "same-supplement-key");
    const replay = await submitValidSupplement(appealId, "same-supplement-key");

    assert.equal(first.payload.account.status, "ACTIVE");
    assert.equal(replay.payload.replayed, true);
    assert.equal(replay.payload.receipt.receiptId, first.payload.receipt.receiptId);
    assert.equal(replay.payload.account.version, 2);
  });

  test("replays the initial appeal after account activation", async () => {
    const first = await submitAppeal("appeal-before-activation");
    await submitValidSupplement(first.payload.appeal.appealId, "activation-supplement");

    const replay = await submitAppeal("appeal-before-activation");

    assert.equal(replay.response.status, 202);
    assert.equal(replay.payload.replayed, true);
    assert.equal(replay.payload.receipt.receiptId, first.payload.receipt.receiptId);
  });

  test("rejects an invalid supplement and preserves the suspension", async () => {
    const submitted = await submitAppeal();
    const appealId = submitted.payload.appeal.appealId;
    const rejected = await request("POST", `/v1/appeals/${appealId}/supplements`, {
      idempotencyKey: "invalid-supplement-key",
      body: {
        artifactSha256: "0".repeat(64),
        template: SUPPLEMENT_TEMPLATE,
        disclosedFields: REQUIRED_DEVICE_LOG_FIELDS
      }
    });

    assert.equal(rejected.response.status, 200);
    assert.equal(rejected.payload.appeal.status, "REJECTED");
    assert.equal(rejected.payload.account.status, "SUSPENDED");
    assert.equal(rejected.payload.outboundEvent.type, "DECISION_REJECTED");
  });

  test("recovers the original platform receipt by idempotency key", async () => {
    const submitted = await submitAppeal("recoverable-key");
    const recovered = await request(
      "GET",
      "/v1/actions/by-idempotency/recoverable-key"
    );

    assert.equal(recovered.response.status, 200);
    assert.equal(recovered.payload.actionType, "SUBMIT_APPEAL");
    assert.equal(recovered.payload.receipt.receiptId, submitted.payload.receipt.receiptId);
    assert.equal(recovered.payload.requestHash.length, 64);
  });
});
