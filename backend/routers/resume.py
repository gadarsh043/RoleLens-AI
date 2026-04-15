from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from services.rag_service import get_rag_service
from services.session import get_session_id

router = APIRouter()


@router.get("/status")
async def resume_status(session_id: str = Depends(get_session_id)):
    rag_service = get_rag_service()
    rag_service.prepare_session(session_id)
    return rag_service.get_resume_status(session_id)


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    session_id: str = Depends(get_session_id),
):
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
    rag_service.prepare_session(session_id)
    try:
        result = rag_service.index_resume(session_id, file.filename or "resume.pdf", contents)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return result
