from sqlalchemy.orm import Session

from app.models.almacen_auditoria import (
    AlmacenAuditoria
)


class AuditoriaService:

    def __init__(
        self,
        db: Session
    ):
        self.db = db

    def registrar(
        self,
        usuario_id: int,
        accion: str,
        entidad: str,
        entidad_id: int,
        descripcion: str
    ):

        auditoria = (
            AlmacenAuditoria(
                usuario_id=usuario_id,
                accion=accion,
                entidad=entidad,
                entidad_id=entidad_id,
                descripcion=descripcion
            )
        )

        self.db.add(
            auditoria
        )

        self.db.commit()