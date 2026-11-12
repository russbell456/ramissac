from sqlalchemy.orm import Session
from app.models.almacen_obras import AlmacenObra


class AlmacenObraRepository:
    def __init__(self, db: Session):
        self.db = db

    def crear_obra(self, obra: AlmacenObra):
        self.db.add(obra)
        self.db.commit()
        self.db.refresh(obra)
        return obra

    def obtener_todas(self):
        return self.db.query(AlmacenObra).all()

    def obtener_por_id(self, obra_id: int):
        return self.db.query(AlmacenObra).filter(AlmacenObra.id == obra_id).first()
