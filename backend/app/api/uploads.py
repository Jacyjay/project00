from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.services.image_upload import prepare_uploaded_image, media_type_for_extension

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post("/normalize-image")
async def normalize_image(file: UploadFile = File(...)):
    try:
        content = await file.read()
        normalized_bytes, extension = prepare_uploaded_image(file.filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return Response(
        content=normalized_bytes,
        media_type=media_type_for_extension(extension),
        headers={
            "X-Normalized-Extension": extension,
        },
    )
