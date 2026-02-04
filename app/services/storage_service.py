from datetime import timedelta

import google.auth
from google.auth import impersonated_credentials
from google.cloud import storage

from app.config import GCP_PROJECT_ID, GCS_BUCKET_NAME
from app.utils.exceptions import StorageError

SERVICE_ACCOUNT_EMAIL = f"cloud-run-app@{GCP_PROJECT_ID}.iam.gserviceaccount.com"

_SCOPES = ["https://www.googleapis.com/auth/devstorage.read_only"]


def _signing_credentials() -> impersonated_credentials.Credentials:
    base_creds, _ = google.auth.default()
    return impersonated_credentials.Credentials(
        source_credentials=base_creds,
        target_principal=SERVICE_ACCOUNT_EMAIL,
        target_scopes=_SCOPES,
    )


def upload_image(image_bytes: bytes, filename: str) -> str:
    """Upload an image to GCS and return the object name."""
    try:
        client = storage.Client(project=GCP_PROJECT_ID)
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type="image/jpeg")
        return filename
    except Exception as e:
        raise StorageError(f"Failed to upload {filename}: {e}")


def generate_signed_url(filename: str, expiration_minutes: int = 15) -> str:
    """Generate a signed URL for an object in the GCS bucket."""
    try:
        client = storage.Client(project=GCP_PROJECT_ID)
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        url = blob.generate_signed_url(
            expiration=timedelta(minutes=expiration_minutes),
            method="GET",
            credentials=_signing_credentials(),
        )
        return url
    except Exception as e:
        raise StorageError(f"Failed to generate signed URL for {filename}: {e}")
