"""Carga datos sintéticos realistas y completos para la demostración de roles en RamisToolX.

Ejecutar:
    .venv/bin/python -m app.scripts.seed_demo_full
"""

from datetime import datetime, timedelta
from decimal import Decimal

import app.models  # noqa: F401
from app.database.base import Base
from app.database.connection import SessionLocal, engine
from app.models.almacen_articulos import AlmacenArticulo, TipoArticulo
from app.models.almacen_obras import AlmacenObra
from app.models.almacen_prestamo import (
    AlmacenPrestamo,
    AlmacenPrestamoDetalle,
    EstadoPrestamo,
    TipoPrestamo,
)
from app.models.rq_campo import EstadoItemRq, EstadoRqCampo, RqCampo, RqCampoItem, RqCampoItemSeguimiento, TipoItemRqCampo
from app.models.user import User
from app.security.hashing import Hash


USUARIOS = [
    {
        "nombre": "Admin",
        "apellidos": "Principal",
        "dni": "00000000A",
        "cargo": "Gerente de Operaciones",
        "codigo_unico": "ADMIN-001",
        "email": "admin@example.com",
        "role": "admin",
    },
    {
        "nombre": "Carlos",
        "apellidos": "Mamani Almacén",
        "dni": "12345678",
        "cargo": "Jefe de Almacén Central",
        "codigo_unico": "ALM-001",
        "email": "almacenero@example.com",
        "role": "almacenero",
    },
    {
        "nombre": "Juan",
        "apellidos": "Pérez Quispe",
        "dni": "70123456",
        "cargo": "Residente de Campo / Técnico",
        "codigo_unico": "TRAB-001",
        "email": "trabajador@example.com",
        "role": "trabajador",
    },
    {
        "nombre": "María",
        "apellidos": "López Flores",
        "dni": "72345678",
        "cargo": "Coordinadora de Logística y Compras",
        "codigo_unico": "LOG-001",
        "email": "logistica@example.com",
        "role": "logistica",
    },
    {
        "nombre": "Pedro",
        "apellidos": "Condori Chambi",
        "dni": "73456789",
        "cargo": "Técnico Mecánico Soldador",
        "codigo_unico": "TRAB-002",
        "email": "pedro.condori@example.com",
        "role": "trabajador",
    },
    {
        "nombre": "Luis",
        "apellidos": "Mamani Apaza",
        "dni": "74567890",
        "cargo": "Operador de Planta Minera",
        "codigo_unico": "TRAB-003",
        "email": "luis.mamani@example.com",
        "role": "trabajador",
    },
]

OBRAS = [
    {
        "nombre": "Pulmón de Aire 2025",
        "descripcion": "Instalación y puesta en servicio de pulmón de aire industrial.",
        "cliente": "Corporación Ramis SAC",
        "ubicacion": "Juliaca, Puno",
        "estado": "activo",
        "fecha_inicio": datetime(2025, 11, 3),
    },
    {
        "nombre": "Ampliación de Planta Industrial",
        "descripcion": "Ampliación de redes mecánicas y servicios auxiliares.",
        "cliente": "Cliente Industrial Demo",
        "ubicacion": "Arequipa",
        "estado": "activo",
        "fecha_inicio": datetime(2026, 1, 12),
    },
    {
        "nombre": "Mantenimiento de Sistema Neumático",
        "descripcion": "Mantenimiento preventivo de líneas y equipos neumáticos.",
        "cliente": "Operaciones Andinas Demo",
        "ubicacion": "Puno",
        "estado": "activo",
        "fecha_inicio": datetime(2026, 2, 2),
    },
    {
        "nombre": "Tajo Abierto - Sector Sur",
        "descripcion": "Montaje de compresores y líneas de aire en interior mina.",
        "cliente": "Minera San Rafael",
        "ubicacion": "Antauta, Puno",
        "estado": "activo",
        "fecha_inicio": datetime(2026, 3, 1),
    },
]

ARTICULOS = [
    ("DEMO-EQ-001", "Manómetro 0-150 PSI", TipoArticulo.EQUIPO, "Instrumentación", "UND", 12, "WIKA", "111.10", "Manómetro para control de presión de aire."),
    ("DEMO-EQ-002", "Compresor de aire 100 L", TipoArticulo.EQUIPO, "Equipos neumáticos", "UND", 3, "Schulz", "MSV 10/100", "Compresor monofásico para trabajos de campo."),
    ("DEMO-EQ-003", "Multímetro digital", TipoArticulo.EQUIPO, "Instrumentación", "UND", 8, "Fluke", "117", "Equipo para mediciones eléctricas en campo."),
    ("DEMO-EQ-004", "Máquina de soldar inverter", TipoArticulo.EQUIPO, "Soldadura", "UND", 4, "Soldexa", "Mega Force 225", "Soldadora portátil para electrodo revestido."),
    ("DEMO-EQ-005", "Casco de seguridad", TipoArticulo.EQUIPO, "EPP", "UND", 30, "3M", "H-700", "Casco industrial con suspensión regulable."),
    ("DEMO-HR-001", "Taladro percutor 1/2 pulgada", TipoArticulo.HERRAMIENTA, "Herramientas eléctricas", "UND", 6, "Bosch", "GSB 13 RE", "Taladro para metal, madera y concreto."),
    ("DEMO-HR-002", "Amoladora angular 4 1/2 pulgadas", TipoArticulo.HERRAMIENTA, "Herramientas eléctricas", "UND", 7, "Makita", "9557HNG", "Amoladora para corte y desbaste."),
    ("DEMO-HR-003", "Llave Stillson 14 pulgadas", TipoArticulo.HERRAMIENTA, "Herramientas manuales", "UND", 10, "Truper", "STI-14", "Llave para instalación de tuberías."),
    ("DEMO-HR-004", "Juego de llaves combinadas", TipoArticulo.HERRAMIENTA, "Herramientas manuales", "JGO", 5, "Stanley", "STMT78099", "Juego métrico de llaves combinadas."),
    ("DEMO-HR-005", "Calibrador Vernier 0-150 mm", TipoArticulo.HERRAMIENTA, "Medición", "UND", 6, "Mitutoyo", "530-312", "Instrumento para medición dimensional."),
    ("DEMO-CS-001", "Guantes de seguridad anticorte", TipoArticulo.CONSUMIBLE, "EPP", "PAR", 80, "Ansell", "HyFlex", "Guantes para manipulación de metal."),
    ("DEMO-CS-002", "Electrodo E6011 1/8 pulgada", TipoArticulo.CONSUMIBLE, "Soldadura", "KG", 120, "Soldexa", "Punto Azul", "Electrodo para soldadura de acero al carbono."),
    ("DEMO-CS-003", "Cinta de teflón industrial", TipoArticulo.CONSUMIBLE, "Gasfitería", "ROLLO", 60, "Genérica", "PTFE-19", "Cinta PTFE para sellado de roscas."),
    ("DEMO-CS-004", "Tubería galvanizada 2 pulgadas", TipoArticulo.CONSUMIBLE, "Tuberías", "M", 180, "Tupemesa", "SCH40", "Tubería para red de aire comprimido."),
    ("DEMO-CS-005", "Válvula de bola 2 pulgadas", TipoArticulo.CONSUMIBLE, "Válvulas", "UND", 24, "Itap", "IDEAL 090", "Válvula roscada de paso completo."),
    ("DEMO-CS-006", "Pintura anticorrosiva gris", TipoArticulo.CONSUMIBLE, "Pinturas", "GAL", 18, "Tekno", "Anticorrosivo", "Base protectora para estructuras metálicas."),
    ("DEMO-CS-007", "Perno hexagonal 1/2 x 3 pulgadas", TipoArticulo.CONSUMIBLE, "Ferretería", "UND", 250, "Genérica", "G5", "Perno zincado con tuerca y arandela."),
    ("DEMO-CS-008", "Disco de corte 4 1/2 pulgadas", TipoArticulo.CONSUMIBLE, "Abrasivos", "UND", 75, "Norton", "BNA12", "Disco abrasivo para corte de acero."),
]


def seed_full():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. USUARIOS
        print("Cargando usuarios...")
        for u_data in USUARIOS:
            user = db.query(User).filter(User.email == u_data["email"]).first()
            if user is None:
                user = User(
                    **u_data,
                    password=Hash.get_password_hash("admin123"),
                )
                db.add(user)
            else:
                for k, v in u_data.items():
                    setattr(user, k, v)
                user.password = Hash.get_password_hash("admin123")
        db.commit()

        # 2. OBRAS
        print("Cargando obras...")
        for o_data in OBRAS:
            obra = db.query(AlmacenObra).filter(AlmacenObra.nombre == o_data["nombre"]).first()
            if obra is None:
                db.add(AlmacenObra(**o_data))
            else:
                for k, v in o_data.items():
                    setattr(obra, k, v)
        db.commit()

        # 3. ARTÍCULOS
        print("Cargando catálogo de almacén...")
        for codigo, nombre, tipo, categoria, unidad, stock, marca, modelo, descripcion in ARTICULOS:
            articulo = db.query(AlmacenArticulo).filter(AlmacenArticulo.codigo_excel == codigo).first()
            data = {
                "codigo_excel": codigo,
                "nombre": nombre,
                "tipo": tipo,
                "categoria": categoria,
                "unidad_medida": unidad,
                "stock_total": stock,
                "stock_actual": stock,
                "en_prestamo": 0,
                "marca": marca,
                "modelo": modelo,
                "descripcion": descripcion,
                "estado_fisico": "BUENO",
                "costo_reposicion": Decimal("150.00"),
                "requiere_foto_prestamo": tipo != TipoArticulo.CONSUMIBLE,
                "requiere_foto_devolucion": tipo != TipoArticulo.CONSUMIBLE,
                "es_activo_alto_valor": tipo == TipoArticulo.EQUIPO,
                "activo": True,
            }
            if articulo is None:
                db.add(AlmacenArticulo(**data))
            else:
                for k, v in data.items():
                    setattr(articulo, k, v)
        db.commit()

        # Obtener referencias clave
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        juan = db.query(User).filter(User.email == "trabajador@example.com").first()
        pedro = db.query(User).filter(User.email == "pedro.condori@example.com").first()
        carlos = db.query(User).filter(User.email == "almacenero@example.com").first()
        obra_pulmon = db.query(AlmacenObra).filter(AlmacenObra.nombre == "Pulmón de Aire 2025").first()
        obra_planta = db.query(AlmacenObra).filter(AlmacenObra.nombre == "Ampliación de Planta Industrial").first()
        obra_mantenimiento = db.query(AlmacenObra).filter(AlmacenObra.nombre == "Mantenimiento de Sistema Neumático").first()

        # 4. REQUERIMIENTOS VARIADOS
        print("Cargando requerimientos de prueba...")
        rqs_data = [
            {
                "numero": "RQ-2026-001",
                "obra": obra_pulmon,
                "creador": juan,
                "descripcion": "Instalación de compresor y red primaria de aire en caseta.",
                "estado": EstadoRqCampo.ENVIADO,
                "items": [
                    ("DEMO-EQ-002", 1, EstadoItemRq.ATENDIDO_STOCK),
                    ("DEMO-EQ-001", 2, EstadoItemRq.ATENDIDO_STOCK),
                    ("DEMO-CS-004", 30, EstadoItemRq.ATENDIDO_STOCK),
                ],
            },
            {
                "numero": "RQ-2026-002",
                "obra": obra_planta,
                "creador": juan,
                "descripcion": "Repuestos e instrumentación de alta presión para red secundaria de aire.",
                "estado": EstadoRqCampo.ENVIADO,
                "items": [
                    ("DEMO-CS-005", 8, EstadoItemRq.POR_COMPRAR),
                    ("NO-CAT-001", 3, EstadoItemRq.POR_COMPRAR, "Sensor de presión 4-20mA WIKA (No catalogado)", "UND"),
                    ("NO-CAT-002", 25, EstadoItemRq.POR_COMPRAR, "Manguera hidráulica alta presión 3/4\" 4 mallas", "M"),
                ],
            },
            {
                "numero": "RQ-2026-003",
                "obra": obra_mantenimiento,
                "creador": pedro,
                "descripcion": "Materiales para soldadura y mantenimiento estructural.",
                "estado": EstadoRqCampo.ENVIADO,
                "items": [
                    ("DEMO-CS-002", 40, EstadoItemRq.EN_PROCESO),
                    ("DEMO-CS-008", 60, EstadoItemRq.EN_PROCESO),
                ],
            },
            {
                "numero": "RQ-2026-004",
                "obra": obra_pulmon,
                "creador": juan,
                "descripcion": "Herramientas de medición para inspección y puesta en marcha.",
                "estado": EstadoRqCampo.BORRADOR,
                "items": [
                    ("DEMO-EQ-003", 1, EstadoItemRq.PENDIENTE),
                    ("DEMO-HR-005", 1, EstadoItemRq.PENDIENTE),
                ],
            },
        ]

        firma_demo = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5W7FYAAAAASUVORK5CYII="

        for r_info in rqs_data:
            rq = db.query(RqCampo).filter(RqCampo.numero == r_info["numero"]).first()
            if rq is None:
                rq = RqCampo(
                    numero=r_info["numero"],
                    obra_id=r_info["obra"].id,
                    creador_id=r_info["creador"].id,
                    nombre_proyecto=r_info["obra"].nombre,
                    solicitante_nombre=f"{r_info['creador'].nombre} {r_info['creador'].apellidos}".strip(),
                    solicitante_cargo=r_info["creador"].cargo,
                    fecha_requerimiento=datetime.now() - timedelta(days=1),
                    descripcion_general=r_info["descripcion"],
                    estado=r_info["estado"],
                    firma_base64=firma_demo if r_info["estado"] == EstadoRqCampo.ENVIADO else None,
                    firmado_por_id=r_info["creador"].id if r_info["estado"] == EstadoRqCampo.ENVIADO else None,
                    fecha_firma=datetime.now() - timedelta(days=1) if r_info["estado"] == EstadoRqCampo.ENVIADO else None,
                    fecha_envio=datetime.now() - timedelta(days=1) if r_info["estado"] == EstadoRqCampo.ENVIADO else None,
                )
                for pos, it_info in enumerate(r_info["items"], 1):
                    codigo = it_info[0]
                    cant = it_info[1]
                    estado_it = it_info[2]
                    if codigo.startswith("NO-CAT"):
                        nombre_prod = it_info[3]
                        unidad = it_info[4]
                        item = RqCampoItem(
                            numero_item=pos,
                            tipo=TipoItemRqCampo.NO_CATALOGADO,
                            codigo_producto=codigo,
                            nombre_producto=nombre_prod,
                            unidad_medida=unidad,
                            cantidad=cant,
                            descripcion="Ítem de campo sin stock en almacén, requiere compra urgente.",
                        )
                    else:
                        art = db.query(AlmacenArticulo).filter(AlmacenArticulo.codigo_excel == codigo).first()
                        if not art:
                            continue
                        item = RqCampoItem(
                            numero_item=pos,
                            tipo=TipoItemRqCampo.CATALOGADO,
                            articulo_id=art.id,
                            codigo_producto=art.codigo_excel,
                            nombre_producto=art.nombre,
                            unidad_medida=art.unidad_medida,
                            cantidad=cant,
                            descripcion=art.descripcion,
                        )
                    if estado_it != EstadoItemRq.PENDIENTE:
                        item.seguimiento = RqCampoItemSeguimiento(
                            estado=estado_it.value,
                            nota="Revisión de logística y compras para demo",
                            actualizado_por_id=r_info["creador"].id,
                            actualizado_en=datetime.utcnow(),
                        )
                    rq.items.append(item)
                db.add(rq)
            else:
                rq.estado = r_info["estado"]
        db.commit()

        # 5. PRÉSTAMOS REALISTAS
        print("Cargando préstamos de almacén...")
        art_taladro = db.query(AlmacenArticulo).filter(AlmacenArticulo.codigo_excel == "DEMO-HR-001").first()
        art_mano = db.query(AlmacenArticulo).filter(AlmacenArticulo.codigo_excel == "DEMO-EQ-001").first()
        art_soldar = db.query(AlmacenArticulo).filter(AlmacenArticulo.codigo_excel == "DEMO-EQ-004").first()
        art_amoladora = db.query(AlmacenArticulo).filter(AlmacenArticulo.codigo_excel == "DEMO-HR-002").first()
        art_stillson = db.query(AlmacenArticulo).filter(AlmacenArticulo.codigo_excel == "DEMO-HR-003").first()

        # Préstamo 1: Activo para Juan Pérez (Pulmón de Aire)
        p1 = db.query(AlmacenPrestamo).filter(AlmacenPrestamo.codigo_unico == "PRE-2026-001").first()
        if not p1 and juan and carlos and art_taladro and art_mano and obra_pulmon:
            p1 = AlmacenPrestamo(
                trabajador_id=juan.id,
                almacenero_id=carlos.id,
                obra_id=obra_pulmon.id,
                codigo_unico="PRE-2026-001",
                fecha_prestamo=datetime.now() - timedelta(days=2),
                fecha_devolucion_prevista=datetime.now() + timedelta(days=5),
                firma_base64=firma_demo,
                estado=EstadoPrestamo.ABIERTO,
                registrado_por="Carlos Mamani Almacén",
                tipo_prestamo=TipoPrestamo.INTERNO,
            )
            db.add(p1)
            db.flush()
            db.add_all([
                AlmacenPrestamoDetalle(prestamo_id=p1.id, articulo_id=art_taladro.id, cantidad_prestada=1, cantidad_devuelta=0, esta_devuelto=False),
                AlmacenPrestamoDetalle(prestamo_id=p1.id, articulo_id=art_mano.id, cantidad_prestada=2, cantidad_devuelta=0, esta_devuelto=False),
            ])
            art_taladro.en_prestamo = 1
            art_taladro.stock_actual = max(0, art_taladro.stock_total - 1)
            art_mano.en_prestamo = 2
            art_mano.stock_actual = max(0, art_mano.stock_total - 2)

        # Préstamo 2: Activo para Pedro Condori (Ampliación de Planta)
        p2 = db.query(AlmacenPrestamo).filter(AlmacenPrestamo.codigo_unico == "PRE-2026-002").first()
        if not p2 and pedro and carlos and art_soldar and art_amoladora and obra_planta:
            p2 = AlmacenPrestamo(
                trabajador_id=pedro.id,
                almacenero_id=carlos.id,
                obra_id=obra_planta.id,
                codigo_unico="PRE-2026-002",
                fecha_prestamo=datetime.now() - timedelta(hours=6),
                fecha_devolucion_prevista=datetime.now() + timedelta(days=3),
                firma_base64=firma_demo,
                estado=EstadoPrestamo.ABIERTO,
                registrado_por="Carlos Mamani Almacén",
                tipo_prestamo=TipoPrestamo.INTERNO,
            )
            db.add(p2)
            db.flush()
            db.add_all([
                AlmacenPrestamoDetalle(prestamo_id=p2.id, articulo_id=art_soldar.id, cantidad_prestada=1, cantidad_devuelta=0, esta_devuelto=False),
                AlmacenPrestamoDetalle(prestamo_id=p2.id, articulo_id=art_amoladora.id, cantidad_prestada=1, cantidad_devuelta=0, esta_devuelto=False),
            ])
            art_soldar.en_prestamo = 1
            art_soldar.stock_actual = max(0, art_soldar.stock_total - 1)
            art_amoladora.en_prestamo = 1
            art_amoladora.stock_actual = max(0, art_amoladora.stock_total - 1)

        # Préstamo 3: Devuelto / Cerrado (Historial para Devoluciones)
        p3 = db.query(AlmacenPrestamo).filter(AlmacenPrestamo.codigo_unico == "PRE-2026-003").first()
        if not p3 and juan and carlos and art_stillson and obra_pulmon:
            p3 = AlmacenPrestamo(
                trabajador_id=juan.id,
                almacenero_id=carlos.id,
                obra_id=obra_pulmon.id,
                codigo_unico="PRE-2026-003",
                fecha_prestamo=datetime.now() - timedelta(days=7),
                fecha_devolucion_prevista=datetime.now() - timedelta(days=2),
                firma_base64=firma_demo,
                estado=EstadoPrestamo.CERRADO,
                registrado_por="Carlos Mamani Almacén",
                tipo_prestamo=TipoPrestamo.INTERNO,
            )
            db.add(p3)
            db.flush()
            db.add(AlmacenPrestamoDetalle(prestamo_id=p3.id, articulo_id=art_stillson.id, cantidad_prestada=2, cantidad_devuelta=2, esta_devuelto=True))

        db.commit()

        # Resumen final
        u_count = db.query(User).count()
        o_count = db.query(AlmacenObra).count()
        a_count = db.query(AlmacenArticulo).count()
        r_count = db.query(RqCampo).count()
        p_count = db.query(AlmacenPrestamo).count()

        print(
            "\n🚀 ¡BASE DE DATOS SINTÉTICA COMPLETA LISTA!"
            f"\n• {u_count} Usuarios (Admin, Almacén, Logística, y 3 Técnicos)"
            f"\n• {o_count} Obras mineras e industriales activas"
            f"\n• {a_count} Artículos en catálogo con stock real y en préstamo"
            f"\n• {r_count} Requerimientos (Borrador para firma en vivo, Enviados y con ítems Por Comprar)"
            f"\n• {p_count} Préstamos de almacén (Activos y Devueltos para historial)"
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_full()
