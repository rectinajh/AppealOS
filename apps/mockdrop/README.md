# MockDrop

MockDrop is the fictional delivery-platform service used to prove that AppealOS can mutate an external system. It is a cooperative simulation, not a real platform integration or independent adjudicator.

## Run locally

From the repository root:

```bash
npm run start:mockdrop
```

The service listens on `http://localhost:8080` by default.

## Verify the state loop

```bash
npm test
```

The integration suite proves:

```text
SUSPENDED
→ SUPPLEMENT_REQUESTED
→ APPROVED
→ ACTIVE
```

It also covers identical-request replay, conflicting idempotency-key reuse, supplement replay, rejected evidence, and receipt recovery.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Health check (Cloud Run compatible) |
| `GET` | `/healthz` | Health check (local compatibility) |
| `POST` | `/v1/demo/reset` | Reset the synthetic rider to `SUSPENDED` |
| `GET` | `/v1/accounts/{accountId}` | Read the rider's external account state |
| `POST` | `/v1/appeals` | Submit the initial appeal |
| `GET` | `/v1/actions/by-idempotency/{key}` | Recover a durable action receipt |
| `POST` | `/v1/appeals/{appealId}/supplements` | Submit the requested device log |
| `GET` | `/v1/appeals/{appealId}` | Read the appeal decision |

Write requests require an `Idempotency-Key` header where applicable. Set `MOCKDROP_API_TOKEN` to require a local bearer token for write routes. Cloud Run OIDC authentication and persistent Firestore storage remain the next infrastructure step.

## Deterministic rule

An initial abnormal-location appeal always requests a device log. A supplement is approved only when it contains:

- the expected synthetic device-log SHA-256;
- template `DEVICE_NETWORK_HANDOFF_V1`;
- exactly the four allowed fields: `occurredAt`, `networkFrom`, `networkTo`, and `reason`.

A valid supplement changes the appeal to `APPROVED` and the rider account to `ACTIVE`. Any other supplement changes the appeal to `REJECTED` and leaves the account suspended.
