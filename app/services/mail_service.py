from __future__ import annotations

import smtplib
import os
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

class MailService:
    def __init__(self):
        self.email_address = os.getenv("MAIL_USER")
        self.email_password = os.getenv("MAIL_PASSWORD")
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

    def enviar_requerimiento(self, destinatario: str, usuario_email: str, ruta_adjunto: str):
        msg = EmailMessage()
        # Asunto claro para Logística
        msg['Subject'] = f"NUEVO RQ - {usuario_email}"
        msg['From'] = self.email_address
        msg['To'] = destinatario
        msg['Reply-To'] = usuario_email 

        msg.set_content(f"""
        Saludos,
        
        Se adjunta el requerimiento generado por el usuario: {usuario_email}
        
        Por favor, revisar el archivo Excel adjunto para procesar el pedido.
        """)

        try:
            with open(ruta_adjunto, 'rb') as f:
                file_data = f.read()
                msg.add_attachment(
                    file_data,
                    maintype='application',
                    subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    filename=os.path.basename(ruta_adjunto)
                )

            # Conexión Segura con Gmail
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as smtp:
                smtp.starttls() 
                smtp.login(self.email_address, self.email_password)
                smtp.send_message(msg)
                print(f"✅ Correo enviado desde {self.email_address} a {destinatario}")
                
        except Exception as e:
            print(f"❌ Error al enviar por Gmail: {e}")
            raise e