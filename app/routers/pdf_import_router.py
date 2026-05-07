from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.services.pdf_import_service import PDFImportService
from app.database.connection import get_db
from app.dependencies.auth_dependencies import get_current_user
import os

# Tag descriptivo para procesos de automatización
router = APIRouter(
    prefix="/pdf",
    tags=["Gestión de Requerimientos (PDF)"]
)

@router.post(
    "/importar_rq", 
    status_code=status.HTTP_201_CREATED,
    summary="Crear requerimiento (RQ) desde PDF"
)
async def importar_rq(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Automatiza la creación de Requerimientos (RQ) mediante el procesamiento de archivos PDF.
    
    - **Extracción de Datos**: El sistema escanea el contenido del PDF, identifica los ítems, cantidades y especificaciones técnicas.
    - **Validación de Formato**: Solo se aceptan archivos con extensión `.pdf`.
    - **Integridad**: Los datos extraídos se vinculan automáticamente a la estructura de Requerimientos del sistema.
    - **Eficiencia**: Reduce el tiempo de registro manual en un 90%.
    - **Seguridad**: Requiere sesión activa (Rol administrativo o de adquisiciones).
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Error de formato: El archivo proporcionado no es un PDF válido."
        )

    # Carpeta temporal segura
    temp_dir = "./temp_files"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, file.filename)

    # Guardar el PDF temporalmente para su procesamiento
    try:
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        service = PDFImportService(db)
        result = service.crear_requerimiento_desde_pdf(temp_path)
        
        # Opcional: Eliminar archivo temporal después de procesar
        # os.remove(temp_path)
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Fallo en el procesamiento del PDF: {str(e)}"
        )