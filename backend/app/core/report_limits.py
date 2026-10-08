"""Lightweight bounds shared by PDF export admission and signature validation."""

MAX_SNAPSHOT_PAYLOAD_BYTES = 384 * 1024
MAX_SNAPSHOT_TOKEN_BYTES = 512 * 1024
MAX_SNAPSHOT_BODY_BYTES = MAX_SNAPSHOT_TOKEN_BYTES + 256
