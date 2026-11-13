import base64
import io
from datetime import datetime
from types import SimpleNamespace

import pytest
import pdfplumber
from PIL import Image
from pydantic import ValidationError

from app.database.base import Base
from app.database.connection import SessionLocal, engine
from app.models.almacen_articulos import AlmacenArticulo, TipoArticulo
from app.models.almacen_obras import AlmacenObra
from app.models.rq_campo import EstadoRqCampo
from app.models.user import User
from app.dependencies.auth_dependencies import get_current_user
from app.main import app
from app.schemas.rq_campo import FirmaEnvioRequest, RqCampoCreate
from app.services.rq_campo_pdf_service import generar_pdf
from app.services.rq_campo_service import EnvioRqError, RqCampoService
from app.services.rq_email_service import RqEmailService


def firma_png_base64():
    salida = io.BytesIO()
    Image.new("RGB", (120, 40), "white").save(salida, format="PNG")
    return "data:image/png;base64," + \
        base64.b64encode(salida.getvalue()).decode()


@pytest.fixture()
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    sesion = SessionLocal()
    yield sesion
    sesion.close()


@pytest.fixture()
def escenario(db):
    usuario = User(
        nombre="Ana",
        apellidos="Quispe",
        dni="12345678",
        cargo="Ingeniera",
        email="ana@example.com",
        password="x",
        role="user")
    obra = AlmacenObra(nombre="Pulmón de aire 2025", estado="activo")
    articulo = AlmacenArticulo(
        nombre="Manómetro",
        unidad_medida="UND",
        tipo=TipoArticulo.EQUIPO,
        codigo_excel="EQ-001",
        activo=True)
    db.add_all([usuario, obra, articulo])
    db.commit()
    return usuario, obra, articulo


def datos_rq(obra_id, articulo_id):
    return RqCampoCreate.model_validate({
        "obra_id": obra_id,
        "descripcion_general": "Trabajo de campo",
        "items": [
            {"tipo": "CATALOGADO", "articulo_id": articulo_id, "cantidad": 2},
            {
                "tipo": "NO_CATALOGADO",
                "nombre_producto": "Adaptador",
                "unidad_medida": "UND",
                "cantidad": 1,
            },
        ],
    })


def test_crea_firma_envia_y_genera_pdf(db, escenario, monkeypatch):
    usuario, obra, articulo = escenario
    rq = RqCampoService.crear(db, datos_rq(obra.id, articulo.id), usuario)
    assert rq.numero.startswith("RQ-001-")
    assert rq.estado == EstadoRqCampo.BORRADOR
    assert rq.items[0].nombre_producto == "Manómetro"

    enviados = []
    monkeypatch.setattr(
        "app.services.rq_campo_service.RqEmailService.enviar",
        lambda *args: enviados.append(args))
    rq = RqCampoService.firmar_y_enviar(
        db, rq.id, firma_png_base64(), [
            "a@example.com", "b@example.com", "c@example.com"], usuario)

    assert rq.estado == EstadoRqCampo.ENVIADO
    assert len(enviados) == 1
    assert generar_pdf(rq).startswith(b"%PDF")


def test_pdf_conserva_campos_y_aplica_estilo_corporativo(db, escenario):
    usuario, obra, articulo = escenario
    rq = RqCampoService.crear(db, datos_rq(obra.id, articulo.id), usuario)

    with pdfplumber.open(io.BytesIO(generar_pdf(rq))) as documento:
        pagina = documento.pages[0]
        texto = " ".join(pagina.extract_text().split())

        assert pagina.width > pagina.height
        assert (
            "REQUERIMIENTOS DE MATERIALES, INSUMOS, EQUIPOS "
            "Y HERRAMIENTAS" in texto
        )
        assert rq.numero in texto
        assert obra.nombre in texto
        assert "Manómetro" in texto and "Adaptador" in texto
        assert "DESCRIPCIÓN / JUSTIFICACIÓN GENERAL: Trabajo de campo" in texto
        colores = []
        for rect in pagina.rects:
            if rect["non_stroking_color"]:
                color = tuple(
                    round(componente * 255)
                    for componente in rect["non_stroking_color"]
                )
                colores.append(color)
        assert (23, 54, 93) in colores


def test_fallo_de_correo_conserva_firma_para_reintento(
        db, escenario, monkeypatch):
    usuario, obra, articulo = escenario
    rq = RqCampoService.crear(db, datos_rq(obra.id, articulo.id), usuario)

    def fallar(*_):
        raise OSError("SMTP no disponible")

    monkeypatch.setattr(
        "app.services.rq_campo_service.RqEmailService.enviar",
        fallar)
    with pytest.raises(EnvioRqError):
        RqCampoService.firmar_y_enviar(
            db, rq.id, firma_png_base64(), ["a@example.com"], usuario)

    db.refresh(rq)
    assert rq.estado == EstadoRqCampo.FIRMADO
    assert rq.firma_base64
    assert "SMTP no disponible" in rq.error_envio


def test_solo_acepta_hasta_tres_destinatarios():
    with pytest.raises(ValidationError):
        FirmaEnvioRequest(firma_base64=firma_png_base64(), destinatarios=[
            "a@example.com", "b@example.com", "c@example.com", "d@example.com"
        ])


def test_email_usa_un_solo_mensaje_para_tres_destinatarios(monkeypatch):
    clientes = []

    class SmtpFalso:
        def __init__(self, host, port, timeout):
            self.host, self.port, self.timeout = host, port, timeout
            self.mensajes = []
            clientes.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def starttls(self):
            self.tls = True

        def login(self, usuario, password):
            self.credenciales = usuario, password

        def send_message(self, mensaje):
            self.mensajes.append(mensaje)

    monkeypatch.setenv("RQ_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("RQ_SMTP_PORT", "587")
    monkeypatch.setenv("RQ_SMTP_USERNAME", "origen@example.com")
    monkeypatch.setenv("RQ_SMTP_PASSWORD", "secreto")
    monkeypatch.setenv("RQ_SMTP_FROM_EMAIL", "origen@example.com")
    monkeypatch.setattr(
        "app.services.rq_email_service.smtplib.SMTP",
        SmtpFalso)

    rq = SimpleNamespace(
        numero="RQ-001-2026",
        nombre_proyecto="Obra API",
        solicitante_nombre="Ana Quispe",
        solicitante_cargo="Ingeniera",
        fecha_requerimiento=datetime(2026, 9, 25, 14, 30),
    )
    RqEmailService.enviar(
        rq,
        ["a@example.com", "b@example.com", "c@example.com"],
        b"%PDF-prueba",
    )

    assert len(clientes) == 1
    assert len(clientes[0].mensajes) == 1
    assert clientes[0].mensajes[0]["To"] == (
        "a@example.com, b@example.com, c@example.com"
    )
    cuerpo = clientes[0].mensajes[0].get_body(
        preferencelist=("plain",)).get_content()
    assert "Proyecto: Obra API" in cuerpo
    assert "Solicitante: Ana Quispe" in cuerpo
    assert "Fecha y hora de emisión: 25/09/2026 14:30" in cuerpo


def test_flujo_completo_desde_api(client, db_session, monkeypatch):
    usuario = User(
        nombre="Luis",
        apellidos="Mamani",
        dni="87654321",
        cargo="Ingeniero",
        email="luis@example.com",
        password="x",
        role="trabajador")
    obra = AlmacenObra(nombre="Obra API", estado="activo")
    articulo = AlmacenArticulo(
        nombre="Taladro",
        unidad_medida="UND",
        tipo=TipoArticulo.HERRAMIENTA,
        codigo_excel="HER-001",
        activo=True)
    db_session.add_all([usuario, obra, articulo])
    db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: usuario
    enviados = []
    monkeypatch.setattr(
        "app.services.rq_campo_service.RqEmailService.enviar",
        lambda *args: enviados.append(args))

    respuesta = client.post("/rq-campo",
                            json={"obra_id": obra.id,
                                  "descripcion_general": "Primera versión",
                                  "items": [{"tipo": "CATALOGADO",
                                             "articulo_id": articulo.id,
                                             "cantidad": 2}],
                                  })
    assert respuesta.status_code == 201, respuesta.text
    rq_id = respuesta.json()["id"]
    assert respuesta.json()["estado"] == "BORRADOR"

    assert client.get("/rq-campo").json()[0]["id"] == rq_id
    assert client.get(f"/rq-campo/{rq_id}").status_code == 200

    respuesta = client.put(
        f"/rq-campo/{rq_id}",
        json={
            "obra_id": obra.id,
            "descripcion_general": "Versión <campo> & urgente",
            "items": [{
                "tipo": "NO_CATALOGADO",
                "nombre_producto": "Adaptador",
                "unidad_medida": "UND",
                "cantidad": 3,
                "observacion": (
                    "Texto de observación suficientemente largo para "
                    "comprobar "
                    "el ajuste dentro de la tabla del PDF."
                ),
            }],
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["items"][0]["nombre_producto"] == "Adaptador"

    respuesta = client.post(
        f"/rq-campo/{rq_id}/firmar-y-enviar",
        json={
            "firma_base64": firma_png_base64(),
            "destinatarios": [
                "compras@example.com",
                "logistica@example.com",
                "gerencia@example.com"],
        })
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "ENVIADO"
    assert respuesta.json()["destinatarios"] == [
        "compras@example.com", "logistica@example.com", "gerencia@example.com"
    ]
    assert len(enviados) == 1

    pdf = client.get(f"/rq-campo/{rq_id}/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")

    respuesta = client.post(
        f"/rq-campo/{rq_id}/reenviar",
        json={
            "destinatarios": ["compras@example.com"]})
    assert respuesta.status_code == 200, respuesta.text
    assert len(enviados) == 2

    intruso = User(
        nombre="Otro",
        apellidos="Usuario",
        dni="11223344",
        cargo="Operario",
        email="otro@example.com",
        password="x",
        role="trabajador")
    db_session.add(intruso)
    db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: intruso
    assert client.get(f"/rq-campo/{rq_id}").status_code == 403
    assert client.get("/rq-campo").json() == []
