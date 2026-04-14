from fastapi import APIRouter, File, HTTPException, UploadFile, status

from services.rag_service import get_rag_service

router = APIRouter()


@router.get("/status")
async def resume_status():
    rag_service = get_rag_service()
    return rag_service.get_resume_status()


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF uploads are supported.",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    rag_service = get_rag_service()
    try:
        result = rag_service.index_resume(file.filename or "resume.pdf", contents)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return result
