import os
import shutil
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.staticfiles import StaticFiles

from app.auth import get_current_active_user
from app.config import UPLOAD_DIR
from app.models import User
from app.database import get_session

router = APIRouter(prefix="/media", tags=["media"])


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...), current_user: User = Depends(get_current_active_user), session: Session = Depends(get_session)):
    filename = f"{uuid4().hex}_{file.filename}"
    file_location = os.path.join(UPLOAD_DIR, filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    url = f"/uploads/{filename}"
    return {"image_url": url}
