from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User
from app.schemas.rq_campo import FirmaEnvioRequest, ReenvioRqRequest, RqCampoCreate, RqCampoResponse, RqCampoUpdate, RqItemGestionRequest
from app.services.rq_campo_pdf_service import generar_pdf
from app.services.rq_campo_service import EnvioRqError, RqCampoService


router = APIRouter(prefix="/rq-campo", tags=["RQ Campo"])


def _ejecutar(accion):
    try:
        return accion()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except EnvioRqError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("", response_model=RqCampoResponse, status_code=status.HTTP_201_CREATED)
def crear(datos: RqCampoCreate, db: Session = Depends(get_db), usuario: User = Depends(get_current_user)):
    return _ejecutar(lambda: RqCampoService.crear(db, datos, usuario))


@router.get("", response_model=list[RqCampoResponse])
def listar(db: Session = Depends(get_db), usuario: User = Depends(get_current_user)):
    return RqCampoService.listar(db, usuario)


@router.get("/{rq_id}", response_model=RqCampoResponse)
def obtener(rq_id: int, db: Session = Depends(get_db), usuario: User = Depends(get_current_user)):
    return _ejecutar(lambda: RqCampoService._obtener(db, rq_id, usuario))


@router.put("/{rq_id}", response_model=RqCampoResponse)
def actualizar(rq_id: int, datos: RqCampoUpdate, db: Session = Depends(get_db), usuario: User = Depends(get_current_user)):
    return _ejecutar(lambda: RqCampoService.actualizar(db, rq_id, datos, usuario))


@router.delete("/{rq_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(rq_id: int, db: Session = Depends(get_db), usuario: User = Depends(get_current_user)):
    _ejecutar(lambda: RqCampoService.eliminar(db, rq_id, usuario))


@router.post("/{rq_id}/firmar-y-enviar", response_model=RqCampoResponse)
def firmar_y_enviar(rq_id: int, datos: FirmaEnvioRequest, db: Session = Depends(get_db), usuario: User = Depends(get_current_user)):
    correos = [str(correo) for correo in datos.destinatarios] if datos.destinatarios else None
    return _ejecutar(lambda: RqCampoService.firmar_y_enviar(db, rq_id, datos.firma_base64, correos, usuario))


@router.post("/{rq_id}/reenviar", response_model=RqCampoResponse)
def reenviar(rq_id: int, datos: ReenvioRqRequest, db: Session = Depends(get_db), usuario: User = Depends(get_current_user)):
    correos = [str(correo) for correo in datos.destinatarios] if datos.destinatarios else None
    return _ejecutar(lambda: RqCampoService.reenviar(db, rq_id, correos, usuario))


@router.get("/{rq_id}/pdf")
def descargar_pdf(rq_id: int, db: Session = Depends(get_db), usuario: User = Depends(get_current_user)):
    rq = _ejecutar(lambda: RqCampoService._obtener(db, rq_id, usuario))
    contenido = _ejecutar(lambda: generar_pdf(rq))
    return StreamingResponse(
        io.BytesIO(contenido), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{rq.numero}.pdf"'},
    )


@router.get("/{rq_id}/stock")
def revisar_stock(rq_id: int, db: Session = Depends(get_db), usuario: User = Depends(get_current_user)):
    rq = _ejecutar(lambda: RqCampoService._obtener(db, rq_id, usuario))
    resultado = []
    for item in rq.items:
        articulo = item.articulo
        stock = articulo.stock_actual if articulo and articulo.activo else 0
        resultado.append({
            "item_id": item.id, "numero_item": item.numero_item, "nombre": item.nombre_producto,
            "cantidad": item.cantidad, "unidad": item.unidad_medida,
            "stock_actual": stock, "faltante": max(0, item.cantidad - stock),
            "catalogado": articulo is not None,
        })
    return resultado


@router.patch("/{rq_id}/items/{item_id}/gestion", response_model=RqCampoResponse)
def gestionar_item(rq_id: int, item_id: int, datos: RqItemGestionRequest,
                   db: Session = Depends(get_db), usuario: User = Depends(get_current_user)):
    return _ejecutar(lambda: RqCampoService.gestionar_item(db, rq_id, item_id, datos, usuario))
