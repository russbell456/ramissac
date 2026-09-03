from sqlalchemy.orm import Session
from app.models.almacen_terceros import AlmacenTercero
from app.repositories.almacen_terceros_repository import AlmacenTerceroRepository


class AlmacenTercerosService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AlmacenTerceroRepository(db)

    def crear_tercero(self, data: dict):
        tercero = AlmacenTercero(
            tipo=data.get("tipo", "empresa"),
            ruc=data.get("ruc"),
            dni=data.get("dni"),
            nombres=data.get("nombres"),
            empresa_nombre=data.get("empresa_nombre"),
            telefono=data.get("telefono"),
            email=data.get("email"),
            direccion=data.get("direccion"),
            observaciones=data.get("observaciones")
        )
        return self.repo.crear_tercero(tercero)

    def listar(self):
        return self.repo.obtener_todos()

    def obtener(self, tercero_id: int):
        return self.repo.obtener_por_id(tercero_id)
