from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from app.api.dependencies import verify_api_key
from app.services import pdf_processor, firestore_service, storage_service
from app.utils.exceptions import ReportNotFoundError

router = APIRouter()


@router.post("/reports", dependencies=[Depends(verify_api_key)])
async def upload_report(file: UploadFile = File(...)):

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    pdf_bytes = await file.read()
    report = pdf_processor.process_report(pdf_bytes, original_filename=file.filename)

    return JSONResponse(content=report, status_code=201)


@router.get("/reports/{report_id}", dependencies=[Depends(verify_api_key)])
async def get_report(report_id: str):
    """Retrieve a previously processed report by ID.

    Image URLs are regenerated on each request since signed URLs expire.
    """
    try:
        report = firestore_service.get_report(report_id)

        # Regenerate signed URLs for images (they expire after 15 minutes)
        # Using ThreadPoolExecutor for parallel URL generation
        if report.get("images"):
            def generate_url(image: dict) -> tuple[dict, str]:
                gcs_path = f"{report_id}/{image['filename']}"
                return image, storage_service.generate_signed_url(gcs_path)

            with ThreadPoolExecutor(max_workers=len(report["images"])) as pool:
                results = list(pool.map(generate_url, report["images"]))

            for image, url in results:
                image["url"] = url

        return JSONResponse(content=report)

    except ReportNotFoundError:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
