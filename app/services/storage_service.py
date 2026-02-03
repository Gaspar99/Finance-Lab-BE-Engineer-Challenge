from datetime import timedelta

from google.cloud import storage

from app.config import GCS_BUCKET_NAME
from app.utils.exceptions import StorageError


def upload_image(image_bytes: bytes, filename: str) -> str:
    """Upload an image to GCS and return the object name."""
    try:
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type="image/jpeg")
        return filename
    except Exception as e:
        raise StorageError(f"Failed to upload {filename}: {e}")


def generate_signed_url(filename: str, expiration_minutes: int = 15) -> str:
    """Generate a signed URL for an object in the GCS bucket."""
    try:
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        url = blob.generate_signed_url(
            expiration=timedelta(minutes=expiration_minutes),
            method="GET",
        )
        return url
    except Exception as e:
        raise StorageError(f"Failed to generate signed URL for {filename}: {e}")
