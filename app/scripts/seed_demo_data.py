"""Carga datos sintéticos de almacén para desarrollo local.

Ejecutar desde la raíz del backend:
    .venv/bin/python -m app.scripts.seed_demo_data

El proceso es idempotente: usa el nombre de la obra y codigo_excel del artículo
para actualizar los registros demo existentes sin duplicarlos.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import app.models  # noqa: F401  # registra todos los modelos y relaciones
from app.database.base import Base
from app.database.connection import SessionLocal, engine
from app.models.almacen_articulo_imagen import AlmacenArticuloImagen  # noqa: F401
from app.models.almacen_articulos import AlmacenArticulo, TipoArticulo
from app.models.almacen_obras import AlmacenObra
from app.models.almacen_prestamo import (
    AlmacenPrestamo,
    AlmacenPrestamoDetalle,
    EstadoPrestamo,
    TipoPrestamo,
)
from app.models.rq_campo import EstadoRqCampo, RqCampo, RqCampoItem, TipoItemRqCampo
from app.models.user import User
from app.security.hashing import Hash


USUARIOS = [
    {
        "nombre": "Admin",
        "apellidos": "Principal",
        "dni": "00000000A",
        "cargo": "Administrador",
        "codigo_unico": "ADMIN-ORBIT",
        "email": "admin@example.com",
        "role": "admin",
    },
    {
        "nombre": "Carlos",
        "apellidos": "Mamani Almacén",
        "dni": "12345678",
        "cargo": "Jefe de Almacén",
        "codigo_unico": "ALM-001",
        "email": "almacenero@example.com",
        "role": "almacenero",
    },
    {
        "nombre": "Juan",
        "apellidos": "Pérez Quispe",
        "dni": "70123456",
        "cargo": "Técnico Mecánico",
        "codigo_unico": "TRAB-001",
        "email": "trabajador@example.com",
        "role": "trabajador",
    },
    {
        "nombre": "María",
        "apellidos": "López Flores",
        "dni": "72345678",
        "cargo": "Coordinadora Logística",
        "codigo_unico": "LOG-001",
        "email": "logistica@example.com",
        "role": "logistica",
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


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    obras_creadas = articulos_creados = requerimientos_creados = usuarios_creados = prestamos_creados = 0

    try:
        # 1. USUARIOS
        for u_data in USUARIOS:
            user = db.query(User).filter(User.email == u_data["email"]).first()
            if user is None:
                user = User(
                    **u_data,
                    password=Hash.get_password_hash("admin123"),
                )
                db.add(user)
                usuarios_creados += 1
            else:
                for k, v in u_data.items():
                    setattr(user, k, v)
        db.commit()

        # 2. OBRAS
        for data in OBRAS:
            obra = db.query(AlmacenObra).filter(AlmacenObra.nombre == data["nombre"]).first()
            if obra is None:
                obra = AlmacenObra(**data)
                db.add(obra)
                obras_creadas += 1
            else:
                for campo, valor in data.items():
                    setattr(obra, campo, valor)

        # 3. ARTÍCULOS
        for codigo, nombre, tipo, categoria, unidad, stock, marca, modelo, descripcion in ARTICULOS:
            articulo = (
                db.query(AlmacenArticulo)
                .filter(AlmacenArticulo.codigo_excel == codigo)
                .first()
            )
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
                "costo_reposicion": Decimal("100.00"),
                "requiere_foto_prestamo": tipo != TipoArticulo.CONSUMIBLE,
                "requiere_foto_devolucion": tipo != TipoArticulo.CONSUMIBLE,
                "es_activo_alto_valor": tipo == TipoArticulo.EQUIPO,
                "activo": True,
                "fecha_baja": None,
            }
            if articulo is None:
                db.add(AlmacenArticulo(**data))
                articulos_creados += 1
            else:
                for campo, valor in data.items():
                    setattr(articulo, campo, valor)

        db.commit()

        # 4. REQUERIMIENTOS
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        obra_principal = db.query(AlmacenObra).filter(AlmacenObra.nombre == "Pulmón de Aire 2025").first()
        if admin and obra_principal:
            demos = [
                (
                    "RQ-DEMO-001",
                    "Materiales para instalación de la línea principal de aire.",
                    [("DEMO-EQ-001", 2), ("DEMO-CS-004", 24), ("DEMO-CS-005", 4)],
                ),
                (
                    "RQ-DEMO-002",
                    "Herramientas y consumibles para montaje en campo.",
                    [("DEMO-HR-001", 1), ("DEMO-HR-002", 2), ("DEMO-CS-008", 12)],
                ),
            ]
            for numero, descripcion, items_demo in demos:
                rq = db.query(RqCampo).filter(RqCampo.numero == numero).first()
                if rq is not None:
                    continue
                rq = RqCampo(
                    numero=numero,
                    obra_id=obra_principal.id,
                    creador_id=admin.id,
                    nombre_proyecto=obra_principal.nombre,
                    solicitante_nombre=f"{admin.nombre} {admin.apellidos}".strip(),
                    solicitante_cargo=admin.cargo,
                    fecha_requerimiento=datetime.now(),
                    descripcion_general=descripcion,
                    estado=EstadoRqCampo.BORRADOR,
                )
                for posicion, (codigo, cantidad) in enumerate(items_demo, 1):
                    articulo = db.query(AlmacenArticulo).filter(AlmacenArticulo.codigo_excel == codigo).one()
                    rq.items.append(RqCampoItem(
                        numero_item=posicion,
                        tipo=TipoItemRqCampo.CATALOGADO,
                        articulo_id=articulo.id,
                        codigo_producto=articulo.codigo_excel,
                        nombre_producto=articulo.nombre,
                        unidad_medida=articulo.unidad_medida,
                        cantidad=cantidad,
                        descripcion=articulo.descripcion,
                        observacion="Dato sintético para pruebas del módulo móvil.",
                    ))
                db.add(rq)
                requerimientos_creados += 1

            db.commit()

        # 5. PRÉSTAMO SINTÉTICO (Para pruebas en la App Móvil)
        trabajador = db.query(User).filter(User.email == "trabajador@example.com").first()
        almacenero = db.query(User).filter(User.email == "almacenero@example.com").first()
        art_taladro = db.query(AlmacenArticulo).filter(AlmacenArticulo.codigo_excel == "DEMO-HR-001").first()
        art_mano = db.query(AlmacenArticulo).filter(AlmacenArticulo.codigo_excel == "DEMO-EQ-001").first()

        if trabajador and almacenero and art_taladro and art_mano and obra_principal:
            prestamo_demo = db.query(AlmacenPrestamo).filter(AlmacenPrestamo.codigo_unico == "PRE-DEMO-001").first()
            if not prestamo_demo:
                prestamo_demo = AlmacenPrestamo(
                    trabajador_id=trabajador.id,
                    almacenero_id=almacenero.id,
                    obra_id=obra_principal.id,
                    codigo_unico="PRE-DEMO-001",
                    fecha_prestamo=datetime.now() - timedelta(days=2),
                    fecha_devolucion_prevista=datetime.now() + timedelta(days=5),
                    firma_base64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5W7FYAAAAASUVORK5CYII=",
                    estado=EstadoPrestamo.ABIERTO,
                    registrado_por="almacenero",
                    tipo_prestamo=TipoPrestamo.INTERNO,
                )
                db.add(prestamo_demo)
                db.flush()

                det1 = AlmacenPrestamoDetalle(
                    prestamo_id=prestamo_demo.id,
                    articulo_id=art_taladro.id,
                    cantidad_prestada=1,
                    cantidad_devuelta=0,
                    esta_devuelto=False,
                )
                det2 = AlmacenPrestamoDetalle(
                    prestamo_id=prestamo_demo.id,
                    articulo_id=art_mano.id,
                    cantidad_prestada=2,
                    cantidad_devuelta=0,
                    esta_devuelto=False,
                )
                db.add_all([det1, det2])
                art_taladro.en_prestamo = 1
                art_taladro.stock_actual = max(0, art_taladro.stock_total - 1)
                art_mano.en_prestamo = 2
                art_mano.stock_actual = max(0, art_mano.stock_total - 2)
                db.commit()
                prestamos_creados += 1

        total_usuarios = db.query(User).count()
        total_obras = db.query(AlmacenObra).count()
        total_articulos = db.query(AlmacenArticulo).count()
        total_requerimientos = db.query(RqCampo).count()
        total_prestamos = db.query(AlmacenPrestamo).count()
        print(
            f"✅ Datos demo listos: {usuarios_creados} usuarios, {obras_creadas} obras, "
            f"{articulos_creados} artículos, {requerimientos_creados} requerimientos y "
            f"{prestamos_creados} préstamos creados.\n"
            f"Totales en BD: {total_usuarios} usuarios, {total_obras} obras, "
            f"{total_articulos} artículos, {total_requerimientos} requerimientos, {total_prestamos} préstamos."
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
