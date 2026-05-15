from __future__ import annotations

import pdfplumber
import re
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.rq_model import Requerimiento
from app.models.rq_item_model import RQItem


class PDFImportService:

    # ============================================
    # 1. EXTRAER ÍTEMS POR COLUMNAS REALES
    # ============================================
    def extract_items(self, pdf):
        items = []

        # Columnas reales detectadas por tu OCR
        COL_ITEM = (20, 60)
        COL_CODIGO = (60, 120)
        COL_DESC = (120, 400)
        COL_CANT = (450, 520)
        COL_UM = (520, 600)

        for page in pdf.pages:
            words = page.extract_words()

            # Agrupar palabras por línea (top redondeado)
            lines = {}
            for w in words:
                y = round(w["top"])
                if y not in lines:
                    lines[y] = []
                lines[y].append(w)

            for y in sorted(lines.keys()):
                row_words = lines[y]

                codigo = None
                descripcion = []
                cantidad = None
                unidad = None

                for w in row_words:
                    x = w["x0"]
                    t = w["text"]

                    # CODIGO
                    if COL_CODIGO[0] <= x <= COL_CODIGO[1] and t.startswith("PD"):
                        codigo = t

                    # DESCRIPCION
                    elif COL_DESC[0] <= x <= COL_DESC[1]:
                        descripcion.append(t)

                    # CANTIDAD (solo números REALES)
                    elif COL_CANT[0] <= x <= COL_CANT[1] and re.match(r"^\d+(\.\d+)?$", t):
                        cantidad = float(t)

                    # UNIDAD (solo letras cortas)
                    elif COL_UM[0] <= x <= COL_UM[1] and re.match(r"^[A-Z]{1,5}$", t):
                        unidad = t

                # Validar fila completa
                if codigo and cantidad is not None and unidad:
                    items.append({
                        "codigo": codigo,
                        "descripcion": " ".join(descripcion),
                        "cantidad": cantidad,
                        "unidad": unidad
                    })

        return items

    # ============================================
    # 2. PARSEAR ENCABEZADOS + ÍTEMS
    # ============================================
    def parse_rq_pdf(self, pdf_path: str):
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join([p.extract_text() or "" for p in pdf.pages])

            nro_rq = re.search(r"NRO-(\d+)", text)
            fecha = re.search(r"Fecha Emisión\s*:\s*(\d{2}/\d{2}/\d{4})", text)
            proyecto = re.search(r"Zona o Proyecto\s*:(.*?)\n", text)
            solicitante = re.search(r"Solicitado Por\s*:\s*(.*)", text)

            items = self.extract_items(pdf)

            return {
                "nro_rq": nro_rq.group(1) if nro_rq else None,
                "fecha_emision": datetime.strptime(fecha.group(1), "%d/%m/%Y"),
                "proyecto": proyecto.group(1).strip() if proyecto else "Desconocido",
                "solicitante": solicitante.group(1).strip() if solicitante else "Desconocido",
                "items": items
            }

    # ============================================
    # 3. GUARDAR EN BASE DE DATOS
    # ============================================
    def __init__(self, db: Session):
        self.db = db

    def crear_requerimiento_desde_pdf(self, pdf_path: str):
        data = self.parse_rq_pdf(pdf_path)

        rq = Requerimiento(
            nro_rq=f"NRO-{data['nro_rq']}",
            proyecto=data["proyecto"],
            solicitante=data["solicitante"],
            fecha_emision=data["fecha_emision"]
        )
        self.db.add(rq)
        self.db.commit()
        self.db.refresh(rq)

        for item in data["items"]:
            rq_item = RQItem(
                rq_id=rq.id,
                codigo=item["codigo"],
                descripcion=item["descripcion"],
                cantidad=item["cantidad"],
                unidad=item["unidad"]
            )
            self.db.add(rq_item)

        self.db.commit()

        return {
            "message": f"Requerimiento {rq.nro_rq} importado con {len(data['items'])} ítems",
            "rq_id": rq.id
        }
