from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy.sql import func # Importación necesaria para _total_comprado_existente
from app.repositories.orden_compra_repository import OrdenCompraRepository, OrdenCompraComprobanteRepository, OrdenCompraItemRepository # NUEVO REPO
from app.repositories.inventario_repository import InventarioRepository
from app.repositories.rq_item_repository import RQItemRepository
from app.models.orden_compra_model import OrdenCompra, OrdenCompraComprobante, OrdenCompraItem # NUEVOS MODELOS
from app.models.inventario_model import Inventario # Asumo que esta importación es correcta
from app.services.rq_service import RQService # Asumo que esta importación es correcta
from app.schemas.orden_compra_schema import ComprobanteItem, OrdenCompraCreate, OrdenCompraItemCreate # Usar nuevo esquema de creación
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import HTTPException
from app.core.config import BASE_UPLOAD_DIR


# --- Importación e Inicialización del Servicio de Inventario ---
from app.services.inventario_service import InventarioService # 💡 Importación NUEVA
# -------------------------------------------------------------

# --- Constantes de Tipos de Documento ---
MERCADERIA_COMPROBANTE = "MERCADERIA_COMPROBANTE"
ENVIO_COMPROBANTE = "ENVIO_COMPROBANTE"
GUIA_REMISION = "GUIA_REMISION"
XML_MERCADERIA = "XML_MERCADERIA"
XML_ENVIO = "XML_ENVIO"


class OrdenCompraService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = OrdenCompraRepository(db)
        self.item_repo = OrdenCompraItemRepository(db)
        self.comprobante_repo = OrdenCompraComprobanteRepository(db)
        self.inventario_repo = InventarioRepository(db)
        self.rq_item_repo = RQItemRepository(db)
        
        # 💡 Inicialización NUEVA del Servicio de Inventario
        self.inventario_service = InventarioService(db)

    def _total_comprado_existente(self, rq_item_id: int) -> int:
        """Calcula el total comprado para un RQItem específico a través de la tabla de detalle (M:M)."""
        total = self.db.query(func.sum(OrdenCompraItem.cantidad_comprada)).filter(
            OrdenCompraItem.rq_item_id == rq_item_id
        ).scalar()
        return total or 0
    
    # ---------------- Lógica de Validación (Intacta) ----------------
    def _validar_comprobantes(self, tipo_compra: str, comprobantes: List[ComprobanteItem]):
        if not comprobantes or len(comprobantes) == 0:
            raise ValueError("Debe adjuntar al menos un comprobante.")

        # --- 1. No permitir tipos duplicados ---
        tipos = [c.tipo_documento for c in comprobantes]
        if len(tipos) != len(set(tipos)):
            raise ValueError("No se permiten comprobantes duplicados del mismo tipo.")

        archivos = {c.tipo_documento: c for c in comprobantes}

        # --- 2. Siempre obligatorio: comprobante de mercadería ---
        if MERCADERIA_COMPROBANTE not in archivos:
            raise ValueError(
                "Es obligatorio subir la Factura o Boleta de la mercadería."
            )

        # --- 3. Reglas para COMPRA FÍSICA ---
        if tipo_compra == "FISICA":
            documentos_invalidos = [
                ENVIO_COMPROBANTE,
                XML_ENVIO
            ]

            for doc in documentos_invalidos:
                if doc in archivos:
                    raise ValueError(
                        "Compra FÍSICA no puede incluir comprobantes de envío."
                    )

            # XML y guía son opcionales en física (permitidos)
            return True

        # --- 4. Reglas para COMPRA POR ENVÍO ---
        if tipo_compra == "ENVIO":
            obligatorios = [
                MERCADERIA_COMPROBANTE,
                ENVIO_COMPROBANTE,
                GUIA_REMISION
            ]

            for doc in obligatorios:
                if doc not in archivos:
                    raise ValueError(
                        f"Para compra por ENVÍO es obligatorio adjuntar: {doc.replace('_', ' ')}"
                    )

            return True

        # --- 5. Tipo de compra inválido ---
        raise ValueError("Tipo de compra inválido. Use ENVIO o FISICA.")

    # ---------------- Crear orden (ACTUALIZADO: Integración de InventarioService) ----------------
    def create_orden(self, orden_data: OrdenCompraCreate) -> Dict[str, Any]:
            
            # 1. Validación Previa
            if not orden_data.items_comprados:
                raise ValueError("La orden debe contener al menos un ítem comprado.")

            # 2. Validación Estricta del Flujo de Comprobantes
            self._validar_comprobantes(orden_data.tipo_compra, orden_data.comprobantes)

            # 3. Creación de la Cabecera de la Orden
            orden_dict = orden_data.model_dump(exclude={'items_comprados', 'comprobantes'})
            db_orden = OrdenCompra(**orden_dict)
            self.repo.create(db_orden)
            orden_id = db_orden.id
            
            # Ubicación de envío para el inventario
            ubicacion = orden_data.ubicacion_envio if orden_data.ubicacion_envio else "ALMACEN" # 💡 NUEVO

            # 4. Creación de los Comprobantes
            for c in orden_data.comprobantes:
                comprobante = OrdenCompraComprobante(
                    orden_compra_id=orden_id,
                    tipo_documento=c.tipo_documento,
                    archivo_ruta=c.archivo_ruta,
                    numero_comprobante=c.numero_comprobante,
                    es_factura=c.es_factura,
                    fecha=c.fecha if c.fecha else datetime.utcnow().date()
                )
                self.comprobante_repo.create(comprobante)
                
            # --- LÓGICA DE INVENTARIO Y RQ (Iteración sobre cada ítem) ---
            avance_items = []
            rq_estados_afectados = {} 
            
            for item_compra in orden_data.items_comprados:
                item_data: OrdenCompraItemCreate = item_compra
                rq_item = self.rq_item_repo.get_by_id(item_data.rq_item_id)
                if not rq_item:
                    raise ValueError(f"El RQItem con ID {item_data.rq_item_id} no existe")
                if item_data.cantidad_comprada <= 0:
                    raise ValueError(f"La cantidad comprada para el ítem {rq_item.codigo} debe ser mayor que 0")

                # A. Creación del Detalle M:M
                db_item_compra = OrdenCompraItem(
                    orden_compra_id=orden_id,
                    rq_item_id=rq_item.id,
                    cantidad_comprada=item_data.cantidad_comprada,
                    costo_unitario=item_data.costo_unitario
                )
                self.item_repo.create(db_item_compra)

                # B. Cálculos
                cantidad_pedida = rq_item.cantidad or 0
                comprado_antes = self._total_comprado_existente(rq_item.id) - item_data.cantidad_comprada
                cantidad_nueva = item_data.cantidad_comprada

                total_comprado = comprado_antes + cantidad_nueva
                exceso = max(0, total_comprado - cantidad_pedida)
                avance_real_rq = min(total_comprado, cantidad_pedida)
                
                # C. Actualizar inventario (Usando el Servicio Aislado)
                # 💡 Uso del nuevo InventarioService
                self.inventario_service.registrar_entrada_compra( 
                    codigo_producto=rq_item.codigo,
                    descripcion=rq_item.descripcion,
                    cantidad_recibida=cantidad_nueva,
                    ubicacion=ubicacion
                )

                # D. Recalcular progreso del RQ padre
                rq_actualizado = RQService(self.db).actualizar_estado_compra(rq_item.rq_id)
                
                rq_estados_afectados[rq_item.rq_id] = {
                    "rq_id": rq_actualizado.id,
                    "estado_compra": rq_actualizado.estado_compra,
                    "progreso_compra": rq_actualizado.progreso_compra
                }
                
                progreso_item = round((avance_real_rq / cantidad_pedida) * 100, 2) if cantidad_pedida > 0 else 0
                estado_item = "completado" if avance_real_rq >= cantidad_pedida else "parcial" if avance_real_rq > 0 else "sin_iniciar"
                
                avance_items.append({
                    "item_id": rq_item.id,
                    "codigo": rq_item.codigo,
                    "descripcion": rq_item.descripcion,
                    "cantidad_requerida": cantidad_pedida,
                    "comprado_antes": comprado_antes,
                    "comprado_nuevo": cantidad_nueva,
                    "comprado_total": total_comprado,
                    "avance_efectivo_rq": avance_real_rq,
                    "exceso": exceso,
                    "progreso": f"{progreso_item}%",
                    "estado_item": estado_item
                })
                
            self.db.commit() # Commit final de toda la transacción

            # 5. Respuesta 
            return {
                "message": f"Orden {orden_id} creada y {len(avance_items)} ítems registrados correctamente",
                "orden_id": orden_id,
                "avances_items": avance_items,
                "estados_requerimientos_afectados": list(rq_estados_afectados.values()) 
            }
    
    # ---------------- Listar órdenes por item (Intacta) ----------------
    def get_ordenes_by_item(self, rq_item_id: int) -> List[OrdenCompra]:
        """Obtiene las órdenes de compra asociadas a un RQItem específico."""
        return self.repo.get_by_item(rq_item_id)
        
    # ---------------- Patch parcial de orden (Intacta) ----------------
    def patch_orden(self, orden_id: int, cambios: Dict[str, Any]):
        orden = self.repo.get_by_id(orden_id)
        if not orden:
            raise ValueError("Orden no encontrada")

        # Lógica de adición de nuevos comprobantes
        for c_data in cambios.pop("comprobantes", []):
            c = ComprobanteItem(**c_data)
            comprobante = OrdenCompraComprobante(
                orden_compra_id=orden.id,
                tipo_documento=c.tipo_documento,
                archivo_ruta=c.archivo_ruta,
                numero_comprobante=c.numero_comprobante,
                es_factura=c.es_factura,
                fecha=c.fecha if c.fecha else datetime.utcnow().date()
            )
            self.comprobante_repo.create(comprobante)
        
        # Actualización de la cabecera
        orden_actualizada = self.repo.update(orden_id, **cambios)
        
        return {
            "orden": orden_actualizada,
            "message": "Cabecera y comprobantes adicionales actualizados."
        }

    # ---------------- Update completo de orden (Intacta) ----------------
    def update_orden(self, orden_id: int, cambios: Dict[str, Any]):
        orden = self.repo.get_by_id(orden_id)
        if not orden:
            raise ValueError("Orden no encontrada")
            
        # 1. Manejo de Comprobantes (Reemplazo total)
        if "comprobantes" in cambios:
            self.comprobante_repo.delete_by_orden(orden.id) 
            
            for c_data in cambios["comprobantes"]:
                c = ComprobanteItem(**c_data)
                comprobante = OrdenCompraComprobante(
                    orden_compra_id=orden.id,
                    tipo_documento=c.tipo_documento,
                    archivo_ruta=c.archivo_ruta,
                    numero_comprobante=c.numero_comprobante,
                    es_factura=c.es_factura,
                    fecha=c.fecha if c.fecha else datetime.utcnow().date()
                )
                self.comprobante_repo.create(comprobante)
            cambios.pop("comprobantes") 
            
        # 2. Manejo de Items Comprados (Lógica omitida por complejidad)
        
        # 3. Actualización de Cabecera
        orden_actualizada = self.repo.update(orden_id, **cambios)
        return orden_actualizada

    # ---------------- Eliminar orden (ACTUALIZADO: Integración de Reversión) ----------------
    def delete_orden(self, orden_id: int):
        orden = self.repo.get_by_id(orden_id)
        if not orden:
            raise ValueError("Orden no encontrada")
        
        # Obtener los ítems afectados antes de eliminar
        items_a_recalcular = []
        for item_detalle in orden.items_comprados:
            rq_item = self.rq_item_repo.get_by_id(item_detalle.rq_item_id)
            if rq_item:
                # 1. Ajustar Inventario (reversión)
                # 💡 Uso del nuevo InventarioService
                self.inventario_service.revertir_salida_compra(
                    codigo_producto=rq_item.codigo,
                    cantidad_a_revertir=item_detalle.cantidad_comprada
                )
                
                items_a_recalcular.append(rq_item.rq_id)

        ruta_oc = os.path.join(BASE_UPLOAD_DIR, f"OC_{orden_id}")
        if os.path.exists(ruta_oc):
            shutil.rmtree(ruta_oc)
            
        # Eliminar la orden y sus detalles/comprobantes (gracias a cascade="all, delete-orphan")
        self.repo.delete(orden_id)
        
        # Recalcular estado de los RQs afectados
        for rq_id in set(items_a_recalcular): # Usar set para recalcular solo una vez por RQ
            RQService(self.db).actualizar_estado_compra(rq_id)
            
        self.db.commit() # 💡 Commit al final
        return {"message": f"Orden {orden_id} y sus {len(orden.items_comprados)} ítems eliminados correctamente."}
    
    # ---------------- Listar resumen de órdenes por RQ (Intacta) ----------------
    def listar_ordenes_por_rq(self, estado: Optional[str] = None, fecha_inicio: Optional[str] = None, fecha_fin: Optional[str] = None):
        """Retorna todas las órdenes de compra agrupadas por RQ, usando la tabla de detalle."""
        # Se usará la función 'listar_ordenes_resumen' del repositorio que retorna la tupla (OrdenCompra, OrdenCompraItem, RQItem)
        resultados_join = self.repo.listar_ordenes_resumen(estado, fecha_inicio, fecha_fin)
        
        resumen_rq = {} # Agrupador final por RQ ID
        
        # Agrupar la información
        for orden, orden_item, rq_item in resultados_join:
            rq_id = rq_item.rq_id
            
            if rq_id not in resumen_rq:
                resumen_rq[rq_id] = {
                    "rq_id": rq_id,
                    "items": {} # Agrupador por RQItem ID
                }
            
            rq_item_id = rq_item.id
            if rq_item_id not in resumen_rq[rq_id]["items"]:
                # Calcular total comprado antes de este reporte
                total_comprado_item = self._total_comprado_existente(rq_item_id)
                cantidad_requerida = rq_item.cantidad or 0
                
                exceso = max(0, total_comprado_item - cantidad_requerida)
                avance = min(total_comprado_item, cantidad_requerida)
                progreso = round((avance / cantidad_requerida) * 100, 2) if cantidad_requerida > 0 else 0
                estado_item = "completado" if avance >= cantidad_requerida else "parcial" if avance > 0 else "sin_iniciar"
                
                resumen_rq[rq_id]["items"][rq_item_id] = {
                    "item_id": rq_item_id,
                    "codigo": rq_item.codigo,
                    "descripcion": rq_item.descripcion,
                    "cantidad_requerida": cantidad_requerida,
                    "comprado_total": total_comprado_item,
                    "avance_efectivo_rq": avance,
                    "exceso": exceso,
                    "progreso": f"{progreso}%",
                    "estado_item": estado_item,
                    "ordenes_asociadas": []
                }
            
            # Agregar la orden actual a la lista de órdenes asociadas al item
            resumen_rq[rq_id]["items"][rq_item_id]["ordenes_asociadas"].append({
                "orden_id": orden.id,
                "proveedor": orden.proveedor,
                "fecha": orden.fecha.isoformat() if orden.fecha else None,
                "cantidad_comprada_en_orden": orden_item.cantidad_comprada,
                "costo_unitario": orden_item.costo_unitario
            })
            
        # Finalizar el cálculo de progreso por RQ
        resultado_final = []
        for r_data in resumen_rq.values():
            total_requerido_rq = sum(item['cantidad_requerida'] for item in r_data['items'].values())
            total_avance_rq = sum(item['avance_efectivo_rq'] for item in r_data['items'].values())
            total_exceso_rq = sum(item['exceso'] for item in r_data['items'].values())
            
            progreso_rq = round((total_avance_rq / total_requerido_rq) * 100, 2) if total_requerido_rq > 0 else 0
            estado_rq = "completado" if total_avance_rq >= total_requerido_rq else "parcial" if total_avance_rq > 0 else "sin_iniciar"

            r_data["progreso_compra"] = progreso_rq
            r_data["estado_compra"] = estado_rq
            r_data["exceso_total"] = total_exceso_rq
            r_data["items"] = list(r_data["items"].values()) # Convertir el diccionario de ítems a lista
            resultado_final.append(r_data)
            
        return resultado_final
    def update_orden_completa(self, orden_id: int, nueva_orden_data: OrdenCompraCreate) -> Dict[str, Any]:
        """
        Actualiza una orden de compra completamente: cabecera, comprobantes e ítems.
        Requiere una lógica transaccional de reversión y re-aplicación.
        """
        db = self.db # Alias de la sesión
        
        # 1. VALIDACIÓN PREVIA Y OBTENCIÓN DE DATOS ANTIGUOS
        orden_antigua = self.repo.get_by_id(orden_id)
        if not orden_antigua:
            raise ValueError(f"Orden de Compra con ID {orden_id} no encontrada.")

        if not nueva_orden_data.items_comprados:
            raise ValueError("La orden debe contener al menos un ítem comprado.")
            
        self._validar_comprobantes(nueva_orden_data.tipo_compra, nueva_orden_data.comprobantes)

        # Lista de RQs que se afectaron anteriormente y que deben recalcularse
        rqs_a_recalcular = set()
        
        try:
            # --- PASO A: REVERSIÓN TOTAL DE STOCK Y PROGRESO ---
            
            # 1. Revertir Inventario y registrar los RQs afectados
            for item_detalle in orden_antigua.items_comprados:
                rq_item = self.rq_item_repo.get_by_id(item_detalle.rq_item_id)
                if rq_item:
                    # Revertir Stock
                    self.inventario_service.revertir_salida_compra(
                        codigo_producto=rq_item.codigo,
                        cantidad_a_revertir=item_detalle.cantidad_comprada
                    )
                    rqs_a_recalcular.add(rq_item.rq_id)
                    
            # 2. Recalcular el progreso de los RQs antes de eliminarlos
            # (Esto garantiza que el RQ quede en un estado "limpio" antes de la nueva aplicación)
            for rq_id in rqs_a_recalcular:
                RQService(db).actualizar_estado_compra(rq_id)
                
            # --- PASO B: ELIMINACIÓN DE DETALLES Y COMPROBANTES ANTIGUOS ---
            
            # 3. Eliminar todos los ítems M:M de la OC antigua
            self.item_repo.delete_by_orden_id(orden_id) # DEBES IMPLEMENTAR ESTE MÉTODO EN EL REPO
            
            # 4. Eliminar comprobantes antiguos
            self.comprobante_repo.delete_by_orden(orden_id)
            
            # --- PASO C: APLICACIÓN DE LA NUEVA DATA (SIMILAR A create_orden) ---
            
            # 5. Actualizar Cabecera de la Orden (usando el mismo ID)
            orden_dict = nueva_orden_data.model_dump(exclude={'items_comprados', 'comprobantes'})
            orden_dict['id'] = orden_id # Aseguramos que el ID se mantenga
            self.repo.update(orden_id, **orden_dict)
            
            ubicacion = nueva_orden_data.ubicacion_envio if nueva_orden_data.ubicacion_envio else "ALMACEN"
            
            # 6. Crear los Nuevos Comprobantes
            for c in nueva_orden_data.comprobantes:
                comprobante = OrdenCompraComprobante(
                    orden_compra_id=orden_id,
                    tipo_documento=c.tipo_documento,
                    archivo_ruta=c.archivo_ruta,
                    # ... (resto de campos de comprobante)
                )
                self.comprobante_repo.create(comprobante)
                
            # 7. Crear los Nuevos Ítems, Afectar Stock y Recalcular RQs
            avances_items = []
            rqs_a_recalcular_final = set() # RQs afectados por la nueva data
            
            for item_compra in nueva_orden_data.items_comprados:
                rq_item = self.rq_item_repo.get_by_id(item_compra.rq_item_id)
                if not rq_item:
                    raise ValueError(f"RQItem ID {item_compra.rq_item_id} no existe en la nueva data.")

                # A. Creación del Nuevo Detalle
                db_item_compra = OrdenCompraItem(
                    orden_compra_id=orden_id,
                    rq_item_id=rq_item.id,
                    cantidad_comprada=item_compra.cantidad_comprada,
                    costo_unitario=item_compra.costo_unitario
                )
                self.item_repo.create(db_item_compra)

                # B. Actualizar inventario (Usando el Servicio Aislado)
                self.inventario_service.registrar_entrada_compra( 
                    codigo_producto=rq_item.codigo,
                    descripcion=rq_item.descripcion,
                    cantidad_recibida=item_compra.cantidad_comprada,
                    ubicacion=ubicacion
                )
                
                rqs_a_recalcular_final.add(rq_item.rq_id)

                # C. Lógica de cálculo de avance (puedes reutilizar la de create_orden)
                total_comprado = self._total_comprado_existente(rq_item.id) # Debe incluir la nueva cantidad
                cantidad_pedida = rq_item.cantidad or 0
                
                avances_items.append({
                    # ... Lógica para construir la respuesta de avance aquí ...
                    "item_id": rq_item.id,
                    "comprado_total": total_comprado,
                    # ...
                })
                
            # 8. Recalcular el progreso de los RQs afectados por la nueva data
            estados_finales = []
            for rq_id in rqs_a_recalcular_final:
                rq_actualizado = RQService(db).actualizar_estado_compra(rq_id)
                estados_finales.append({
                    "rq_id": rq_actualizado.id,
                    "estado_compra": rq_actualizado.estado_compra,
                    "progreso_compra": rq_actualizado.progreso_compra
                })

            db.commit() # Commit final
            
            return {
                "message": f"Orden {orden_id} actualizada completamente. {len(avances_items)} ítems re-registrados.",
                "orden_id": orden_id,
                "avances_items": avances_items,
                "estados_requerimientos_afectados": estados_finales 
            }

        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error transaccional al actualizar la orden: {str(e)}")
