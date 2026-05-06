from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.pdf_import_service import PDFImportService
from app.database.connection import get_db
from app.dependencies.auth_dependencies import get_current_user
import os

router = APIRouter(
    prefix="/pdf",
    tags=["Importación PDF"],
    #dependencies=[Depends(get_current_user)]  # 🔐 SEGURIDAD GLOBAL
)

@router.post("/importar_rq")
async def importar_rq(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    # Carpeta temporal dentro del proyecto
    temp_dir = "./temp_files"
    os.makedirs(temp_dir, exist_ok=True)

    temp_path = os.path.join(temp_dir, file.filename)

    # Guardar el PDF
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    service = PDFImportService(db)
    try:
        result = service.crear_requerimiento_desde_pdf(temp_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
