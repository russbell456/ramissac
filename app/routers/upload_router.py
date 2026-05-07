from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from pathlib import Path
import shutil
import uuid

from app.dependencies.auth_dependencies import get_current_user

# Organizamos bajo una etiqueta de infraestructura técnica
router = APIRouter(
    prefix="/uploads",
    tags=["Infraestructura: Archivos"]
)

# Configuración de rutas estáticas
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads" / "comprobantes"

# Aseguramos que la estructura de carpetas exista al iniciar el módulo
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post(
    "/comprobantes", 
    status_code=status.HTTP_201_CREATED,
    summary="Cargar archivo físico al servidor"
)
def subir_comprobante(
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """
    Gestiona el almacenamiento físico de documentos digitales en el servidor de **RamisToolX**.
    
    - **Seguridad de Nombramiento**: El sistema renombra automáticamente cada archivo usando un **UUID (Universally Unique Identifier)** para evitar colisiones de nombres o sobrescritura de datos.
    - **Organización**: Los archivos se clasifican en el directorio de `uploads/comprobantes`.
    - **Persistencia**: Devuelve la ruta relativa del archivo para que pueda ser guardada en la base de datos y vinculada a una Orden de Compra o Requerimiento.
    - **Restricción**: Requiere autenticación de usuario para prevenir el llenado malintencionado del almacenamiento.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Error de archivo: No se ha detectado un nombre de archivo válido."
        )

    # Procesamiento del archivo
    ext = Path(file.filename).suffix
    if not ext:
        # Por seguridad, si no tiene extensión, podrías forzar una o rechazarlo
        ext = ".bin"
        
    filename = f"{uuid.uuid4()}{ext}"
    file_path = UPLOAD_DIR / filename

    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fallo en el sistema de archivos: No se pudo escribir el documento. {str(e)}"
        )

    return {
        "message": "Archivo almacenado correctamente.",
        "archivo_ruta": f"/uploads/comprobantes/{filename}",
        "filename_original": file.filename
    }