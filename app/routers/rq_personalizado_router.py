from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, status
import json
import os
import uuid

from app.services.excel_service import ExcelRQService
from app.services.product_service import ProductService
from app.services.mail_service import MailService

from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User

# Definimos una etiqueta que destaque la movilidad del sistema
router = APIRouter(
    prefix="/rq-residente",
    tags=["Operaciones Móviles: Residentes"]
)

# Instanciamos los servicios
excel_service = ExcelRQService()
product_service = ProductService()
mail_service = MailService()

# Asegurar persistencia de directorios
os.makedirs("static/firmas", exist_ok=True)
os.makedirs("static/generados", exist_ok=True)

@router.get(
    "/buscar-productos", 
    summary="Buscador de insumos para App Móvil"
)
async def buscar_productos(q: str = ""):
    """
    Endpoint optimizado para la búsqueda reactiva en la App Móvil.
    
    - **Rendimiento**: Requiere un mínimo de 3 caracteres para activar la búsqueda en la base de datos de productos.
    - **Uso**: El residente busca materiales (cemento, fierro, etc.) para añadirlos al carrito de requerimiento.
    """
    if len(q) < 3:
        return []
    return product_service.search_products(q)

@router.post(
    "/generar", 
    status_code=status.HTTP_201_CREATED,
    summary="Generar y despachar RQ vía Email"
)
async def crear_rq(
    servicio: str = Form(..., description="Nombre del servicio o proyecto"),
    solicitante: str = Form(..., description="Nombre del residente que solicita"),
    user_email: str = Form(..., description="Email de cuenta logueada"),
    fecha: str = Form(..., description="Fecha de la solicitud"),
    productos_json: str = Form(..., description="Lista de productos en formato JSON string"),
    firma: UploadFile = File(..., description="Imagen de la firma digitalizada"),
    user=Depends(get_current_user)
):
    """
    Procesa un requerimiento complejo desde el dispositivo móvil del residente.
    
    **Flujo de Trabajo Automatizado:**
    1. **Firma Digital**: Almacena físicamente la firma capturada en la App.
    2. **Conversión de Datos**: Parsea el JSON de productos enviados por el residente.
    3. **Motor de Excel**: Genera un archivo `.xlsx` profesional basado en el formato oficial de **Ramis SAC**.
    4. **Notificación**: Envía automáticamente el archivo adjunto al departamento de Logística mediante **SMTP**.
    
    - **Seguridad**: Requiere autenticación Bearer Token.
    """
    try:
        # 1. Gestión de la firma
        ext = firma.filename.split(".")[-1] if "." in firma.filename else "png"
        nombre_firma = f"firma_{uuid.uuid4().hex}.{ext}"
        ruta_firma = os.path.join("static/firmas", nombre_firma)

        with open(ruta_firma, "wb") as buffer:
            buffer.write(await firma.read())

        # 2. Validación de datos de productos
        try:
            lista_productos = json.loads(productos_json)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error de formato: El campo 'productos_json' no es un JSON válido."
            )

        # 3. Generación de entregable (Excel)
        ruta_excel = excel_service.generar_archivo(
            {"servicio": servicio, "solicitante": solicitante, "fecha": fecha},
            lista_productos,
            ruta_firma
        )

        # 4. Despacho por correo a Logística
        # Nota: El destinatario se mantiene según configuración de la Corporación.
        mail_service.enviar_requerimiento(
            destinatario="andresmorenochechomoreno1995@gmail.com",
            usuario_email=user_email,
            ruta_adjunto=ruta_excel
        )

        return {
            "status": "success",
            "message": "Operación completada: RQ generado y enviado a Logística.",
            "file_metadata": {
                "path": ruta_excel,
                "download_url": f"/{ruta_excel}"
            }
        }

    except Exception as e:
        print(f"Error crítico en proceso RQ Móvil: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fallo en la automatización: {str(e)}"
        )