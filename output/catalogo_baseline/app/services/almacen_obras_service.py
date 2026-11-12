from sqlalchemy.orm import Session
from app.models.almacen_obras import AlmacenObra
from app.repositories.almacen_obras_repository import AlmacenObraRepository


class AlmacenObrasService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AlmacenObraRepository(db)

    def crear_obra(self, nombre: str, descripcion: str | None = None, cliente: str | None = None, ubicacion: str | None = None):
        obra = AlmacenObra(
            nombre=nombre,
            descripcion=descripcion,
            cliente=cliente,
            ubicacion=ubicacion
        )
        return self.repo.crear_obra(obra)

    def listar_obras(self):
        return self.repo.obtener_todas()

    def obtener_obra(self, obra_id: int):
        return self.repo.obtener_por_id(obra_id)
