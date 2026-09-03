import os
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.almacen_articulos import (
    TipoArticulo,
)
from app.repositories.almacen_articulo_repository import (
    AlmacenArticuloRepository,
)
from app.services.auditoria_service import (
    AuditoriaService,
)


ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

MAX_IMAGE_SIZE = 5 * 1024 * 1024


class AlmacenArticuloService:

    def __init__(self, db: Session):
        self.db = db
        self.repo = AlmacenArticuloRepository(db)

    def crear_articulo(
        self,
        data: dict,
        usuario_id: int,
    ):
        codigo = data.get("codigo_excel")
        serie = data.get("serie")

        if codigo and self.repo.get_by_codigo(codigo):
            raise ValueError(
                "El código del artículo ya existe"
            )

        if serie and self.repo.get_by_serie(serie):
            raise ValueError(
                "El número de serie ya existe"
            )

        if data["tipo"] == TipoArticulo.EQUIPO:
            data["stock_total"] = 1
            data["stock_actual"] = 1

        articulo = self.repo.create(data)

        AuditoriaService(self.db).registrar(
            usuario_id=usuario_id,
            accion="CREAR",
            entidad="ARTICULO",
            entidad_id=articulo.id,
            descripcion=(
                f"Artículo {articulo.nombre} creado"
            ),
        )

        return articulo

    def obtener_articulo(
        self,
        articulo_id: int,
    ):
        articulo = self.repo.get_by_id(
            articulo_id
        )

        if not articulo:
            raise ValueError(
                "Artículo no encontrado"
            )

        return articulo

    def actualizar_articulo(
        self,
        articulo_id: int,
        data: dict,
        usuario_id: int,
    ):
        articulo = self.obtener_articulo(
            articulo_id
        )

        codigo = data.get("codigo_excel")

        if (
            codigo
            and codigo != articulo.codigo_excel
            and self.repo.get_by_codigo(codigo)
        ):
            raise ValueError(
                "El código del artículo ya existe"
            )

        serie = data.get("serie")

        if (
            serie
            and serie != articulo.serie
            and self.repo.get_by_serie(serie)
        ):
            raise ValueError(
                "El número de serie ya existe"
            )

        articulo = self.repo.update(
            articulo,
            data,
        )

        AuditoriaService(self.db).registrar(
            usuario_id=usuario_id,
            accion="ACTUALIZAR",
            entidad="ARTICULO",
            entidad_id=articulo.id,
            descripcion=(
                f"Artículo {articulo.nombre} actualizado"
            ),
        )

        return articulo

    def desactivar_articulo(
        self,
        articulo_id: int,
        usuario_id: int,
    ):
        articulo = self.obtener_articulo(
            articulo_id
        )

        if not articulo.activo:
            raise ValueError(
                "El artículo ya está inactivo"
            )

        if articulo.en_prestamo > 0:
            raise ValueError(
                "No se puede desactivar un artículo "
                "que está en préstamo"
            )

        articulo = self.repo.deactivate(
            articulo
        )

        AuditoriaService(self.db).registrar(
            usuario_id=usuario_id,
            accion="DESACTIVAR",
            entidad="ARTICULO",
            entidad_id=articulo.id,
            descripcion=(
                f"Artículo {articulo.nombre} desactivado"
            ),
        )

        return articulo

    def activar_articulo(
        self,
        articulo_id: int,
        usuario_id: int,
    ):
        articulo = self.obtener_articulo(
            articulo_id
        )

        if articulo.activo:
            raise ValueError(
                "El artículo ya está activo"
            )

        articulo = self.repo.activate(
            articulo
        )

        AuditoriaService(self.db).registrar(
            usuario_id=usuario_id,
            accion="ACTIVAR",
            entidad="ARTICULO",
            entidad_id=articulo.id,
            descripcion=(
                f"Artículo {articulo.nombre} activado"
            ),
        )

        return articulo

    def buscar_articulos(
        self,
        termino: str,
    ):
        if len(termino.strip()) < 2:
            return self.repo.get_all_disponibles()

        return self.repo.search(
            termino.strip()
        )

    async def guardar_imagen(
        self,
        articulo_id: int,
        file: UploadFile,
        usuario_id: int,
    ):
        self.obtener_articulo(articulo_id)

        extension = ALLOWED_IMAGE_TYPES.get(
            file.content_type
        )

        if not extension:
            raise ValueError(
                "Formato de imagen no permitido. "
                "Use JPG, PNG o WEBP"
            )

        content = await file.read()

        if len(content) > MAX_IMAGE_SIZE:
            raise ValueError(
                "La imagen no puede superar los 5 MB"
            )

        directory = Path(
            "uploads/articulos"
        )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        filename = (
            f"{uuid.uuid4().hex}"
            f"{extension}"
        )

        filepath = directory / filename

        filepath.write_bytes(content)

        image_data = {
            "nombre_archivo": file.filename or filename,
            "ruta": f"/uploads/articulos/{filename}",
            "tipo_mime": file.content_type,
        }

        try:
            imagen = self.repo.add_image(
                articulo_id,
                image_data,
            )
        except IntegrityError as exc:
            self.db.rollback()

            if filepath.exists():
                os.remove(filepath)

            raise ValueError(
                "No se pudo registrar la imagen"
            ) from exc

        AuditoriaService(self.db).registrar(
            usuario_id=usuario_id,
            accion="SUBIR_IMAGEN",
            entidad="ARTICULO",
            entidad_id=articulo_id,
            descripcion=(
                f"Imagen agregada al artículo "
                f"{articulo_id}"
            ),
        )

        return imagen

    def eliminar_imagen(
        self,
        imagen_id: int,
        usuario_id: int,
    ):
        imagen = self.repo.get_image(
            imagen_id
        )

        if not imagen:
            raise ValueError(
                "Imagen no encontrada"
            )

        ruta = imagen.ruta

        self.repo.delete_image(
            imagen
        )

        filepath = Path(
            ruta.lstrip("/")
        )

        if filepath.exists():
            filepath.unlink()

        AuditoriaService(self.db).registrar(
            usuario_id=usuario_id,
            accion="ELIMINAR_IMAGEN",
            entidad="ARTICULO",
            entidad_id=imagen.articulo_id,
            descripcion=(
                f"Imagen {imagen_id} eliminada"
            ),
        )