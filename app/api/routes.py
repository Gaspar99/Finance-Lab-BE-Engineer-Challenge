from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from app.api.dependencies import verify_api_key

router = APIRouter()


@router.post("/reports", dependencies=[Depends(verify_api_key)])
async def upload_report(file: UploadFile = File(...)):
    # Phase 7: call pdf_processor and return the report
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/reports/{report_id}", dependencies=[Depends(verify_api_key)])
async def get_report(report_id: str):
    # Phase 7: call firestore_service and return the report
    raise HTTPException(status_code=501, detail="Not implemented yet")
