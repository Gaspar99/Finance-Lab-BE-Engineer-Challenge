import uuid
from datetime import datetime, timezone

from app.models.report import ReportStatus
from app.services import ocr_service, storage_service, firestore_service
from app.utils.pdf_utils import extract_images
from app.utils.exceptions import InvalidFileError


def process_report(pdf_bytes: bytes, original_filename: str) -> dict:
    """Orchestrate the full pipeline: extract fields + images, upload, persist.

    Returns the saved report dict (same shape as the Firestore document).
    On any extraction/storage failure the report is still saved with status=failed.
    """
    report_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    try:
        if not pdf_bytes:
            raise InvalidFileError("Uploaded file is empty")

        # 1. OCR — extract structured fields from the PDF
        fields = ocr_service.extract_fields(pdf_bytes)

        # 2. Images — pull embedded images out of the PDF
        raw_images = extract_images(pdf_bytes)

        # 3. Storage — upload each image to GCS, collect signed URLs
        images = []
        for filename, image_bytes in raw_images:
            # Namespace filenames under this report so they don't collide
            namespaced = f"{report_id}/{filename}"
            storage_service.upload_image(image_bytes, namespaced)
            url = storage_service.generate_signed_url(namespaced)
            images.append({"filename": filename, "url": url})

        # 4. Assemble the report document
        report_data = {
            "id": report_id,
            "created_at": now,
            "status": ReportStatus.COMPLETED.value,
            "original_filename": original_filename,
            "patient": fields.get("patient"),
            "owner": fields.get("owner"),
            "veterinarian": fields.get("veterinarian"),
            "diagnosis": fields.get("diagnosis"),
            "recommendations": fields.get("recommendations"),
            "images": images,
            "error": None,
        }

    except Exception as e:
        report_data = {
            "id": report_id,
            "created_at": now,
            "status": ReportStatus.FAILED.value,
            "original_filename": original_filename,
            "patient": None,
            "owner": None,
            "veterinarian": None,
            "diagnosis": None,
            "recommendations": None,
            "images": [],
            "error": str(e),
        }

    # 5. Persist — always save, whether completed or failed
    firestore_service.create_report(report_data)

    return report_data
