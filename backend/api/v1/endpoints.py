import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter(prefix="/v1")

# вынести в конфиги
UPLOAD_DIR = Path("backend/storage")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "text/plain": ".txt",
}


@router.post("/upload_cv")
async def upload_cv(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported {file.content_type}. Upload only *.pdf, *.docx, *.doc, *.txt files",
        )
    extension = ALLOWED_TYPES[file.content_type]
    save_filename = f"{uuid.uuid4()}.{extension}"
    file_path = UPLOAD_DIR / save_filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "original_filename": file.filename,
        "stored_filename": save_filename,
        "content_type": file.content_type,
        "path": str(file_path),
    }
