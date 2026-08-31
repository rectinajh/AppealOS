#!/usr/bin/env python3
"""Seed the AppealOS Evidence Vault in Cloud Storage + Secret Manager.

Creates the demo AES-256 key in Secret Manager if it does not already exist,
then uploads the three synthetic evidence fixtures as AES-256-GCM ciphertext
to the configured Cloud Storage bucket.  This script never prints the key.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from google.api_core import exceptions as api_exceptions  # type: ignore
from google.cloud import secretmanager  # type: ignore

from app.vault import (
    EVIDENCE_BUCKET,
    EVIDENCE_CASE_ID,
    EVIDENCE_SECRET,
    GcsEvidenceVault,
)


def ensure_demo_key(project: str, secret_name: str) -> bytes:
    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{project}"
    secret_path = f"projects/{project}/secrets/{secret_name}"

    try:
        client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_name,
                "secret": {
                    "replication": {"automatic": {}},
                    "labels": {
                        "purpose": "appealos-evidence-vault-demo",
                        "synthetic": "true",
                        "server-decryptable": "true",
                    },
                },
            }
        )
        print(f"Created Secret Manager secret: {secret_name}")
    except api_exceptions.AlreadyExists:
        print(f"Reusing existing Secret Manager secret: {secret_name}")

    try:
        response = client.access_secret_version(
            request={"name": f"{secret_path}/versions/latest"}
        )
        print("Reusing existing demo key version")
        return response.payload.data
    except api_exceptions.NotFound:
        pass

    key = os.urandom(32)
    client.add_secret_version(
        request={
            "parent": secret_path,
            "payload": {"data": key},
        }
    )
    print(f"Created new demo key version in {secret_name}")
    return key


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT", "boxwood-scope-364905"))
    parser.add_argument("--bucket", default=EVIDENCE_BUCKET)
    parser.add_argument("--secret", default=EVIDENCE_SECRET)
    args = parser.parse_args()

    os.environ["GOOGLE_CLOUD_PROJECT"] = args.project
    key = ensure_demo_key(args.project, args.secret)

    vault = GcsEvidenceVault(bucket=args.bucket, secret=args.secret)
    # Make the bucket deterministic by touching it through the storage client.
    bucket = vault._storage().bucket(args.bucket)
    if not bucket.exists():
        bucket.create()
        print(f"Created Cloud Storage bucket: gs://{args.bucket}")
    else:
        print(f"Reusing Cloud Storage bucket: gs://{args.bucket}")

    for artifact_id in ["delivery-receipt", "gps-trace", "device-log"]:
        public = vault.upload_artifact(artifact_id, key=key)
        print(
            f"Uploaded {artifact_id} -> {public['storageUri']} "
            f"plaintextSha256={public['plaintextSha256'][:12]}... "
            f"ciphertextSha256={public['ciphertextSha256'][:12]}..."
        )

    print(f"Evidence Vault seeded: caseId={EVIDENCE_CASE_ID}, bucket={args.bucket}, secret={args.secret}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
