"""Cloudflare R2 (S3-compatible) client for the Living Library upload path.

R2 holds ONLY the transient original upload: the browser PUTs the file straight to the
bucket via a presigned URL (off the app server), the extraction job fetches it, extracts
text into the private tier-1 vault, then deletes it. R2 is never on a read path — an
outage blocks new uploads only, never reading the library.

Config (env / Fly secrets): R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
R2_BUCKET. Absent → uploads disabled (configured() is False). boto3 is synchronous, so
the network calls are exposed as async wrappers that run in a thread.
"""
from __future__ import annotations

import asyncio
import logging
import os

logger = logging.getLogger("study-bible-web.r2")

_client = None
_REQUIRED = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY")


def _bucket() -> str:
    return os.environ.get("R2_BUCKET") or os.environ.get("R2_BUCKET_NAME") or ""


def configured() -> bool:
    return all(os.environ.get(k) for k in _REQUIRED) and bool(_bucket())


def _get_client():
    global _client
    if _client is None:
        import boto3
        from botocore.config import Config

        acct = os.environ["R2_ACCOUNT_ID"]
        _client = boto3.client(
            "s3",
            endpoint_url=f"https://{acct}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            region_name="auto",
            config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
        )
    return _client


def presign_put(object_key: str, content_type: str, expires: int = 600) -> str:
    """A presigned PUT URL for a direct browser→bucket upload (no network here)."""
    return _get_client().generate_presigned_url(
        "put_object",
        Params={"Bucket": _bucket(), "Key": object_key, "ContentType": content_type},
        ExpiresIn=expires,
    )


def presign_get(object_key: str, expires: int = 600) -> str:
    """A presigned GET URL, so an outside service can read one private object for a short time."""
    return _get_client().generate_presigned_url(
        "get_object", Params={"Bucket": _bucket(), "Key": object_key}, ExpiresIn=expires)


def _head(object_key: str) -> dict | None:
    try:
        r = _get_client().head_object(Bucket=_bucket(), Key=object_key)
        return {"size": r.get("ContentLength"), "content_type": r.get("ContentType")}
    except Exception:  # noqa: BLE001
        return None


def _put_bytes(object_key: str, data: bytes, content_type: str) -> None:
    _get_client().put_object(
        Bucket=_bucket(), Key=object_key, Body=data, ContentType=content_type,
        CacheControl="public, max-age=31536000, immutable",
    )


async def put_bytes_async(object_key: str, data: bytes, content_type: str) -> None:
    """Store bytes durably (used to snapshot cover art so it survives the source link rotting)."""
    await asyncio.to_thread(_put_bytes, object_key, data, content_type)


def _upload_file(object_key: str, local_path: str, content_type: str, callback=None) -> None:
    # boto3 upload_file is multipart + streams from disk, so a multi-GB file never loads into RAM.
    _get_client().upload_file(local_path, _bucket(), object_key,
                              ExtraArgs={"ContentType": content_type}, Callback=callback)


async def upload_file_async(object_key: str, local_path: str,
                            content_type: str = "application/octet-stream", callback=None) -> None:
    await asyncio.to_thread(_upload_file, object_key, local_path, content_type, callback)


def _download_file(object_key: str, local_path: str) -> None:
    _get_client().download_file(_bucket(), object_key, local_path)  # streams to disk, low memory


async def download_file_async(object_key: str, local_path: str) -> None:
    await asyncio.to_thread(_download_file, object_key, local_path)


def _get_object(object_key: str):
    try:
        r = _get_client().get_object(Bucket=_bucket(), Key=object_key)
        return r["Body"].read(), (r.get("ContentType") or "image/jpeg")
    except Exception:  # noqa: BLE001
        return None


async def get_object_async(object_key: str):
    """Return (bytes, content_type) for a stored object, or None."""
    return await asyncio.to_thread(_get_object, object_key)


def _get_bytes(object_key: str) -> bytes | None:
    try:
        r = _get_client().get_object(Bucket=_bucket(), Key=object_key)
        return r["Body"].read()
    except Exception:  # noqa: BLE001
        logger.exception("r2 get failed")
        return None


def _delete(object_key: str) -> None:
    try:
        _get_client().delete_object(Bucket=_bucket(), Key=object_key)
    except Exception:  # noqa: BLE001
        logger.exception("r2 delete failed")


async def head_async(object_key: str) -> dict | None:
    return await asyncio.to_thread(_head, object_key)


async def get_bytes_async(object_key: str) -> bytes | None:
    return await asyncio.to_thread(_get_bytes, object_key)


async def delete_async(object_key: str) -> None:
    await asyncio.to_thread(_delete, object_key)


def _delete_prefix(prefix: str) -> int:
    """Delete every object under `prefix`; returns how many. Raises on failure, so account
    deletion can stop before it removes the database rows that point here."""
    client, bucket, n = _get_client(), _bucket(), 0
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        keys = [{"Key": o["Key"]} for o in page.get("Contents") or []]
        if keys:
            client.delete_objects(Bucket=bucket, Delete={"Objects": keys, "Quiet": True})
            n += len(keys)
    return n


async def delete_prefix_async(prefix: str) -> int:
    if not prefix or not prefix.endswith("/"):
        raise ValueError("prefix must name a folder")
    return await asyncio.to_thread(_delete_prefix, prefix)
