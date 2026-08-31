import { randomUUID } from "node:crypto";

import { canonicalize, sha256Canonical, sha256Text } from "./canonical.js";
import {
  DEVICE_LOG_SHA256,
  REQUIRED_DEVICE_LOG_FIELDS,
  RIDER_ACCOUNT_ID,
  SUPPLEMENT_TEMPLATE
} from "./fixtures.js";

export class MockDropError extends Error {
  constructor(status, code, message, details = undefined) {
    super(message);
    this.name = "MockDropError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function requireString(value, field) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new MockDropError(400, "INVALID_REQUEST", `${field} must be a non-empty string`);
  }

  return value;
}

function sameStringSet(actual, expected) {
  if (!Array.isArray(actual) || actual.some((item) => typeof item !== "string")) {
    return false;
  }

  return [...actual].sort().join("\n") === [...expected].sort().join("\n");
}

export class MockDropStore {
  constructor({ now = () => new Date(), id = () => randomUUID() } = {}) {
    this.now = now;
    this.id = id;
    this.reset();
  }

  reset() {
    this.accounts = new Map([
      [
        RIDER_ACCOUNT_ID,
        {
          accountId: RIDER_ACCOUNT_ID,
          status: "SUSPENDED",
          suspensionReason: "ABNORMAL_LOCATION",
          version: 1,
          updatedAt: this.now().toISOString()
        }
      ]
    ]);
    this.appeals = new Map();
    this.idempotencyRecords = new Map();
    this.platformSequence = 0;

    return this.getAccount(RIDER_ACCOUNT_ID);
  }

  getAccount(accountId) {
    const account = this.accounts.get(accountId);
    if (!account) {
      throw new MockDropError(404, "ACCOUNT_NOT_FOUND", `Account ${accountId} was not found`);
    }

    return structuredClone(account);
  }

  getAppeal(appealId) {
    const appeal = this.appeals.get(appealId);
    if (!appeal) {
      throw new MockDropError(404, "APPEAL_NOT_FOUND", `Appeal ${appealId} was not found`);
    }

    return structuredClone(appeal);
  }

  getActionByIdempotencyKey(idempotencyKey) {
    const record = this.idempotencyRecords.get(idempotencyKey);
    if (!record) {
      throw new MockDropError(
        404,
        "IDEMPOTENCY_RECORD_NOT_FOUND",
        `No action exists for idempotency key ${idempotencyKey}`
      );
    }

    return structuredClone({
      actionType: record.actionType,
      requestHash: record.requestHash,
      receipt: record.receipt,
      response: record.response
    });
  }

  submitAppeal(body, idempotencyKey) {
    const normalized = {
      caseId: requireString(body?.caseId, "caseId"),
      accountId: requireString(body?.accountId, "accountId"),
      allegationType: requireString(body?.allegationType, "allegationType"),
      claimIds: Array.isArray(body?.claimIds) ? body.claimIds : []
    };

    if (normalized.allegationType !== "ABNORMAL_LOCATION") {
      throw new MockDropError(
        422,
        "UNSUPPORTED_ALLEGATION",
        "MockDrop only supports the ABNORMAL_LOCATION demo case"
      );
    }

    return this.#executeIdempotent({
      idempotencyKey,
      actionType: "SUBMIT_APPEAL",
      request: normalized,
      execute: () => {
        const account = this.accounts.get(normalized.accountId);
        if (!account) {
          throw new MockDropError(404, "ACCOUNT_NOT_FOUND", "The rider account does not exist");
        }
        if (account.status !== "SUSPENDED") {
          throw new MockDropError(409, "ACCOUNT_NOT_SUSPENDED", "Only suspended accounts can appeal");
        }

        const submittedAt = this.now().toISOString();
        const appealId = `appeal-${this.id()}`;
        const receipt = this.#createReceipt({
          actionType: "SUBMIT_APPEAL",
          request: normalized,
          platformState: "SUPPLEMENT_REQUESTED"
        });
        const appeal = {
          appealId,
          caseId: normalized.caseId,
          accountId: normalized.accountId,
          allegationType: normalized.allegationType,
          claimIds: [...normalized.claimIds],
          status: "SUPPLEMENT_REQUESTED",
          requestedSupplement: {
            artifactKind: "DEVICE_LOG",
            requiredFields: [...REQUIRED_DEVICE_LOG_FIELDS],
            template: SUPPLEMENT_TEMPLATE
          },
          submittedAt,
          updatedAt: submittedAt,
          version: 1,
          latestReceiptId: receipt.receiptId
        };
        this.appeals.set(appealId, appeal);

        return {
          receipt,
          appeal: structuredClone(appeal),
          outboundEvent: {
            externalEventId: `event-${this.id()}`,
            type: "SUPPLEMENT_REQUESTED",
            caseId: normalized.caseId,
            accountId: normalized.accountId,
            appealId,
            platformSequence: receipt.platformSequence,
            occurredAt: submittedAt,
            bodyHash: sha256Canonical(appeal.requestedSupplement)
          }
        };
      }
    });
  }

  submitSupplement(appealId, body, idempotencyKey) {
    const appeal = this.appeals.get(appealId);
    if (!appeal) {
      throw new MockDropError(404, "APPEAL_NOT_FOUND", `Appeal ${appealId} was not found`);
    }

    const normalized = {
      artifactSha256: requireString(body?.artifactSha256, "artifactSha256"),
      template: requireString(body?.template, "template"),
      disclosedFields: Array.isArray(body?.disclosedFields) ? body.disclosedFields : []
    };

    return this.#executeIdempotent({
      idempotencyKey,
      actionType: "SUBMIT_SUPPLEMENT",
      request: { appealId, ...normalized },
      execute: () => {
        if (appeal.status !== "SUPPLEMENT_REQUESTED") {
          throw new MockDropError(
            409,
            "INVALID_APPEAL_STATE",
            `Appeal ${appealId} is ${appeal.status}, not SUPPLEMENT_REQUESTED`
          );
        }

        const accepted =
          normalized.artifactSha256 === DEVICE_LOG_SHA256 &&
          normalized.template === SUPPLEMENT_TEMPLATE &&
          sameStringSet(normalized.disclosedFields, REQUIRED_DEVICE_LOG_FIELDS);
        const updatedAt = this.now().toISOString();

        appeal.status = accepted ? "APPROVED" : "REJECTED";
        appeal.decisionReason = accepted
          ? "Device log confirms a cellular-network handoff during a legitimate delivery"
          : "Supplement did not match the requested device-log evidence contract";
        appeal.updatedAt = updatedAt;
        appeal.version += 1;

        const account = this.accounts.get(appeal.accountId);
        if (accepted) {
          account.status = "ACTIVE";
          account.suspensionReason = null;
          account.version += 1;
          account.updatedAt = updatedAt;
        }

        const receipt = this.#createReceipt({
          actionType: "SUBMIT_SUPPLEMENT",
          request: { appealId, ...normalized },
          platformState: appeal.status
        });
        appeal.latestReceiptId = receipt.receiptId;

        return {
          receipt,
          appeal: structuredClone(appeal),
          account: structuredClone(account),
          outboundEvent: {
            externalEventId: `event-${this.id()}`,
            type: accepted ? "DECISION_APPROVED" : "DECISION_REJECTED",
            caseId: appeal.caseId,
            accountId: appeal.accountId,
            appealId,
            platformSequence: receipt.platformSequence,
            occurredAt: updatedAt,
            bodyHash: sha256Canonical({
              status: appeal.status,
              decisionReason: appeal.decisionReason
            })
          }
        };
      }
    });
  }

  #executeIdempotent({ idempotencyKey, actionType, request, execute }) {
    requireString(idempotencyKey, "Idempotency-Key header");
    const requestHash = sha256Canonical({ actionType, request });
    const existing = this.idempotencyRecords.get(idempotencyKey);

    if (existing) {
      if (existing.requestHash !== requestHash) {
        throw new MockDropError(
          409,
          "IDEMPOTENCY_KEY_REUSE",
          "The idempotency key was already used with a different request",
          {
            originalRequestHash: existing.requestHash,
            conflictingRequestHash: requestHash
          }
        );
      }

      return {
        ...structuredClone(existing.response),
        replayed: true
      };
    }

    const response = execute();
    this.idempotencyRecords.set(idempotencyKey, {
      actionType,
      requestHash,
      receipt: response.receipt,
      response: structuredClone(response)
    });

    return {
      ...response,
      replayed: false
    };
  }

  #createReceipt({ actionType, request, platformState }) {
    this.platformSequence += 1;
    const receivedAt = this.now().toISOString();
    const requestBody = canonicalize(request);

    return {
      receiptId: `receipt-${this.id()}`,
      actionType,
      requestHash: sha256Text(requestBody),
      responseHash: sha256Canonical({ platformState, platformSequence: this.platformSequence }),
      platformState,
      platformSequence: this.platformSequence,
      receivedAt
    };
  }
}
