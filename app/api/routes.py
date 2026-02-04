from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from app.api.dependencies import verify_api_key
from app.services import pdf_processor

router = APIRouter()


@router.post("/reports", dependencies=[Depends(verify_api_key)])
async def upload_report(file: UploadFile = File(...)):
    # Validate file extension
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Read bytes and run the full pipeline
    pdf_bytes = await file.read()
    report = pdf_processor.process_report(pdf_bytes, original_filename=file.filename)

    return JSONResponse(content=report, status_code=201)


@router.get("/reports/{report_id}", dependencies=[Depends(verify_api_key)])
async def get_report(report_id: str):
    # Phase 7: call firestore_service and return the report
    raise HTTPException(status_code=501, detail="Not implemented yet")
