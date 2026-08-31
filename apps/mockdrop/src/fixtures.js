import { sha256Canonical } from "./canonical.js";

export const RIDER_ACCOUNT_ID = "rider-r-2048";
export const SUPPLEMENT_TEMPLATE = "DEVICE_NETWORK_HANDOFF_V1";
export const REQUIRED_DEVICE_LOG_FIELDS = Object.freeze([
  "occurredAt",
  "networkFrom",
  "networkTo",
  "reason"
]);

export const DEVICE_LOG_FIXTURE = Object.freeze({
  deviceId: "mock-device-r-2048",
  occurredAt: "2026-08-18T02:17:00.000Z",
  networkFrom: "5G",
  networkTo: "LTE",
  reason: "CELLULAR_HANDOFF"
});

export const DEVICE_LOG_SHA256 = sha256Canonical(DEVICE_LOG_FIXTURE);
