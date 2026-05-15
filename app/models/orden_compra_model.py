from __future__ import annotations

from sqlalchemy import Column, Integer, String, Date, ForeignKey, Float, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base 

# --- NUEVO MODELO: CABECERA DE LA ORDEN DE COMPRA ---
# (Reemplaza y extiende la antigua OrdenCompraParcial)
class OrdenCompra(Base):
    __tablename__ = "ordenes_compra" 
    
    id = Column(Integer, primary_key=True, index=True)
    # ⚠️ CAMPO ELIMINADO: rq_item_id
    # ⚠️ CAMPO ELIMINADO: cantidad_comprada
    
    cantidad_restante = Column(Integer, nullable=True) # Mantener si se usa a nivel de cabecera
    estado = Column(String, default="comprado")
    ubicacion_envio = Column(String, nullable=True)
    proveedor = Column(String, nullable=True)
    fecha = Column(Date, default=datetime.utcnow().date)
    tipo_compra = Column(String, nullable=False)  # ENVIO | FISICA
    costo_envio = Column(Float, nullable=True)
    notas = Column(String, nullable=True)

    # NUEVA RELACIÓN: Detalle de Ítems comprados (M:M)
    items_comprados = relationship(
        "OrdenCompraItem", 
        back_populates="orden_compra", 
        cascade="all, delete-orphan"
    )
    
    # RELACIÓN MANTENIDA: Comprobantes (ahora apuntando a esta nueva cabecera)
    comprobantes = relationship(
        "OrdenCompraComprobante", 
        back_populates="orden_compra", # Renombrado back_populates
        cascade="all, delete-orphan"
    )

# --- NUEVO MODELO: DETALLE Y RELACIÓN M:M ---
class OrdenCompraItem(Base):
    __tablename__ = "ordenes_compra_items"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Claves Foráneas de la relación M:M
    orden_compra_id = Column(Integer, ForeignKey("ordenes_compra.id"))
    rq_item_id = Column(Integer, ForeignKey("rq_items.id")) # Trazabilidad al RQItem
    
    # Datos de la cantidad y costo
    cantidad_comprada = Column(Integer, nullable=False)
    costo_unitario = Column(Float, nullable=True) # Nuevo campo opcional
    
    # Relaciones
    orden_compra = relationship("OrdenCompra", back_populates="items_comprados")
    rq_item = relationship("RQItem", back_populates="ordenes_compra_items")


# --- MODELO DE COMPROBANTE (Ajustado para la nueva cabecera) ---
class OrdenCompraComprobante(Base):
    __tablename__ = "ordenes_comprobantes"

    id = Column(Integer, primary_key=True, index=True)

    orden_compra_id = Column(
        Integer,
        ForeignKey("ordenes_compra.id", ondelete="CASCADE"),
        nullable=False
    )

    tipo_documento = Column(String(50), nullable=False)
    archivo_ruta = Column(String(255), nullable=False)
    numero_comprobante = Column(String(100), nullable=True)
    es_factura = Column(Boolean, nullable=True)
    fecha = Column(Date, default=datetime.utcnow().date)

    orden_compra = relationship(
        "OrdenCompra",
        back_populates="comprobantes"
    )
