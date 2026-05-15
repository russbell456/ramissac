from __future__ import annotations

import os
import shutil
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from datetime import date

from app.models.orden_compra_model import OrdenCompraComprobante
from app.core.config import BASE_UPLOAD_DIR


class ComprobanteService:

    def __init__(self, db: Session):
        self.db = db

    def subir_comprobante(
        self,
        orden_id: int,
        file: UploadFile,
        tipo_documento: str,
        numero_comprobante: str | None,
        es_factura: bool | None,
        fecha: date | None
    ):
        # 📂 carpeta por OC
        carpeta_oc = os.path.join(BASE_UPLOAD_DIR, f"OC_{orden_id}")
        os.makedirs(carpeta_oc, exist_ok=True)

        # 📄 nombre único por tipo
        extension = os.path.splitext(file.filename)[1]
        nombre_archivo = f"{tipo_documento}{extension}"
        ruta_archivo = os.path.join(carpeta_oc, nombre_archivo)

        # 🔒 BUSCAR SI YA EXISTE ESE TIPO
        existente = (
            self.db.query(OrdenCompraComprobante)
            .filter(
                OrdenCompraComprobante.orden_compra_id == orden_id,
                OrdenCompraComprobante.tipo_documento == tipo_documento
            )
            .first()
        )

        # 🔥 SI EXISTE → SE REEMPLAZA
        if existente:
            if os.path.exists(existente.archivo_ruta):
                os.remove(existente.archivo_ruta)

            comprobante = existente
        else:
            comprobante = OrdenCompraComprobante(
                orden_compra_id=orden_id,
                tipo_documento=tipo_documento
            )
            self.db.add(comprobante)

        # 💾 GUARDAR ARCHIVO
        with open(ruta_archivo, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 🧾 ACTUALIZAR DATA
        comprobante.archivo_ruta = ruta_archivo
        comprobante.numero_comprobante = numero_comprobante
        comprobante.es_factura = es_factura
        comprobante.fecha = fecha

        self.db.commit()
        self.db.refresh(comprobante)

        return comprobante
