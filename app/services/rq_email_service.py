from __future__ import annotations

import os
import base64
import smtplib
from email.message import EmailMessage

from email_validator import EmailNotValidError, validate_email

from app.models.rq_campo import RqCampo


class ConfiguracionEmailError(RuntimeError):
    pass


class RqEmailService:
    @staticmethod
    def destinatarios_por_defecto() -> list[str]:
        raw = os.getenv("RQ_EMAIL_DESTINATARIOS", "")
        return RqEmailService.normalizar_destinatarios(
            [correo.strip() for correo in raw.split(",") if correo.strip()]
        )

    @staticmethod
    def normalizar_destinatarios(destinatarios: list[str]) -> list[str]:
        if len(destinatarios) > 3:
            raise ConfiguracionEmailError("Solo se permiten hasta tres destinatarios")
        resultado = []
        for correo in destinatarios:
            try:
                normalizado = validate_email(correo, check_deliverability=False).normalized
            except EmailNotValidError as exc:
                raise ConfiguracionEmailError(f"Correo destinatario inválido: {correo}") from exc
            if normalizado not in resultado:
                resultado.append(normalizado)
        return resultado

    @staticmethod
    def enviar(rq: RqCampo, destinatarios: list[str], pdf: bytes) -> None:
        host = os.getenv("RQ_SMTP_HOST")
        usuario = os.getenv("RQ_SMTP_USERNAME")
        password = os.getenv("RQ_SMTP_PASSWORD")
        remitente = os.getenv("RQ_SMTP_FROM_EMAIL") or usuario
        puerto = int(os.getenv("RQ_SMTP_PORT", "587"))
        usar_tls = os.getenv("RQ_SMTP_USE_TLS", "true").lower() == "true"
        usar_ssl = os.getenv("RQ_SMTP_USE_SSL", "false").lower() == "true"

        destinatarios = RqEmailService.normalizar_destinatarios(destinatarios)
        if not host or not remitente:
            raise ConfiguracionEmailError("Falta configurar RQ_SMTP_HOST y RQ_SMTP_FROM_EMAIL")
        if bool(usuario) != bool(password):
            raise ConfiguracionEmailError("RQ_SMTP_USERNAME y RQ_SMTP_PASSWORD deben configurarse juntos")
        if not destinatarios:
            raise ConfiguracionEmailError("No se configuraron destinatarios para el requerimiento")

        mensaje = EmailMessage()
        fecha_emision = rq.fecha_requerimiento.strftime("%d/%m/%Y %H:%M")
        mensaje["Subject"] = f"Requerimiento de campo {rq.numero} - {rq.nombre_proyecto}"
        mensaje["From"] = remitente
        mensaje["To"] = ", ".join(destinatarios)
        mensaje.set_content(
            "\n".join([
                f"Se adjunta el requerimiento {rq.numero}, firmado por el solicitante.",
                "",
                f"Proyecto: {rq.nombre_proyecto}",
                f"Solicitante: {rq.solicitante_nombre}",
                f"Cargo: {rq.solicitante_cargo or '-'}",
                f"Fecha y hora de emisión: {fecha_emision}",
            ])
        )
        mensaje.add_attachment(
            pdf,
            maintype="application",
            subtype="pdf",
            filename=f"{rq.numero}.pdf",
        )
        # Las fotos están en el anexo del requerimiento; los PDF se entregan
        # además como archivos originales para que Compras pueda consultarlos.
        for item in getattr(rq, "items", []):
            for adjunto in item.adjuntos:
                if adjunto.tipo_mime == "application/pdf":
                    mensaje.add_attachment(
                        base64.b64decode(adjunto.contenido_base64),
                        maintype="application", subtype="pdf",
                        filename=f"Item-{item.numero_item}-{adjunto.nombre}",
                    )

        cliente_cls = smtplib.SMTP_SSL if usar_ssl else smtplib.SMTP
        with cliente_cls(host, puerto, timeout=30) as cliente:
            if usar_tls and not usar_ssl:
                cliente.starttls()
            if usuario and password:
                cliente.login(usuario, password)
            cliente.send_message(mensaje)
