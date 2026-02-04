import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from app.models.report import ReportStatus
from app.services import ocr_service, storage_service, firestore_service
from app.utils.pdf_utils import extract_images, filter_medical_images
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

        # 1. OCR and image extraction run in parallel (both only read pdf_bytes)
        with ThreadPoolExecutor(max_workers=2) as pool:
            fields_future = pool.submit(ocr_service.extract_fields, pdf_bytes)
            images_future = pool.submit(extract_images, pdf_bytes)
            fields = fields_future.result()
            raw_images = images_future.result()

        # 2. Filter to keep only medical diagnostic images (parallel classification)
        medical_images = filter_medical_images(raw_images)

        # 3. Upload all medical images to GCS concurrently, then sign URLs
        def _upload_and_sign(filename: str, image_bytes: bytes) -> dict:
            namespaced = f"{report_id}/{filename}"
            storage_service.upload_image(image_bytes, namespaced)
            url = storage_service.generate_signed_url(namespaced)
            return {"filename": filename, "url": url}

        with ThreadPoolExecutor(max_workers=min(len(medical_images), 10) or 1) as pool:
            futures = [pool.submit(_upload_and_sign, fn, data) for fn, data in medical_images]
            images = [f.result() for f in futures]

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
