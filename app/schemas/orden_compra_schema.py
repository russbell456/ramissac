# app/schemas/orden_compra_schema.py
from __future__ import annotations
from pydantic import BaseModel, Field, validator
from datetime import date
from typing import Optional, List, Any, Literal, Dict

MERCADERIA_COMPROBANTE = "MERCADERIA_COMPROBANTE"
ENVIO_COMPROBANTE = "ENVIO_COMPROBANTE"
GUIA_REMISION = "GUIA_REMISION"
XML_MERCADERIA = "XML_MERCADERIA"
XML_ENVIO = "XML_ENVIO"

class ComprobanteItem(BaseModel):
    # ... (cuerpo se mantiene idéntico, ya que valida tipos de documento) ...
    tipo_documento: str = Field(..., description="Tipo de documento subido (e.g., MERCADERIA_COMPROBANTE)")
    archivo_ruta: str = Field(..., description="Ruta o URL del archivo subido")
    numero_comprobante: Optional[str] = None
    es_factura: Optional[bool] = None
    fecha: Optional[date] = None

    @validator('es_factura', pre=True, always=True)
    def validate_es_factura_and_number(cls, v: Optional[bool], values: Any) -> Optional[bool]:
        # ... (Lógica de validación de comprobante se mantiene intacta) ...
        doc_type = values.get('tipo_documento')
        number = values.get('numero_comprobante')
        
        is_comprobante = doc_type in [MERCADERIA_COMPROBANTE, ENVIO_COMPROBANTE]
        is_auxiliary = doc_type in [GUIA_REMISION, XML_MERCADERIA, XML_ENVIO]

        if is_comprobante:
            if v is None:
                raise ValueError(f"Para {doc_type}, 'es_factura' (True/False) es obligatorio.")
            if not number:
                 raise ValueError(f"Para {doc_type}, el 'numero_comprobante' es obligatorio.")
        
        if is_auxiliary and v is not None:
             raise ValueError(f"Para {doc_type}, 'es_factura' debe ser nulo.")
            
        return v
@validator("items_comprados")
def validar_items_comprados(cls, v):
    if not v or len(v) == 0:
        raise ValueError("La orden de compra debe tener al menos un ítem comprado.")
    return v

class DocumentoCreateItem(BaseModel):
    tipo: str       # 'factura', 'boleta', 'factura_envio', 'boleta_envio', 'xml', 'guia'
    archivo: str
    fecha: Optional[date] = None

@validator("comprobantes")
def validar_comprobantes_minimos(cls, comprobantes, values):
    tipo_compra = values.get("tipo_compra")

    if not comprobantes or len(comprobantes) == 0:
        raise ValueError("Debe adjuntar al menos un comprobante.")

    tipos = [c.tipo_documento for c in comprobantes]

    # ❌ Tipos duplicados
    if len(tipos) != len(set(tipos)):
        raise ValueError("No se permiten comprobantes duplicados del mismo tipo.")

    archivos = set(tipos)

    # ✅ Siempre obligatorio
    if MERCADERIA_COMPROBANTE not in archivos:
        raise ValueError("Es obligatorio adjuntar comprobante de mercadería.")

    # 🔹 COMPRA FÍSICA
    if tipo_compra == "FISICA":
        prohibidos = {ENVIO_COMPROBANTE, XML_ENVIO}
        if archivos & prohibidos:
            raise ValueError(
                "Compra FÍSICA no puede incluir comprobantes de envío."
            )

    # 🔹 COMPRA POR ENVÍO
    if tipo_compra == "ENVIO":
        obligatorios = {
            MERCADERIA_COMPROBANTE,
            ENVIO_COMPROBANTE,
            GUIA_REMISION,
        }
        faltantes = obligatorios - archivos
        if faltantes:
            raise ValueError(
                f"Para compra por ENVÍO faltan comprobantes obligatorios: {', '.join(faltantes)}"
            )

    return comprobantes


class OrdenCompraItemCreate(BaseModel):
    rq_item_id: int = Field(..., description="ID del RQItem al que se asigna la compra.")
    cantidad_comprada: int
    costo_unitario: Optional[float] = None # Nuevo campo

class OrdenCompraCreate(BaseModel):
    # ⚠️ CAMPOS ELIMINADOS: rq_item_id y cantidad_comprada (Movidos a items_comprados)
    estado: Optional[str] = "comprado"
    ubicacion_envio: Optional[str] = None
    fecha: Optional[date] = None
    proveedor: Optional[str] = None
    tipo_compra: Literal['ENVIO', 'FISICA'] = Field(..., description="Tipo de compra: ENVIO o FISICA")
    costo_envio: Optional[float] = None
    notas: Optional[str] = None
    
    # ⚠️ NUEVO ARRAY CLAVE para múltiples ítems
    items_comprados: List[OrdenCompraItemCreate]

    comprobantes: List[ComprobanteItem]




class ComprobanteEntity(BaseModel):
    id: int
    tipo_documento: str
    archivo_ruta: str
    numero_comprobante: Optional[str] = None
    es_factura: Optional[bool] = None
    fecha: Optional[date] = None

    model_config = {"from_attributes": True}


class OrdenCompraEntity(BaseModel):
    id: int
    # ⚠️ CAMPO ELIMINADO: rq_item_id
    # ⚠️ CAMPO ELIMINADO: cantidad_comprada
    estado: Optional[str] = None
    ubicacion_envio: Optional[str] = None
    fecha: Optional[date] = None
    proveedor: Optional[str] = None
    tipo_compra: Optional[str] = None
    costo_envio: Optional[float] = None
    notas: Optional[str] = None
    
    # El detalle de los ítems ahora va aquí (debe mapearse vía relación)
    items_comprados: List[Dict[str, Any]] = [] # Usamos Dict temporalmente para reportar la relación
    comprobantes: List[ComprobanteEntity] = []
    
# respuesta summary
class AvanceItem(BaseModel):
    item_id: int
    codigo: str
    descripcion: str
    cantidad_requerida: int
    comprado_antes: int
    comprado_nuevo: int
    comprado_total: int
    avance_efectivo_rq: int
    exceso: int
    progreso: str
    estado_item: str
    
class OrdenCompraResponse(BaseModel):
    id: int
    # ⚠️ CAMPO ELIMINADO: rq_item_id
    # ⚠️ CAMPO ELIMINADO: cantidad_comprada
    estado: Optional[str]
    fecha: Optional[date]
    proveedor: Optional[str]
    tipo_compra: Optional[str]

    model_config = {"from_attributes": True}
class EstadoRQResumen(BaseModel):
    rq_id: int
    estado_compra: str
    progreso_compra: float

class OrdenCompraSummaryResponse(BaseModel):
    message: str
    orden: OrdenCompraEntity
    avance_item: AvanceItem
    estado_rq: EstadoRQResumen

    class Config:
        orm_mode = True

class ComprobanteCreateItem(BaseModel): # Renombrado para claridad en PATCH/UPDATE
    tipo_documento: str = Field(..., description="Tipo de documento subido (e.g., MERCADERIA_COMPROBANTE)")
    archivo_ruta: str = Field(..., description="Ruta o URL del archivo subido")
    numero_comprobante: Optional[str] = None
    es_factura: Optional[bool] = None
    fecha: Optional[date] = None
    
    # Aquí se pueden añadir los validadores de ComprobanteItem si se desea
    # ...
class OrdenCompraItemUpdateCantidad(BaseModel):
    nueva_cantidad: int
    
class OrdenCompraPatch(BaseModel):
    """Esquema para la actualización parcial (PATCH) de la cabecera de la Orden."""
    estado: Optional[str] = None
    ubicacion_envio: Optional[str] = None
    fecha: Optional[date] = None
    proveedor: Optional[str] = None
    tipo_compra: Optional[Literal['ENVIO', 'FISICA']] = None
    costo_envio: Optional[float] = None
    notas: Optional[str] = None
    
    # Permite añadir nuevos comprobantes a la orden existente
    comprobantes_adicionales: Optional[List[ComprobanteCreateItem]] = Field(
        None, description="Lista de comprobantes adicionales a agregar, sin reemplazar los existentes."
    )

    # Nota: No se permite actualizar items_comprados (detalles) con un simple PATCH
    # ya que requiere una lógica de inventario y RQ compleja.

    model_config = {"extra": "ignore"} # Ignorar campos no definidos