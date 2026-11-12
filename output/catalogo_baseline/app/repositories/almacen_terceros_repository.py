from sqlalchemy.orm import Session
from app.models.almacen_terceros import AlmacenTercero


class AlmacenTerceroRepository:
    def __init__(self, db: Session):
        self.db = db

    def crear_tercero(self, tercero: AlmacenTercero):
        self.db.add(tercero)
        self.db.commit()
        self.db.refresh(tercero)
        return tercero

    def obtener_todos(self):
        return self.db.query(AlmacenTercero).all()

    def obtener_por_id(self, tercero_id: int):
        return self.db.query(AlmacenTercero).filter(AlmacenTercero.id == tercero_id).first()
