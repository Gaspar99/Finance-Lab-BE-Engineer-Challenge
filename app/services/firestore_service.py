from google.cloud import firestore

from app.config import GCP_PROJECT_ID
from app.utils.exceptions import FirestoreError, ReportNotFoundError

COLLECTION_NAME = "reports"


def create_report(report_data: dict) -> str:
    """Save a report to Firestore. Returns the report ID."""
    try:
        db = firestore.Client(project=GCP_PROJECT_ID)
        doc_ref = db.collection(COLLECTION_NAME).document(report_data["id"])
        doc_ref.set(report_data)
        return report_data["id"]
    except Exception as e:
        raise FirestoreError(f"Failed to save report: {e}")


def get_report(report_id: str) -> dict:
    """Read a report from Firestore by ID. Returns the report as a dict."""
    try:
        db = firestore.Client(project=GCP_PROJECT_ID)
        doc_ref = db.collection(COLLECTION_NAME).document(report_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise ReportNotFoundError(f"Report {report_id} not found")
        return doc.to_dict()
    except ReportNotFoundError:
        raise
    except Exception as e:
        raise FirestoreError(f"Failed to read report {report_id}: {e}")
