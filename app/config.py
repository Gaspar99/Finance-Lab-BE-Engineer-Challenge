import os
from dotenv import load_dotenv
from google.cloud import secretmanager

load_dotenv()

# --- Env vars (set locally in .env, set in Cloud Run config in production) ---

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
FIRESTORE_DATABASE = os.getenv("FIRESTORE_DATABASE", "(default)")
SECRET_NAME = os.getenv("SECRET_NAME", "api-key")
DOCUMENT_AI_PROCESSOR_ID = os.getenv("DOCUMENT_AI_PROCESSOR_ID")


# --- Secret Manager ---

def get_api_key() -> str:
    """Read the API key from Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    secret_version = f"projects/{GCP_PROJECT_ID}/secrets/{SECRET_NAME}/versions/latest"
    response = client.access_secret_version(request={"name": secret_version})
    return response.payload.data.decode("UTF-8")
