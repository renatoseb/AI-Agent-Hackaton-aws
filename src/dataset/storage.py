"""Abstraction layer for writing raw and curated data either locally or to S3.

If the destination root starts with s3:// we use boto3. Otherwise we write to local filesystem.
"""
from __future__ import annotations

import io
import json
import os
import pathlib
import tempfile
from typing import Any, Iterable

import pandas as pd

try:
    import boto3  # type: ignore
    from botocore.exceptions import ClientError  # type: ignore
except Exception:  # pragma: no cover - boto3 may not be installed in minimal env
    boto3 = None  # type: ignore
    ClientError = Exception  # type: ignore


def is_s3(path: str) -> bool:
    return path.startswith("s3://")


def split_s3_uri(uri: str):
    # s3://bucket/key
    without = uri[5:]
    bucket, _, key = without.partition("/")
    return bucket, key


def ensure_local_dir(path: str):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)


def write_json_lines(records: Iterable[dict], dest_uri: str):
    if is_s3(dest_uri):
        if not boto3:
            raise RuntimeError("boto3 not available to write to S3")
        bucket, key = split_s3_uri(dest_uri)
        body = io.BytesIO()
        for rec in records:
            body.write(json.dumps(rec, ensure_ascii=False).encode("utf-8"))
            body.write(b"\n")
        body.seek(0)
        boto3.client("s3").upload_fileobj(body, bucket, key)
    else:
        ensure_local_dir(os.path.dirname(dest_uri))
        with open(dest_uri, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False))
                f.write("\n")


def write_parquet(df: pd.DataFrame, dest_uri: str):
    if is_s3(dest_uri):
        if not boto3:
            raise RuntimeError("boto3 not available to write to S3")
        bucket, key = split_s3_uri(dest_uri)
        with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
            df.to_parquet(tmp.name, index=False)
            boto3.client("s3").upload_file(tmp.name, bucket, key)
    else:
        ensure_local_dir(os.path.dirname(dest_uri))
        df.to_parquet(dest_uri, index=False)


def read_state(state_root: str, filename: str) -> dict | None:
    path = os.path.join(state_root, filename)
    if is_s3(state_root):  # state_root includes bucket prefix path part
        if not boto3:
            return None
        bucket, key_prefix = split_s3_uri(state_root)
        key = f"{key_prefix.rstrip('/')}/{filename}" if key_prefix else filename
        try:
            obj = boto3.client("s3").get_object(Bucket=bucket, Key=key)
        except ClientError:
            return None
        return json.loads(obj["Body"].read())
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_state(state_root: str, filename: str, data: dict):
    if is_s3(state_root):
        if not boto3:
            raise RuntimeError("boto3 not available to write to S3")
        bucket, key_prefix = split_s3_uri(state_root)
        key = f"{key_prefix.rstrip('/')}/{filename}" if key_prefix else filename
        boto3.client("s3").put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(data).encode("utf-8"),
            ContentType="application/json",
        )
        return
    ensure_local_dir(state_root)
    with open(os.path.join(state_root, filename), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)