"""Storage abstraction layer with MinIO and local filesystem implementations."""

import os
from datetime import timedelta
from pathlib import Path
from typing import Protocol

from minio import Minio
from minio.error import S3Error

from backend.core.config import settings


class StorageProtocol(Protocol):
    """Protocol defining storage interface."""

    def upload_file(self, key: str, data: bytes, content_type: str) -> None:
        """
        Upload file to storage.

        Args:
            key: Storage key/path for the file
            data: File content as bytes
            content_type: MIME type of the file
        """
        ...

    def download_file(self, key: str) -> bytes:
        """
        Download file from storage.

        Args:
            key: Storage key/path for the file

        Returns:
            File content as bytes
        """
        ...

    def generate_presigned_url(self, key: str, expiry_seconds: int = 3600) -> str:
        """
        Generate presigned URL for file access.

        Args:
            key: Storage key/path for the file
            expiry_seconds: URL expiry time in seconds

        Returns:
            Presigned URL string
        """
        ...


class MinIOStorageClient:
    """MinIO/S3-compatible storage client."""

    def __init__(self) -> None:
        """Initialize MinIO client from settings."""
        # Internal client for uploads/downloads (uses Docker internal hostname)
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self.bucket = settings.MINIO_BUCKET
        self._ensure_bucket_exists()

        # Separate client for presigned URLs — signs against the PUBLIC endpoint
        # (localhost:9000) so the browser can use the URL directly.
        # The HMAC signature includes the hostname, so we must sign with the
        # same hostname the browser will use — rewriting after signing breaks it.
        # We pre-cache the region to avoid a network call to localhost:9000
        # (which isn't reachable from inside Docker).
        public_endpoint = settings.MINIO_PUBLIC_ENDPOINT or settings.MINIO_ENDPOINT
        self._presign_client = Minio(
            public_endpoint,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        # Pre-populate region cache so presigned_get_object doesn't make a
        # network request to localhost:9000 (unreachable from inside Docker)
        self._presign_client._region_map[self.bucket] = "us-east-1"

    def _ensure_bucket_exists(self) -> None:
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error as e:
            if e.code == "BucketAlreadyOwnedByYou":
                pass  # bucket already exists, that's fine
            else:
                raise RuntimeError(f"Failed to ensure bucket exists: {e}")

    def upload_file(self, key: str, data: bytes, content_type: str) -> None:
        """Upload file to MinIO."""
        from io import BytesIO

        try:
            self.client.put_object(
                self.bucket,
                key,
                BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
        except S3Error as e:
            raise RuntimeError(f"Failed to upload file to MinIO: {e}")

    def download_file(self, key: str) -> bytes:
        """Download file from MinIO."""
        try:
            response = self.client.get_object(self.bucket, key)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            raise RuntimeError(f"Failed to download file from MinIO: {e}")

    def generate_presigned_url(self, key: str, expiry_seconds: int = 3600) -> str:
        """Generate presigned URL signed against the public endpoint.

        Uses _presign_client (localhost:9000) so the HMAC signature matches
        the hostname the browser sends in the request.
        """
        try:
            return self._presign_client.presigned_get_object(
                self.bucket, key, expires=timedelta(seconds=expiry_seconds)
            )
        except S3Error as e:
            raise RuntimeError(f"Failed to generate presigned URL: {e}")


class LocalStorageClient:
    """Local filesystem storage client."""

    def __init__(self) -> None:
        """Initialize local storage client from settings."""
        self.storage_path = Path(settings.LOCAL_STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def upload_file(self, key: str, data: bytes, content_type: str) -> None:
        """Upload file to local filesystem."""
        file_path = self.storage_path / key
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, "wb") as f:
                f.write(data)
        except OSError as e:
            raise RuntimeError(f"Failed to write file to local storage: {e}")

    def download_file(self, key: str) -> bytes:
        """Download file from local filesystem."""
        file_path = self.storage_path / key

        try:
            with open(file_path, "rb") as f:
                return f.read()
        except OSError as e:
            raise RuntimeError(f"Failed to read file from local storage: {e}")

    def generate_presigned_url(self, key: str, expiry_seconds: int = 3600) -> str:
        """
        Generate URL for local file access.

        Note: For local storage, this returns a path that should be served
        by FastAPI static files endpoint.
        """
        # Return a path that will be served by FastAPI
        return f"/files/{key}"


def get_storage_client() -> StorageProtocol:
    """
    Factory function to get storage client based on configuration.

    Returns:
        Storage client instance (MinIO or Local)
    """
    if settings.STORAGE_BACKEND == "minio":
        return MinIOStorageClient()
    elif settings.STORAGE_BACKEND == "local":
        return LocalStorageClient()
    else:
        raise ValueError(
            f"Invalid STORAGE_BACKEND: {settings.STORAGE_BACKEND}. "
            "Must be 'minio' or 'local'."
        )


# Global storage client instance
storage_client = get_storage_client()