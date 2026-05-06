from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
import json
import os
import uuid

from app.services.excel_service import ExcelRQService
from app.services.product_service import ProductService
from app.services.mail_service import MailService

from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User


router = APIRouter(
    prefix="/rq-residente",
    tags=["Requerimientos Mobiles"],
    #dependencies=[Depends(get_current_user)]  # 🔐 PROTEGE TODO
)

# Instanciamos los servicios una sola vez
excel_service = ExcelRQService()
product_service = ProductService()
mail_service = MailService()

# Asegurar que las carpetas existan al arrancar
os.makedirs("static/firmas", exist_ok=True)
os.makedirs("static/generados", exist_ok=True)


@router.get("/buscar-productos")
async def buscar_productos(q: str = ""):
    if len(q) < 3:
        return []
    return product_service.search_products(q)


@router.post("/generar")
async def crear_rq(
    servicio: str = Form(...),
    solicitante: str = Form(...),
    user_email: str = Form(...),  # correo del usuario logueado
    fecha: str = Form(...),
    productos_json: str = Form(...),
    firma: UploadFile = File(...)
):
    try:
        # 1. Guardar la firma físicamente
        ext = firma.filename.split(".")[-1] if "." in firma.filename else "png"
        nombre_firma = f"firma_{uuid.uuid4().hex}.{ext}"
        ruta_firma = os.path.join("static/firmas", nombre_firma)

        with open(ruta_firma, "wb") as buffer:
            buffer.write(await firma.read())

        # 2. Parsear productos del JSON de la App
        try:
            lista_productos = json.loads(productos_json)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="El formato de productos_json es inválido"
            )

        # 3. Generar el Excel
        ruta_excel = excel_service.generar_archivo(
            {"servicio": servicio, "solicitante": solicitante, "fecha": fecha},
            lista_productos,
            ruta_firma
        )

        # 4. Enviar por Correo a Logística
        mail_service.enviar_requerimiento(
            destinatario="andresmorenochechomoreno1995@gmail.com",
            usuario_email=user_email,
            ruta_adjunto=ruta_excel
        )

        return {
            "status": "success",
            "message": "Excel generado y enviado a Logística con éxito",
            "path": ruta_excel,
            "download_url": f"/{ruta_excel}"
        }

    except Exception as e:
        print(f"Error en proceso RQ: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )
