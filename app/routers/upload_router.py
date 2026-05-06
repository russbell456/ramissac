from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pathlib import Path
import shutil
import uuid

from app.dependencies.auth_dependencies import get_current_user

router = APIRouter(
    prefix="/uploads",
    tags=["Uploads"],
    #dependencies=[Depends(get_current_user)]  # 🔐 SEGURIDAD GLOBAL
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads" / "comprobantes"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/comprobantes")
def subir_comprobante(
    file: UploadFile = File(...)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Archivo inválido")

    ext = Path(file.filename).suffix
    filename = f"{uuid.uuid4()}{ext}"
    file_path = UPLOAD_DIR / filename

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "archivo_ruta": f"/uploads/comprobantes/{filename}"
    }
